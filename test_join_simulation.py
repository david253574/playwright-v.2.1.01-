from playwright.sync_api import sync_playwright
import time

# Pick an account
user_data_dir = "./user_data/account 2"
# Pick a community
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
    
    print("Going to:", comm_url)
    page.goto(comm_url, wait_until="domcontentloaded", timeout=60000)
    
    join_btn = page.get_by_role("button", name="Join", exact=False)
    found = False
    for i in range(6):
        time.sleep(2)
        count = join_btn.count()
        print(f"Attempt {i+1}: Found {count} Join buttons.")
        if count > 0:
            for j in range(count):
                vis = join_btn.nth(j).is_visible()
                print(f"  Button {j} visible: {vis}")
                if vis:
                    found = True
                    break
        if found:
            break
            
    if not found:
        page.screenshot(path="sim_fail.png", full_page=True)
        print("Failed. Screenshot saved to sim_fail.png")
    
    context.close()
