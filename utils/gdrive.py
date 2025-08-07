import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path, PurePath

SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDriveAPI:
    def __init__(self, cred_path=None, token_path=None):
        base_dir = Path(__file__).parent.parent
        self.cred_path = str(cred_path or (base_dir / 'credentials.json'))
        self.token_path = str(token_path or (base_dir / 'token.json'))
        self.creds = None
        self.service = self._authorize()

    def _authorize(self):
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.cred_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        return build('drive', 'v3', credentials=self.creds)

    def upload_file(self, file_path, folder_id=None, overwrite=True, drive_filename=None):
        filename = drive_filename if drive_filename else os.path.basename(file_path)
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        media = MediaFileUpload(file_path, resumable=True)
        # Overwrite if exists
        if overwrite and folder_id:
            existing = self.find_file(filename, folder_id)
            if existing:
                file_id = existing['id']
                updated = self.service.files().update(fileId=file_id, media_body=media).execute()
                print(f"File '{filename}' updated in Google Drive.")
                return updated.get('id')
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File '{filename}' uploaded to Google Drive.")
        return file.get('id')

    def find_file(self, filename, folder_id):
        safe_filename = self.escape_drive_query_value(filename)
        # Looks for an existing file by name in the specified folder
        query = f"name='{safe_filename}' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        return files[0] if files else None

    def get_or_create_folder(self, path, root_folder_id=None):
        parts = path.strip('/').split('/')
        parent_id = root_folder_id
        for part in parts:
            safe_part = self.escape_drive_query_value(part)
            query = (
                f"mimeType='application/vnd.google-apps.folder' "
                f"and trashed=false "
                f"and name='{safe_part}' "
                f"and '{parent_id}' in parents"
            )
            results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = results.get('files', [])
            if files:
                parent_id = files[0]['id']
            else:
                metadata = {'name': safe_part, 'mimeType': 'application/vnd.google-apps.folder'}
                if parent_id:
                    metadata['parents'] = [parent_id]
                folder = self.service.files().create(body=metadata, fields='id').execute()
                parent_id = folder['id']
        return parent_id

    @staticmethod
    def escape_drive_query_value(value):
        """
        Escapes single quotes in a value for use in a Google Drive API query.
        Leaves Unicode characters as is.
        """
        if not isinstance(value, str):
            value = str(value)
        return value.replace("'", "\\'")
