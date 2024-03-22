# Revit Server BackupManager


## Overview
`BackupManager` is a Python class designed to manage and perform backups of models stored in a Revit Server. It retrieves model paths from a `ModelLocationTable.db3`, determines if each model has been modified within a specified timeframe (default is the last 24 hours), and performs a backup operation if necessary. Additionally, it verifies the success of each backup by checking the modification time of the backed-up files.

## Requirements
- Python 3.6 or higher
- Access to the filesystem and network locations specified in the script
- Proper permissions to read from the source database and write to the target backup location

## Initialization Parameters
- source (str): The root directory path of the source models stored on the local filesystem.
- target (PureWindowsPath): The root directory path of the target backup location. This can be a UNC path for network locations.
- db_location (str): The file path to the SQLite database containing model path information.
- servername (str): The name of the server where the Revit Server is hosted.
- rstoollocation (str): The file path to the Revit Server Tool Command executable used for performing the backup operation.

## Methods
**`run_backup`**

* Initiates the backup process by connecting to the SQLite database, retrieving model paths, and processing each model for backup.
* Logs the start and end of the backup process, along with the number of models processed.

**`backup_model(model_path)`**

* Processes an individual model for backup.
* Parameters:
  * **model_path** (str): The relative path of the model to be backed up.
* Determines if a model should be backed up based on its last modification time and performs the backup operation if necessary.

**`_should_backup(last_edit_datetime)`**

* Checks if a model's last modification time is within the specified timeframe for backing up.
* Parameters:
  * **last_edit_datetime** (datetime): The last modification time of the model.
* Returns True if the model should be backed up; otherwise, False.

**`_perform_backup(model_path, target_path)`**

* Executes the backup operation for a model.
* Parameters:
  * **model_path** (str): The relative path of the model to be backed up.
  * **target_path** (Path): The target path where the backup will be stored.

**`_verify_backup(target_path)`**

* Verifies the success of the backup operation by checking the modification time of the backed-up file.
* Parameters:
  * **target_path** (Path): The path to the backed-up file.

## Usage Example
```
backup_manager = BackupManager(
    source='D:\ProgramData\Autodesk\Revit Server 2022\Projects\',
    target=PureWindowsPath(r'\10.10.11.31\FI-V3-RVT22 (backup)'),
    db_location='D:\ProgramData\Autodesk\Revit Server 2022\Projects\ModelLocationTable.db3',
    servername='FI-V3-RVT22',
    rstoollocation='C:\Program Files\Autodesk\Revit Server 2022\Tools\RevitServerToolCommand\RevitServerTool'
)
backup_manager.run_backup()
```
## Logging
The script logs significant events throughout the backup process, including the start and end of the process, models being backed up, and any errors or issues encountered. Ensure the logging configuration is set appropriately for your environment and needs.
