# Revit Server Backup Project

## Overview
This project is designed to automate the backup of models from an Autodesk Revit Server environment. The script runs daily using Windows Task Scheduler, collecting Revit models from the server and storing them in a target directory with a versioning approach. The project provides flexibility, allowing you to gather additional data related to model activity and user engagement on the Revit Server, which can further be used for visualization and analysis.

The main orientation of this project is towards working with Google Drive or any other storage solution that supports version control to ensure that the backup process maintains a proper history of changes made to the Revit models.

## Features
- **Daily Automated Backup**: A script that runs daily via Windows Task Scheduler to perform automated backups of Revit models.
- **Flexible Backup Options**:
  - **Backup All Models**: Backs up all models available in the Revit Server database.
  - **Backup Edited Models**: Backs up models that were edited in the last 24 hours.
  - **Backup Specific Model**: Backs up a specific model given its path.
- **Model Data Collection**: The script has the potential to collect additional model-related data, including activity metrics and user engagement, which can be visualized.
- **Cloud Integration**: Designed to work with Google Drive or similar cloud storage platforms for version control.

## Requirements
- **Python 3.x**: Make sure you have Python installed.
- **Libraries**: The following libraries are required and can be installed using `pip install -r requirements.txt`:
  - `sqlite3`
  - `shutil`
  - `subprocess`
  - `dataclasses`
  - `logging`
  - `pathlib`
- **Google Drive or Similar Version Control-Enabled Storage**: To ensure versioning of backup files.

## Usage
### Configuration
1. Update `config.json` with your configuration details, including:
   - Source path of the Revit models.
   - Target backup path.
   - Database location of the Revit Server.
   - Revit server name.
   - Path to the RevitServerTool executable.
   - Temporary folder path for intermediate storage.
   - Your Google Drive Root Folder id

### Running the Backup
- **Daily Execution**: The script can be scheduled to run daily using **Windows Task Scheduler**.
- **Manual Execution**: Run the script manually using Python:
  ```sh
  python run_backup.py
  ```
- The backup method (`backup_all_models`, `backup_edited_models`, `backup_specific_model`) is specified in `config.json`.

### Log File
- All backup actions, warnings, and errors are logged in the `logs/revit_backup.log` file for easy monitoring and debugging.

## Example Config File (`config.json`)
```json
{
  "source": "D:\\ProgramData\\Autodesk\\Revit Server 2022\\Projects\\",
  "target": "\\\\10.10.11.31\\FI-V3-RVT22 (backup)",
  "db_location": "D:\\ProgramData\\Autodesk\\Revit Server 2022\\Projects\\ModelLocationTable.db3",
  "servername": "FI-V3-RVT22",
  "rstoollocation": "C:\\Program Files\\Autodesk\\Revit Server 2022\\Tools\\RevitServerToolCommand\\RevitServerTool",
  "temp_folder": "C:\\Temp\\RevitBackup",
  "root_folder_id": "your_google_drive_root_folder_id"
}
```

## Potential Enhancements
- **Model Activity Data Collection**: Enhance the script to collect model activity metrics such as model counts, user engagements, and identify idle models.
- **Data Visualization**: Use free cloud-based tools like Google Looker Studio or Google Sheets for visualizing model data and server statistics.
- **Cloud-Based Version Control**: Integrate with cloud-based version control systems like Google Drive or any similar service that supports keeping a history of changes.

## License
This project is open-source and can be freely modified to suit specific needs. Make sure to acknowledge the author if redistributed.

## Contributing
Feel free to contribute by opening issues or creating pull requests. Suggestions and enhancements are always welcome.

## Contact
If you have questions or need help setting up the project, reach out via email or submit an issue on the project's GitHub repository.
