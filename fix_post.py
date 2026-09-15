with open('app.py', 'r') as f:
    content = f.read()

old_hotkey = """            st.info(f"[{profile['id']}] Engaging global accessibility hotkey...")
            try:
                text_area.focus()
                page.keyboard.press("Control+Enter")
            except Exception as e:
                st.warning(f"Failed to trigger hotkey submission: {e}")"""

new_hotkey = """            st.info(f"[{profile['id']}] Clicking the Post button...")
            try:
                # Wait for any media uploads to finish by checking if the post button is enabled
                post_btn = page.locator('button[data-testid="tweetButton"], button[data-testid="tweetButtonInline"]').last
                post_btn.wait_for(state="visible", timeout=5000)
                
                # Wait up to 15 seconds for the button to become enabled (media uploading)
                for _ in range(15):
                    if not post_btn.is_disabled():
                        break
                    time.sleep(1)
                    
                post_btn.click()
                time.sleep(5)
            except Exception as e:
                st.warning(f"Could not find or click the Post button, falling back to hotkey: {e}")
                page.locator(combined_editor).first.focus()
                page.keyboard.press("Control+Enter")
                time.sleep(5)"""

content = content.replace(old_hotkey, new_hotkey)

with open('app.py', 'w') as f:
    f.write(content)
