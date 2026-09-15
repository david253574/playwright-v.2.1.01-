import re

def fix_script(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # 1. Fix the page.goto to wait for domcontentloaded instead of commit
    content = content.replace(
        'wait_until="commit"',
        'wait_until="domcontentloaded"'
    )

    # 2. Re-insert the logic to wait for the community title, then press 'n'
    # In my previous fix, I replaced the trigger block with:
    # log/st.info("Locating community inline composer...")
    # time.sleep(...)
    
    # We will find this and replace it with a robust trigger block
    if "Locating community inline composer..." in content:
        # App.py pattern
        if "st.info" in content:
            pattern = r'st\.info\(f"\[\{profile\[\'id\'\]\}\] Locating community inline composer\.\.\."\)\s+time\.sleep\(random\.uniform\(2\.0,\s*4\.0\)\)'
            replacement = """st.info(f"[{profile['id']}] Waiting for community context to load...")
            try:
                page.locator('h2[role="heading"]').first.wait_for(state="visible", timeout=15000)
            except: pass
            time.sleep(random.uniform(3.0, 5.0))
            
            st.info(f"[{profile['id']}] Triggering compose modal...")
            page.keyboard.press('n')
            time.sleep(random.uniform(2.0, 4.0))"""
            content = re.sub(pattern, replacement, content)
        # Background worker pattern
        else:
            pattern = r'log\(f"\[\{profile\[\'id\'\]\}\] Locating community inline composer\.\.\."\)\s+time\.sleep\(random\.uniform\(2\.0,\s*4\.0\)\)'
            replacement = """log(f"[{profile['id']}] Waiting for community context to load...")
            try:
                page.locator('h2[role="heading"]').first.wait_for(state="visible", timeout=15000)
            except: pass
            time.sleep(random.uniform(3.0, 5.0))
            
            log(f"[{profile['id']}] Triggering compose modal...")
            page.keyboard.press('n')
            time.sleep(random.uniform(2.0, 4.0))"""
            content = re.sub(pattern, replacement, content)

    with open(filepath, "w") as f:
        f.write(content)

fix_script("app.py")
fix_script("background_worker.py")
print("Composer trigger fixed")
