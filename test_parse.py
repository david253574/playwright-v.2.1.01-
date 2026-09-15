import json
from datetime import datetime, timezone

dt_str = "2026-07-19T19:23:41.558Z"
dt_str = dt_str.replace('Z', '+00:00')
msg_time = datetime.fromisoformat(dt_str)
now_utc = datetime.now(timezone.utc)
diff = now_utc - msg_time
print(f"Seconds diff: {diff.total_seconds()}")
print(f"Hours: {diff.total_seconds() / 3600}")
