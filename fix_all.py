import re

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Fix 1: Strip notifications from title
    pattern1 = r"community_name\s*=\s*full_title\.split\(' / X'\)\[0\]\.replace\(' Community',\s*''\)\.strip\(\)"
    # Use raw string for the replacement properly or double escape
    replacement1 = "import re\n            raw_name = full_title.split(' / X')[0].replace(' Community', '').strip()\n            community_name = re.sub(r'^\\\\(\\\\d+\\\\+?\\\\)\\\\s*', '', raw_name)"
    content = re.sub(pattern1, replacement1, content)
    
    # Fix 2: Toast timeout
    pattern2 = r'toast_link\.wait_for\(state="visible", timeout=7000\)'
    replacement2 = 'toast_link.wait_for(state="visible", timeout=15000)'
    content = re.sub(pattern2, replacement2, content)

    # Fix 3: Force close any dropdowns before clicking text area
    pattern3 = r'(editor_selectors\s*=\s*\[)'
    replacement3 = r"""# SAFETY: Press escape once just in case the audience dropdown or any menu stayed open and is blocking the click
            page.keyboard.press('Escape')
            time.sleep(0.5)
            \1"""
    content = re.sub(pattern3, replacement3, content)

    with open(filepath, "w") as f:
        f.write(content)

update_file("app.py")
update_file("background_worker.py")
print("Fixed!")
