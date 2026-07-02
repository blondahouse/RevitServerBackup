# Revit Server Backup Project

## Overview

This project automates backups of models from one or more Autodesk Revit Server instances on the same Windows virtual machine.

The tool can:

- Back up all models.
- Back up only models edited in the last 24 hours.
- Back up one selected model.
- Run against a single `config.json`.
- Run against a folder of configs, one config per Revit Server instance.
- Run against one multi-instance config containing an `instances` array.
- Write a separate log file per Revit Server instance.

The project is designed to work with Google Drive or another versioned storage solution. It can also copy files to a local/network target if `backup_to_target` is enabled.

## Requirements

- Python 3.10 or newer.
- Autodesk Revit Server Tool installed for each Revit Server version you want to back up.
- Google Drive API credentials if `backup_to_gdrive` is enabled.
- Python packages from `requirements.txt`.

Install dependencies:

```bat
pip install -r requirements.txt
```

## Configuration

### Single-instance config

The classic `config.json` format is still supported:

```json
{
  "name": "RVT-25",
  "source": "C:\\ProgramData\\Autodesk\\Revit Server 2025\\Projects",
  "target": "\\\\10.10.40.31\\BIM-Backup\\RVT-25",
  "db_location": "C:\\ProgramData\\Autodesk\\Revit Server 2025\\Projects\\ModelLocationTable.db3",
  "servername": "WIN-UFN5R6U38BF",
  "rstoollocation": "C:\\Program Files\\Autodesk\\Revit Server 2025\\Tools\\RevitServerToolCommand\\RevitServerTool.exe",
  "temp_folder": "C:\\Temp\\RevitBackups\\RVT-25",
  "root_folder_id": "your_google_drive_root_folder_id",
  "mode": "edited",
  "backup_to_target": false,
  "backup_to_gdrive": true
}
```

Required keys:

- `source`
- `target`
- `db_location`
- `servername`
- `rstoollocation`
- `temp_folder`
- `root_folder_id`

Optional keys:

- `name`: instance/log name.
- `mode`: `all`, `edited`, or `selected`.
- `model` or `specific_model`: model path for selected mode.
- `backup_to_target`: copy the created RVT to the configured local/network target. Default: `false`.
- `backup_to_gdrive`: upload the created RVT to Google Drive. Default: `true`.
- `enabled`: set to `false` to skip an instance inside a multi-instance config.

### Multiple separate config files

Create one config per Revit Server instance:

```text
configs/
  rvt_2024.json
  rvt_2025.json
```

Then run:

```bat
python run_backup.py --config-dir configs --mode edited
```

Each config gets its own log file in `logs/<name>.log`.

### Multi-instance config

You can also keep all instances in one JSON file:

```json
{
  "backup_to_target": false,
  "backup_to_gdrive": true,
  "mode": "edited",
  "instances": [
    {
      "name": "RVT-24",
      "source": "C:\\ProgramData\\Autodesk\\Revit Server 2024\\Projects",
      "target": "\\\\10.10.40.31\\BIM-Backup\\RVT-24",
      "db_location": "C:\\ProgramData\\Autodesk\\Revit Server 2024\\Projects\\ModelLocationTable.db3",
      "servername": "YOUR-SERVER-NAME",
      "rstoollocation": "C:\\Program Files\\Autodesk\\Revit Server 2024\\Tools\\RevitServerToolCommand\\RevitServerTool.exe",
      "temp_folder": "C:\\Temp\\RevitBackups\\RVT-24",
      "root_folder_id": "google_drive_root_folder_id_for_rvt_24"
    },
    {
      "name": "RVT-25",
      "source": "C:\\ProgramData\\Autodesk\\Revit Server 2025\\Projects",
      "target": "\\\\10.10.40.31\\BIM-Backup\\RVT-25",
      "db_location": "C:\\ProgramData\\Autodesk\\Revit Server 2025\\Projects\\ModelLocationTable.db3",
      "servername": "YOUR-SERVER-NAME",
      "rstoollocation": "C:\\Program Files\\Autodesk\\Revit Server 2025\\Tools\\RevitServerToolCommand\\RevitServerTool.exe",
      "temp_folder": "C:\\Temp\\RevitBackups\\RVT-25",
      "root_folder_id": "google_drive_root_folder_id_for_rvt_25"
    }
  ]
}
```

Run it like this:

```bat
python run_backup.py --config revit_servers.json
```

Top-level keys are shared defaults. Instance-level keys override them.

## Usage

### Default behavior

This keeps backward compatibility with the old workflow:

```bat
python run_backup.py
```

It uses:

- `config.json`
- `edited` mode, unless `mode` is set in config.

### Back up one instance with explicit mode

```bat
python run_backup.py --config configs\rvt_2025.json --mode edited
python run_backup.py --config configs\rvt_2025.json --mode all
```

### Back up one selected model

```bat
python run_backup.py --config configs\rvt_2025.json --mode selected --model "4174_Project\YDZ_4174_Model.rvt"
```

### Back up all configured instances

```bat
python run_backup.py --config-dir configs --mode edited
```

## Windows Task Scheduler

Recommended task setup:

- Program/script:
  ```text
  C:\Path\To\Python\python.exe
  ```

- Add arguments:
  ```text
  run_backup.py --config-dir configs --mode edited
  ```

- Start in:
  ```text
  C:\Path\To\RevitServerBackup
  ```

This replaces multiple edited `.bat` files with one stable scheduled task and per-instance JSON configs.

A `.bat` wrapper is still acceptable if you want a double-click launcher or need to set environment variables before Python starts. For long-term maintenance, keep the actual backup behavior in Python arguments/configs rather than by editing code comments.

## Logs

Logs are written to:

```text
logs/<instance-name>.log
```

For example:

```text
logs/RVT-25.log
```

## Notes

- Use a unique `temp_folder` per Revit Server instance, for example `C:\Temp\RevitBackups\RVT-25`.
- The script checks that `RevitServerTool createLocalRvt` actually created a non-empty temporary RVT before upload/copy.
- If `backup_to_target` is disabled, the script no longer verifies the network target path, because no file is expected there.
- If `backup_to_gdrive` is enabled, Google Drive upload uses `credentials.json` and `token.json` from the project root.

## License

This project is open-source and can be freely modified to suit specific needs.
