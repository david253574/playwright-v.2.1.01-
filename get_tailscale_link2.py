import pexpect
import sys
import re

ip = "20.74.251.220"
username = "azureuser"
password = "07058478793David=."

print("Connecting...")
child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {username}@{ip}', encoding='utf-8')
child.expect('password:')
child.sendline(password)
child.expect(r'\$')

print("Wiping Tailscale state to prevent network break...")
child.sendline('sudo rm -f /var/lib/tailscale/tailscaled.state')
i = child.expect(['password for azureuser:', r'\$'])
if i == 0:
    child.sendline(password)
    child.expect(r'\$')

print("Starting tailscaled service...")
child.sendline('sudo systemctl start tailscaled')
child.expect(r'\$')

print("Generating fresh Tailscale login link...")
child.sendline('sudo tailscale up --reset')
i = child.expect([r'To authenticate, visit:\s+(https://login.tailscale.com/a/[a-zA-Z0-9]+)', pexpect.TIMEOUT], timeout=15)
if i == 0:
    print(f"\nTAILSCALE_URL_FOUND: {child.match.group(1)}")
else:
    print("Timeout or no URL found.")
    print(child.before)

child.close()
