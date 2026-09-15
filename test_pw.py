from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content('<div><time datetime="2026">hello</time></div>')
    convo = page.locator('div')
    time_el = convo.locator('time').first
    print(f"Count: {time_el.count()}")
    if time_el.count() > 0:
        print(time_el.get_attribute('datetime'))
    browser.close()
