from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_profile_test",
            executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-features=Translate",
                "--disable-sync"
            ],
            ignore_default_args=["--enable-automation"]
        )
        page = context.new_page()
        print("Navigating...")
        page.goto("https://x.com/i/communities", wait_until="domcontentloaded", timeout=15000)
        print("Done")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'context' in locals():
            context.close()
