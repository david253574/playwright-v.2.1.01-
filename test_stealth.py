from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time

user_data_dir = "./user_data/account1"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path="/usr/bin/google-chrome-stable",
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
        ignore_default_args=["--enable-automation"]
    )
    page = context.new_page()
    try:
        Stealth().apply_stealth_sync(page)
        print("Stealth applied successfully")
    except Exception as e:
        print("Stealth error:", e)
    context.close()
