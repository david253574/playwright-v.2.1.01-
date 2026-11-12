import os
import sys
from patchright.sync_api import sync_playwright

def extract_auth_token_from_cookies(user_data_dir):
    """
    Launches browser in background to extract auth_token from persistent user data directory.
    Cross-platform support for Windows and Linux.
    """
    try:
        if not user_data_dir or not os.path.exists(user_data_dir):
            return ""
        with sync_playwright() as pw:
            kwargs = {
                "user_data_dir": os.path.abspath(user_data_dir),
                "headless": True,
                "args": ["--disable-blink-features=AutomationControlled"]
            }
            if sys.platform == "win32":
                kwargs["channel"] = "chrome"
            else:
                kwargs["channel"] = "chrome"
                
            b = pw.chromium.launch_persistent_context(**kwargs)
            cookies = b.cookies()
            b.close()
            for c in cookies:
                if c.get("name") == "auth_token" and c.get("value"):
                    return c["value"]
    except Exception:
        pass
    return ""
