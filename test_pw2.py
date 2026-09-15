from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content('<div><span>hello</span></div>')
    convo = page.locator('div')
    time_el = convo.locator('time').first
    print(f"Count: {time_el.count()}")
    browser.close()
