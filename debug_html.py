from playwright.sync_api import sync_playwright
import time

user_data_dir = "./user_data/account 2"
comm_url = "https://x.com/i/communities/1855279306299085191"

print("Launching visible browser for inspection...")
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--disable-infobars"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    
    print(f"Navigating to {comm_url}...")
    page.goto(comm_url)
    
    print("Waiting 15 seconds for page to fully load...")
    time.sleep(15)
    
    # Save HTML just in case
    with open("community_debug.html", "w", encoding="utf-8") as f:
        f.write(page.content())
        
    print("\n>>> BROWSER IS READY! <<<")
    print("The browser will remain open for exactly 5 minutes (300 seconds).")
    print("Right-click the 'Join' button, select 'Inspect', and copy the HTML to paste to me.")
    
    time.sleep(300)
    
    print("Time is up. Closing browser.")
    context.close()
