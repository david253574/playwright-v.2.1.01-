import pexpect
import sys
import os

ip = "20.74.251.220"
username = "azureuser"
password = "07058478793David=."
local_path = "/home/david/Desktop/playwright/user_data/"
remote_path = f"{username}@{ip}:~/playwright/user_data/"

print(f"Syncing {local_path} to {remote_path} (Excluding Cache)...")
cmd = f'rsync -avz --exclude="*Cache*" --exclude="*cache*" --exclude="Service Worker" --exclude="Crashpad" -e "ssh -o StrictHostKeyChecking=no" "{local_path}" "{remote_path}"'
child = pexpect.spawn(cmd, encoding='utf-8', timeout=600)

i = child.expect(['password:', pexpect.EOF])
if i == 0:
    child.sendline(password)
    
while True:
    try:
        # Print output as it syncs
        print(child.readline(), end='')
    except pexpect.EOF:
        break
    except pexpect.TIMEOUT:
        print("Timeout reached, still syncing...")
        
child.close()
if child.exitstatus == 0:
    print("Sync completed successfully!")
else:
    print(f"Sync failed with exit status {child.exitstatus}")
