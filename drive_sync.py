# drive_sync.py
import streamlit as st
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

def init_drive():
    """Initialize Google Drive service using Streamlit secret."""
    # Convert nested AttrDict to a plain dict
    creds_dict = dict(st.secrets["GOOGLE_DRIVE_SERVICE_ACCOUNT"])
    
    # Ensure private_key has proper newlines
    creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')

    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds)


def upload_db(service, folder_id):
    """Upload local events.db to Google Drive (replace existing one)."""
    file_name = "events.db"
    if not os.path.exists(file_name):
        return False

    # Delete existing file with same name
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{file_name}' and trashed=false",
        fields="files(id)"
    ).execute()

    for f in results.get("files", []):
        service.files().delete(fileId=f["id"]).execute()

    # Upload new file
    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_name, mimetype="application/x-sqlite3")
    service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return True


def download_db(service, folder_id):
    """Download events.db from Google Drive."""
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='events.db' and trashed=false",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])
    if not files:
        return False

    file_id = files[0]["id"]
    request = service.files().get_media(fileId=file_id)
    with io.FileIO("events.db", "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    return True
