import pexpect
import sys

ip = "20.74.251.220"
username = "azureuser"
password = "07058478793David=."

print(f"Connecting to {username}@{ip}...")
child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {username}@{ip}', encoding='utf-8')

child.expect('password:')
child.sendline(password)

# Wait for the prompt
child.expect(r'\$')

print("Running tailscale up...")
child.sendline('sudo tailscale up')

# Handle sudo password prompt if it asks
i = child.expect(['password for azureuser:', r'To authenticate, visit:\s+(https://login.tailscale.com/a/[a-zA-Z0-9]+)'])
if i == 0:
    child.sendline(password)
    child.expect(r'To authenticate, visit:\s+(https://login.tailscale.com/a/[a-zA-Z0-9]+)')

# Extract URL
match = child.match
if match:
    url = match.group(1)
    print(f"\nTAILSCALE_URL_FOUND: {url}")
else:
    print("\nCould not find Tailscale URL. Output:")
    print(child.before)

child.close()
