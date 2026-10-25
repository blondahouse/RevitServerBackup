# Revit Server Backup Project

## Overview

This project automates backups of models from one or more Autodesk Revit Server instances on the same Windows virtual machine.

The tool can:

- Back up all models.
- Back up only models edited in the last 24 hours.
- Back up one selected model.
- Run against a single config file.
- Run multiple Revit Server instances sequentially from a config folder.
- Write a separate log file per Revit Server instance.

The recommended multi-instance workflow uses two folders:

```text
configs/
  active/
  disabled/
  examples/
```

A config placed in `configs/active` is included in the scheduled backup run. A config placed in `configs/disabled` is not run.

There is no `enabled` flag inside the JSON config. Folder placement is the single source of truth for whether a backup is active.

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

### One config per Revit Server instance

Use `configs/examples/revit_server.example.json` as a template:

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
- `mode`: `all`, `edited`, or `selected`. Default: `edited`.
- `model` or `specific_model`: model path for selected mode.
- `backup_to_target`: copy the created RVT to the configured local/network target. Default: `false`.
- `backup_to_gdrive`: upload the created RVT to Google Drive. Default: `true`.

## Active / disabled workflow

Recommended structure:

```text
configs/
  active/
    01_RVT-2023.json
    02_RVT-2024.json
    03_RVT-2025.json

  disabled/
    RVT-2021.json
    RVT-2022.json

  examples/
    revit_server.example.json
```

Only files in `configs/active` are passed to the scheduled multi-instance run.

To disable a backup:

```text
configs/active/02_RVT-2024.json
```

move it to:

```text
configs/disabled/RVT-2024.json
```

To enable it again, move the file back to `configs/active`.

No config values need to be deleted or rewritten.

### Execution order

Config files in the active folder are sorted by filename before execution.

For example:

```text
01_RVT-2023.json
02_RVT-2024.json
03_RVT-2025.json
```

will run sequentially in that order:

```text
RVT-2023
RVT-2024
RVT-2025
```

The backups are not started in parallel.

Using numeric filename prefixes therefore gives simple visual control over execution order.

## Usage

### Recommended multi-instance run

```bat
python run_backup.py --config-dir configs\active
```

Each active JSON file is loaded and executed sequentially.

If one instance fails, the error is logged and the runner continues with the next instance.

To stop on the first error instead:

```bat
python run_backup.py --config-dir configs\active --stop-on-error
```

### Override the mode for all active configs

```bat
python run_backup.py --config-dir configs\active --mode edited
python run_backup.py --config-dir configs\active --mode all
```

The command-line `--mode` overrides the `mode` value inside each config.

### Run one instance manually

```bat
python run_backup.py --config configs\active\03_RVT-2025.json
```

or with an explicit mode:

```bat
python run_backup.py --config configs\active\03_RVT-2025.json --mode all
```

### Back up one selected model

```bat
python run_backup.py --config configs\active\03_RVT-2025.json --mode selected --model "4174_Project\YDZ_4174_Model.rvt"
```

### Backward-compatible default

Running without arguments still uses `config.json` from the project root:

```bat
python run_backup.py
```

This is kept for compatibility with older installations, but the `configs/active` workflow is recommended for multi-instance servers.

## Windows Task Scheduler

The recommended setup is one scheduled task for all Revit Server instances on the VM.

Program/script:

```text
C:\Path\To\Python\python.exe
```

Add arguments:

```text
run_backup.py --config-dir configs\active
```

Start in:

```text
C:\Path\To\RevitServerBackup
```

With this setup:

- Task Scheduler controls **when** the backup sequence starts.
- `configs/active` controls **which** instances run.
- Filename prefixes control **in what order** they run.
- Each JSON config controls **how** its Revit Server instance is backed up.

This avoids having many Task Scheduler jobs that need to be manually spaced apart to prevent overlapping CPU, RAM, disk, or network load.

## Logs

Each instance writes to its own log file:

```text
logs/<instance-name>.log
```

For example:

```text
logs/RVT-2024.log
logs/RVT-2025.log
```

## Git behavior

Operational JSON files inside these folders are ignored by Git:

```text
configs/active/*.json
configs/disabled/*.json
```

This keeps VM-specific server paths and backup state out of repository history while preserving the folder structure in Git.

The reusable template remains version-controlled at:

```text
configs/examples/revit_server.example.json
```

## Notes

- Use a unique `temp_folder` per Revit Server instance, for example `C:\Temp\RevitBackups\RVT-25`.
- The script checks that `RevitServerTool createLocalRvt` actually created a non-empty temporary RVT before upload/copy.
- If `backup_to_target` is disabled, the script does not verify the network target path because no file is expected there.
- If `backup_to_gdrive` is enabled, Google Drive upload uses `credentials.json` and `token.json` from the project root.
- The old single-file `instances` array format is no longer supported. Use one JSON file per Revit Server instance.

## License

This project is open-source and can be freely modified to suit specific needs.
