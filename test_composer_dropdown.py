import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        user_data_dir = "/home/david/Desktop/playwright/user_data/account1"
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1440, "height": 900}
            )
            page = context.new_page()
            
            community_url = "https://x.com/i/communities/1806977501140570599"
            page.goto(community_url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            page.keyboard.press('n')
            time.sleep(3)
            
            audience_btn = page.locator('div[aria-label="Choose audience"], button[aria-label="Choose audience"], div[role="button"][aria-label="Choose audience"]').first
            audience_btn.click()
            time.sleep(3)
            
            menu_items = page.locator('[role="menuitem"]').all_inner_texts()
            print("MENU ITEMS:")
            for m in menu_items:
                print(repr(m))
            
            context.close()
        except Exception as e:
            print("Fatal error:", e)

if __name__ == "__main__":
    run()
