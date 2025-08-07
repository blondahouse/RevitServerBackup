import logging
import json
from backup_manager.backup_manager import BackupManager, BackupConfig

# Set up logging
logging.basicConfig(filename='logs/revit_backup.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Create a BackupManager instance
backup_config = BackupConfig(
    source=config['source'],
    target=config['target'],
    db_location=config['db_location'],
    servername=config['servername'],
    rstoollocation=config['rstoollocation'],
    temp_folder=config['temp_folder'],
    root_folder_id=config['root_folder_id']
)

backup_manager = BackupManager(backup_config)

# Usage Examples:
#
# All models
#backup_manager.backup_all_models()
#
# Edited in 24 hours
backup_manager.backup_edited_models()
#
# Specific model with the path to the model
# specific_model = "4174_MAHDI_AMJAD’S_VILLA\\YDZ_4174_MAHDI AMJAD'S VILLA_new_spa.rvt"
# backup_manager.backup_specific_model(specific_model)