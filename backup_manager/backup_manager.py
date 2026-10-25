import logging
import shutil
import sqlite3
import subprocess
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Optional

from utils.gdrive import GoogleDriveAPI


@dataclass
class BackupConfig:
    source: str
    target: str
    db_location: str
    servername: str
    rstoollocation: str
    temp_folder: str
    root_folder_id: str
    backup_to_target: bool = False
    backup_to_gdrive: bool = True


# noinspection SqlNoDataSourceInspection
class BackupManager:
    LOCATION_QUERY = "SELECT ModelPath FROM 'ModelStorageTable'"
    MAX_DATE_QUERY = "SELECT MAX(Time) FROM 'ModelHistory'"
    MODEL_SUBPATH = Path("Data/Model.db3")
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%SZ"

    def __init__(self, config: BackupConfig):
        """
        Initializes the BackupManager with the provided configuration.
        """
        self.source = Path(config.source)
        self.target = Path(config.target)
        self.temp_folder = Path(config.temp_folder)
        self.root_folder_id = config.root_folder_id
        self.db_location = config.db_location
        self.servername = config.servername
        self.rstoollocation = config.rstoollocation
        self.backup_to_target = config.backup_to_target
        self.backup_to_gdrive = config.backup_to_gdrive

    def set_connection(self, db_path):
        return sqlite3.connect(db_path)

    def backup_all_models(self):
        """
        Backs up all models available in the database.
        """
        logging.info("Backup process started for all models.")
        try:
            with self.set_connection(self.db_location) as connection:
                model_paths = self._get_all_paths(connection)
                logging.info(f"Retrieved {len(model_paths)} model paths for backup.")
                self._backup_selected_models(model_paths)
        except sqlite3.Error as e:
            logging.error(f"Database error in backup process: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in backup process: {e}")
        finally:
            logging.info("Backup process finished.")

    def backup_edited_models(self):
        """
        Backs up models that were edited in the last 24 hours.
        """
        logging.info("Backup process started for edited models.")
        try:
            with self.set_connection(self.db_location) as connection:
                model_paths = self._get_edited_paths(connection)
                logging.info(f"Retrieved {len(model_paths)} edited model paths for backup.")
                self._backup_selected_models(model_paths)
        except sqlite3.Error as e:
            logging.error(f"Database error in backup process: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in backup process: {e}")
        finally:
            logging.info("Backup process finished.")

    def backup_specific_model(self, specific_model):
        """
        Backs up a specific model given its path.

        Parameters:
        specific_model (str): The path of the specific model to be backed up.
        Example: folder_name\\file_name.rvt
        """
        logging.info(f"Backup process started for specific model: {specific_model}")
        try:
            with self.set_connection(self.db_location) as connection:
                model_paths = self._get_specific_path(connection, specific_model)
                if model_paths:
                    logging.info(f"Starting backup for specific model: {model_paths[0]}")
                    self._backup_selected_models(model_paths)
                else:
                    logging.warning(f"Specified model '{specific_model}' not found.")
        except sqlite3.Error as e:
            logging.error(f"Database error retrieving specific model '{specific_model}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error in backup process: {e}")
        finally:
            logging.info("Backup process finished.")

    def _get_all_paths(self, connection):
        """
        Retrieves all model paths from the database.
        """
        try:
            cursor = connection.cursor()
            return [row[0] for row in cursor.execute(self.LOCATION_QUERY)]
        except sqlite3.Error as e:
            logging.error(f"Database error retrieving model paths: {e}")
            return []

    def _get_edited_paths(self, connection):
        """
        Retrieves model paths that were edited in the last 24 hours.
        """
        model_paths = self._get_all_paths(connection)
        edited_paths = []
        for model_path in model_paths:
            try:
                if self._was_edited_in_last_24_hours(model_path):
                    edited_paths.append(model_path)
            except Exception as e:
                logging.error(f"Error checking edit status for model '{model_path}': {e}")
                continue
        return edited_paths

    def _get_specific_path(self, connection, specific_model):
        """
        Retrieves the path for a specific model.
        """
        try:
            cursor = connection.cursor()
            cursor.execute(self.LOCATION_QUERY + " WHERE ModelPath = ?", (specific_model,))
            result = cursor.fetchone()
            if result:
                return [result[0]]
            return []
        except sqlite3.Error as e:
            logging.error(f"Database error retrieving specific model '{specific_model}': {e}")
            return []

    def _was_edited_in_last_24_hours(self, model_path):
        """
        Checks if a model was edited in the last 24 hours.
        """
        try:
            full_model_path = self._get_full_model_path(model_path)
            with self.set_connection(full_model_path) as connection:
                last_edit_datetime = self._get_last_edit_datetime(full_model_path, connection)
                now_date_utc = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
                return (now_date_utc - last_edit_datetime).total_seconds() < 86400
        except sqlite3.Error as e:
            logging.error(f"Database error determining if model '{model_path}' was edited in the last 24 hours: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error determining if model '{model_path}' was edited in the last 24 hours: {e}")
            return False

    def _backup_selected_models(self, model_paths):
        if not model_paths:
            logging.info("No models selected for backup.")
            return

        for model_path in model_paths:
            try:
                self._perform_backup_for_model(model_path)
            except Exception as e:
                logging.error(f"Error during backup for model '{model_path}': {e}")

    def _perform_backup_for_model(self, model_path):
        """
        Performs the backup for a specific model.
        """
        logging.info(f"Starting backup for model: {model_path}")
        start_time = time.time()

        relative_model_path = self._to_relative_path(model_path)
        temp_path = self.temp_folder / relative_model_path
        target_path = self.target / relative_model_path

        try:
            if not self.backup_to_target and not self.backup_to_gdrive:
                logging.warning(
                    "Both backup_to_target and backup_to_gdrive are disabled. "
                    f"Skipping model: {model_path}"
                )
                return

            self._create_temp_rvt(model_path, temp_path, self.rstoollocation, self.servername)
            self._verify_temp_backup(model_path, temp_path)

            if self.backup_to_target:
                self._copy_to_target(model_path, temp_path, target_path)
                self._verify_backup(model_path, target_path)
            else:
                logging.info("Local/network target copy is disabled for this config.")

            if self.backup_to_gdrive:
                self._upload_file_to_gdrive(temp_path, self.root_folder_id, model_path)
            else:
                logging.info("Google Drive upload is disabled for this config.")

            self._clean_temp_folder(self.temp_folder)
            logging.info(f"Backup completed for model: {model_path} in {time.time() - start_time:.2f} seconds")
        except FileNotFoundError as e:
            logging.error(f"File not found during backup operations for '{model_path}': {e}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Subprocess error during backup operations for '{model_path}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error during backup operations for '{model_path}': {e}")

    def _get_full_model_path(self, model_path):
        """
        Constructs the full path to the model database file.
        """
        return self.source / self._to_relative_path(model_path) / self.MODEL_SUBPATH

    def _get_last_edit_datetime(self, full_model_path, connection):
        """
        Retrieves the last edit datetime for a specific model from the database.
        """
        try:
            cursor = connection.cursor()
            last_edit = cursor.execute(self.MAX_DATE_QUERY).fetchone()[0]
            if not last_edit:
                last_edit = "1900-01-01 00:00:00Z"
            return datetime.strptime(last_edit, self.DATETIME_FORMAT)
        except sqlite3.Error as e:
            logging.error(f"Error retrieving last edit time for '{full_model_path}': {e}")
            raise
        except ValueError as e:
            logging.error(f"Error parsing datetime for '{full_model_path}': {e}")
            raise

    @staticmethod
    def _to_relative_path(model_path):
        return Path(*PureWindowsPath(model_path).parts)

    @staticmethod
    def _create_temp_rvt(model_path, temp_path, rstoollocation, servername):
        """
        Creates a temporary Revit file by running the backup subprocess for RevitServerTool.
        """
        logging.info(f"Performing backup for model: {model_path}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    rstoollocation,
                    "createLocalRvt",
                    str(model_path),
                    "-server",
                    servername,
                    "-destination",
                    str(temp_path),
                    "-overwrite",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout:
                logging.info(f"RevitServerTool stdout for '{model_path}': {result.stdout.strip()}")
            if result.stderr:
                logging.warning(f"RevitServerTool stderr for '{model_path}': {result.stderr.strip()}")

            result.check_returncode()
        except Exception as e:
            logging.error(f"Error during backup subprocess for model '{model_path}': {e}")
            raise

    @staticmethod
    def _verify_temp_backup(model_path, temp_path):
        """
        Verifies that RevitServerTool created the temporary RVT file before upload/copy.
        """
        if not temp_path.exists() or not temp_path.is_file():
            raise FileNotFoundError(f"Temporary backup file was not created for '{model_path}': {temp_path}")

        file_size = temp_path.stat().st_size
        if file_size <= 0:
            raise ValueError(f"Temporary backup file is empty for '{model_path}': {temp_path}")

        logging.info(f"Temporary backup file ready: {temp_path} ({file_size} bytes)")

    @staticmethod
    def _copy_to_target(model_path, temp_path, target_path):
        """
        Copies the temporary backup file to the target location.
        """
        try:
            logging.info(f"Copying backup for model: {model_path} to target location")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(temp_path, target_path)
            logging.info(f"Copied backup from temporary location to target: {target_path}")
        except FileNotFoundError as e:
            logging.error(f"File not found during copying for model '{model_path}': {e}")
            raise
        except Exception as e:
            logging.error(f"Error copying backup to target location for model '{model_path}': {e}")
            raise

    @staticmethod
    def _upload_file_to_gdrive(
        source_path,
        drive_root_id,
        drive_relative_path,
        drive_api: Optional[GoogleDriveAPI] = None,
        max_attempts=3,
        wait_seconds=30,
    ):
        """
        Upload a file to Google Drive, creating the necessary folder structure.
        """
        try:
            source = Path(source_path)
            if not source.exists() or not source.is_file():
                logging.error(f"Source file does not exist: {source}")
                raise FileNotFoundError(f"Source file does not exist: {source}")

            if drive_api is None:
                drive_api = GoogleDriveAPI("credentials.json", "token.json")

            rel_path = PureWindowsPath(drive_relative_path)
            folder_parts = rel_path.parts[:-1]
            drive_filename = rel_path.name

            folder_id = drive_root_id
            if folder_parts:
                folder_path = "/".join(folder_parts)
                try:
                    logging.info(
                        f"Preparing to create/find Google Drive folder. "
                        f"Full target path: '{folder_path}', drive_root_id: '{drive_root_id}'"
                    )
                    folder_id = drive_api.get_or_create_folder(folder_path, drive_root_id)
                    logging.info(f"Google Drive folder '{folder_path}' ready (ID: {folder_id})")
                except Exception as e:
                    logging.error(
                        f"Error during get_or_create_folder for path '{folder_path}' "
                        f"under root ID '{drive_root_id}': {e}\n{traceback.format_exc()}"
                    )
                    raise

            for attempt in range(1, max_attempts + 1):
                try:
                    file_id = drive_api.upload_file(
                        str(source),
                        folder_id=folder_id,
                        overwrite=True,
                        drive_filename=drive_filename,
                    )
                    logging.info(
                        f"Uploaded '{source}' to Google Drive as '{drive_filename}' "
                        f"with file ID {file_id}"
                    )
                    break
                except Exception as e:
                    logging.error(f"Upload attempt {attempt} failed: {e}")
                    if attempt < max_attempts:
                        logging.info(f"Retrying in {wait_seconds} seconds...")
                        time.sleep(wait_seconds)
                    else:
                        logging.error("Max upload attempts reached. Upload failed.")
                        raise

        except Exception as e:
            logging.error(f"Error uploading file to Google Drive: {e}")
            raise

    @staticmethod
    def _verify_backup(model_path, target_path):
        """
        Verifies that the backup file exists and was recently updated.
        """
        try:
            if target_path.exists():
                modification_time = datetime.fromtimestamp(target_path.stat().st_mtime, timezone.utc)
                if (datetime.now().astimezone(timezone.utc) - modification_time).total_seconds() < 28800:
                    logging.info(f"Backup successfully updated: {target_path}")
                else:
                    logging.warning(f"Backup file not updated within the last 8 hours: {target_path}")
            else:
                logging.error(f"Backup file does not exist: {target_path}")
        except FileNotFoundError as e:
            logging.error(f"File not found during verification for model '{model_path}': {e}")
            raise
        except Exception as e:
            logging.error(f"Error verifying backup for model '{model_path}': {e}")
            raise

    @staticmethod
    def _clean_temp_folder(temp_folder):
        """
        Cleans up the temporary folder by deleting the specified file or directory.
        """
        try:
            if temp_folder.is_file():
                temp_folder.unlink()
            elif temp_folder.is_dir():
                shutil.rmtree(temp_folder)
            logging.info(f"Temporary folder cleaned up for: {temp_folder}")
        except Exception as e:
            logging.error(f"Error cleaning temporary folder: {e}")
