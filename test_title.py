from playwright.sync_api import sync_playwright
def run():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="/home/david/Desktop/playwright/user_data/account1",
            executable_path="/usr/bin/google-chrome-stable",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        page = context.new_page()
        page.goto("https://x.com/i/communities/1806977501140570599", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("TITLE:", page.title())
        context.close()
run()
