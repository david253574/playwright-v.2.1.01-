import time
import json
from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="/home/david/Desktop/playwright/chrome_profile/account1",
            headless=True
        )
        page = browser.new_page()
        
        page.goto("https://x.com", wait_until="commit")
        
        urls = [
            "https://x.com/i/communities/1971770370664603838",
            "https://x.com/i/communities/1855279306299085191"
        ]
        
        js_code = """
            async (urls) => {
                const fetchPromises = urls.map(async (url) => {
                    try {
                        const response = await fetch(url, {credentials: 'omit'});
                        const html = await response.text();
                        const match = html.match(/<meta[^>]*name="twitter:data1"[^>]*content="([^"]+)"/);
                        if (match && match[1]) {
                            return { url, membersStr: match[1] };
                        }
                        return { url, membersStr: "0" };
                    } catch (e) {
                        return { url, error: e.message };
                    }
                });
                
                return await Promise.all(fetchPromises);
            }
        """
        
        start = time.time()
        results = page.evaluate(js_code, urls)
        print(f"Results: {json.dumps(results, indent=2)} (Took {time.time() - start:.2f}s)")
        
        browser.close()

if __name__ == "__main__":
    test()
