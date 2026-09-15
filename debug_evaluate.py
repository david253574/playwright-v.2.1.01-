import time
import re
from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("https://x.com", wait_until="commit")
        
        html = page.evaluate("""
            async () => {
                const response = await fetch("https://x.com/i/communities/1971770370664603838");
                return await response.text();
            }
        """)
        
        idx = html.lower().find("member")
        if idx != -1:
            print("Found 'member' context:")
            print(html[max(0, idx-100):idx+100])
        else:
            print("No 'member' found.")
            
        # Try finding 'members' as well
        idx = html.lower().find("members")
        if idx != -1:
            print("Found 'members' context:")
            print(html[max(0, idx-100):idx+100])
        
        browser.close()

if __name__ == "__main__":
    test()
