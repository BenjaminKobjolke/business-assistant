"""Interactive RTM OAuth setup — obtains token and stores it in data/rtm_token."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

# Add project root to path so dotenv can find .env
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_project_root / ".env")

import os  # noqa: E402

from rtmilk import AuthorizationSession  # noqa: E402


def main() -> None:
    api_key = os.environ.get("RTM_API_KEY", "")
    shared_secret = os.environ.get("RTM_SHARED_SECRET", "")

    if not api_key or not shared_secret:
        print("ERROR: RTM_API_KEY and RTM_SHARED_SECRET must be set in .env")
        sys.exit(1)

    auth = AuthorizationSession(apiKey=api_key, sharedSecret=shared_secret, perms="delete")

    print(f"Opening browser for RTM authorization:\n  {auth.url}\n")
    webbrowser.open(auth.url)
    input("Press Enter after you have approved the application in the browser...")

    token = auth.Done()

    token_path = _project_root / "data" / "rtm_token"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token, encoding="utf-8")

    print(f"Token saved to {token_path}")


if __name__ == "__main__":
    main()
