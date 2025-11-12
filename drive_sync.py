# drive_sync.py
import streamlit as st
import json
import os
from pydrive2.auth import GoogleAuth, GoogleServiceAccountAuth
from pydrive2.drive import GoogleDrive

def init_drive():
    """Initialize Google Drive client using service account JSON from Streamlit secrets."""
    creds_dict = st.secrets["GOOGLE_DRIVE_SERVICE_ACCOUNT"]

    # Write credentials temporarily
    creds_path = "/tmp/service_account.json"
    with open(creds_path, "w") as f:
        json.dump(creds_dict, f)

    # Authenticate using Service Account
    gauth = GoogleAuth()
    gauth.auth_method = GoogleServiceAccountAuth
    gauth.ServiceAuth(creds_path)
    drive = GoogleDrive(gauth)
    return drive


def upload_db(drive, folder_id=""):
    """Upload the events.db file to Google Drive (replace existing one)."""
    local_path = "events.db"
    if not os.path.exists(local_path):
        return False

    # Delete previous version if exists
    for file in drive.ListFile({'q': f"'{folder_id}' in parents and title='events.db' and trashed=false"}).GetList():
        file.Delete()

    f = drive.CreateFile({'title': 'events.db', 'parents': [{'id': folder_id}]})
    f.SetContentFile(local_path)
    f.Upload()
    return True


def download_db(drive, folder_id=""):
    """Download the events.db file from Google Drive."""
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and title='events.db' and trashed=false"}).GetList()
    if not file_list:
        return False
    file_list[0].GetContentFile("events.db")
    return True
