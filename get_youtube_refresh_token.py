import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_refresh_token():
    client_config = {
        "installed": {
            "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
            "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    
    credentials = flow.run_local_server(port=0)

    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")



get_refresh_token()