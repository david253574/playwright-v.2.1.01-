import json
from app import check_cloudflare_status

try:
    with open('profiles.json', 'r') as f:
        profiles = json.load(f)
        
    print(f"Testing checking for profile {profiles[0]['id']}")
    status = check_cloudflare_status(profiles[0])
    print(f"Status: {status}")
except Exception as e:
    print(f"Error: {e}")
