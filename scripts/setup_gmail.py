#!/usr/bin/env python3
"""Gmail OAuth2 credential setup — run once to authorize Istari to read your Gmail.

Prerequisites:
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create an OAuth 2.0 Client ID (Application type: Desktop app)
  3. Download the JSON file and save it as `credentials.json` in the project root
  4. Enable the Gmail API at https://console.cloud.google.com/apis/library/gmail.googleapis.com
  5. Run this script: python scripts/setup_gmail.py

The script opens a browser for Google sign-in, then saves the token locally.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "gmail_token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        print(f"Error: {CREDENTIALS_PATH} not found.")
        print()
        print("To set up Gmail access:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an OAuth 2.0 Client ID (type: Desktop app)")
        print("  3. Download the JSON and save it as credentials.json in the project root")
        print("  4. Enable the Gmail API at:")
        print("     https://console.cloud.google.com/apis/library/gmail.googleapis.com")
        print("  5. Re-run this script")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Error: google-auth-oauthlib not installed.")
        print("Run: cd backend && pip install -e '.[dev]'")
        sys.exit(1)

    print("Opening browser for Google sign-in...")
    print("(Grant read-only Gmail access when prompted)")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    print(f"Token saved to {TOKEN_PATH}")
    print("Gmail setup complete. Istari can now read your inbox.")


if __name__ == "__main__":
    main()
