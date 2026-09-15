from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time

user_data_dir = "./user_data/account 2"
comm_url = "https://x.com/i/communities/1855279306299085191"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
        ignore_default_args=["--enable-automation"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    Stealth().apply_stealth_sync(page)
    
    print(f"Navigating to {comm_url}")
    page.goto(comm_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(10) # wait for render
    
    page.screenshot(path="debug_community.png")
    print("Screenshot saved to debug_community.png")
    
    buttons = page.get_by_role("button").all()
    print("Buttons found:")
    for b in buttons:
        try:
            print(f" - {b.inner_text()}")
        except:
            pass
            
    context.close()
