import sys

def patch_file(filename, old_str, new_str):
    with open(filename, 'r') as f:
        content = f.read()
    
    if old_str in content and new_str not in content:
        content = content.replace(old_str, new_str)
        with open(filename, 'w') as f:
            f.write(content)
        print(f"Patched {filename}")
    else:
        print(f"Skipped {filename} (already patched or string not found)")

old_stealth = "Stealth().apply_stealth_sync(page)"
new_stealth = 'Stealth().apply_stealth_sync(page)\n            try: page.route("**/*", lambda route: route.abort() if route.request.resource_type == "media" else route.continue_())\n            except: pass'

patch_file("app.py", old_stealth, new_stealth)
patch_file("background_worker.py", old_stealth, new_stealth)

old_new_page = "page = context.new_page()"
new_new_page = 'page = context.new_page()\n            try: page.route("**/*", lambda route: route.abort() if route.request.resource_type == "media" else route.continue_())\n            except: pass'

patch_file("auto_responder_bg.py", old_new_page, new_new_page)
