with open('background_worker.py', 'r') as f:
    content = f.read()

start = content.find('# FORCE the audience to be the community if it defaulted to Everyone')
end = content.find("log(f\"[{profile['id']}] Directing text payload...\")")
print(content[start:end])
