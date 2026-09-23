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
    
    join_btns = page.get_by_role("button", name="Join", exact=True)
    count = join_btns.count()
    print(f"Total 'Join' buttons: {count}")
    for i in range(count):
        print(f"Button {i} visible: {join_btns.nth(i).is_visible()}")
        
    context.close()
