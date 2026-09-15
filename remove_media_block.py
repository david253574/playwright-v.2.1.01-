import os

def remove_media_block(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    target = '            try: page.route("**/*", lambda route: route.abort() if route.request.resource_type == "media" else route.continue_())\n            except: pass\n'
    if target in content:
        content = content.replace(target, '')
        with open(filename, 'w') as f:
            f.write(content)
        print(f"Removed from {filename}")
    else:
        print(f"Not found in {filename}")

remove_media_block("background_worker.py")
remove_media_block("app.py")
remove_media_block("auto_responder_bg.py")
