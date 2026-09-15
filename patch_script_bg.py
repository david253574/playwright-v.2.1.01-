import re
with open('background_worker.py', 'r') as f:
    content = f.read()

start = content.find('page = context.new_page()')
end = content.find('page.goto(', start)
print(content[start:end])
