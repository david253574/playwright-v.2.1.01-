import time
import re
from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        urls = [
            "https://x.com/i/communities/1971770370664603838",
            "https://x.com/i/communities/1855279306299085191"
        ]
        
        for url in urls:
            print(f"Navigating to {url}")
            start = time.time()
            try:
                page.goto(url, wait_until="commit", timeout=20000)
                time.sleep(2)
                body_text = page.locator("body").inner_text()
                matches = re.findall(r'([\d.,]+[KkMm]?)\s*[Mm]embers?', body_text)
                print(f"Matches: {matches} (Took {time.time() - start:.2f}s)")
            except Exception as e:
                print(f"Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    test()
