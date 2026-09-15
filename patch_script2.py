import re
with open('app.py', 'r') as f:
    content = f.read()

start = content.find('st.info("No communities cached yet. Please sync accounts first to populate the cache.")')
end = content.find('# TAB 3: AUTO-RESPONDER', start)
print(content[start:end])
