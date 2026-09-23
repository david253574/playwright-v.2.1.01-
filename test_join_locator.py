from playwright.sync_api import sync_playwright
import time

user_data_dir = "./user_data/account 2"
comm_url = "https://x.com/i/communities/1855279306299085191"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path="/usr/bin/google-chrome-stable",
        headless=False
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(comm_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    
    print("Trying get_by_role('button', name='Join', exact=False)")
    b1 = page.get_by_role("button", name="Join", exact=False)
    print(f"Count: {b1.count()}")
    
    print("Trying locator('button:has-text(\"Join\")')")
    b2 = page.locator('button:has-text("Join")')
    print(f"Count: {b2.count()}")
    
    print("Trying get_by_test_id('joinButton') - just a guess")
    b3 = page.get_by_test_id("joinButton")
    print(f"Count: {b3.count()}")

    context.close()
