from playwright.sync_api import sync_playwright
import time
import json

with open("profiles.json", "r") as f:
    profiles = json.load(f)
    user_data_dir = profiles[0]["user_data_dir"]

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=True
    )
    page = context.new_page()
    page.goto("https://x.com/i/communities/1850206958130720908", wait_until="commit", timeout=60000)
    time.sleep(10)
    
    page.screenshot(path="community_debug.png", full_page=True)
    
    html = page.evaluate('''() => {
        let buttons = document.querySelectorAll('div[role="button"], a[role="link"]');
        return Array.from(buttons).map(b => b.innerText + " | " + b.className).join('\\n');
    }''')
    
    with open("community_buttons.txt", "w") as f:
        f.write(html)
        
    context.close()
