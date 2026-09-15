from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content('<div><span>hello</span></div>')
    print(page.locator('span').is_visible(timeout=1000))
    browser.close()
