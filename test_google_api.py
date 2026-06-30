"""
Standalone diagnostic test for the Google Slides OAuth flow.

Run this first to authenticate and verify the API is working:
    python test_google_api.py

On first run, it will open a browser for you to log in.
Token is saved to credentials/token.json for future runs.
"""
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]

TOKEN_PATH = "credentials/token.json"
CLIENT_SECRET_PATH = "credentials/client_secret.json"

# -------------------------------------------------------
# Step 1: Authenticate via OAuth
# -------------------------------------------------------
creds = None

if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    print(f"Loaded cached token from {TOKEN_PATH}.")

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        print("Token expired. Refreshing automatically...")
        creds.refresh(Request())
    else:
        print("No valid token found. Launching browser for OAuth consent...")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

    os.makedirs("credentials", exist_ok=True)
    with open(TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())
    print(f"Token saved to {TOKEN_PATH}.")

print(f"\nAuthenticated! Token valid: {creds.valid}")

# -------------------------------------------------------
# Step 2: Test Slides API - create a blank presentation
# -------------------------------------------------------
print("\n--- Testing Google Slides API: create_presentation() ---")
try:
    slides_service = build("slides", "v1", credentials=creds)
    presentation = slides_service.presentations().create(body={"title": "OAuth Test Presentation"}).execute()
    pres_id = presentation.get("presentationId")
    print(f"SUCCESS: Presentation created. ID: {pres_id}")

    # -------------------------------------------------------
    # Step 3: Test Drive API - share the presentation
    # -------------------------------------------------------
    print("\n--- Testing Google Drive API: share_presentation() ---")
    drive_service = build("drive", "v3", credentials=creds)
    drive_service.permissions().create(
        fileId=pres_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    url = f"https://docs.google.com/presentation/d/{pres_id}/edit?usp=sharing"
    print(f"SUCCESS: Presentation shared publicly.")
    print(f"\nPresentation URL: {url}")

    # -------------------------------------------------------
    # Step 4: Cleanup - delete test presentation
    # -------------------------------------------------------
    print("\n--- Cleanup: deleting test presentation ---")
    drive_service.files().delete(fileId=pres_id).execute()
    print("SUCCESS: Test presentation deleted.")

except HttpError as exc:
    print(f"STATUS: {exc.status_code}")
    print(f"CONTENT: {exc.content.decode('utf-8', errors='ignore')}")
    raise
