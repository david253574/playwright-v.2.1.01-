import re

def fix_clicks(filepath):
    with open(filepath, "r") as f:
        content = f.read()
        
    # 1. Update human_typing
    # From: element.click()
    # To: element.click(force=True)
    # Be careful not to replace it if it already has force=True
    if "element.click()" in content:
        content = content.replace("element.click()", "element.click(force=True)")
        
    # 2. Update audience_btn.click()
    if "audience_btn.click()" in content:
        content = content.replace("audience_btn.click()", "audience_btn.click(force=True)")
        
    # 3. Update menu_item.click()
    if "menu_item.click()" in content:
        content = content.replace("menu_item.click()", "menu_item.click(force=True)")

    # 4. Update post_btn.click(position=...) to also include force=True
    # The post_btn has: post_btn.click(position={"x": random.randint(10, 40), "y": random.randint(5, 15)})
    pattern = r'(post_btn\.click\(position=\{.*?\}\))'
    content = re.sub(pattern, r'\g<1>.replace(")", ", force=True)")', content) # Wait, regex replace string method is wrong here.
    
    # Let's just do a simpler regex for post_btn
    pattern = r'post_btn\.click\(position=(\{.*?\})\)'
    content = re.sub(pattern, r'post_btn.click(position=\1, force=True)', content)

    with open(filepath, "w") as f:
        f.write(content)

fix_clicks("app.py")
fix_clicks("background_worker.py")
print("Force clicks applied")
