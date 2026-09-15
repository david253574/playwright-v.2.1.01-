import re
with open('app.py', 'r') as f:
    content = f.read()

start = content.find('def fetch_joined_communities_manual')
end = content.find('def process_profile', start)
print(content[start:end])
