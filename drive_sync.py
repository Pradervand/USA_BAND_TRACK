# drive_sync.py
import os
import io
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import streamlit as st

def init_drive():
    """Initialize Google Drive client from Streamlit secret."""
    secrets = json.loads(st.secrets["GOOGLE_DRIVE_SERVICE_ACCOUNT"])
    creds_path = "/tmp/service_account.json"
    with open(creds_path, "w") as f:
        json.dump(secrets, f)

    gauth = GoogleAuth()
    gauth.LoadCredentialsFile(creds_path)
    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    return drive

def download_db(drive, filename="events.db", folder_id=None):
    file_list = drive.ListFile({
        "q": f"'{folder_id}' in parents and title='{filename}' and trashed=false"
    }).GetList()
    if not file_list:
        print("⚠️ No DB file found on Google Drive.")
        return False
    f = file_list[0]
    f.GetContentFile(f"data/{filename}")
    print("✅ Downloaded DB from Google Drive.")
    return True

def upload_db(drive, filename="events.db", folder_id=None):
    path = f"data/{filename}"
    if not os.path.exists(path):
        print("⚠️ Local DB not found, skipping upload.")
        return False

    # Delete any previous version
    file_list = drive.ListFile({
        "q": f"'{folder_id}' in parents and title='{filename}' and trashed=false"
    }).GetList()
    for old_file in file_list:
        old_file.Delete()

    new_file = drive.CreateFile({
        "title": filename,
        "parents": [{"id": folder_id}]
    })
    new_file.SetContentFile(path)
    new_file.Upload()
    print("✅ Uploaded DB to Google Drive.")
    return True
