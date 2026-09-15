import re

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()
        
    # We are going to replace the current trigger logic which starts from:
    # log/st.info("Waiting for community context to load...")
    
    # We will search for the block and replace it.
    
    if "app.py" in filepath:
        log_func = "st.info"
        success_func = "st.success"
        warn_func = "st.warning"
    else:
        log_func = "log"
        success_func = "log"
        warn_func = "log"
        
    # Locate the block we added in our last fix:
    # {log_func}(f"[{profile['id']}] Waiting for community context to load...")
    # ... up to the sleep after pressing 'n'
    
    pattern = r'(?:st\.info|log)\(f"\[\{profile\[\'id\'\]\}\] Waiting for community context to load\.\.\."\).*?time\.sleep\(random\.uniform\(2\.0,\s*4\.0\)\)'
    
    replacement = f"""{log_func}(f"[{{profile['id']}}] Waiting for community page to stabilize...")
            time.sleep(random.uniform(3.0, 5.0))
            
            # Extract community name from page title to force it later
            full_title = page.title()
            community_name = full_title.split(' / X')[0].replace(' Community', '').strip()
            {log_func}(f"[{{profile['id']}}] Identified community as: {{community_name}}")
            
            {log_func}(f"[{{profile['id']}}] Triggering compose modal...")
            page.keyboard.press('n')
            time.sleep(random.uniform(2.0, 4.0))
            
            # FORCE the audience to be the community if it defaulted to Everyone
            try:
                audience_btn = page.locator('div[aria-label="Choose audience"], button[aria-label="Choose audience"], div[role="button"][aria-label="Choose audience"]').first
                if audience_btn.is_visible(timeout=5000):
                    current_audience = audience_btn.inner_text()
                    if "Everyone" in current_audience and community_name:
                        {log_func}(f"[{{profile['id']}}] Audience defaulted to 'Everyone'. Forcing community selection...")
                        audience_btn.click()
                        time.sleep(random.uniform(1.0, 2.0))
                        
                        # Find the menu item containing the community name
                        menu_item = page.locator(f'[role="menuitem"]:has-text("{{community_name}}")').first
                        if menu_item.is_visible(timeout=5000):
                            menu_item.click()
                            time.sleep(random.uniform(0.5, 1.5))
                            {success_func}(f"[{{profile['id']}}] Successfully forced audience to: {{community_name}}")
                        else:
                            {warn_func}(f"[{{profile['id']}}] Could not find '{{community_name}}' in audience dropdown! Aborting to prevent main feed spam.")
                            page.keyboard.press('Escape')
                            return False
                    else:
                        {success_func}(f"[{{profile['id']}}] Audience is correctly set to: {{current_audience}}")
            except Exception as e:
                {warn_func}(f"[{{profile['id']}}] Audience verification skipped/failed: {{e}}")"""
                
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # We must also REMOVE the old "SAFETY NET" block because we just implemented a much better inline one.
    old_safety_net = r'# 2\. SAFETY NET: Check if the audience defaulted to "Everyone".*?except PlaywrightTimeoutError:\s+pass'
    new_content = re.sub(old_safety_net, '', new_content, flags=re.DOTALL)
    
    with open(filepath, "w") as f:
        f.write(new_content)

update_file("app.py")
update_file("background_worker.py")
print("Updated composer logic")
