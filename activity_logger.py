import os
import json
from datetime import datetime

HISTORY_FILE = "history_log.json"

def log_activity(action, account="", status="Info", details=""):
    """
    Appends an activity event to history_log.json so the Manage Accounts dashboard
    displays real-time account lifecycle and automation events.
    """
    try:
        entries = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = []
            except Exception:
                entries = []

        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account": str(account).strip() if account else "System",
            "action": str(action),
            "status": str(status),
            "details": str(details)
        }
        entries.append(entry)

        # Keep last 500 records
        if len(entries) > 500:
            entries = entries[-500:]

        with open(HISTORY_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        print(f"Error logging activity: {e}")
