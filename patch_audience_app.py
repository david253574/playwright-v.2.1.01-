with open('app.py', 'r') as f:
    content = f.read()

start = content.find('# FORCE the audience to be the community if it defaulted to Everyone')
end = content.find("st.info(f\"[{profile['id']}] Directing text payload...\")")
print(content[start:end])
