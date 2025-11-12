# drive_sync.py
import streamlit as st
import json
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

def init_drive():
    """Initialize Google Drive client using a Google service account."""
    creds_dict = st.secrets["GOOGLE_DRIVE_SERVICE_ACCOUNT"]

    # Write credentials to a temp file
    creds_path = "/tmp/service_account.json"
    with open(creds_path, "w") as f:
        json.dump(creds_dict, f)

    # Configure PyDrive2 for service account auth
    gauth = GoogleAuth()
    gauth.settings = {
        "client_config_backend": "service",
        "service_config": {
            "client_json_file_path": creds_path,
        },
    }

    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    return drive


def upload_db(drive, folder_id=""):
    """Upload local events.db to Google Drive."""
    local_path = "events.db"
    if not os.path.exists(local_path):
        return False

    # Delete previous DB versions in folder
    for file in drive.ListFile({'q': f"'{folder_id}' in parents and title='events.db' and trashed=false"}).GetList():
        file.Delete()

    f = drive.CreateFile({'title': 'events.db', 'parents': [{'id': folder_id}]})
    f.SetContentFile(local_path)
    f.Upload()
    return True


def download_db(drive, folder_id=""):
    """Download events.db from Google Drive."""
    files = drive.ListFile({'q': f"'{folder_id}' in parents and title='events.db' and trashed=false"}).GetList()
    if not files:
        return False
    files[0].GetContentFile("events.db")
    return True
