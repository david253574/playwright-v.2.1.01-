import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        user_data_dir = "/home/david/Desktop/playwright/user_data/account1"
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path="/usr/bin/google-chrome-stable",
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            
            # Go to a community
            community_url = "https://x.com/i/communities/1806977501140570599"
            print("Navigating...")
            page.goto(community_url, wait_until="domcontentloaded", timeout=60000)
            
            print("Waiting for heading...")
            try:
                page.locator('h2[role="heading"]').first.wait_for(state="visible", timeout=15000)
            except Exception as e:
                print("Heading not found:", e)
                
            time.sleep(3)
            
            print("Pressing n...")
            page.keyboard.press('n')
            time.sleep(3)
            
            print("Checking audience...")
            audience_btn = page.locator('div[aria-label="Choose audience"], button[aria-label="Choose audience"], div[role="button"][aria-label="Choose audience"]').first
            try:
                if audience_btn.is_visible(timeout=5000):
                    print("Audience text:", audience_btn.inner_text())
                else:
                    print("Could not find Choose audience button.")
                    # Let's dump all button/role=button text in the modal
                    buttons = page.locator('div[role="dialog"] button, div[role="dialog"] [role="button"]').all_inner_texts()
                    print("Modal buttons:", buttons)
            except Exception as e:
                print("Audience error:", e)
                
            context.close()
        except Exception as e:
            print("Fatal error:", e)

if __name__ == "__main__":
    run()
