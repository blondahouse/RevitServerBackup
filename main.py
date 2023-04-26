# loading in modules
import sqlite3
from datetime import datetime, timezone
import subprocess

# Constants

LOCATION_QUERY = """
SELECT ModelPath
FROM 'ModelStorageTable'
"""

MAX_DATE_QUERY = """
SELECT MAX(Time)
FROM 'ModelHistory'
"""

LOCATION = 'C:\\ProgramData\\Autodesk\\Revit Server 2020\\Projects\\ModelLocationTable.db3'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%SZ'
SOURCE = 'C:\\ProgramData\\Autodesk\\Revit Server 2020\\Projects\\'
TARGET = 'X:\\Revit Server 2020\\'
MODEL = '\\Data\\Model.db3'
RSTOOLLOCATION = 'C:\\Program Files\\Autodesk\\Revit Server 2020\\Tools\\RevitServerToolCommand\\RevitServerTool'
SERVERNAME = 'WIN-YOURSERVERNAME'

# connect to ModelLocationTable and request to get all available models
location_connection = sqlite3.connect(LOCATION)
location_cursor = location_connection.cursor()
location_paths = [a[0] for a in location_cursor.execute(LOCATION_QUERY)]
# Be sure to close the connection
location_connection.close()

# Get date difference between now and last edit date in days
for location_path in location_paths:
    model_path = SOURCE + location_path + MODEL
    # connect and request
    model_connection = sqlite3.connect(model_path)
    model_cursor = sqlite3.connect(model_path).cursor()
    model_date = model_cursor.execute(MAX_DATE_QUERY).fetchone()[0]
    # Be sure to close the connection
    model_connection.close()
    # datetime conversion and difference
    model_date_tz = datetime.strptime(model_date, DATETIME_FORMAT).astimezone(timezone.utc).replace(tzinfo=None)
    model_delta = datetime.now() - model_date_tz

    # create backup
    t = [
        RSTOOLLOCATION, "createLocalRvt", location_path,
        "-server", SERVERNAME,
        "-destination", TARGET + location_path, "-overwrite"]
    result = subprocess.run(t, capture_output=True)
