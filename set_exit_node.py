import pexpect
import sys

ip = "20.74.251.220"
username = "azureuser"
password = "07058478793David=."
exit_node = "100.103.157.41"

print("Connecting...")
child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {username}@{ip}', encoding='utf-8')
child.expect('password:')
child.sendline(password)
child.expect(r'\$')

print(f"Setting exit node to {exit_node}...")
child.sendline(f'sudo tailscale up --exit-node={exit_node} --accept-routes')
i = child.expect(['password for azureuser:', r'\$'], timeout=5)
if i == 0:
    child.sendline(password)
    # Don't wait for prompt, network will drop!
    
print("Command sent. (Connection drop expected)")
child.close()
