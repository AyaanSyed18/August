import os
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/chat.spaces.readonly"
]

def get_creds(scopes: Optional[List[str]] = None, token_file: str = "token.json", credentials_file: str = "credentials.json") -> Credentials:
    """Generic helper to get Google API credentials."""
    if scopes is None:
        scopes = SCOPES
        
    creds: Optional[Credentials] = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds or not creds.valid:
            try:
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(f"Missing {credentials_file}. Please download it from the Google Cloud Console.")
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"\n[bold red]AUTHENTICATION ERROR:[/bold red] {e}")
                print("1. Ensure 'credentials.json' is in the project root.")
                print("2. Check your internet connection.")
                print("3. Ensure the Google Cloud Project has the required APIs enabled.\n")
                raise

        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return creds
