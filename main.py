import sqlite3
from datetime import datetime, timezone
import subprocess
import logging
from pathlib import Path, PureWindowsPath


def _verify_backup(target_path):
    if target_path.exists():
        modification_time = datetime.fromtimestamp(target_path.stat().st_mtime, timezone.utc)
        if (datetime.now().astimezone(timezone.utc) - modification_time).total_seconds() < 28800:  # 8 hours
            logging.info(f"Backup successfully updated: {target_path}")
        else:
            logging.error(f"Backup file not updated within the last 8 hours: {target_path}")
    else:
        logging.error(f"Backup file does not exist: {target_path}")


class BackupManager:
    def __init__(self, source, target, db_location, servername, rstoollocation):
        self.source = source
        self.target = Path(target)
        self.db_location = db_location
        self.servername = servername
        self.rstoollocation = rstoollocation
        self.location_query = "SELECT ModelPath FROM 'ModelStorageTable'"
        self.max_date_query = "SELECT MAX(Time) FROM 'ModelHistory'"
        self.model_subpath = '\\Data\\Model.db3'
        self.datetime_format = '%Y-%m-%d %H:%M:%SZ'

    def run_backup(self):
        logging.info("Backup process started.")
        try:
            with sqlite3.connect(self.db_location) as connection:
                cursor = connection.cursor()
                model_paths = [row[0] for row in cursor.execute(self.location_query)]
                logging.info(f"Retrieved {len(model_paths)} model paths for backup.")
                for model_path in model_paths:
                    self.backup_model(model_path)
        except Exception as e:
            logging.error(f"Error in backup process: {e}")
        finally:
            logging.info("Backup process finished.")

    def backup_model(self, model_path):
        full_model_path = self.source + model_path + self.model_subpath
        target_path = self.target / model_path
        try:
            with sqlite3.connect(str(full_model_path)) as model_connection:
                cursor = model_connection.cursor()
                last_edit = cursor.execute(self.max_date_query).fetchone()[0]
                last_edit_datetime = datetime.strptime(last_edit, self.datetime_format)

                if self._should_backup(last_edit_datetime):
                    self._perform_backup(model_path, target_path)
                    _verify_backup(target_path)
        except Exception as e:
            logging.error(f"Error processing model at {full_model_path}: {e}")

    def _should_backup(self, last_edit_datetime):
        now_date_utc = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
        return (now_date_utc - last_edit_datetime).total_seconds() < 86400  # 24 hours

    def _perform_backup(self, model_path, target_path):
        logging.info(f"Backing up: {model_path}")
        subprocess.run([
            self.rstoollocation, "createLocalRvt", str(model_path),
            "-server", self.servername,
            "-destination", str(target_path), "-overwrite"
        ], capture_output=True)


# Set up logging
logging.basicConfig(filename='backup_log_oop.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

# Create a BackupManager instance and run the backup
backup_manager = BackupManager(
    source='D:\\ProgramData\\Autodesk\\Revit Server 2022\\Projects\\',
    target=PureWindowsPath(r'\\10.10.11.31\FI-V3-RVT22 (backup)'),
    db_location='D:\\ProgramData\\Autodesk\\Revit Server 2022\\Projects\\ModelLocationTable.db3',
    servername='FI-V3-RVT22',
    rstoollocation='C:\\Program Files\\Autodesk\\Revit Server 2022\\Tools\\RevitServerToolCommand\\RevitServerTool'
)
backup_manager.run_backup()
