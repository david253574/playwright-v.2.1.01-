from playwright.sync_api import sync_playwright
import time
import os

user_data_dir = "./user_data/account1"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path="/usr/bin/google-chrome-stable",
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
        ignore_default_args=["--enable-automation"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    
    url = "https://x.com/i/communities/1855279306299085191" # An example community URL
    print(f"Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)
    
    buttons = page.get_by_role("button").all()
    print("Found buttons:")
    for b in buttons:
        try:
            print(" -", b.inner_text())
        except:
            pass
            
    join_btn = page.get_by_role("button", name="Join")
    if join_btn.count() > 0:
        print("Join button found!")
    else:
        print("No join button. Taking screenshot...")
        page.screenshot(path="join_test.png")
        
    context.close()
