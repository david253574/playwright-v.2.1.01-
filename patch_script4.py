import re
with open('app.py', 'r') as f:
    content = f.read()

start = content.find('for idx, c_text in enumerate(comments_to_post):')
end = content.find('except Exception as e:', start)
print(f"Start index: {start}, End index: {end}")
print(content[start:end])
