import os
import json
import time
import random
from playwright.sync_api import sync_playwright

def random_delay(min_seconds=1.0, max_seconds=3.0):
    """Simulate human reading/reaction time."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def process_profile(p, profile):
    print(f"--- Processing profile: {profile['id']} ---")
    
    # Implement CDP Handshake
    # Connect directly to the manually spawned Google Chrome instance on port 9222
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    
    # Refactor Context and State Management
    # CDP uses the existing active browser session
    context = browser.contexts[0]
    context.set_default_navigation_timeout(60000)
    
    # Spawn a fresh tab specifically for this profile's test run
    page = context.new_page()
    
    try:
        # Non-Blocking Navigation State
        page.goto("https://x.com", wait_until="commit")
        
        # Hard pause to let the initial payload construct natively
        time.sleep(5)
        
        # =========================================================
        # INTERACTIVE DIAGNOSTIC PAUSE
        # =========================================================
        print("\n" + "="*60)
        print(f"MANUAL INTERVENTION REQUIRED FOR PROFILE: {profile['id']}")
        print("1. Look at the visible Chrome browser window.")
        print("2. If you see the logged-out splash page, manually click 'Sign in'.")
        print("3. Enter your credentials and solve any CAPTCHAs or 2FA checks.")
        print("4. Wait until the X Dashboard (home timeline) fully loads on the screen.")
        print("5. Return to this terminal and press [ENTER] to continue.")
        print("="*60 + "\n")
        
        # Halt execution pipeline entirely until human confirmation
        input(">>> Press [ENTER] when you are fully logged in and looking at the dashboard...")
        
        print("\nResuming script... Verifying dashboard layout...")
        try:
            # Verify existing session actually hit the dashboard
            page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=15000)
            print("Dashboard confirmed. Session captured and active.")
        except Exception as e:
            page.screenshot(path="debug_error.png")
            raise Exception("Dashboard layout missing when evaluating manual session setup. Saved layout visual to debug_error.png")
        
        random_delay(2, 4)
        
        # --- Post Creation Workflow ---
        print("Testing post creation on dashboard...")
        
        text_area = page.locator('div[data-testid="tweetTextarea_0"]')
        text_area.click()
        random_delay(1, 2)
        
        post_content = profile.get("text_message", "Default automated test post.")
        text_area.press_sequentially(
            post_content,
            delay=random.randint(80, 100)
        )
        random_delay(1, 2)
        
        media_path = profile.get("media_path")
        if media_path:
            # Check if the image file actually exists locally before attempting upload
            if os.path.exists(media_path):
                print(f"Attaching media from path: {media_path}")
                # Locate the hidden file input used for uploads and set the file path
                file_input = page.locator('input[data-testid="fileInput"]')
                file_input.set_input_files(media_path)
                random_delay(3, 5) # wait for the media preview to render
            else:
                print(f"Warning: Image file not found locally. Skipping media upload and posting text-only.")
            
        submit_selector = 'div[data-testid="tweetButtonInline"], div[data-testid="tweetButton"]'
        try:
            page.wait_for_selector(submit_selector, timeout=5000)
            submit_btn = page.locator(submit_selector).first
            submit_btn.click()
            print("Post created successfully via UI button click.")
        except Exception:
            print("Submit button UI node not found. Falling back to global accessibility shortcut...")
            page.keyboard.press("Control+Enter")
            print("Post created successfully via keyboard shortcut.")
            
        random_delay(4, 6)
        
    except Exception as e:
        print(f"An error occurred for profile {profile['id']}: {e}")
        try:
            page.screenshot(path="debug_error.png")
            print("Fallback error state saved to debug_error.png")
        except Exception:
            pass
        
    finally:
        print(f"Finished processing profile: {profile['id']}\n")
        # Graceful CDP Shutdown: Close ONLY this specific tab.
        page.close()
        # Close the connection instance so the next loop can re-establish it safely
        browser.close()

def main():
    try:
        with open("profiles.json", "r") as f:
            profiles = json.load(f)
    except FileNotFoundError:
        print("profiles.json not found. Please create it first.")
        return

    # Keep a single sync_playwright() pipeline active for all loops
    with sync_playwright() as p:
        for profile in profiles:
            process_profile(p, profile)

if __name__ == "__main__":
    main()
