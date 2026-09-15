from playwright.sync_api import sync_playwright

def main():
    print("Launching Chrome...")
    with sync_playwright() as p:
        b = p.chromium.launch_persistent_context(
            user_data_dir='./user_data/account 23',
            executable_path='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = b.new_page()
        page.goto('https://x.com')
        print("Chrome is open! Go to your profile, inspect the HTML, and copy it.")
        input("Press Enter in this terminal window when you are completely done to close Chrome...")

if __name__ == "__main__":
    main()
