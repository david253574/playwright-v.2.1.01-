import re

files_to_patch = ['app.py', 'background_worker.py']

patch_code = """
                                    if "compose/post" in page.url or page.locator('div[data-testid="tweetTextarea_0"]').count() > 0:
                                        log(f"[{profile['id']}] Post seems to have failed (compose modal still open). Skipping comments.")
                                        page.keyboard.press("Escape")
                                        page.wait_for_timeout(1000)
                                        page.keyboard.press("Escape")
                                        raise Exception("Post failed to send. Modal was still open.")
"""
patch_code_app = patch_code.replace('log(f"', 'st.warning(f"')

for file_path in files_to_patch:
    with open(file_path, 'r') as f:
        content = f.read()

    # Find where it says: profile_tab.click(force=True)
    
    if file_path == 'app.py':
        replacement = patch_code_app + "\n                                    profile_tab.click(force=True)"
    else:
        replacement = patch_code + "\n                                    profile_tab.click(force=True)"
        
    content = content.replace("                                    profile_tab.click(force=True)", replacement)

    with open(file_path, 'w') as f:
        f.write(content)

print("Patch applied successfully.")
