import sqlite3
from datetime import datetime, timezone
import logging
from pathlib import Path
from dataclasses import dataclass
import shutil
import subprocess
import time

@dataclass
class BackupConfig:
    source: str
    target: str
    db_location: str
    servername: str
    rstoollocation: str
    temp_folder: str


# noinspection SqlNoDataSourceInspection
class BackupManager:
    LOCATION_QUERY = "SELECT ModelPath FROM 'ModelStorageTable'"
    MAX_DATE_QUERY = "SELECT MAX(Time) FROM 'ModelHistory'"
    MODEL_SUBPATH = Path('Data/Model.db3')
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%SZ'

    def __init__(self, config: BackupConfig):
        """
        Initializes the BackupManager with the provided configuration.

        Parameters:
        config (BackupConfig): Configuration object containing:
        source,
        target,
        database location,
        server name,
        tool location,
        temp folder.
        """
        # self.config = config
        self.source = Path(config.source)
        self.target = Path(config.target)
        self.temp_folder = Path(config.temp_folder)
        self.db_location = config.db_location
        self.servername = config.servername
        self.rstoollocation = config.rstoollocation

    def set_connection(self):
        return sqlite3.connect(self.db_location)

    def backup_all_models(self):
        """
        Backs up all models available in the database.
        """
        logging.info("Backup process started for all models.")
        try:
            with self.set_connection() as connection:
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
            with self.set_connection() as connection:
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
            with self.set_connection() as connection:
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

        Parameters:
        connection (sqlite3.Connection): The SQLite database connection.

        Returns:
        list: A list of model paths.
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

        Parameters:
        connection (sqlite3.Connection): The SQLite database connection.

        Returns:
        list: A list of model paths edited in the last 24 hours.
        """
        model_paths = self._get_all_paths(connection)
        return [model_path for model_path in model_paths if self._was_edited_in_last_24_hours(model_path, connection)]

    def _get_specific_path(self, connection, specific_model):
        """
        Retrieves the path for a specific model.

        Parameters:
        connection (sqlite3.Connection): The SQLite database connection.
        specific_model (str): The path of the specific model to be retrieved.

        Returns:
        list: A list containing the path of the specific model, or an empty list if not found.
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

    def _was_edited_in_last_24_hours(self, model_path, connection):
        """
        Checks if a model was edited in the last 24 hours.

        Parameters:
        model_path (str): The path of the model to be checked.
        connection (sqlite3.Connection): The SQLite database connection.

        Returns:
        bool: True if the model was edited in the last 24 hours, False otherwise.
        """
        try:
            last_edit_datetime = self._get_last_edit_datetime(self._get_full_model_path(model_path), connection)
            now_date_utc = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
            return (now_date_utc - last_edit_datetime).total_seconds() < 86400  # 24 hours
        except sqlite3.Error as e:
            logging.error(f"Database error determining if model '{model_path}' was edited in the last 24 hours: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error determining if model '{model_path}' was edited in the last 24 hours: {e}")
            return False

    def _backup_selected_models(self, model_paths):
        for model_path in model_paths:
            try:
                self._perform_backup_for_model(model_path)
            except Exception as e:
                logging.error(f"Error during backup for model '{model_path}': {e}")

    def _perform_backup_for_model(self, model_path):
        """
        Performs the backup for a specific model.

        Parameters:
        model_path (str): The path of the model to be backed up.
        """
        logging.info(f"Starting backup for model: {model_path}")
        start_time = time.time()
        temp_path = self.temp_folder / model_path
        target_path = self.target / model_path
        try:
            self._create_temp_rvt(model_path, temp_path, self.rstoollocation, self.servername)
            self._copy_to_target(model_path, temp_path, target_path)
            self._verify_backup(model_path, target_path)
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

        Parameters:
        model_path (str): The path of the model.

        Returns:
        Path: The full path to the model database file.
        """
        return self.source / model_path / self.MODEL_SUBPATH

    def _get_last_edit_datetime(self, full_model_path, connection):
        """
        Retrieves the last edit datetime for a specific model from the database.

        Parameters:
        full_model_path (Path): The full path to the model database file.
        connection (sqlite3.Connection): The SQLite database connection.

        Returns:
        datetime: The last edit datetime of the model.

        Raises:
        sqlite3.Error: If there is an error retrieving data from the database.
        ValueError: If there is an error parsing the datetime.
        """
        try:
            cursor = connection.cursor()
            last_edit = cursor.execute(self.MAX_DATE_QUERY).fetchone()[0]
            return datetime.strptime(last_edit, self.DATETIME_FORMAT)
        except sqlite3.Error as e:
            logging.error(f"Error retrieving last edit time for '{full_model_path}': {e}")
            raise
        except ValueError as e:
            logging.error(f"Error parsing datetime for '{full_model_path}': {e}")
            raise

    @staticmethod
    def _create_temp_rvt(model_path, temp_path, rstoollocation, servername):
        """
        Creates a temporary Revit file by running the backup subprocess for RevitServerTool.

        Parameters:
        model_path (str): The path of the model to be backed up.
        temp_path (Path): The temporary path where the backup will be created.
        rstoollocation (str): The location of the RevitServerTool executable.
        servername (str): The name of the Revit server.

        Raises:
        Exception: If there is an error during the subprocess call.
        """
        logging.info(f"Performing backup for model: {model_path}")
        try:
            subprocess.run([
                rstoollocation, "createLocalRvt", str(model_path),
                "-server", servername,
                "-destination", str(temp_path), "-overwrite"
            ], capture_output=True)
        except Exception as e:
            logging.error(f"Error during backup subprocess for model '{model_path}': {e}")
            raise

    @staticmethod
    def _copy_to_target(model_path, temp_path, target_path):
        """
        Copies the temporary backup file to the target location.

        Parameters:
        model_path (str): The path of the model being backed up.
        temp_path (Path): The temporary path of the backup file.
        target_path (Path): The target path where the backup will be copied.

        Raises:
        FileNotFoundError: If the source file to be copied does not exist.
        Exception: If there is an error during the copying process.
        """
        try:
            logging.info(f"Copying backup for model: {model_path} to target location")
            if not target_path.parent.exists():
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
    def _verify_backup(model_path, target_path):
        """
        Verifies that the backup file exists and was recently updated.

        Parameters:
        model_path (str): The path of the model being backed up.
        target_path (Path): The target path where the backup file is located.

        Raises:
        FileNotFoundError: If the target backup file does not exist.
        Exception: If there is an error during verification or if the backup file is outdated.
        """
        try:
            if target_path.exists():
                modification_time = datetime.fromtimestamp(target_path.stat().st_mtime, timezone.utc)
                if (datetime.now().astimezone(timezone.utc) - modification_time).total_seconds() < 28800:  # 8 hours
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

        Parameters:
        temp_folder (Path): The path to the temporary folder or file to be cleaned up.

        Raises:
        Exception: If there is an error during the cleanup process.
        """
        try:
            if temp_folder.is_file():
                temp_folder.unlink()
            elif temp_folder.is_dir():
                shutil.rmtree(temp_folder)
            logging.info(f"Temporary folder cleaned up for: {temp_folder}")
        except Exception as e:
            logging.error(f"Error cleaning temporary folder: {e}")
