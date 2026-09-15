import os
import subprocess
from playwright.sync_api import sync_playwright

os.environ["DISPLAY"] = ":0" # Assuming the user's display is :0

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome-stable",
            headless=False,
            env=os.environ
        )
        page = browser.new_page()
        page.goto("https://google.com")
        print("Successfully opened on :0")
        browser.close()
    except Exception as e:
        print(f"Failed on :0 with error: {e}")

