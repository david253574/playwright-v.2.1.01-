from playwright.sync_api import sync_playwright

def get_community_info(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)
        
        # Try to extract the text from the page
        print("Page title:", page.title())
        # Let's see if we can find members
        import re
        body_text = page.locator("body").inner_text()
        matches = re.findall(r'[\d.,]+[KkMm]?\s*[Mm]embers?', body_text)
        print("Matches:", matches)
        browser.close()

if __name__ == "__main__":
    # Use one of the communities we found in the debug output
    get_community_info("https://x.com/i/communities/1971770370664603838")
