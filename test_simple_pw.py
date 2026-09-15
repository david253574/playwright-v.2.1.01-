from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, executable_path="/usr/bin/google-chrome-stable")
    page = browser.new_page()
    print("Navigating...")
    page.goto("https://x.com/i/communities", wait_until="domcontentloaded", timeout=15000)
    print("Done")
    browser.close()
