#!/usr/bin/env python3
"""Google Calendar OAuth2 credential setup — run once to authorize Istari to read your calendar.

Prerequisites:
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create an OAuth 2.0 Client ID (Application type: Desktop app)
     (You can reuse the same credentials.json as Gmail setup)
  3. Download the JSON file and save it as `credentials.json` in the project root
  4. Enable the Google Calendar API at:
     https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
  5. Run this script: python scripts/setup_calendar.py

The script opens a browser for Google sign-in, then saves the token locally.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "calendar_token.json"

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        print(f"Error: {CREDENTIALS_PATH} not found.")
        print()
        print("To set up Calendar access:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an OAuth 2.0 Client ID (type: Desktop app)")
        print("     (You can reuse the same credentials.json as Gmail setup)")
        print("  3. Download the JSON and save it as credentials.json in the project root")
        print("  4. Enable the Google Calendar API at:")
        print("     https://console.cloud.google.com/apis/library/calendar-json.googleapis.com")
        print("  5. Re-run this script")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Error: google-auth-oauthlib not installed.")
        print("Run: cd backend && pip install -e '.[dev]'")
        sys.exit(1)

    print("Opening browser for Google sign-in...")
    print("(Grant read-only Calendar access when prompted)")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    print(f"Token saved to {TOKEN_PATH}")
    print("Calendar setup complete. Istari can now read your calendar.")


if __name__ == "__main__":
    main()
