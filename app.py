import streamlit as st
import json
import os

with st.sidebar:
    st.header("⚙️ Global Settings")
    config_data = {"block_videos": False}
    if os.path.exists("global_config.json"):
        try:
            with open("global_config.json", "r") as _f:
                config_data = json.load(_f)
        except: pass
        
    block_videos = st.toggle("Block Heavy Media & Ads (Saves 80% Data)", value=config_data.get("block_videos", False), help="Blocks MP4 streams, heavy post images, and background trackers to massively save bandwidth while keeping profile pictures to remain stealthy.")
    
    if block_videos != config_data.get("block_videos", False):
        config_data["block_videos"] = block_videos
        with open("global_config.json", "w") as _f:
            json.dump(config_data, _f)

import json
import os
import random
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

def human_pause(min_seconds: float = 2.0, max_seconds: float = 4.0):
    """Simulates user read-time and layout stability checks."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def is_session_locked(user_data_dir):
    """Checks if the browser profile is currently locked by another process."""
    if not user_data_dir or not os.path.exists(user_data_dir):
        return False
    lock_file = os.path.join(user_data_dir, "SingletonLock")
    if not os.path.exists(lock_file):
        return False
    if sys.platform == "win32":
        try:
            os.remove(lock_file)
            cookie_file = os.path.join(user_data_dir, "SingletonCookie")
            if os.path.exists(cookie_file):
                try: os.remove(cookie_file)
                except Exception: pass
            return False
        except (PermissionError, OSError):
            st.warning("The browser profile is currently in use. Please close all browser windows to continue.")
            return True
    else:
        if os.path.lexists(lock_file):
            try:
                target = os.readlink(lock_file)
                parts = target.rsplit('-', 1)
                if len(parts) == 2:
                    pid = int(parts[1])
                    try:
                        os.kill(pid, 0)
                        st.warning("The browser profile is currently in use. Please close all browser windows to continue.")
                        return True # Process is still alive and locked
                    except OSError:
                        pass # Process is dead, safe to remove lock
                # If we reach here, process is dead or we couldn't parse PID
                try:
                    os.remove(lock_file)
                    cookie_file = os.path.join(user_data_dir, "SingletonCookie")
                    if os.path.lexists(cookie_file):
                        os.remove(cookie_file)
                except: pass
                return False
            except Exception as e:
                try:
                    os.remove(lock_file)
                except: pass
                return False
    return False

def setup_persistent_session(user_data_path, target_login_url="https://x.com"):
    """Launches a visible browser for initial login and waits for the user to close it."""
    with sync_playwright() as p:
        context = None
        if is_session_locked(user_data_path):
            return False, "Browser in use."
            
        try:
            import os
            browser_env = os.environ.copy()
            if sys.platform != "win32":
                browser_env["DISPLAY"] = ":0"  # Force Chrome to the real, visible physical monitor
            
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                channel="chrome",
                headless=False,
                env=browser_env,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-features=Translate",
                    "--disable-sync"
                ],
                viewport={"width": random.choice([1366, 1440, 1920, 1536]), "height": random.choice([768, 900, 1080, 864])},
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            # --- FIX: Relax the strict loading rules for the initial login ---
            try:
                page.goto(target_login_url, wait_until="domcontentloaded", timeout=60000)
            except PlaywrightTimeoutError:
                # Ignore the timeout if background trackers take too long. The page is visible.
                pass
            
            # Script pauses here until the user physically closes the browser tab/window
            page.wait_for_event("close", timeout=0)
            return True, "Session saved successfully!"
        except Exception as e:
            st.error("The browser could not be opened. Please verify that the browser is not already running.")
            return False, f"Setup failed: {str(e)}"
        finally:
            if context:
                try:
                    time.sleep(random.uniform(4.0, 6.5))
                    context.close()
                except:
                    pass

def can_post_to_community(p_id, comm_url, max_daily_posts):
    if max_daily_posts <= 0: return True
    history_file = "daily_post_history.json"
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except: pass
    
    import datetime as dt
    now = dt.datetime.now()
    cutoff = now - dt.timedelta(days=1)
    
    if p_id not in history: return True
    timestamps = history[p_id].get(comm_url, [])
    valid_count = sum(1 for ts in timestamps if dt.datetime.fromisoformat(ts) > cutoff)
    return valid_count < max_daily_posts

def record_community_post(p_id, comm_url):
    history_file = "daily_post_history.json"
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except: pass
    
    if p_id not in history: history[p_id] = {}
    if comm_url not in history[p_id]: history[p_id][comm_url] = []
    
    import datetime as dt
    history[p_id][comm_url].append(dt.datetime.now().isoformat())
    with open(history_file, "w") as f:
        json.dump(history, f)

def force_join_community(profile, comm_url):
    """Navigates directly to a community URL and clicks the Join button if available."""
    user_data_dir = profile.get("user_data_dir")
    
    if is_session_locked(user_data_dir):
        return False, "Browser session is locked by another task. Please close other browser instances."

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
                ignore_default_args=["--enable-automation"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            
            target = comm_url if comm_url.startswith("http") else f"https://x.com{comm_url}"
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            # Dynamically wait for the Join button to render (React apps can be slow)
            # X.com often uses aria-label="Join [Community Name]" and might have hidden buttons.
            join_btns = page.get_by_role("button", name="Join", exact=False)
            joined_btns = page.get_by_role("button", name="Joined", exact=False)
            pending_btns = page.get_by_role("button", name="Pending", exact=False)
            
            found_join = False
            already_member = False
            status_msg = ""
            target_btn = None
            
            for _ in range(15):
                time.sleep(2)
                
                # Check for Cloudflare/Captcha blocks
                if page.locator("text='Verify you are human'").count() > 0 or page.locator("text='Performing security verification'").count() > 0:
                    page.screenshot(path="join_fail_debug.png", full_page=True)
                    context.close()
                    return False, "Blocked by Cloudflare Security Verification! Please use 'Open Visible Browser' to solve the captcha for this account first."
                
                # Check for "Welcome to Communities" modal overlay and dismiss it
                welcome_btn = page.get_by_role("button", name="Check it out", exact=False)
                if welcome_btn.count() > 0 and welcome_btn.first.is_visible():
                    try:
                        welcome_btn.first.click()
                        time.sleep(1)
                    except: pass
                
                vis_joins = join_btns.filter(visible=True)
                if vis_joins.count() > 0:
                    found_join = True
                    target_btn = vis_joins.first
                    break
                    
                if joined_btns.filter(visible=True).count() > 0:
                    already_member = True
                    status_msg = "You are already a member (Joined)."
                    break
                    
                if pending_btns.filter(visible=True).count() > 0:
                    already_member = True
                    status_msg = "Your request is Pending."
                    break
            
            if found_join and target_btn:
                target_btn.click(position={"x": random.randint(5, 20), "y": random.randint(5, 15)})
                time.sleep(4)
                context.close()
                return True, "Successfully joined!"
            elif already_member:
                context.close()
                return False, f"Account is already in this community! ({status_msg})"
            else:
                page.screenshot(path="join_fail_debug.png", full_page=True)
                context.close()
                return False, "Join button not found after 30s wait. X.com might be rate-limiting or loading slowly. (Debug screenshot saved to join_fail_debug.png)"
        except Exception as e:
            if context:
                try:
                    context.close()
                except: pass
            return False, f"Playwright error: {str(e)}"

def fetch_joined_communities(profile):
    """Scrapes joined community metadata with strict filtering."""
    user_data_dir = profile.get("user_data_dir")
    communities = {}
    
    with sync_playwright() as p:
        context = None
        if is_session_locked(user_data_dir):
            return communities
            
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            
            # FIX: Never use networkidle on X. Use "commit" and a hard sleep.
            page.goto("https://x.com/i/communities", wait_until="domcontentloaded", timeout=60000)
            time.sleep(6) # Give React time to paint the UI
            
            # FIX: Restore the sidebar clicker in case X redirects to the homepage
            if "home" in page.url or "compose" in page.url:
                try:
                    page.locator('a[aria-label="Communities"]').first.click()
                    time.sleep(random.uniform(4.0, 6.5))
                except:
                    pass
            
            # Use a more specific locator to avoid navigation buttons, "See more", and hashtag links
            selector = 'a[href*="/i/communities/"]:not([href*="/hashtag/"]):not([href="/i/communities/discover"]):not([href="/i/communities/create"])'
            
            try:
                page.wait_for_selector(selector, timeout=15000, state="attached")
            except:
                pass # Don't crash, let it try to pull anyway
                
            elements = page.locator(selector)
            
            comm_list = []
            for i in range(elements.count()):
                el = elements.nth(i)
                href = el.get_attribute("href")
                # Clean up text: get only the first line, filter out noise
                title = el.inner_text().split("\n")[0].strip()
                
                # STRICT FILTER: Exclude system keywords
                invalid_keywords = ["see more", "communities", "discover", "create", "home", "notifications"]
                if href and title and not any(word in title.lower() for word in invalid_keywords):
                    comm_list.append((title, href))
            
            if comm_list:
                urls_to_fetch = [f"https://x.com{href}" for title, href in comm_list]
                js_code = """
                    async (urls) => {
                        let results = [];
                        const sleep = ms => new Promise(r => setTimeout(r, ms));
                        
                        for (let url of urls) {
                            try {
                                const response = await fetch(url, {credentials: 'omit'});
                                const html = await response.text();
                                const match = html.match(/<meta[^>]*name="twitter:data1"[^>]*content="([^"]+)"/);
                                results.push({ url, count: (match && match[1]) ? match[1] : "0" });
                                
                                // Wait 0.8 to 2 seconds between each fetch
                                await sleep(Math.floor(Math.random() * 1200) + 800); 
                            } catch (e) {
                                results.push({ url, count: "0" });
                            }
                        }
                        return results;
                    }
                """
                try:
                    results = page.evaluate(js_code, urls_to_fetch)
                    counts_dict = {res["url"]: res.get("count", "0") for res in results}
                except Exception as e:
                    counts_dict = {}
                
                for title, href in comm_list:
                    full_url = f"https://x.com{href}"
                    num_str = counts_dict.get(full_url, "0").upper().replace(',', '')
                    members = 0
                    try:
                        if 'K' in num_str:
                            members = int(float(num_str.replace('K', '')) * 1000)
                        elif 'M' in num_str:
                            members = int(float(num_str.replace('M', '')) * 1000000)
                        else:
                            members = int(float(num_str))
                    except ValueError:
                        pass
                    communities[title] = {"url": href, "members": members}
                    
        except Exception as e:
            st.warning(f"Sync failed for {profile['id']}: {e}")
        finally:
            if context: context.close()
            
    return communities if communities else None

def fetch_joined_communities_manual(profile):
    """Scrapes communities with a visible browser and a 60-second delay for manual login/captcha resolution."""
    user_data_dir = profile.get("user_data_dir")
    communities = {}
    
    with sync_playwright() as p:
        context = None
        page = None
        if is_session_locked(user_data_dir):
            return communities
            
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-features=Translate",
                    "--disable-sync"
                ],
                viewport={"width": random.choice([1366, 1440, 1920, 1536]), "height": random.choice([768, 900, 1080, 864])},
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            
            st.info("Opening browser. Please manually navigate to the Communities tab or resolve any login walls.")
            try:
                # Use "commit" so it doesn't wait for heavy background trackers
                page.goto("https://x.com/i/communities", wait_until="domcontentloaded", timeout=60000)
            except PlaywrightTimeoutError:
                # If it still times out, ignore the error and let the 30-second manual UI countdown continue
                pass
            except Exception as e:
                st.warning(f"Network navigation interrupted, but continuing manual fallback... ({e})")
            
            # 60-second wait for manual interaction
            progress = st.progress(0)
            for i in range(60):
                time.sleep(random.uniform(0.8, 1.5))
                progress.progress((i + 1) / 60, text=f"Waiting for manual approval... {60 - i} seconds remaining.")
            
            st.info("Scanning DOM tree...")
            # Use a more specific locator to avoid navigation buttons, "See more", and hashtag links
            selector = 'a[href*="/i/communities/"]:not([href*="/hashtag/"]):not([href="/i/communities/discover"]):not([href="/i/communities/create"])'
            elements = page.locator(selector)
            if elements.count() == 0:
                st.warning("Manual sync failed: No communities found on screen after 60 seconds.")
                
            comm_list = []
            for i in range(elements.count()):
                el = elements.nth(i)
                try:
                    href = el.get_attribute("href")
                    if not href or href.strip() == "/i/communities" or href.strip() == "/i/communities/":
                        continue
                    raw_text = el.inner_text().strip()
                    if not raw_text or "Communities" in raw_text:
                        continue
                    title = raw_text.split("\n")[0]
                    if title and href:
                        comm_list.append((title, href))
                except Exception:
                    continue
            
            if comm_list:
                st.info(f"Found {len(comm_list)} communities. Fetching member counts...")
            if comm_list:
                urls_to_fetch = [f"https://x.com{href}" for title, href in comm_list]
                js_code = """
                    async (urls) => {
                        return await Promise.all(urls.map(async (url) => {
                            try {
                                const response = await fetch(url, {credentials: 'omit'});
                                const html = await response.text();
                                const match = html.match(/<meta[^>]*name="twitter:data1"[^>]*content="([^"]+)"/);
                                return { url, count: (match && match[1]) ? match[1] : "0" };
                            } catch (e) {
                                return { url, count: "0" };
                            }
                        }));
                    }
                """
                try:
                    results = page.evaluate(js_code, urls_to_fetch)
                    counts_dict = {res["url"]: res.get("count", "0") for res in results}
                except Exception as e:
                    counts_dict = {}
                
                for title, href in comm_list:
                    full_url = f"https://x.com{href}"
                    num_str = counts_dict.get(full_url, "0").upper().replace(',', '')
                    members = 0
                    try:
                        if 'K' in num_str:
                            members = int(float(num_str.replace('K', '')) * 1000)
                        elif 'M' in num_str:
                            members = int(float(num_str.replace('M', '')) * 1000000)
                        else:
                            members = int(float(num_str))
                    except ValueError:
                        pass
                    communities[title] = {"url": href, "members": members}
        except Exception as e:
            st.error(f"Manual browser could not be opened: {e}")
        finally:
            if context:
                try:
                    context.close()
                except:
                    pass
    return communities


def check_cloudflare_status(profile):
    """Checks if an account is blocked by Cloudflare Turnstile/Security verification."""
    user_data_dir = profile.get("user_data_dir")
    with sync_playwright() as p:
        if is_session_locked(user_data_dir):
            return "Locked (Skipped)"
            
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-features=Translate",
                    "--disable-sync"
                ],
                viewport={"width": random.choice([1366, 1440, 1920, 1536]), "height": random.choice([768, 900, 1080, 864])},
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            
            try:
                page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=45000)
            except Exception:
                pass
                
            time.sleep(random.uniform(4.0, 6.0))
            
            # Check for various Cloudflare Turnstile / verification signs
            is_blocked = (
                page.locator('text="Performing security verification"').count() > 0 or
                page.locator('#cf-turnstile-response').count() > 0 or
                page.locator('text="This website uses a security service to protect against malicious bots"').count() > 0 or
                page.locator('text="Enable JavaScript and cookies to continue"').count() > 0
            )
            
            return "Blocked" if is_blocked else "OK"
        except Exception as e:
            return f"Error: {e}"
        finally:
            if context:
                try: context.close()
                except: pass

def human_typing(page, selector, text):
    element = page.locator(selector).first
    element.focus()
    element.click(force=True)
    time.sleep(random.uniform(0.5, 1.5))
    for char in text:
        try:
            page.keyboard.press(char)
        except Exception:
            # Fallback for unrecognized characters (like smart quotes)
            page.keyboard.insert_text(char)
            
        if char in [" ", ",", ".", "!", "?", "\n"]:
            time.sleep(random.uniform(0.2, 0.6))
        else:
            time.sleep(random.uniform(0.03, 0.15))

def process_profile(profile, user_tweet_text, uploaded_media_path=None, selected_group_url=None, comment_text=None):
    """Executes the automated posting sequence using headless persistent contexts."""
    user_data_dir = profile.get("user_data_dir")
    
    with sync_playwright() as p:
        context = None
        if is_session_locked(user_data_dir):
            return
            
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-features=Translate",
                    "--disable-sync"
                ],
                viewport={"width": random.choice([1366, 1440, 1920, 1536]), "height": random.choice([768, 900, 1080, 864])},
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            context.set_default_navigation_timeout(60000)
            
            if selected_group_url and selected_group_url.startswith("/i/communities/"):
                page_loaded = False
                for attempt in range(3):
                    try:
                        time.sleep(random.uniform(1.0, 5.0)) # Stagger network requests
                        st.info(f"[{profile['id']}] Navigating to community (Attempt {attempt+1}/3)...")
                        page.goto(f"https://x.com{selected_group_url}", wait_until="domcontentloaded", timeout=60000, referer="https://x.com/home")
                        page_loaded = True
                        break
                    except Exception as e:
                        st.warning(f"[{profile['id']}] Connection error during navigation: {e}")
                        time.sleep(random.uniform(2.0, 4.0))
                
                if not page_loaded:
                    st.error(f"[{profile['id']}] Failed to load community page after 3 attempts. Aborting.")
                    return False
            else:
                st.error(f"Invalid community URL: {selected_group_url}")
                return False
            
            time.sleep(random.uniform(3.0, 5.0))
            
            # --- CAPTCHA / HUMAN VERIFICATION CHECK ---
            try:
                if page.locator('text="Let\'s confirm you are a human"').count() > 0 or \
                   page.locator('text="Scan code with a phone camera to continue"').count() > 0 or \
                   page.locator('text="Confirm you are a human"').count() > 0:
                    st.error(f":material/emergency: HUMAN VERIFICATION DETECTED for {profile['id']} ({profile.get('username', 'Unknown')})!")
                    st.warning("Please scan the QR code below with your phone camera within 3 minutes.")
                    
                    page.screenshot(path=f"captcha_alert_{profile['id']}.png")
                    st.image(f"captcha_alert_{profile['id']}.png")
                    
                    # Also write to file for the global alert just in case
                    import json
                    with open("bot_status.json", "w") as f:
                        json.dump({
                            "status": "captcha_waiting", 
                            "profile": profile['id'],
                            "username": profile.get('username', 'Unknown')
                        }, f)
                    
                    st.info("Pausing for 180 seconds to allow you to scan...")
                    time.sleep(180) # Wait 3 minutes
                    
                    if os.path.exists("bot_status.json"): os.remove("bot_status.json")
                    
                    if page.locator('text="Scan code with a phone camera"').count() > 0:
                        st.error(f"[{profile['id']}] Verification failed or not completed in time. Aborting.")
                        return False
                    else:
                        st.success(f"[{profile['id']}] Verification successful! Continuing...")
                        page.goto(f"https://x.com{selected_group_url}", wait_until="domcontentloaded", timeout=60000)
                        time.sleep(random.uniform(3.0, 5.0))
            except Exception as e:
                pass
            # --- END CAPTCHA CHECK ---
            
            # Check for "Welcome to Communities" modal overlay and dismiss it
            try:
                welcome_btn = page.get_by_role("button", name="Check it out", exact=False)
                if welcome_btn.count() > 0 and welcome_btn.first.is_visible():
                    welcome_btn.first.click()
                    time.sleep(1)
            except: pass

            # 1. Automatically join the community if not a member!
            try:
                join_btns = page.get_by_role("button", name="Join", exact=False).filter(visible=True)
                if join_btns.count() > 0:
                    st.info(f"[{profile['id']}] Account is not a member. Clicking Join...")
                    time.sleep(random.uniform(0.8, 1.8))
                    join_btns.first.click(position={"x": random.randint(5, 20), "y": random.randint(5, 15)})
                    time.sleep(random.uniform(2.0, 4.0))
            except: pass
            
                        # Simulate human mouse movement and scroll
            try:
                page.mouse.move(random.randint(100, 500), random.randint(100, 500), steps=10)
                time.sleep(random.uniform(0.5, 1.5))
                page.mouse.wheel(0, random.randint(200, 500))
                time.sleep(random.uniform(0.5, 1.5))
                page.mouse.wheel(0, -random.randint(100, 300))
            except: pass
            
            st.info(f"[{profile['id']}] Waiting for community page to stabilize...")
            time.sleep(random.uniform(3.0, 5.0))
            
            # Extract community name from page title to force it later
            full_title = page.title()
            import re
            raw_name = full_title.split(' / X')[0].replace(' Community', '').strip()
            community_name = re.sub(r'^\(\d+\+?\)\s*', '', raw_name)
            
            if community_name == "X" or community_name == "Just a moment..." or not community_name:
                st.error(f"[{profile['id']}] CRITICAL ERROR: Page failed to render community (Title is '{full_title}'). X.com blocked the request or it crashed. Aborting post.")
                return False
                
            st.info(f"[{profile['id']}] Identified community as: {community_name}")
            
            st.info(f"[{profile['id']}] Triggering compose modal...")
            page.keyboard.press('n')
            time.sleep(random.uniform(2.0, 4.0))
            
            # FORCE the audience to be the community if it defaulted to Everyone
            try:
                audience_btn = page.locator('div[aria-label="Choose audience"], button[aria-label="Choose audience"], div[role="button"][aria-label="Choose audience"]').last
                audience_set_successfully = False
                
                for attempt in range(3):
                    if audience_btn.is_visible(timeout=5000):
                        current_audience = audience_btn.inner_text()
                        if community_name in current_audience or not community_name:
                            st.success(f"[{profile['id']}] Audience is safely verified as: {current_audience}")
                            audience_set_successfully = True
                            break
                            
                        st.info(f"[{profile['id']}] Audience is '{current_audience}', but we want '{community_name}'. Attempt {attempt+1}/3 to force community selection...")
                        audience_btn.click(force=True)
                        time.sleep(random.uniform(1.0, 2.0))
                        
                        # Find the menu item containing the community name
                        menu_item = page.locator(f'[role="menuitem"]:has-text("{community_name}")').first
                        if menu_item.is_visible(timeout=15000):
                            menu_item.click(force=True)
                            time.sleep(random.uniform(1.0, 2.0))
                        else:
                            st.warning(f"[{profile['id']}] Could not find '{community_name}' in audience dropdown! (Attempt {attempt+1})")
                            page.keyboard.press('Escape')
                            time.sleep(1.0)
                    else:
                        st.warning(f"[{profile['id']}] Audience button not visible. Cannot verify audience.")
                        break

                if not audience_set_successfully and community_name:
                    st.error(f"[{profile['id']}] FAILED to securely set audience to '{community_name}' after 3 attempts. Aborting post for safety.")
                    page.keyboard.press('Escape')
                    return False

            except Exception as e:
                st.error(f"[{profile['id']}] Audience verification crashed: {e}. Aborting post for safety.")
                page.keyboard.press('Escape')
                return False
                    
            st.info(f"[{profile['id']}] Directing text payload to dashboard composer...")
            
            editor_selectors = [
                'div[data-testid="tweetTextarea_0RichTextInputContainer"]',
                'div[data-testid="tweetTextarea_0RichTextField"]', 
                'div[data-testid="tweetTextarea_0"]', 
                'div[role="textbox"]',
                '.public-DraftEditor-content'
            ]
            combined_editor = ", ".join(editor_selectors)
            try:
                page.wait_for_selector(combined_editor, state="visible", timeout=15000)
            except PlaywrightTimeoutError:
                st.error("Composer element missing.")
                return False

            human_typing(page, combined_editor, user_tweet_text)
            time.sleep(random.uniform(0.8, 1.5))
            
            if uploaded_media_path and os.path.exists(uploaded_media_path):
                st.info(f"[{profile['id']}] Attaching local media upload stream...")
                file_input = page.locator('input[data-testid="fileInput"]')
                file_input.set_input_files(uploaded_media_path)
                time.sleep(random.uniform(4.0, 6.5))
            
            st.info(f"[{profile['id']}] Clicking the Post button...")
            posted_tweet_id = None
            
            try:
                # Wait for any media uploads to finish by checking if the post button is enabled
                post_btn = page.locator('button[data-testid="tweetButton"], button[data-testid="tweetButtonInline"]').last
                post_btn.wait_for(state="visible", timeout=5000)
                
                # Wait up to 15 seconds for the button to become enabled (media uploading)
                for _ in range(15):
                    if not post_btn.is_disabled():
                        break
                    time.sleep(random.uniform(0.8, 1.5))
                    
                # Listen for the Tweet creation while clicking
                with page.expect_response(lambda response: "CreateTweet" in response.url, timeout=15000) as response_info:
                    post_btn.click(position={"x": random.randint(10, 40), "y": random.randint(5, 15)}, force=True)
                
                import re
                match = re.search(r'"rest_id":"(\d+)"', response_info.value.text())
                if match:
                    posted_tweet_id = match.group(1)
                    
            except Exception as e:
                st.warning(f"Could not click Post button or intercept network, trying hotkey: {e}")
                try:
                    page.locator(combined_editor).first.focus()
                    with page.expect_response(lambda response: "CreateTweet" in response.url, timeout=15000) as response_info:
                        page.keyboard.press("Control+Enter")
                        
                    import re
                    match = re.search(r'"rest_id":"(\d+)"', response_info.value.text())
                    if match:
                        posted_tweet_id = match.group(1)
                except Exception:
                    pass
                    
            time.sleep(random.uniform(4.0, 6.5))
            st.success(f"[{profile['id']}] Content published! (Intercepted ID: {posted_tweet_id or 'Unknown'})")

            if comment_text:
                comments_to_post = [c.strip() for c in comment_text.split('---') if c.strip()]
                if comments_to_post:
                    st.info(f"[{profile['id']}] Waiting for post to appear to add {len(comments_to_post)} comment(s)...")
                    
                    expected_post_url = None
                    
                    try:
                        try:
                            try:
                                page.locator('button:has-text("Got it"), button:has-text("Got It")').first.click(timeout=3000)
                                time.sleep(1)
                            except:
                                pass
                                
                            toast_link = page.locator('div[data-testid="toast"] a[href*="/status/"]').first
                            toast_link.wait_for(state="visible", timeout=8000)
                            
                            # Grab URL from toast
                            toast_href = toast_link.get_attribute("href")
                            if toast_href:
                                expected_post_url = toast_href
                                
                            toast_link.click(force=True)
                            
                        except Exception:
                            st.warning(f"[{profile['id']}] Toast not found.")
                            
                            # Fallback 1: Use the intercepted network ID!
                            if posted_tweet_id:
                                st.info(f"[{profile['id']}] Using intercepted Tweet ID to navigate directly...")
                                expected_post_url = f"/i/web/status/{posted_tweet_id}"
                                page.goto(f"https://x.com{expected_post_url}")
                                
                            # Fallback 2: The original profile scraping method
                            else:
                                st.warning(f"[{profile['id']}] Navigating to Profile as a last resort...")
                                try:
                                    page.wait_for_timeout(2000)
                                    profile_tab = page.locator('a[data-testid="AppTabBar_Profile_Link"]')
                                    profile_href = profile_tab.get_attribute('href')

                                    if "compose/post" in page.url or page.locator('div[data-testid="tweetTextarea_0"]').count() > 0:
                                        st.warning(f"[{profile['id']}] Post seems to have failed (compose modal still open). Skipping comments.")
                                        page.keyboard.press("Escape")
                                        page.wait_for_timeout(1000)
                                        page.keyboard.press("Escape")
                                        raise Exception("Post failed to send. Modal was still open.")

                                    profile_tab.click(force=True)
                                    
                                    page.wait_for_url(f"**{profile_href}**", timeout=10000)
                                    page.wait_for_selector('article[data-testid="tweet"]', state="visible", timeout=15000)
                                    page.wait_for_timeout(3000) 
                                    
                                    first_tweet = page.locator(f'article[data-testid="tweet"] a[href*="{profile_href}/status/"]').first
                                    
                                    if first_tweet.count() == 0:
                                        st.warning(f"[{profile['id']}] Post not found on profile, refreshing...")
                                        page.reload(wait_until="domcontentloaded")
                                        page.wait_for_selector('article[data-testid="tweet"]', state="visible", timeout=15000)
                                        page.wait_for_timeout(3000)
                                        first_tweet = page.locator(f'article[data-testid="tweet"] a[href*="{profile_href}/status/"]').first
                                    
                                    first_tweet.wait_for(state="visible", timeout=10000)
                                    expected_post_url = first_tweet.get_attribute("href")
                                    first_tweet.click(force=True)
                                    
                                except Exception as inner_e:
                                    st.error(f"[{profile['id']}] Could not locate our post in profile feed: {inner_e}")
                                    raise Exception("Aborting comment: could not navigate to post status page.")
                        
                        # --- THE ULTIMATE FIX: Wait for the URL to actually change! ---
                        try:
                            if posted_tweet_id:
                                page.wait_for_url(f"**/{posted_tweet_id}**", timeout=15000)
                            elif expected_post_url:
                                page.wait_for_url(f"**{expected_post_url}**", timeout=15000)
                            else:
                                page.wait_for_url("**/status/**", timeout=15000)
                        except Exception:
                            st.warning(f"[{profile['id']}] Warning: URL wait timed out. Checking current URL...")
                        
                        if "/status/" not in page.url:
                            raise Exception(f"Failed to navigate to the post. Current URL: {page.url}. Aborting comment to prevent main feed spam.")
                            
                        time.sleep(random.uniform(2.0, 4.0))
                        
                        reply_selectors = [
                            'div[data-testid="tweetTextarea_0RichTextInputContainer"]',
                            'div[data-testid="tweetTextarea_0RichTextField"]',
                            'div[data-testid="tweetTextarea_0"]',
                            '.public-DraftEditor-content'
                        ]
                        
                        for idx, c_text in enumerate(comments_to_post):
                            # --- FAILSAFE URL CHECK ---
                            if "/status/" not in page.url:
                                st.warning(f"[{profile['id']}] Alert: Navigated away from post status page to {page.url}! Aborting remaining comments to prevent main feed spam.")
                                break
                            
                            reply_area = page.locator(", ".join(reply_selectors)).first
                            reply_area.wait_for(state="visible", timeout=10000)
                            human_typing(page, ", ".join(reply_selectors), c_text)
                            time.sleep(random.uniform(0.8, 1.5))
                            
                            reply_btn = page.locator('button[data-testid="tweetButtonInline"]').first
                            try:
                                for _ in range(10):
                                    if not reply_btn.is_disabled(): break
                                    time.sleep(1)
                                reply_btn.click(position={"x": random.randint(10, 30), "y": random.randint(5, 15)}, timeout=5000)
                            except Exception:
                                st.warning(f"[{profile['id']}] Reply button disabled/unclickable, falling back to hotkey.")
                                reply_area.focus()
                                page.keyboard.press("Control+Enter")
                                
                            time.sleep(random.uniform(2.0, 4.0))
                            st.success(f"[{profile['id']}] Comment {idx+1} added successfully.")
                    except Exception as e:
                        try: page.screenshot(path=f"debug_comments_{profile['id']}.png")
                        except: pass
                        st.warning(f"[{profile['id']}] Could not add comments: {e} (Screenshot saved as debug_comments_{profile['id']}.png)")

            time.sleep(random.uniform(3.0, 5.0))
            return True
            
        except Exception as e:
            st.error(f"Browser launch error: {e}")
            return False
        finally:
            if context: 
                try:
                    context.close()
                except Exception:
                    pass

def process_auto_responder(profile, universal_msg, check_priority=True, check_hidden=True, unlock_password="2004", skip_older_than_hours=2.0):
    """Auto-replies to messages in Priority and Hidden tabs."""
    user_data_dir = profile.get("user_data_dir")
    final_reply = universal_msg
    
    with sync_playwright() as p:
        context = None
        if is_session_locked(user_data_dir):
            st.error(f"Browser locked for {profile['id']}")
            return False
            
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-features=Translate",
                    "--disable-sync"
                ],
                viewport={"width": random.choice([1366, 1440, 1920, 1536]), "height": random.choice([768, 900, 1080, 864])},
                ignore_default_args=["--enable-automation"]
            )
            page = context.new_page()
            try:
                import json, os
                if os.path.exists('global_config.json'):
                    with open('global_config.json', 'r') as __f:
                        if json.load(__f).get('block_videos', False):
                            def smart_route(route):
                                req = route.request
                                r_type = req.resource_type
                                url = req.url.lower()
                                if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                                if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                                try: is_chat_page = 'messages' in page.url.lower()
                                except: is_chat_page = False
                                if r_type == 'image' and not is_chat_page:
                                    if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                                route.continue_()
                            page.route('**/*', smart_route)
            except: pass

            Stealth().apply_stealth_sync(page)
            context.set_default_navigation_timeout(60000)
            
            # X Message Requests URL
            # Scrape main inbox first to build a whitelist of already-accepted users
            st.info(f"[{profile['id']}] Scraping main inbox for already-accepted users...")
            page.goto("https://x.com/messages", wait_until="domcontentloaded")
            human_pause(4.0, 6.0)
            
            try:
                pwd_input = page.locator('input[type="password"], input[name="pin"], input[placeholder*="password" i], input[placeholder*="pin" i]').first
                pwd_input.wait_for(state="visible", timeout=3000)
                st.info(f"[{profile['id']}] Found standard chat lock screen on main inbox. Entering password...")
                pwd_input.fill(unlock_password)
                human_pause(1.5, 3.0)
                page.keyboard.press("Enter")
                human_pause(3.0, 5.0)
            except Exception:
                try:
                    passcode_text = page.get_by_text("Enter Passcode").first
                    passcode_text.wait_for(state="visible", timeout=10000)
                    st.info(f"[{profile['id']}] Found Encrypted DM Passcode screen. Typing PIN...")
                    pin_inputs = page.locator('div[data-testid="pin-code-input-container"] input')
                    try: pin_inputs.first.wait_for(state="attached", timeout=5000)
                    except: pass
                    if pin_inputs.count() >= 4:
                        for i in range(4):
                            if i < len(unlock_password):
                                pin_inputs.nth(i).focus()
                                page.keyboard.press(unlock_password[i])
                                human_pause(0.2, 0.4)
                    else:
                        box = passcode_text.bounding_box()
                        if box: page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] + 60)
                        else: page.mouse.click(500, 500)
                        for char in unlock_password:
                            page.keyboard.press(char)
                            human_pause(0.2, 0.4)
                    human_pause(1.0, 2.0)
                    page.keyboard.press("Enter")
                    human_pause(3.0, 5.0)
                except Exception: pass
                
            accepted_users_whitelist = set()
            try:
                page.wait_for_selector('[data-testid^="dm-conversation-item-"], [data-testid="conversation"]', timeout=5000)
                # Scrape while scrolling to catch virtualized DOM elements
                for _ in range(12):
                    main_convos = page.locator('[data-testid^="dm-conversation-item-"], [data-testid="conversation"]')
                    for i in range(main_convos.count()):
                        try:
                            name = main_convos.nth(i).inner_text().split('\n')[0].strip()
                            accepted_users_whitelist.add(name)
                        except Exception: pass
                    page.keyboard.press("PageDown")
                    human_pause(1.0, 2.0)
                st.success(f"[{profile['id']}] Whitelisted {len(accepted_users_whitelist)} users from main inbox.")
            except Exception as e:
                # Check if we hit a login screen or Cloudflare instead of an empty inbox
                if page.locator('input[autocomplete="username"]').count() > 0 or \
                   page.get_by_text("Verify you are human").count() > 0 or \
                   page.get_by_text("Continue with Google").count() > 0:
                    st.error(f"[{profile['id']}] Account is logged out or blocked by Cloudflare! Aborting.")
                    try: page.screenshot(path=f"debug_inbox_{profile['id']}.png")
                    except: pass
                    with open("login_needed.json", "w") as f:
                        json.dump({"id": profile['id'], "user_data_dir": profile['user_data_dir']}, f)
                    raise Exception("Account requires manual login or Cloudflare bypass.")
                
                st.warning(f"[{profile['id']}] Main inbox is empty or loading took too long. Proceeding...")
                try: page.screenshot(path=f"debug_inbox_{profile['id']}.png")
                except: pass

            # X Message Requests URL
            st.info(f"[{profile['id']}] Navigating to message requests...")
            page.goto("https://x.com/messages/requests", wait_until="domcontentloaded")
            human_pause(4.0, 6.0)
            
            try:
                pwd_input = page.locator('input[type="password"], input[name="pin"], input[placeholder*="password" i], input[placeholder*="pin" i]').first
                pwd_input.wait_for(state="visible", timeout=3000)
                st.info(f"[{profile['id']}] Found standard chat lock screen. Entering password...")
                pwd_input.fill(unlock_password)
                human_pause(1.5, 3.0)
                page.keyboard.press("Enter")
                human_pause(3.0, 5.0)
            except Exception:
                try:
                    passcode_text = page.get_by_text("Enter Passcode").first
                    passcode_text.wait_for(state="visible", timeout=10000)
                    st.info(f"[{profile['id']}] Found Encrypted DM Passcode screen. Typing PIN...")
                    pin_inputs = page.locator('div[data-testid="pin-code-input-container"] input')
                    if pin_inputs.count() >= 4:
                        for i in range(4):
                            if i < len(unlock_password):
                                pin_inputs.nth(i).focus()
                                page.keyboard.press(unlock_password[i])
                                human_pause(0.2, 0.4)
                    else:
                        box = passcode_text.bounding_box()
                        if box: page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] + 60)
                        else: page.mouse.click(500, 500)
                        for char in unlock_password:
                            page.keyboard.press(char)
                            human_pause(0.2, 0.4)
                    human_pause(1.0, 2.0)
                    page.keyboard.press("Enter")
                    human_pause(3.0, 5.0)
                except Exception: pass
            
            tabs_to_check = []
            if check_priority: tabs_to_check.append("Priority")
            if check_hidden: tabs_to_check.append("Hidden")
            
            processed_unified_list = False
            
            
            for tab_name in tabs_to_check:
                st.info(f"[{profile['id']}] Processing '{tab_name}' tab...")
                try:
                    # Give X more time to render the UI, targeting only visible elements
                    selector = f"[role='tab']:has-text('{tab_name}'), a:has-text('{tab_name}'), span:text-is('{tab_name}')"
                    if tab_name == "Hidden":
                        selector += ", button[data-testid='dm-message-requests-other-button'], [role='tab']:has-text('Other'), a:has-text('Other'), span:text-is('Other')"
                    tab_locator = page.locator(selector).first
                    
                    tab_found = False
                    try:
                        # Wait up to 5 seconds for the tab to appear (X can be slow)
                        tab_locator.wait_for(state="visible", timeout=5000)
                        tab_locator.click()
                        human_pause(2.0, 4.0)
                        tab_found = True
                    except Exception:
                        st.warning(f"Could not find the '{tab_name}' tab on screen. Your account might not use tabs. Processing visible requests anyway...")
                        processed_unified_list = True
                        # Proceed to process the unified list of requests instead of skipping
                    
                    processed_users = set()
                    
                    # Find conversation list
                    # X uses data-testid="conversation" for each chat in the list
                    while True:
                        try:
                            # Wait up to 10 seconds for conversations OR the empty state to load
                            page.wait_for_selector('[data-testid^="dm-conversation-item-"], [data-testid^="dm-message-request-item-"], [data-testid="conversation"], [data-testid="dm-message-requests-empty"]', timeout=10000)
                        except: pass
                        
                        convos = page.locator('[data-testid^="dm-conversation-item-"], [data-testid^="dm-message-request-item-"], [data-testid="conversation"]')
                        if convos.count() == 0:
                            st.info(f"[{profile['id']}] No more pending conversations found in {tab_name}.")
                            break
                            
                        # Extract handles/names from visible convos
                        visible_convo_names = []
                        for idx in range(convos.count()):
                            try:
                                txt = convos.nth(idx).inner_text()
                                name = txt.split('\n')[0].strip()
                                visible_convo_names.append((idx, name))
                            except Exception: pass                       
                        
                        unprocessed_index = -1
                        current_convo_name = None
                        for i in range(convos.count()):
                            try:
                                # Get the username/text from the first line
                                name = convos.nth(i).inner_text().split('\n')[0].strip()
                            except:
                                name = f"unknown_{i}"
                            
                            if name in accepted_users_whitelist:
                                processed_users.add(name)
                                st.info(f"Skipping {name} as they are already in the main inbox (accepted).")
                                continue
                                
                            if name not in processed_users:
                                unprocessed_index = i
                                current_convo_name = name
                                break
                                
                        if unprocessed_index == -1:
                            st.write(f"No more pending conversations found in {tab_name}.")
                            break
                            
                        convo = convos.nth(unprocessed_index)
                        
                        # PRE-SCREEN: 5-Hour Window & Handled Check
                        try:
                            # 1. 5-Hour Time Check using X's <time> element
                            time_el = convo.locator('time').first
                            if time_el.count() > 0:
                                dt_str = time_el.get_attribute('datetime')
                                if dt_str:
                                    dt_str = dt_str.replace('Z', '+00:00')
                                    from datetime import datetime, timezone
                                    msg_time = datetime.fromisoformat(dt_str)
                                    now = datetime.now(timezone.utc)
                                    diff = now - msg_time
                                    if skip_older_than_hours > 0 and diff.total_seconds() > skip_older_than_hours * 3600:
                                        st.write(f"Message from {current_convo_name} is older than {skip_older_than_hours} hours. Skipping.")
                                        processed_users.add(current_convo_name)
                                        continue
                                        
                            # 2. Handled Check
                            convo_text = convo.inner_text().lower()
                            if "you accepted the request" in convo_text or "you sent" in convo_text or "you:" in convo_text:
                                st.write("Conversation shows as already handled in the list. Skipping instantly.")
                                processed_users.add(current_convo_name)
                                continue
                        except Exception as e:
                            st.write(f"Error during pre-screen check for {current_convo_name}: {e}")
                            print(f"Error during pre-screen check for {current_convo_name}: {e}")
                        convo.click()
                        human_pause(1.5, 3.0)
                        
                        # Handle hidden/suspicious content by clicking 'View' if it exists
                        try:
                            view_btn = page.get_by_role("button", name="View", exact=True).last
                            view_btn.wait_for(state="visible", timeout=1500)
                            view_btn.click()
                            st.write("Clicked 'View' to reveal hidden/suspicious message.")
                            human_pause(1.0, 2.0)
                        except Exception:
                            pass
                        
                        # Check if it's a fresh request by looking for the Accept button
                        needs_reply = False
                        
                        # NEW SAFETY CHECK: Look if we already sent our exact reply
                        try:
                            # Extract the first few words to avoid issues with X turning links into HTML cards
                            first_words = " ".join(final_reply.split()[:3])
                            if page.get_by_text(first_words).count() > 0:
                                st.write("Our automated reply is already present in this chat. Skipping to prevent double messages.")
                                processed_users.add(current_convo_name)
                                continue
                        except Exception:
                            pass
                            
                        try:
                            # Use a stricter selector for the Accept button
                            accept_btn = page.get_by_role("button", name="Accept", exact=True).last
                            # Wait 3 seconds to see if the Accept button appears
                            accept_btn.wait_for(state="visible", timeout=3000)
                            accept_btn.click()
                            human_pause(1.5, 3.0)
                            needs_reply = True
                        except:
                            pass # No Accept button means it's already accepted or not a valid request
                            
                        if not needs_reply:
                            st.write("Conversation is already accepted or missing 'Accept'. Skipping to prevent duplicate replies.")
                            processed_users.add(current_convo_name)
                            continue # Skip reply and move to the next conversation index without reloading the page
                            
                        st.write(f"Replying with: {final_reply}")
                        
                        # Focus editor and reply
                        try:
                            # Give the chat pane a few seconds to fully render
                            human_pause(1.5, 3.0)
                            
                            all_textboxes = page.locator('div[role="textbox"], textarea')
                            visible_boxes = []
                            for i in range(all_textboxes.count()):
                                box = all_textboxes.nth(i)
                                if box.is_visible():
                                    visible_boxes.append(box)
                            
                            if not visible_boxes:
                                raise Exception("No visible text input fields found on screen.")
                                
                            # The chat composer is always the lowest textbox on the screen, so we take the last visible one
                            editor = visible_boxes[-1]
                            editor.click(timeout=3000)
                            human_pause(0.5, 1.5)
                            
                            # 1 & 2. Unified String Compilation & Atomic UI Injection
                            editor.fill(final_reply)
                            human_pause(0.5, 1.0)
                            editor.press("Space")
                            editor.press("Backspace")
                            
                            # 3. Submission Synchronization
                            # Introduce explicit wait state to allow frontend event hooks to process the payload
                            human_pause(1.5, 3.0)
                            
                            # Explicitly target and click the physical 'Send' button for 100% reliability
                            try:
                                send_btn = page.locator('div[data-testid="dmComposerSendButton"], button[aria-label="Send"], div[aria-label="Send"]').last
                                send_btn.wait_for(state="visible", timeout=3000)
                                send_btn.click(timeout=3000)
                            except Exception:
                                # Fallback to Enter key if the button cannot be located
                                editor.press("Enter")
                                
                            # CRITICAL: Wait long enough for the network request to finish!
                            # If we navigate away too quickly, the browser aborts the API call.
                            human_pause(4.0, 6.0)
                            
                        except Exception as e:
                            st.warning(f"Could not find message input for this conversation: {e}")
                        
                        processed_users.add(current_convo_name)
                        
                        # Go back to requests list
                        page.goto("https://x.com/messages/requests", wait_until="domcontentloaded")
                        human_pause(3.0, 5.0)
                        
                        # Click the tab again to continue
                        try:
                            selector = f"[role='tab']:has-text('{tab_name}'), a:has-text('{tab_name}'), span:text-is('{tab_name}')"
                            if tab_name == "Hidden":
                                selector += ", button[data-testid='dm-message-requests-other-button'], [role='tab']:has-text('Other'), a:has-text('Other'), span:text-is('Other')"
                            tab_locator = page.locator(selector).first
                            tab_locator.wait_for(state="visible", timeout=5000)
                            tab_locator.click()
                            human_pause(2.0, 4.0)
                        except Exception:
                            st.warning(f"Could not re-select the '{tab_name}' tab. Moving to next.")
                            
                        # We reloaded the page, so the DOM shifted. Reset the processed list to start from the top again.
                        # processed_users.clear() # Preserved across reloads to prevent O(N^2) checking
                            
                except Exception as e:
                    st.warning(f"Finished or encountered issue in {tab_name} tab: {e}")
                    
        except Exception as e:
            st.error(f"Browser launch failed: {e}")
        finally:
            if context:
                try:
                    context.close()
                except:
                    pass

# --- Streamlit Dashboard UI Setup ---
st.set_page_config(page_title="Assistive Workspace Dashboard", layout="wide")

# Custom CSS for a professional, sleek UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Main Typography */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Sleek Sidebar / Glassmorphism */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #27272a;
        background: rgba(24, 24, 27, 0.6) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    section[data-testid="stSidebar"] hr {
        border-color: #27272a;
    }

    /* Style Streamlit Alerts */
    div[data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.05) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* Forms and Containers (Premium Dark Cards) */
    div[data-testid="stForm"] {
        background-color: #121214;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        border: 1px solid #27272a;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background-color: #121214;
        border-radius: 10px;
        border: 1px solid #27272a;
        overflow: hidden;
        margin-bottom: 16px;
        transition: border-color 0.2s;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #3f3f46;
    }
    div[data-testid="stExpander"] details summary {
        padding: 16px 20px;
        font-weight: 500;
        background-color: #121214;
        color: #ededed;
        transition: all 0.2s;
    }
    div[data-testid="stExpander"] details summary:hover {
        background-color: #18181b;
        color: #6366f1;
    }

    /* Headers */
    h1, h2, h3 {
        color: #f8fafc;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Modern Buttons */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
        border: 1px solid #3f3f46;
        background-color: #18181b;
        color: #e4e4e7;
    }
    .stButton>button:hover {
        border-color: #52525b;
        background-color: #27272a;
        color: #ffffff;
    }
    /* Primary Buttons (Neon Glow) */
    .stButton>button[kind="primary"] {
        background: #4f46e5 !important;
        color: white !important;
        border: 1px solid #4338ca !important;
        box-shadow: 0 0 15px rgba(79, 70, 229, 0.3) !important;
    }
    .stButton>button[kind="primary"]:hover {
        background: #6366f1 !important;
        border: 1px solid #4f46e5 !important;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.5) !important;
        transform: translateY(-1px);
    }

    /* Inputs */
    .stTextArea>div>div>textarea, .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 6px;
        border: 1px solid #27272a;
        background-color: #18181b;
        padding: 10px 14px;
        font-size: 14px;
        color: #ededed;
        transition: all 0.2s;
    }
    .stTextArea>div>div>textarea:focus, .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus {
        border-color: #6366f1;
        background-color: #121214;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
    }

    /* Modern Apple-style Segmented Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #18181b;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
        border: 1px solid #27272a;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 24px;
        font-weight: 500;
        color: #a1a1aa;
        background: transparent;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #27272a !important;
        color: #ffffff !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    
    /* Dividers */
    hr {
        margin: 2rem 0;
        border-color: #27272a;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header(":material/emergency: System Alerts")
    
    # --- CAPTCHA ALERT SECTION ---
    if os.path.exists("captcha_alert.png") and os.path.exists("bot_status.json"):
        try:
            with open("bot_status.json", "r") as f:
                status_data = json.load(f)
            
            st.error(f"Profile '{status_data.get('profile', 'Unknown')}' ({status_data.get('username', 'Unknown')}) is paused for verification!")
            st.warning("Please scan this QR code with your phone camera. Bot resumes in 3 min.")
            st.image("captcha_alert.png", use_container_width=True)
            
            if st.button("Refresh Status"):
                st.rerun()
                
            st.divider()
        except Exception as e:
            pass
    # -----------------------------
    
    # --- LOGIN NEEDED ALERT ---
    if os.path.exists("login_needed.json"):
        try:
            with open("login_needed.json", "r") as f:
                login_data = json.load(f)
            
            st.warning(f":material/warning: Profile '{login_data.get('id', 'Unknown')}' logged out / Cloudflare check!")
            st.write("Open browser, resolve issue, and close window.")
            
            if st.button("Open Visible Browser", key="btn_login_needed"):
                with st.spinner("Opening browser..."):
                    success, message = setup_persistent_session(login_data['user_data_dir'], "https://x.com")
                    if success:
                        st.success(message)
                        if os.path.exists("login_needed.json"):
                            os.remove("login_needed.json")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(message)
                        
            if st.button("Dismiss Alert", key="btn_dismiss_login"):
                if os.path.exists("login_needed.json"):
                    os.remove("login_needed.json")
                st.rerun()
                
            st.divider()
        except Exception as e:
            pass
    # -----------------------------
    
    if not os.path.exists("captcha_alert.png") and not os.path.exists("bot_status.json") and not os.path.exists("login_needed.json"):
        st.success("No active security verifications or alerts. Everything is running smoothly.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Publish Dashboard", "Manage Accounts", "Auto-Responder", "Promo Videos", "Account Onboarding & Provisioning"])

def load_profiles():
    try:
        with open("profiles.json", "r") as f: 
            return json.load(f)
    except FileNotFoundError: 
        return []

def save_profiles(data):
    with open("profiles.json", "w") as f: 
        json.dump(data, f, indent=4)

profiles_data = load_profiles()

class LocalFileWrapper:
    def __init__(self, p):
        self.path = p
        self.name = os.path.basename(p)
    def getbuffer(self):
        with open(self.path, "rb") as f: return f.read()

# TAB 1: DAILY POSTING INTERFACE
with tab1:
    st.header("Post Content Framework")
    if profiles_data:
        profile_options = {p["id"]: p for p in profiles_data}
        
        # --- FIX: New Bulk Auto-Sync Button ---
        fetch_triggered = st.button("Auto-Sync Linked Accounts", use_container_width=True)
        if fetch_triggered:
            with st.spinner("Fetching communities for all accounts... (Running 3 concurrent bots)"):
                full_cache = {}
                if os.path.exists("communities_cache.json"):
                    try:
                        with open("communities_cache.json", "r") as f:
                            full_cache = json.load(f)
                    except:
                        pass
                
                failed_accounts = []
                import concurrent.futures
                
                # Use the 3 bot chunking logic
                def process_sync_chunk(chunk):
                    chunk_results = []
                    for profile_id, prof in chunk:
                        try:
                            comms = fetch_joined_communities(prof)
                            chunk_results.append((profile_id, comms))
                        except Exception as e:
                            chunk_results.append((profile_id, None))
                    return chunk_results
                
                items = list(profile_options.items())
                chunk_size = 10
                chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    for chunk_res in executor.map(process_sync_chunk, chunks):
                        for profile_id, comms in chunk_res:
                            if comms is None:
                                failed_accounts.append(profile_id)
                            elif comms:
                                full_cache[profile_id] = comms
                                
                with open("communities_cache.json", "w") as f: 
                    json.dump(full_cache, f, indent=4)
                    
                if failed_accounts:
                    st.session_state.sync_auth_failed = failed_accounts
                else:
                    st.session_state.sync_auth_failed = []
                    st.success("All accounts synced successfully!")
                
                time.sleep(2)
                st.rerun()
                    
        if st.session_state.get("sync_auth_failed"):
            st.warning(f"Auto-sync was blocked for: {', '.join(st.session_state.sync_auth_failed)}. Please use Manual Sync below.")
            
        st.divider()
        st.subheader("Manual Account Sync (Fallback)")
        selected_id = st.selectbox("Select Profile Handle for Manual Sync", options=list(profile_options.keys()))
        current_profile = profile_options[selected_id]
        
        manual_sync = st.button(f":material/visibility: Manual Sync via Visible Browser [{current_profile['id']}]")
        if manual_sync:
            with st.spinner(f"Opening browser for {current_profile['id']}... Please resolve the login/captcha, then wait for 60 seconds."):
                comms = fetch_joined_communities_manual(current_profile)
                if comms:
                    full_cache = {}
                    if os.path.exists("communities_cache.json"):
                        try:
                            with open("communities_cache.json", "r") as f:
                                full_cache = json.load(f)
                        except:
                            pass
                    full_cache[current_profile["id"]] = comms
                    with open("communities_cache.json", "w") as f: 
                        json.dump(full_cache, f, indent=4)
                    st.success(f"Manual sync successful for {current_profile['id']}! Loaded {len(comms)} targets.")
                    
                    if isinstance(st.session_state.get("sync_auth_failed"), list) and current_profile["id"] in st.session_state.sync_auth_failed:
                        st.session_state.sync_auth_failed.remove(current_profile["id"])
                        
                    time.sleep(2)
                    st.rerun()
                            
        # --- PHASE 1 & 2: MASTER CACHE & DYNAMIC UI ---
        communities_cache = {}
        if os.path.exists("communities_cache.json"):
            try:
                with open("communities_cache.json", "r") as f: 
                    communities_cache = json.load(f)
            except:
                pass
        
        if "drafted_messages" not in st.session_state:
            st.session_state.drafted_messages = {}
        if "drafted_comments" not in st.session_state:
            st.session_state.drafted_comments = {}
        if "pool_selections" not in st.session_state:
            st.session_state.pool_selections = {}

        if not communities_cache:
            st.info("No communities synced yet. Please run the Sync tool to build your interface.")
        else:
            st.divider()
            st.subheader("Account-Specific Content Router")
            st.write("For each account, draft your message and select communities. The system will randomly pick 2 of your selected communities to post to.")
            
            with st.expander(":material/smart_toy: Auto-fill from JSON"):
                st.write("Paste a JSON object to instantly fill the message and comment boxes for your accounts.")
                st.code('''{
  "account 1": {
    "message": "My main post text",
    "comments": "Comment 1---Comment 2"
  }
}''', language="json")
                autofill_json = st.text_area("Auto-fill JSON Content", height=150, key="autofill_input")
                if st.button("Apply Auto-fill"):
                    if autofill_json.strip():
                        try:
                            import json
                            import re
                            try:
                                parsed_fill = json.loads(autofill_json)
                            except json.JSONDecodeError:
                                # Fallback: User pasted multiple { } objects instead of one big object
                                fixed_json = "[" + re.sub(r'}\s*\{', '},{', autofill_json.strip()) + "]"
                                parsed_list = json.loads(fixed_json)
                                parsed_fill = {}
                                for item in parsed_list:
                                    parsed_fill.update(item)
                                    
                            for acct, data in parsed_fill.items():
                                if "message" in data:
                                    st.session_state.drafted_messages[acct] = data["message"]
                                    st.session_state[f"input_{acct}"] = data["message"]
                                if "comments" in data:
                                    st.session_state.drafted_comments[acct] = data["comments"]
                                    st.session_state[f"comment_{acct}"] = data["comments"]
                            st.success("Successfully applied Auto-fill!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Invalid JSON format. Make sure it's a valid JSON object. Error: {e}")

            with st.expander(":material/save: Save & Load Drafts (Vault)"):
                st.write("Save your currently drafted messages/comments to a growing vault, and reload them later in a randomized order.")
                
                col_save, col_load, col_clear = st.columns(3)
                with col_save:
                    if st.button("Save to Vault"):
                        import os, json
                        drafts_to_save = []
                        for acct in communities_cache.keys():
                            msg = st.session_state.drafted_messages.get(acct, "")
                            cmt = st.session_state.drafted_comments.get(acct, "")
                            if msg or cmt:
                                drafts_to_save.append({"message": msg, "comments": cmt})
                        
                        if drafts_to_save:
                            try:
                                vault = []
                                if os.path.exists("saved_drafts.json"):
                                    with open("saved_drafts.json", "r") as f:
                                        try:
                                            old_data = json.load(f)
                                            if isinstance(old_data, dict):
                                                vault = list(old_data.values())
                                            elif isinstance(old_data, list):
                                                vault = old_data
                                        except: pass
                                
                                vault.extend(drafts_to_save)
                                with open("saved_drafts.json", "w") as f:
                                    json.dump(vault, f)
                                st.success(f"Added {len(drafts_to_save)} drafts! Vault total: {len(vault)}")
                            except Exception as e:
                                st.error(f"Failed to save drafts: {e}")
                        else:
                            st.warning("No drafts to save!")
                
                with col_load:
                    if st.button("Load & Reshuffle Vault"):
                        try:
                            import os, json, random
                            if os.path.exists("saved_drafts.json"):
                                with open("saved_drafts.json", "r") as f:
                                    try:
                                        data = json.load(f)
                                        if isinstance(data, dict):
                                            payloads = list(data.values())
                                        elif isinstance(data, list):
                                            payloads = data
                                        else:
                                            payloads = []
                                    except:
                                        payloads = []
                                
                                if payloads:
                                    random.shuffle(payloads)
                                    
                                    active_accts = list(communities_cache.keys())
                                    for idx, acct in enumerate(active_accts):
                                        data_idx = idx % len(payloads)
                                        data = payloads[data_idx]
                                        st.session_state.drafted_messages[acct] = data.get("message", "")
                                        st.session_state[f"input_{acct}"] = data.get("message", "")
                                        st.session_state.drafted_comments[acct] = data.get("comments", "")
                                        st.session_state[f"comment_{acct}"] = data.get("comments", "")
                                    
                                    st.success(f"Dealt {len(active_accts)} drafts from a vault of {len(payloads)}!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.warning("Vault is empty.")
                            else:
                                st.warning("No saved drafts found. Please save first.")
                        except Exception as e:
                            st.error(f"Failed to load drafts: {e}")
                            
                with col_clear:
                    if st.button("Clear Vault"):
                        import os
                        if os.path.exists("saved_drafts.json"):
                            os.remove("saved_drafts.json")
                            st.success("Vault cleared!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("Vault is already empty.")

            with st.expander(":material/image: Image Vault"):
                st.write("Save images to a vault so the recurring auto-poster can pick them randomly.")
                
                image_vault_dir = "image_vault"
                os.makedirs(image_vault_dir, exist_ok=True)
                
                vault_images_uploaded = st.file_uploader("Upload Media to Vault", type=["jpg", "jpeg", "png", "mp4", "mov"], accept_multiple_files=True, key="vault_images_uploader")
                
                col_save_img, col_load_img, col_clear_img = st.columns(3)
                with col_save_img:
                    if st.button("Save to Image Vault"):
                        if vault_images_uploaded:
                            saved_count = 0
                            for img_file in vault_images_uploaded:
                                safe_name = "".join(c for c in img_file.name if c.isalnum() or c in "._-")
                                file_path = os.path.join(image_vault_dir, safe_name)
                                with open(file_path, "wb") as f:
                                    f.write(img_file.getbuffer())
                                saved_count += 1
                            st.success(f"Saved {saved_count} images to vault!")
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("No images selected.")
                            
                with col_load_img:
                    if st.button("Load & Reshuffle Media"):
                        import random, os, time
                        vault_media = []
                        if os.path.exists("image_vault"):
                            vault_media = [os.path.join("image_vault", f) for f in os.listdir("image_vault") if os.path.isfile(os.path.join("image_vault", f))]
                        if vault_media:
                            random.shuffle(vault_media)
                            if "vault_media_assignments" not in st.session_state:
                                st.session_state.vault_media_assignments = {}
                                
                            active_accts = list(communities_cache.keys())
                            for idx, acct in enumerate(active_accts):
                                media_idx = idx % len(vault_media)
                                st.session_state.vault_media_assignments[acct] = LocalFileWrapper(vault_media[media_idx])
                                
                            st.success(f"Dealt {len(active_accts)} media files randomly!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Media Vault is empty.")
                            
                with col_clear_img:
                    if st.button("Clear Image Vault"):
                        import shutil
                        if os.path.exists(image_vault_dir):
                            shutil.rmtree(image_vault_dir)
                        os.makedirs(image_vault_dir, exist_ok=True)
                        st.success("Image Vault cleared!")
                        import time
                        time.sleep(1)
                        st.rerun()
                        
                existing_images = os.listdir(image_vault_dir) if os.path.exists(image_vault_dir) else []
                if existing_images:
                    st.info(f"Image Vault contains {len(existing_images)} images.")
                    with st.expander("View Vault Images"):
                        for img_name in existing_images:
                            st.text(f":material/image: {img_name}")
                else:
                    st.warning("Image Vault is empty.")

            with st.expander(":material/campaign: Dedicated Promo Vault (Video + Post)"):
                st.write("This vault is completely separate from your general drafts and images. It loads the dedicated 8 promo posts and videos.")
                
                promo_vault_dir = "promo_vault_media"
                os.makedirs(promo_vault_dir, exist_ok=True)
                
                vault_promo_uploaded = st.file_uploader("Upload Promo Videos to Vault", type=["mp4", "mov"], accept_multiple_files=True, key="vault_promo_uploader")
                
                col_save_promo, col_clear_promo = st.columns(2)
                with col_save_promo:
                    if st.button("Save Videos to Promo Vault", use_container_width=True):
                        if vault_promo_uploaded:
                            saved_count = 0
                            for vid_file in vault_promo_uploaded:
                                safe_name = "".join(c for c in vid_file.name if c.isalnum() or c in "._-")
                                file_path = os.path.join(promo_vault_dir, safe_name)
                                with open(file_path, "wb") as f:
                                    f.write(vid_file.getbuffer())
                                saved_count += 1
                            st.success(f"Saved {saved_count} videos to promo vault!")
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("No videos selected.")
                            
                with col_clear_promo:
                    if st.button("Clear Promo Videos", use_container_width=True):
                        import shutil
                        if os.path.exists(promo_vault_dir):
                            shutil.rmtree(promo_vault_dir)
                        os.makedirs(promo_vault_dir, exist_ok=True)
                        st.success("Promo Videos cleared!")
                        import time
                        time.sleep(1)
                        st.rerun()
                        
                existing_promos = os.listdir(promo_vault_dir) if os.path.exists(promo_vault_dir) else []
                if existing_promos:
                    st.info(f"Promo Vault contains {len(existing_promos)} videos.")
                else:
                    st.warning("Promo Vault has no videos.")
                
                st.divider()
                
                st.write("**Promo Text & Comments (JSON)**")
                st.write("Paste a JSON array containing your messages and comments. Example format:")
                st.code('[\n  {\n    "message": "Your post text here",\n    "comments": "Comment 1---Comment 2"\n  }\n]', language='json')
                
                current_promo_json = "[]"
                if os.path.exists("promo_vault_drafts.json"):
                    try:
                        with open("promo_vault_drafts.json", "r") as f:
                            current_promo_json = f.read()
                    except: pass
                
                promo_json_input = st.text_area("Promo JSON", value=current_promo_json, height=200, key="promo_json_input")
                if st.button("Save Promo JSON", use_container_width=True):
                    try:
                        import json
                        parsed_json = json.loads(promo_json_input)
                        if isinstance(parsed_json, list):
                            with open("promo_vault_drafts.json", "w") as f:
                                json.dump(parsed_json, f, indent=4)
                            st.success(f"Saved {len(parsed_json)} promo texts to vault!")
                        else:
                            st.error("JSON must be a list of objects `[{...}, {...}]`.")
                    except Exception as e:
                        st.error(f"Invalid JSON format: {e}")
                
                st.divider()

                if st.button("Load & Reshuffle Promo Vault", use_container_width=True):
                    import os, json, random, time
                    promo_texts = []
                    if os.path.exists("promo_vault_drafts.json"):
                        try:
                            with open("promo_vault_drafts.json", "r") as f:
                                promo_texts = json.load(f)
                        except: pass
                    
                    promo_media = []
                    if os.path.exists("promo_vault_media"):
                        promo_media = [os.path.join("promo_vault_media", f) for f in os.listdir("promo_vault_media") if os.path.isfile(os.path.join("promo_vault_media", f))]
                    
                    if promo_texts and promo_media:
                        random.shuffle(promo_texts)
                        random.shuffle(promo_media)
                        
                        if "vault_media_assignments" not in st.session_state:
                            st.session_state.vault_media_assignments = {}
                        
                        active_accts = list(communities_cache.keys())
                        for idx, acct in enumerate(active_accts):
                            t_data = promo_texts[idx % len(promo_texts)]
                            m_file = promo_media[idx % len(promo_media)]
                            
                            st.session_state.drafted_messages[acct] = t_data.get("message", "")
                            st.session_state[f"input_{acct}"] = t_data.get("message", "")
                            st.session_state.drafted_comments[acct] = t_data.get("comments", "")
                            st.session_state[f"comment_{acct}"] = t_data.get("comments", "")
                            
                            st.session_state.vault_media_assignments[acct] = LocalFileWrapper(m_file)
                        
                        st.success(f"Assigned promo content across {len(active_accts)} accounts!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Promo vault is missing texts or media. Ensure promo_vault_drafts.json and promo_vault_media/ exist.")

            st.divider()
            with st.expander(":material/group_add: Master Community Bulk Assigner", expanded=True):
                st.write("Assign a community to all accounts that are members of it. Accounts that are not members (or have no community selected) will be listed so you can assign a different one to them.")
                
                # Gather all unique communities across all accounts
                all_unique_comms = set()
                for p_id, profile_comms in communities_cache.items():
                    if profile_comms:
                        all_unique_comms.update(list(profile_comms.keys()))
                all_unique_comms = sorted(list(all_unique_comms))
                
                col_ass1, col_ass2, col_ass3 = st.columns([0.5, 0.25, 0.25])
                with col_ass1:
                    selected_master_comm = st.selectbox("Select a Community to Assign:", options=[""] + all_unique_comms, key="master_comm_select")
                with col_ass2:
                    st.write("") # spacing
                    st.write("")
                    if st.button("Assign to Eligible", use_container_width=True):
                        if selected_master_comm:
                            assigned_count = 0
                            for p_id, profile_comms in communities_cache.items():
                                is_unassigned = True
                                if f"pool_{p_id}" in st.session_state and st.session_state[f"pool_{p_id}"]:
                                    is_unassigned = False
                                    
                                if is_unassigned and profile_comms and selected_master_comm in profile_comms:
                                    st.session_state[f"pool_{p_id}"] = [selected_master_comm]
                                    assigned_count += 1
                            st.success(f"Assigned to {assigned_count} accounts!")
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Select a community first.")
                with col_ass3:
                    st.write("")
                    st.write("")
                    if st.button("Clear All Selections", use_container_width=True):
                        for p_id in communities_cache.keys():
                            st.session_state[f"pool_{p_id}"] = []
                        st.success("Cleared all!")
                        import time
                        time.sleep(1)
                        st.rerun()
                
                # Show unassigned accounts
                # We consider an account unassigned if it's explicitly set to an empty list in session_state,
                # or if it hasn't been rendered yet but will be rendered soon.
                # Actually, to make it clear, let's just look at the session_state.
                unassigned = []
                for p_id in communities_cache.keys():
                    if f"pool_{p_id}" in st.session_state:
                        if not st.session_state[f"pool_{p_id}"]:
                            unassigned.append(p_id)
                    else:
                        # Since default_selections is now [], it will be empty initially
                        unassigned.append(p_id)
                
                if unassigned:
                    st.warning(f"**Accounts with NO communities selected ({len(unassigned)}):** " + ", ".join(unassigned))
                    
                    unassigned_comms = set()
                    for p_id in unassigned:
                        if communities_cache.get(p_id):
                            unassigned_comms.update(list(communities_cache[p_id].keys()))
                    if unassigned_comms:
                        with st.expander("Available communities for the unassigned accounts"):
                            st.write(", ".join(sorted(list(unassigned_comms))))
                else:
                    st.success("All accounts have at least one community selected!")

            with st.expander(":material/library_add: Master Content Bulk Assigner"):
                st.write("Apply ONE media file, ONE post, and ONE comment across all accounts.")
                master_msg = st.text_area("Master Message (Post text)", key="master_msg_input")
                master_comment = st.text_area("Master Comments (Separate with '---')", key="master_cmt_input")
                master_media = st.file_uploader("Master Media (Image/Video)", type=["jpg", "jpeg", "png", "mp4", "mov"], accept_multiple_files=False, key="master_media_input")
                
                col_mc1, col_mc2 = st.columns(2)
                with col_mc1:
                    if st.button("Apply Text & Comments to All", use_container_width=True):
                        for p_id in communities_cache.keys():
                            if master_msg:
                                st.session_state.drafted_messages[p_id] = master_msg
                                st.session_state[f"input_{p_id}"] = master_msg
                            if master_comment:
                                st.session_state.drafted_comments[p_id] = master_comment
                                st.session_state[f"comment_{p_id}"] = master_comment
                        st.success("Applied text/comments to all accounts!")
                        import time
                        time.sleep(1)
                        st.rerun()
                with col_mc2:
                    if st.button("Apply Media to All", use_container_width=True):
                        if master_media:
                            st.session_state.master_media_assignment = master_media
                            st.success("Applied media to all accounts!")
                        else:
                            st.session_state.master_media_assignment = None
                            st.success("Cleared master media!")
                        import time
                        time.sleep(1)
                        st.rerun()

            uploaded_images = {}
            for p_id, profile_comms in communities_cache.items():
                st.markdown(f"### Account: {p_id}")
                
                if profile_comms and isinstance(list(profile_comms.values())[0], dict):
                    sorted_comms = dict(sorted(profile_comms.items(), key=lambda item: item[1].get("members", 0), reverse=True))
                else:
                    sorted_comms = profile_comms
                
                comm_names = list(sorted_comms.keys())
                default_selections = []
                
                st.session_state.pool_selections[p_id] = st.multiselect(
                    f"Select community pool for {p_id} (will randomly post to 2):",
                    options=comm_names,
                    default=default_selections,
                    key=f"pool_{p_id}"
                )
                
                if f"input_{p_id}" not in st.session_state:
                    st.session_state[f"input_{p_id}"] = st.session_state.drafted_messages.get(p_id, "")
                
                st.session_state.drafted_messages[p_id] = st.text_area(
                    f"Message for {p_id}:", 
                    max_chars=280,
                    key=f"input_{p_id}"
                )
                
                if f"comment_{p_id}" not in st.session_state:
                    st.session_state[f"comment_{p_id}"] = st.session_state.drafted_comments.get(p_id, "")
                    
                st.session_state.drafted_comments[p_id] = st.text_area(
                    f"Comments to add in {p_id} (Separate multiple comments with '---'):", 
                    height=100,
                    key=f"comment_{p_id}"
                )
                
                uploaded_images[p_id] = st.file_uploader(
                    f"Upload Media for {p_id} (Optional)", 
                    type=["jpg", "jpeg", "png", "mp4", "mov"], 
                    key=f"img_{p_id}"
                )
                st.divider()
                
            if st.session_state.get("master_media_assignment"):
                for p_id in communities_cache.keys():
                    if not uploaded_images.get(p_id):
                        uploaded_images[p_id] = st.session_state.master_media_assignment
                        
            if st.session_state.get("vault_media_assignments"):
                for p_id, media_file in st.session_state.vault_media_assignments.items():
                    if not uploaded_images.get(p_id):
                        uploaded_images[p_id] = media_file
                        
            def reshuffle_callback():
                pass

            st.divider()
            st.subheader("Bulk Media Upload (Optional)")
            st.write("Upload multiple media files here. Accounts that don't have a specific media assigned will randomly receive one of these!")
            bulk_images = st.file_uploader("Upload Bulk Media", type=["jpg", "jpeg", "png", "mp4", "mov"], accept_multiple_files=True, key="bulk_images_uploader")
            
            if "bulk_image_assignments" not in st.session_state:
                st.session_state.bulk_image_assignments = {}
            
            if bulk_images:
                col_btn1, col_btn2 = st.columns([0.5, 0.5])
                with col_btn1:
                    apply_btn = st.button("Apply Image Distribution", use_container_width=True)
                with col_btn2:
                    clear_btn = st.button("Clear Distribution", use_container_width=True)
                
                if clear_btn:
                    st.session_state.bulk_image_assignments = {}
                    st.success("Cleared all image auto-fills.")
                elif apply_btn:
                    import random
                    assignments = {}
                    for p_id in communities_cache.keys():
                        if not uploaded_images.get(p_id):
                            img = random.choice(bulk_images)
                            assignments[p_id] = img
                    st.session_state.bulk_image_assignments = assignments
                    st.success(f"Successfully distributed images across {len(assignments)} accounts!")
                
                for acct, img in st.session_state.bulk_image_assignments.items():
                    if not uploaded_images.get(acct) and img in bulk_images:
                        uploaded_images[acct] = img
                        
                if st.session_state.bulk_image_assignments:
                    with st.expander("View Image Distribution Map"):
                        for acct, img in st.session_state.bulk_image_assignments.items():
                            if img in bulk_images:
                                st.text(f":material/check_circle: {acct} -> {img.name}")
            else:
                st.session_state.bulk_image_assignments = {}

            st.divider()
            st.subheader("Bulk JSON Upload (Optional)")
            st.write("Paste a JSON list of messages (e.g. `[\"Post 1\", \"Post 2\"]`). If provided, the bot will randomly pick from this list instead of using the individual boxes above, ensuring every post gets a unique text!")
            
            bulk_json_input = st.text_area("Bulk JSON List", value="", height=150, help='Must be a valid JSON array like: ["Hello!", "Hi there!"]')
            bulk_json_drafts = []
            if bulk_json_input.strip():
                try:
                    import json
                    parsed_json = json.loads(bulk_json_input)
                    if isinstance(parsed_json, list) and len(parsed_json) > 0:
                        bulk_json_drafts = parsed_json
                        st.success(f"Successfully loaded {len(bulk_json_drafts)} unique drafts from JSON.")
                    else:
                        st.warning("JSON must be a list of strings.")
                except Exception as e:
                    st.error(f"Invalid JSON format. Make sure it looks like `[\"Text 1\", \"Text 2\"]`. Error: {e}")

            st.divider()
            st.subheader("Execution Settings")
            import datetime
            
            exec_mode = st.radio("Execution Mode", ["Single Run", "Recurring Vault Run (Auto-Poster)"])
            
            st.write("### Start Timing")
            col_set1, col_set2 = st.columns(2)
            with col_set1:
                schedule_date = st.date_input("Schedule Date (Start)", value="today")
            with col_set2:
                schedule_time = st.time_input("Schedule Time (Start)", value="now")
                
            interval_hours, interval_minutes, run_count = 0, 0, 1
            image_frequency = 0
            if exec_mode == "Recurring Vault Run (Auto-Poster)":
                st.write("### Recurring Settings")
                st.info("In Recurring Mode, the system will ignore the text boxes above and instead pick randomly from your Saved Vault for each run.")
                col_rec1, col_rec2, col_rec3 = st.columns(3)
                with col_rec1:
                    interval_hours = st.number_input("Interval (Hours)", min_value=0, value=1)
                with col_rec2:
                    interval_minutes = st.number_input("Interval (Minutes)", min_value=0, max_value=59, value=30)
                with col_rec3:
                    run_count = st.number_input("Total Runs", min_value=1, value=5)
                    
                image_frequency = st.number_input(f"Image Usage (Out of {run_count} runs, how many should include an image?)", min_value=0, max_value=run_count, value=run_count)
            
            publish_triggered = st.button("Execute Publish Sequence", type="primary", use_container_width=True)
            
            st.divider()
            st.subheader("Scheduled Queue")
            
            queue_data = []
            if os.path.exists("scheduled_queue.json"):
                for attempt in range(5):
                    try:
                        with open("scheduled_queue.json", "r") as f:
                            content = f.read().strip()
                            if content:
                                queue_data = json.loads(content)
                        break
                    except Exception:
                        if attempt < 4:
                            import time
                            time.sleep(0.5)
                        else:
                            st.error("Could not read scheduled_queue.json because it is currently locked by the background worker. Please try again in a few seconds.")
            
            if queue_data:
                for idx, job in enumerate(queue_data):
                    col_q1, col_q2 = st.columns([0.8, 0.2])
                    col_q1.write(f"**Job {idx+1}**: Scheduled for {job['scheduled_datetime']} ({len(job['active_drafts'])} posts)")
                    if col_q2.button(f"Cancel Job {idx+1}", key=f"del_job_{job['id']}"):
                        queue_data = [j for j in queue_data if j['id'] != job['id']]
                        with open("scheduled_queue.json", "w") as f:
                            json.dump(queue_data, f, indent=4)
                        st.rerun()
            else:
                st.info("No upcoming scheduled posts.")
            
            # --- PHASE 3: SEQUENTIAL EXECUTION (Index-Based Distribution) ---
            if publish_triggered:
                all_keys = list(communities_cache.keys())
                pool_selections = {k: st.session_state.pool_selections.get(k, []) for k in all_keys}
                scheduled_datetime = datetime.datetime.combine(schedule_date, schedule_time)
                now = datetime.datetime.now()
                
                if exec_mode == "Recurring Vault Run (Auto-Poster)":
                    vault_payloads = []
                    if os.path.exists("saved_drafts.json"):
                        try:
                            with open("saved_drafts.json", "r") as f:
                                data = json.load(f)
                                vault_payloads = list(data.values()) if isinstance(data, dict) else data
                        except: pass
                    
                    if not vault_payloads:
                        st.error("Your Vault is empty! Please save some drafts to the Vault first before running in Recurring Mode.")
                    else:
                        import random
                        base_job_id = str(int(time.time()))
                        os.makedirs("scheduled_uploads", exist_ok=True)
                        
                        runs_with_images = set(random.sample(range(run_count), min(int(image_frequency), run_count)))
                        
                        for i in range(run_count):
                            job_dt = scheduled_datetime + datetime.timedelta(hours=interval_hours * i, minutes=interval_minutes * i)
                            
                            job_active_drafts = {}
                            job_active_comments = {}
                            uploaded_images_paths = {}
                            
                            for p_id in all_keys:
                                if not pool_selections.get(p_id): continue
                                
                                choice = random.choice(vault_payloads)
                                job_active_drafts[p_id] = choice.get("message", "")
                                job_active_comments[p_id] = choice.get("comments", "")
                                
                                if i in runs_with_images:
                                    comm_img = None
                                    comm_img_path = None
                                    
                                    vault_img_files = []
                                    if os.path.exists("image_vault"):
                                        vault_img_files = [f for f in os.listdir("image_vault") if os.path.isfile(os.path.join("image_vault", f))]
                                        
                                    if vault_img_files:
                                        chosen_vault_img = random.choice(vault_img_files)
                                        comm_img_path = os.path.join("image_vault", chosen_vault_img)
                                    elif 'bulk_images' in locals() and bulk_images:
                                        comm_img = random.choice(bulk_images)
                                    else:
                                        comm_img = uploaded_images.get(p_id)
                                        
                                    if comm_img_path:
                                        import shutil
                                        safe_pid = "".join([c for c in p_id if c.isalnum()]).rstrip()
                                        img_name = os.path.basename(comm_img_path)
                                        dest_path = os.path.join("scheduled_uploads", f"{base_job_id}_{i}_{safe_pid}_{img_name}")
                                        shutil.copy2(comm_img_path, dest_path)
                                        uploaded_images_paths[p_id] = dest_path
                                    elif comm_img:
                                        safe_pid = "".join([c for c in p_id if c.isalnum()]).rstrip()
                                        img_path = os.path.join("scheduled_uploads", f"{base_job_id}_{i}_{safe_pid}_{comm_img.name}")
                                        with open(img_path, "wb") as f: 
                                            f.write(comm_img.getbuffer())
                                        uploaded_images_paths[p_id] = img_path
                                    
                            new_job = {
                                "id": f"{base_job_id}_{i}",
                                "scheduled_datetime": job_dt.isoformat(),
                                "active_drafts": job_active_drafts,
                                "active_comments": job_active_comments,
                                "pool_selections": pool_selections,
                                "bulk_json_drafts": [],
                                "uploaded_images": uploaded_images_paths
                            }
                            queue_data.append(new_job)
                            
                        with open("scheduled_queue.json", "w") as f:
                            json.dump(queue_data, f, indent=4)
                            
                        st.success(f"Queued {run_count} recurring jobs starting from {scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')}.")
                        st.info("Please make sure the background worker is running. (Run `./start_worker.sh` in your terminal)")
                        time.sleep(2)
                        st.rerun()
                        
                else:
                    active_drafts = {k: st.session_state.drafted_messages.get(k, "") for k in all_keys if st.session_state.drafted_messages.get(k, "").strip() or uploaded_images.get(k) is not None}
                    active_comments = {k: st.session_state.drafted_comments.get(k, "") for k in all_keys}
                    
                    if not active_drafts and not bulk_json_drafts:
                        st.warning("Please draft at least one message or provide a Bulk JSON list before executing.")
                    else:
                        if scheduled_datetime > now:
                            job_id = str(int(time.time()))
                            
                            uploaded_images_paths = {}
                            os.makedirs("scheduled_uploads", exist_ok=True)
                            for p_id, comm_img in uploaded_images.items():
                                if comm_img:
                                    safe_pid = "".join([c for c in p_id if c.isalnum()]).rstrip()
                                    img_path = os.path.join("scheduled_uploads", f"{job_id}_{safe_pid}_{comm_img.name}")
                                    with open(img_path, "wb") as f: 
                                        f.write(comm_img.getbuffer())
                                    uploaded_images_paths[p_id] = img_path
                                    
                            new_job = {
                                "id": job_id,
                                "scheduled_datetime": scheduled_datetime.isoformat(),
                                "active_drafts": active_drafts,
                                "active_comments": active_comments,
                                "pool_selections": pool_selections,
                                "bulk_json_drafts": bulk_json_drafts,
                                "uploaded_images": uploaded_images_paths
                            }
                            
                            queue_data.append(new_job)
                            with open("scheduled_queue.json", "w") as f:
                                json.dump(queue_data, f, indent=4)
                                
                            st.success(f"Post sequence queued for {scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')}.")
                            st.info("Please make sure the background worker is running. (Run `./start_worker.sh` in your terminal)")
                            
                            time.sleep(2)
                            st.rerun()
                            
                        else:
                            st.divider()
                            st.subheader("Execution Log")
                            
                            # Get accounts to post to (must have drafts and selected pool)
                            keys_to_process = list(active_drafts.keys()) + (list(communities_cache.keys()) if bulk_json_drafts else [])
                            unique_keys = []
                            for k in keys_to_process:
                                if k not in unique_keys:
                                    unique_keys.append(k)
                                    
                            for p_id in unique_keys:
                                if p_id not in active_drafts and not bulk_json_drafts: continue
                                
                                st.markdown(f"### Initiating Profile: {p_id}")
                                prof_data = next((p for p in profiles_data if p["id"] == p_id), None)
                                if not prof_data: continue
                                
                                pool = pool_selections.get(p_id, [])
                                if not pool:
                                    st.warning(f"No communities selected for {p_id}.")
                                    continue
                                    
                                to_post = random.sample(pool, min(2, len(pool)))
                                profile_comms = communities_cache.get(p_id, {})
                                
                                drafted_text = active_drafts.get(p_id, "")
                                comment_text = active_comments.get(p_id, "")
                                comm_img = uploaded_images.get(p_id)
                                
                                for i, comm_name in enumerate(to_post):
                                    target_url = profile_comms.get(comm_name, {}).get("url") if isinstance(profile_comms.get(comm_name), dict) else profile_comms.get(comm_name)
                                    if not target_url or "suggested" in target_url:
                                        continue
                                    
                                    if bulk_json_drafts:
                                        drafted_text = random.choice(bulk_json_drafts)
                                    
                                    st.write(f"Posting to '{comm_name}' (Random Selection #{i+1})...")
                                    temp_file_path = None
                                    if comm_img:
                                        os.makedirs("temp_uploads", exist_ok=True)
                                        safe_pid = "".join([c for c in p_id if c.isalnum()]).rstrip()
                                        temp_file_path = os.path.join("temp_uploads", f"{safe_pid}_{comm_img.name}")
                                        with open(temp_file_path, "wb") as f: 
                                            f.write(comm_img.getbuffer())
                                    
                                    success = process_profile(prof_data, drafted_text, temp_file_path, target_url, comment_text)
                                    if success:
                                        record_community_post(p_id, target_url)
                                    else:
                                        st.warning(f"Post failed for '{comm_name}', skipping record.")
                                    
                                    if temp_file_path and os.path.exists(temp_file_path): 
                                        os.remove(temp_file_path)
                                    
                                    wait_time = random.randint(15, 30)
                                    p_bar = st.progress(0)
                                    for secs in range(wait_time):
                                        time.sleep(random.uniform(0.8, 1.5))
                                        p_bar.progress((secs + 1) / wait_time, text=f":material/hourglass_empty: Pacing: Waiting {wait_time - secs}s before next post...")
                                        
                            st.success("Random Publish Complete.")
    else:
        st.info("Configure a user record target inside the 'Manage Accounts' tab first.")

# TAB 2: ACCOUNT CONFIGURATION ADMIN
with tab2:
    st.header("Account Profile Configuration Database")
    action = st.radio("Database Action", ["Edit Existing Profile", ":material/add: Add New Profile"])
    
    current_user_data_dir = ""
    current_p_id = ""
    
    # --- FIX: Move selection outside the form so it triggers an immediate UI update ---
    target_prof = {}
    edit_id = None
    if action == "Edit Existing Profile" and profiles_data:
        profile_ids = [p["id"] for p in profiles_data]
        edit_id = st.selectbox("Select Profile ID to Modify", options=profile_ids)
        target_prof = next((p for p in profiles_data if p["id"] == edit_id), {})

    with st.form("profile_management_form"):
        if action == "Edit Existing Profile" and profiles_data:
            p_id = edit_id
            username = st.text_input("Username/Email Address Handle", value=target_prof.get("username", ""))
            password = st.text_input("Direct Password Configuration", value=target_prof.get("password", ""), type="password")
            user_data_dir = st.text_input("Storage Isolation Profile Path", value=target_prof.get("user_data_dir", f"./user_data/{p_id}"))
            
            current_user_data_dir = user_data_dir
            current_p_id = p_id
        else:
            p_id = st.text_input("Create Unique Profile ID (e.g. tech_handle)")
            username = st.text_input("Username/Email Address Handle")
            password = st.text_input("Direct Password Configuration", type="password")
            user_data_dir = st.text_input("Storage Isolation Profile Path", value=f"./user_data/{p_id}" if p_id else "./user_data/")
            
            current_user_data_dir = user_data_dir
            current_p_id = p_id
            
        submit_save = st.form_submit_button(":material/save: Save Profile Configuration")
        # Add inside the form, below the submit button
        delete_btn = st.form_submit_button(":material/delete: Delete Selected Profile", type="primary")
        
        if submit_save:
            if not p_id or not username or not password:
                st.error("All credential attributes require active inputs before changes can be stored.")
            else:
                new_entry = {
                    "id": p_id, 
                    "username": username, 
                    "password": password, 
                    "user_data_dir": user_data_dir
                }
                updated_profiles = [p for p in profiles_data if p["id"] != p_id]
                updated_profiles.append(new_entry)
                save_profiles(updated_profiles)
                st.success("Profile attributes committed successfully!")
                time.sleep(0.5)
                st.rerun()
        elif delete_btn and edit_id:
            updated_profiles = [p for p in profiles_data if p["id"] != edit_id]
            save_profiles(updated_profiles)
            
            # --- Deep Cleanup: Remove ghost data from cache files ---
            if os.path.exists("communities_cache.json"):
                try:
                    with open("communities_cache.json", "r") as f:
                        comm_cache = json.load(f)
                    if edit_id in comm_cache:
                        del comm_cache[edit_id]
                        with open("communities_cache.json", "w") as f:
                            json.dump(comm_cache, f, indent=4)
                except Exception:
                    pass
                    
            if os.path.exists("daily_post_history.json"):
                try:
                    with open("daily_post_history.json", "r") as f:
                        history = json.load(f)
                    if edit_id in history:
                        del history[edit_id]
                        with open("daily_post_history.json", "w") as f:
                            json.dump(history, f, indent=4)
                except Exception:
                    pass
            # --------------------------------------------------------
            
            st.warning(f"Profile {edit_id} and all associated community data deleted successfully.")
            time.sleep(random.uniform(0.8, 1.5))
            st.rerun()

    st.divider()
    st.subheader("Initial Setup (Sighted Helper Required)")
    st.write("Run this once per account to manually verify the login session. A visible browser page will open.")

    if user_data_dir: 
        button_label = f" Open Visible Browser to Log In [{p_id}]" if p_id else " Open Visible Browser to Log In"
        login_triggered = st.button(button_label)
        
        if login_triggered:
            with st.spinner("Opening browser... Please log in, WAIT 5 SECONDS, then manually close the browser tab."):
                success, message = setup_persistent_session(user_data_dir, "https://x.com")
                if success:
                    st.success(message)
                else:
                    st.error(message)
    else:
        st.info("Please enter a Storage Isolation Profile Path above to enable the login browser.")

    st.divider()
    st.subheader("Community Management Tool")
    st.write("Find accounts missing a specific community and make them join.")
    
    all_communities = {}
    try:
        if os.path.exists("communities_cache.json"):
            with open("communities_cache.json", "r") as f:
                cached_data = json.load(f)
                for acc_id, comms in cached_data.items():
                    for c_name, c_info in comms.items():
                        c_url = c_info.get("url")
                        if c_url:
                            if c_url not in all_communities:
                                all_communities[c_url] = {"name": c_name, "url": c_url, "members": []}
                            if acc_id not in all_communities[c_url]["members"]:
                                all_communities[c_url]["members"].append(acc_id)
    except Exception as e:
        st.error(f"Error loading communities cache: {e}")

    if all_communities:
        comm_options = {c_url: f"{info['name']} ({c_url})" for c_url, info in all_communities.items()}
        selected_comm_url = st.selectbox("Select a Community to cross-check:", options=[""] + list(comm_options.keys()), format_func=lambda x: comm_options[x] if x else "Choose a community...")
        
        if selected_comm_url:
            members = all_communities[selected_comm_url]["members"]
            missing_accounts = [p for p in profiles_data if p["id"] not in members]
            
            if missing_accounts:
                st.write(f"### Accounts missing '{all_communities[selected_comm_url]['name']}'")
                for missing_acc in missing_accounts:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{missing_acc['id']}** ({missing_acc.get('username', '')})")
                    with col2:
                        btn_key = f"join_{missing_acc['id']}_{selected_comm_url}"
                        if st.button("Join Community", key=btn_key):
                            with st.spinner(f"Joining {all_communities[selected_comm_url]['name']} for {missing_acc['id']}..."):
                                success, message = force_join_community(missing_acc, selected_comm_url)
                                if success:
                                    st.success(message)
                                    # Update cache so it doesn't show up again
                                    try:
                                        with open("communities_cache.json", "r") as f:
                                            cache = json.load(f)
                                        if missing_acc['id'] not in cache:
                                            cache[missing_acc['id']] = {}
                                        cache[missing_acc['id']][all_communities[selected_comm_url]['name']] = {
                                            "url": selected_comm_url,
                                            "members": 0
                                        }
                                        with open("communities_cache.json", "w") as f:
                                            json.dump(cache, f, indent=4)
                                    except:
                                        pass
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(message)
            else:
                st.success("All configured accounts are already members of this community!")
    else:
        st.info("No communities cached yet. Please sync accounts first to populate the cache.")

    st.divider()
    st.subheader("Cloudflare Security Status Check")
    st.write("Run a bulk check to see if any accounts are currently blocked by a Cloudflare 'Security Verification' screen.")
    
    if profiles_data:
        if st.button("Run Bulk Security Check (3-Bot Chunking)", use_container_width=True):
            with st.spinner("Checking all accounts... (Running 3 concurrent bots)"):
                
                def process_cf_chunk(chunk):
                    results = []
                    for profile_id, prof in chunk:
                        status = check_cloudflare_status(prof)
                        results.append((profile_id, status))
                    return results

                items = [(p["id"], p) for p in profiles_data]
                chunk_size = 10
                chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
                
                all_results = []
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    for chunk_res in executor.map(process_cf_chunk, chunks):
                        all_results.extend(chunk_res)
                        
                st.session_state.cf_check_results = all_results
                st.rerun()

        if "cf_check_results" in st.session_state:
            st.write("### Security Check Results")
            blocked_accounts = []
            for p_id, status in st.session_state.cf_check_results:
                if status == "Blocked":
                    st.error(f"{p_id}: Blocked by Cloudflare Security Verification")
                    blocked_accounts.append(p_id)
                elif status == "OK":
                    st.success(f"{p_id}: Clear (No Security Verification found)")
                else:
                    st.warning(f"{p_id}: {status}")
                    
            if blocked_accounts:
                st.info(f"Total Blocked Accounts: {len(blocked_accounts)}. Use the 'Manual Sync via Visible Browser' tool above to log into these accounts and solve the challenge manually.")

# TAB 3: AUTO-RESPONDER
with tab3:
    st.header(":material/chat: Automated Message Responder")
    st.write("Automatically reply to messages in your **Priority** and **Other (Hidden)** message tabs on X.")
    
    if not profiles_data:
        st.info("Configure a user record target inside the 'Manage Accounts' tab first.")
    else:
        run_all = st.checkbox("Run for ALL Profiles", value=False)
        
        profile_options = {p["id"]: p for p in profiles_data}
        if not run_all:
            selected_responder_id = st.selectbox("Select Profile for Auto-Responder", options=list(profile_options.keys()), key="responder_profile_select")
        
        chat_password = st.text_input("Chat Unlock Password", value="2004", type="password", help="The password to unlock your chats when opening X messages for the first time.")
        universal_message = st.text_area("Universal Reply Message", value="Message received.", height=100)
        
        col_chk1, col_chk2 = st.columns(2)
        with col_chk1:
            process_priority = st.checkbox("Check 'Priority' tab", value=True)
        with col_chk2:
            process_hidden = st.checkbox("Check 'Other' (Hidden) tab", value=True)
            
        skip_older_than_hours = st.number_input("Skip messages older than (hours)", min_value=0.0, value=2.0, step=0.5, help="Messages older than this will be skipped automatically. Set to 0 to process all.")
        
        if st.button("Start Auto-Responder Sequence", type="primary", use_container_width=True):
            if not process_priority and not process_hidden:
                st.warning("Please select at least one tab to check (Priority or Other).")
            else:
                profiles_to_run = profiles_data if run_all else [profile_options[selected_responder_id]]
                
                with st.spinner(f"Running auto-responder for {len(profiles_to_run)} profile(s)... This will open a visible browser."):
                    for prof in profiles_to_run:
                        st.write(f"Processing profile: {prof['id']}...")
                        process_auto_responder(
                            profile=prof, 
                            universal_msg=universal_message, 
                            check_priority=process_priority, 
                            check_hidden=process_hidden,
                            unlock_password=chat_password,
                            skip_older_than_hours=skip_older_than_hours
                        )
                    st.success("Auto-responder sequence complete.")
        
        st.divider()
        st.subheader("Background Scheduling")
        st.write("Schedule the auto-responder to check automatically in the background using the background worker.")
        
        col_sch1, col_sch2 = st.columns(2)
        with col_sch1:
            check_interval = st.number_input("Check Interval (minutes)", min_value=1, value=60)
        with col_sch2:
            max_checks = st.number_input("Max Checks (0 = Infinite)", min_value=0, value=0)
            
        if st.button("Schedule in Background", type="secondary", use_container_width=True):
            if not process_priority and not process_hidden:
                st.warning("Please select at least one tab to check (Priority or Other).")
            else:
                config = {
                    "interval_minutes": check_interval,
                    "max_checks": max_checks,
                    "run_all": run_all,
                    "selected_profile": selected_responder_id if not run_all else None,
                    "universal_msg": universal_message,
                    "check_priority": process_priority,
                    "check_hidden": process_hidden,
                    "unlock_password": chat_password,
                    "skip_older_than_hours": skip_older_than_hours,
                    "checks_completed": 0,
                    "last_checked_iso": None,
                    "is_active": True
                }
                with open("auto_responder_config.json", "w") as f:
                    json.dump(config, f, indent=4)
                st.success(f"Background Auto-Responder Scheduled. (Interval: {check_interval}m)")
                st.info("Make sure `./start_worker.sh` is running.")
                time.sleep(2)
                st.rerun()

        if os.path.exists("auto_responder_config.json"):
            try:
                with open("auto_responder_config.json", "r") as f:
                    cfg = json.load(f)
                if cfg.get("is_active"):
                    st.success(f"Currently active in background! Checked {cfg.get('checks_completed', 0)} times.")
                    if st.button(":material/stop: Stop Background Auto-Responder", type="primary"):
                        cfg["is_active"] = False
                        with open("auto_responder_config.json", "w") as f:
                            json.dump(cfg, f, indent=4)
                        st.rerun()
            except:
                pass
with tab4:
    st.header("Promo Media Manager")
    st.write("View and delete promo videos currently stored in the promo vault.")
    
    promo_vault_dir = "promo_vault_media"
    os.makedirs(promo_vault_dir, exist_ok=True)
    existing_promos = os.listdir(promo_vault_dir)
    
    if not existing_promos:
        st.info("No promo videos found in the vault.")
    else:
        for vid_name in existing_promos:
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                try:
                    st.video(os.path.join(promo_vault_dir, vid_name))
                except Exception as e:
                    st.error(f"Could not load video {vid_name}: {e}")
                st.write(f"**{vid_name}**")
            with col2:
                if st.button("Delete", key=f"del_promo_tab4_{vid_name}"):
                    try:
                        os.remove(os.path.join(promo_vault_dir, vid_name))
                        st.success(f"Deleted {vid_name}")
                        import time
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete {vid_name}: {e}")
            st.divider()

with tab5:
    import sys
    import account_creator
    import account_login
    import account_creator_email
    import email_alias_manager
    from herosms_client import HeroSMSClient
    import female_profile_vault
    import batch_account_creator

    def render_batch_creator_ui(default_method="email_alias", key_prefix="batch_"):
        runner = batch_account_creator.BatchAccountRunner.get_instance()
        b_status = runner.get_status()
        is_running = b_status.get("is_running", False)
        
        col_bc1, col_bc2 = st.columns([0.55, 0.45])
        
        with col_bc1:
            st.subheader(":material/tune: Batch Execution Parameters")
            b_count = st.number_input(
                "Total Accounts to Create",
                min_value=1,
                max_value=None,
                value=int(b_status.get("target_count") or 10) if is_running else 10,
                step=1,
                help="Set as many accounts to create as desired. No limit.",
                disabled=is_running,
                key=f"{key_prefix}acc_count_input"
            )
            
            b_method_choice = st.radio(
                "Provisioning Engine",
                options=["Email Alias (Gmail Dot Trick / Plus)", "HeroSMS (Automated Phone Rental)"],
                index=0 if default_method == "email_alias" else 1,
                horizontal=True,
                disabled=is_running,
                key=f"{key_prefix}method_radio"
            )
            method_key = "email_alias" if "Email" in b_method_choice else "herosms"

            c_int1, c_int2 = st.columns(2)
            b_interval = c_int1.slider(
                "Base Interval (Minutes)",
                min_value=30,
                max_value=120,
                value=60,
                step=5,
                help="Base cooldown time between each account creation.",
                disabled=is_running,
                key=f"{key_prefix}base_interval_slider"
            )
            b_jitter = c_int2.slider(
                "Random Human Jitter (± Minutes)",
                min_value=0,
                max_value=20,
                value=10,
                step=1,
                help="Adds random variance so intervals are not exact robotic intervals. E.g. 60m ± 10m = 50 to 70 mins.",
                disabled=is_running,
                key=f"{key_prefix}jitter_slider"
            )
            b_retries = c_int1.number_input(
                "Max Retries per Account on Transient Failure",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                help="If registration encounters a network timeout or missing dialog, automatically retries up to this many times (with 15s backoff) before entering cooldown.",
                disabled=is_running,
                key=f"{key_prefix}retries_input"
            )
            st.caption(f"**Actual Pacing:** Each creation will be spaced by **{max(5, b_interval - b_jitter)} to {b_interval + b_jitter} minutes** with **up to {b_retries} automatic retries** per account on transient failure.")

        with col_bc2:
            if method_key == "email_alias":
                st.subheader(":material/alternate_email: Alias Blueprint Settings")
                b_base_email = st.text_input(
                    "Primary Base Gmail Address",
                    value=st.session_state.get("email_base_address", "davidosili93@gmail.com"),
                    help="Incoming verification emails will land in this inbox.",
                    disabled=is_running,
                    key=f"{key_prefix}base_email_input"
                )
                st.session_state.email_base_address = b_base_email

                b_strat = st.radio(
                    "Email Alias Strategy",
                    options=["Gmail Dot Trick (d.avido...)", "Gmail Plus Addressing (+tag)"],
                    index=0,
                    horizontal=True,
                    disabled=is_running,
                    key=f"{key_prefix}strat_radio"
                )
                strat_val = "dot" if "Dot" in b_strat else "plus"

                b_gmail_app_pwd = st.text_input(
                    "Gmail App Password (Optional - for Auto-OTP Extraction)",
                    value="",
                    type="password",
                    placeholder="16-character App Password (leave blank for interactive code entry)",
                    help="If provided, the bot autonomously connects via IMAP SSL to fetch the 6-digit verification code from Gmail without you typing it.",
                    disabled=is_running,
                    key=f"{key_prefix}app_pwd_input"
                )
            else:
                b_base_email = "davidosili93@gmail.com"
                strat_val = "dot"
                b_gmail_app_pwd = ""
                st.subheader(":material/settings_suggest: HeroSMS Settings")
                st.info("Service Target: Twitter / X (US virtual line). Enforces 20s minimum wait and automatic SMS polling.")

            st.subheader(":material/tune: Profile Customization & Stealth Stack")
            b_engine_choice = st.selectbox(
                "Browser Engine",
                ["Google Chrome (Default)", "Microsoft Edge", "Brave Browser", "Auto-Rotate across available browsers"],
                index=0,
                disabled=is_running,
                key=f"{key_prefix}browser_engine_sb"
            )
            b_engine_map = {
                "Google Chrome (Default)": "chrome",
                "Microsoft Edge": "msedge",
                "Brave Browser": "brave",
                "Auto-Rotate across available browsers": "rotate"
            }
            selected_b_engine = b_engine_map.get(b_engine_choice, "chrome")
            b_vault = st.checkbox("Auto-pick Name & Bio from Female Vault", value=True, disabled=is_running, key=f"{key_prefix}vault_cb")
            b_attach_web = st.checkbox("Attach Promo Website Link", value=True, disabled=is_running, key=f"{key_prefix}attach_web_cb")
            b_web_url = st.text_input("Website URL", value="https://getmysocial.com/uwuscrettt", disabled=is_running or not b_attach_web, key=f"{key_prefix}web_url_input")
            b_rotate_vpn = st.checkbox("Rotate VPN Location via Windscribe CLI between accounts (Optional)", value=False, disabled=is_running, key=f"{key_prefix}rotate_vpn_cb")
            
            disp_info = "Windows Native Desktop" if sys.platform == "win32" else "display :0 (Hardware GPU)"
            st.info(f"**Display Pipeline**: Executes {b_engine_choice} via Patchright on {disp_info} with stealth args.")

        st.divider()

        # Action Buttons
        col_btn_start, col_btn_stop = st.columns([0.65, 0.35])
        
        if not is_running:
            disp_method_tag = "Email Alias" if "Email" in b_method_choice else "HeroSMS"
            if col_btn_start.button(f":material/rocket_launch: Start Hourly Batch Creation ({b_count} Accounts via {disp_method_tag})", type="primary", use_container_width=True, key=f"{key_prefix}btn_start"):
                ok, msg = runner.start_batch(
                    count=b_count,
                    base_interval_mins=b_interval,
                    jitter_mins=b_jitter,
                    method=method_key,
                    base_email=b_base_email,
                    strategy=strat_val,
                    use_female_vault=b_vault,
                    website_url=b_web_url if b_attach_web else "",
                    gmail_app_password=b_gmail_app_pwd,
                    rotate_vpn=b_rotate_vpn,
                    max_retries=b_retries,
                    browser_engine=selected_b_engine
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            if col_btn_stop.button(":material/stop_circle: Stop / Cancel Batch Runner", type="secondary", use_container_width=True, key=f"{key_prefix}btn_stop"):
                runner.stop()
                st.warning("Cancellation requested. Stopping...")
                time.sleep(1)
                st.rerun()

        # Live Monitor Card
        st.subheader(":material/monitoring: Batch Execution Monitor")
        current_phase = b_status.get("current_phase", "idle")
        phase_color = {
            "idle": "IDLE",
            "starting": "STARTING",
            "creating": "CREATING ACCOUNT",
            "awaiting_code": "AWAITING VERIFICATION CODE",
            "cooldown": "RESTING / COOLDOWN",
            "completed": "COMPLETED",
            "stopped": "STOPPED",
            "error": "ERROR"
        }.get(current_phase, current_phase.upper())
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Current State", phase_color)
        m_col2.metric("Target Total", f"{b_status.get('target_count', 0)} accounts")
        m_col3.metric("Successfully Created", f"{b_status.get('completed_count', 0)}")
        m_col4.metric("Failed", f"{b_status.get('failed_count', 0)}")
        
        tot = b_status.get("target_count", 1) or 1
        comp = b_status.get("completed_count", 0)
        prog_ratio = min(1.0, max(0.0, comp / tot))
        st.progress(prog_ratio, text=f"Overall Progress: {comp} / {tot} accounts provisioned ({int(prog_ratio * 100)}%)")
        
        st.info(f"**Status Message:** {b_status.get('status_message', '')}")
        
        curr_screen = b_status.get("current_screenshot")
        if curr_screen and os.path.exists(curr_screen):
            with st.expander(":material/screenshot: Current Browser Step Screen Capture", expanded=(current_phase == "awaiting_code")):
                st.image(curr_screen, caption=f"Live capture: {curr_screen}", use_container_width=True)
        
        # INTERACTIVE CODE ENTRY CARD WHEN AWAITING CODE
        if current_phase == "awaiting_code":
            c_type = b_status.get("code_type", "email")
            code_recipient = b_status.get("code_recipient") or b_status.get("current_alias") or "your email"
            if c_type == "sms":
                st.warning(":material/sms: **SMS Verification Code Dispatched!**")
                st.markdown(f"Twitter / X dispatched an SMS confirmation code to rented phone: **`+1 {code_recipient}`** (HeroSMS).")
                st.caption(":material/smart_toy: **Autonomous Monitoring Active:** Bot is polling HeroSMS every 2 seconds. As soon as HeroSMS receives the code, it will submit it automatically.")
            else:
                st.warning(":material/mark_email_unread: **Interactive Verification Code Required!**")
                st.markdown(f"Twitter / X has dispatched a 6-digit confirmation code to: **`{code_recipient}`** (arriving in primary inbox **`{b_status.get('base_email', 'davidosili93@gmail.com')}`**).")
            st.markdown("**Enter the code below (or wait for automatic capture) to finalize this account:**")
            
            c_code1, c_code2, c_code3 = st.columns([0.5, 0.3, 0.2])
            interactive_code_input = c_code1.text_input("6-Digit Code", placeholder="e.g. 849201", max_chars=10, key=f"{key_prefix}interactive_code_input")
            if c_code2.button(":material/send: Submit Code", type="primary", use_container_width=True, key=f"{key_prefix}btn_submit_code"):
                if interactive_code_input.strip():
                    ok, msg = runner.submit_verification_code(interactive_code_input.strip())
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Please enter the verification code first.")
            if c_code3.button(":material/cancel: Cancel Batch", use_container_width=True, key=f"{key_prefix}btn_cancel_code"):
                runner.stop()
                st.rerun()

        # COOLDOWN COUNTDOWN CARD (Client-Side JS - Uses Chrome's Internal Clock)
        if current_phase == "cooldown":
            import streamlit.components.v1 as components
            target_ts = b_status.get("next_run_timestamp")
            if not target_ts:
                target_ts = time.time() + b_status.get("cooldown_seconds_remaining", 0)
            target_ms = int(target_ts * 1000)
            
            countdown_html = f"""
            <div style="
                background: rgba(255, 170, 0, 0.12);
                border: 1px solid rgba(255, 170, 0, 0.4);
                border-radius: 8px;
                padding: 12px 18px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                gap: 14px;
                margin-bottom: 6px;
            ">
                <div>
                    <div style="font-size: 14.5px; font-weight: 700; color: #ffbe33;">Natural 1-Hour Cooldown Active</div>
                    <div style="font-size: 13px; color: #e2e8f0; margin-top: 3px;">
                        Next account creation scheduled in: <span id="cooldown-timer" style="font-weight: 700; color: #38bdf8; font-family: monospace; font-size: 15px;">Calculating...</span>
                    </div>
                </div>
            </div>
            <script>
                const targetMs = {target_ms};
                function updateTimer() {{
                    const now = Date.now();
                    const diffSec = Math.max(0, Math.floor((targetMs - now) / 1000));
                    const mins = Math.floor(diffSec / 60);
                    const secs = diffSec % 60;
                    const el = document.getElementById('cooldown-timer');
                    if (el) {{
                        el.innerText = `${{mins}}m ${{secs < 10 ? '0' : ''}}${{secs}}s`;
                    }}
                    if (diffSec <= 0) {{
                        setTimeout(() => {{
                            try {{ window.parent.location.reload(); }} catch(e) {{}}
                        }}, 1500);
                    }}
                }}
                updateTimer();
                setInterval(updateTimer, 1000);
            </script>
            """
            components.html(countdown_html, height=80)

        # Results table of accounts created in this run
        created_list = b_status.get("created_accounts", [])
        if created_list:
            st.markdown("**Provisioned Accounts in this Batch:**")
            st.dataframe(created_list, use_container_width=True)
            
        # Live log terminal
        b_logs = b_status.get("logs", [])
        with st.expander(":material/terminal: Live Batch Execution Terminal Logs", expanded=is_running):
            st.text_area("Live Terminal", value="\n".join(b_logs), height=250, key=f"{key_prefix}log_area", disabled=True)
            if is_running and current_phase not in ["cooldown"]:
                time.sleep(4)
                st.rerun()

    st.header(":material/person_add: Account Onboarding & Provisioning")
    st.write("Provision new accounts via automated SMS rental, email aliases with interactive verification, or directly authenticate existing accounts using credentials and 2FA Authenticator codes.")
    
    tab_cred, tab_auto, tab_email, tab_batch = st.tabs([
        ":material/key: Direct Credential Login (Username / 2FA TOTP)",
        ":material/smart_toy: Auto-Create via HeroSMS",
        ":material/alternate_email: Create via Email Alias",
        ":material/timer: Paced Batch Creator (Hourly Automation)"
    ])
    
    with tab_cred:
        login_mode = st.radio(
            "Authentication Pipeline Mode",
            options=[":material/person: Single Account Login", ":material/group_add: Batch / Multi-Account Provisioning"],
            horizontal=True,
            key="cred_login_mode"
        )
        
        if login_mode == ":material/person: Single Account Login":
            st.subheader(":material/key: Direct Account Authentication")
            st.write("Directly log in to an existing X account using its username, password, and 2FA secret (authenticator key). The bot automatically calculates the rotating 6-digit TOTP pin, completes the login flow with stealth native Chrome, updates the profile name and bio if configured, extracts session cookies (`auth_token` and `ct0`), and registers the account in `profiles.json`.")
            
            st.markdown("**Quick-Paste Credentials (Auto-detects Username, Password, 2FA, Name, Bio):**")
            raw_paste = st.text_area(
                "Paste credentials block",
                placeholder="Username: cxen2rjc\nPassword: Bgkhy2ei\n2FA: V4A4IEOBEEECEH6P\nName: Fi Kendall\nBio: Welcome to my world! Link in bio 💋",
                height=110,
                key="cred_login_paste",
                label_visibility="collapsed"
            )
            
            parsed_p = account_login.parse_credentials_text(raw_paste) if raw_paste else {}
            
            col_c1, col_c2 = st.columns([0.6, 0.4])
            with col_c1:
                st.subheader(":material/badge: Account Credentials")
                c_acc_id, c_acc_user = st.columns(2)
                login_acc_id = c_acc_id.text_input("Profile ID", value=account_login.get_next_account_id(), key="login_acc_id", help="Identifier in profiles.json")
                login_username = c_acc_user.text_input("Username / Handle", value=parsed_p.get("username", ""), key="login_username", placeholder="e.g. cxen2rjc")
                
                # Detect if handle already exists in profiles.json
                existing_single_acc = None
                if login_username and os.path.exists("profiles.json"):
                    try:
                        with open("profiles.json", "r") as pf:
                            for p in json.load(pf):
                                if p.get("username", "").strip().lower() == login_username.strip().lower():
                                    existing_single_acc = p
                                    break
                    except Exception:
                        pass
                if existing_single_acc:
                    st.info(f":material/info: **@{login_username}** is already active as **[{existing_single_acc.get('id')}]**. Logging in will re-authenticate this account and update its session.")
                
                c_acc_pwd, c_acc_2fa = st.columns(2)
                login_password = c_acc_pwd.text_input("Password", value=parsed_p.get("password", ""), type="password", key="login_password")
                login_2fa = c_acc_2fa.text_input("2FA Secret Key", value=parsed_p.get("two_factor", ""), key="login_2fa", placeholder="e.g. V4A4IEOBEEECEH6P", help="Base32 TOTP secret from authenticator app")
                
            with col_c2:
                st.subheader(":material/shield: 2FA TOTP Live Status")
                if login_2fa.strip():
                    try:
                        pin_code, rem_sec = account_login.generate_totp_pin(login_2fa.strip())
                        st.success(f"Live 6-Digit PIN: **{pin_code}**")
                        st.caption(f"Valid for {rem_sec}s remaining before next 30s rotation cycle. Matches standard RFC 6238 and browserscan.net/2fa.")
                    except Exception as e:
                        st.error(f"Invalid 2FA secret: {e}")
                else:
                    st.info("Paste or enter a 2FA Secret key to preview the live 6-digit TOTP pin.")
                disp_info = "Windows Native Desktop" if sys.platform == "win32" else "display :0"
                st.info(f"Display Pipeline: Executes Native Google Chrome via Patchright on {disp_info}.")
                st.info("Community Seeding: Automatically pre-populates default booster communities upon login.")
                
            st.write("---")
            st.subheader(":material/edit_note: Profile Presentation Customization on X")
            single_cust_enable = st.checkbox("Customize Profile on Login (Edit Display Name, Bio & Website on X)", value=True, key="single_cust_enable")
            single_disp_name = None
            single_bio = None
            single_website = None
            
            if single_cust_enable:
                sc_col1, sc_col2 = st.columns([0.45, 0.55])
                
                # Check for random vault pick in session_state
                default_single_name = st.session_state.get("single_vault_name", parsed_p.get("display_name", ""))
                default_single_bio = st.session_state.get("single_vault_bio", parsed_p.get("bio", ""))
                
                single_disp_name = sc_col1.text_input("Target Display Name on X", value=default_single_name, placeholder="e.g. Chloe", key="single_disp_name_input")
                single_website = sc_col1.text_input("Target Website Link on X", value="https://getmysocial.com/uwuscrettt", key="single_web_input")
                
                if sc_col1.button(":material/shuffle: Pick Random from Female Vault", key="btn_pick_single_vault"):
                    st.session_state["single_vault_name"] = female_profile_vault.get_random_female_name()
                    st.session_state["single_vault_bio"] = female_profile_vault.get_random_female_bio()
                    st.rerun()
                    
                single_bio = sc_col2.text_area("Target Profile Bio on X", value=default_single_bio, placeholder="e.g. 18 ☆ college is ruining me", height=128, key="single_bio_input")
                
            start_cred_login = st.button(":material/login: Authenticate & Save Account", type="primary", use_container_width=True, key="btn_start_cred_login")
            
            if start_cred_login:
                if not login_username or not login_password:
                    st.error("Username and password are required to log in.")
                else:
                    st.subheader(":material/terminal: Login Execution Stream")
                    login_status_box = st.status(f"Starting login flow for [{login_acc_id}] (@{login_username})...", expanded=True)
                    login_log_placeholder = st.empty()
                    login_messages = []
                    
                    def cred_ui_logger(msg):
                        ts = time.strftime("%H:%M:%S")
                        fmsg = f"[{ts}] {msg}"
                        login_messages.append(fmsg)
                        login_status_box.write(fmsg)
                        login_log_placeholder.text_area("Live Login Output", value="\n".join(login_messages), height=260)
                        
                    try:
                        with st.spinner("Logging in and authenticating 2FA..."):
                            import importlib
                            importlib.reload(account_login)
                            logged_profile = account_login.login_twitter_with_credentials(
                                account_id=login_acc_id,
                                username=login_username,
                                password=login_password,
                                two_factor_secret=login_2fa,
                                display_name=single_disp_name if single_cust_enable else None,
                                bio=single_bio if single_cust_enable else None,
                                website=single_website if single_cust_enable else None,
                                log_fn=cred_ui_logger
                            )
                        login_status_box.update(label=f"Account [{login_acc_id}] successfully authenticated and saved!", state="complete", expanded=False)
                        st.success(f"SUCCESS: Account [{login_acc_id}] (@{logged_profile['username']}) successfully saved and ready!")
                        
                        r1, r2, r3, r4 = st.columns(4)
                        r1.metric("Profile ID", logged_profile.get("id"))
                        r2.metric("Handle", f"@{logged_profile.get('username')}")
                        r3.metric("Display Name", logged_profile.get("display_name") or "(Original)")
                        r4.metric("Session Token", "Captured" if logged_profile.get("auth_token") else "Pending")
                        
                        st.info("Account authenticated! Switch to the 'Manage Accounts' tab above to view your configured profile.")
                    except Exception as exc:
                        login_status_box.update(label=f"Login halted: {exc}", state="error", expanded=True)
                        st.error(f"Error during login: {exc}")
                        if os.path.exists(f"rate_limit_{login_acc_id}.png"):
                            st.warning("Twitter Rate Limit Screenshot:")
                            st.image(f"rate_limit_{login_acc_id}.png", caption="Twitter Rate Limit Capture", use_container_width=True)
                        elif os.path.exists(f"login_fail_{login_acc_id}.png"):
                            st.image(f"login_fail_{login_acc_id}.png", caption="Failure Screenshot", use_container_width=True)

        else:
            # Batch / Multi-Account Provisioning Mode
            st.subheader(":material/group_add: Multi-Account Batch Onboarding & Setup")
            disp_info = "Windows Native Desktop" if sys.platform == "win32" else "display :0"
            st.write(f"Batch authenticate multiple X accounts with parallel bot workers. The bot pool executes stealth logins on {disp_info} using native Google Chrome, computes 2FA TOTP codes, randomizes female names and aesthetic bios, attaches your website link, captures session tokens, and registers each profile in `profiles.json`.")
            
            st.markdown("**Paste Multiple Accounts (Supports `user:pass:2fa`, `user:pass:2fa:name:bio`, `user|pass|2fa`, or multi-line blocks):**")
            batch_raw_text = st.text_area(
                "Batch Accounts Raw Block",
                placeholder="user1:pass1:2FAKEY1:Alice Wonder:VIP Link in bio\nuser2:pass2:2FAKEY2:Bella Starr:Official Account\n\n# Or Key-Value blocks:\nUsername: user3\nPassword: pass3\n2FA: 2FAKEY3\nName: Clara\nBio: Daily content updates",
                height=180,
                key="batch_accounts_raw"
            )
            
            import importlib
            importlib.reload(account_login)
            parsed_batch = account_login.parse_bulk_accounts_text(batch_raw_text) if batch_raw_text else []
            
            # Read active profiles for duplicate detection
            existing_active_map = {}
            if os.path.exists("profiles.json"):
                try:
                    with open("profiles.json", "r") as pf:
                        for p in json.load(pf):
                            u = p.get("username", "").strip().lower()
                            if u:
                                existing_active_map[u] = p.get("id", "Active")
                except Exception:
                    pass
            
            new_accounts_count = 0
            existing_accounts_count = 0
            if parsed_batch:
                for acc in parsed_batch:
                    u = acc.get("username", "").strip().lower()
                    if u in existing_active_map:
                        existing_accounts_count += 1
                    else:
                        new_accounts_count += 1

                if existing_accounts_count > 0:
                    st.info(f":material/info: **{len(parsed_batch)} account(s) detected:** **{new_accounts_count} new** and **{existing_accounts_count} already registered** in `profiles.json`.")
                else:
                    st.success(f":material/check_circle: **{len(parsed_batch)} account(s) detected** ready for automated batch onboarding.")
                    
                with st.expander(f"Preview {len(parsed_batch)} Detected Accounts ({new_accounts_count} New, {existing_accounts_count} Already Active)", expanded=True):
                    preview_rows = []
                    for i, acc in enumerate(parsed_batch, 1):
                        u = acc.get("username", "").strip().lower()
                        is_active = u in existing_active_map
                        status_str = f"🟢 Active ({existing_active_map[u]})" if is_active else "🆕 New Profile"
                        preview_rows.append({
                            "#": i,
                            "Status": status_str,
                            "Username": f"@{acc.get('username')}",
                            "Password": "•" * len(acc.get("password", "")),
                            "2FA Key": f"{acc.get('two_factor')[:4]}...{acc.get('two_factor')[-4:]}" if len(acc.get("two_factor", "")) > 8 else acc.get("two_factor", ""),
                            "Display Name": acc.get("display_name") or "(Female Vault / Random)",
                            "Bio": (acc.get("bio")[:40] + "...") if len(acc.get("bio", "")) > 40 else (acc.get("bio") or "(Aesthetic Vault / Random)")
                        })
                    st.dataframe(preview_rows, use_container_width=True)
            else:
                st.info("Paste accounts into the text box above to preview the detected credentials and profile settings.")
                
            st.write("---")
            st.subheader(":material/tune: Multi-Bot Concurrency & Profile Customization")
            col_b1, col_b2 = st.columns([0.55, 0.45])
            
            with col_b1:
                batch_update_profile = st.checkbox("Auto-update Profile on login (Female Name, Bio & Website)", value=True, key="batch_update_profile")
                if batch_update_profile:
                    use_female_vault = st.checkbox(
                        "Enable Female Profile Vault (Randomizes from 35 female names & aesthetic bios)",
                        value=True,
                        key="batch_use_female_vault"
                    )
                    batch_website = st.text_input(
                        "Target Website Link on X",
                        value="https://getmysocial.com/uwuscrettt",
                        key="batch_website_input",
                        help="Link to populate in the X profile website field"
                    )
                    
                    names_pool = female_profile_vault.load_female_names()
                    bios_pool = female_profile_vault.load_female_bios()
                    with st.expander(f":material/auto_awesome: View Female Names ({len(names_pool)}) & Aesthetic Bios ({len(bios_pool)}) Vault", expanded=False):
                        st.markdown("**Female Names Pool (Sample):**")
                        st.caption(", ".join(names_pool[:20]) + f", and {len(names_pool)-20} more...")
                        st.markdown("**Aesthetic Bios Pool (Sample):**")
                        for b in bios_pool[:4]:
                            st.caption(f"- `{b}`")
                            
                    batch_default_name = st.text_input(
                        "Fixed Manual Display Name (Optional)",
                        placeholder="Leave blank to use Female Names Vault randomizer",
                        help="Only fills if an account does not specify a name and you want a fixed name instead of random",
                        key="batch_default_name"
                    )
                    batch_default_bio = st.text_area(
                        "Fixed Manual Bio (Optional)",
                        placeholder="Leave blank to use Aesthetic Bios Vault randomizer",
                        help="Only fills if an account does not specify a bio and you want a fixed bio instead of random",
                        height=68,
                        key="batch_default_bio"
                    )
                else:
                    use_female_vault = False
                    batch_website = None
                    batch_default_name = None
                    batch_default_bio = None
                    
            with col_b2:
                batch_skip_existing = st.checkbox(
                    "Skip already registered accounts (Recommended)",
                    value=True,
                    key="batch_skip_existing",
                    help="Automatically skips accounts that are already registered in profiles.json without launching Chrome, preventing redundant logins and rate limits."
                )
                batch_concurrency = st.radio(
                    "Bot Concurrency Pipeline",
                    options=[1, 2],
                    format_func=lambda c: "1 Bot (Sequential - Ultra Stable)" if c == 1 else f"{c} Bots in Parallel (Fast)",
                    index=0,
                    key="batch_concurrency_radio",
                    help="Runs 1 bot sequentially or 2 bots concurrently with staggered launches"
                )
                batch_delay = st.slider(
                    "Pacing Cooldown between Logins (seconds)",
                    min_value=3,
                    max_value=60,
                    value=6,
                    step=1,
                    help="Cooldown interval before an individual bot worker picks up its next account",
                    key="batch_delay_slider"
                )
                disp_info = "Windows Native Desktop" if sys.platform == "win32" else "display :0"
                st.info(f"Display Pipeline: Executes Native Google Chrome via Patchright on {disp_info}.")
                st.info("Community Seeding & In-Browser Joining: Automatically navigates to booster communities ('Free Trade (18+)' & 'Nude Trades (18+)'), accepts 18+ rules, and confirms membership directly inside the browser.")
                
            if batch_skip_existing and existing_accounts_count > 0:
                btn_caption = f":material/playlist_play: Start Batch Provisioning ({new_accounts_count} New Accounts, {existing_accounts_count} Skipped)"
            else:
                btn_caption = f":material/playlist_play: Start Batch Provisioning ({len(parsed_batch)} Accounts with {batch_concurrency} Bots)"

            start_batch_login = st.button(
                btn_caption,
                type="primary",
                use_container_width=True,
                disabled=len(parsed_batch) == 0 or (batch_skip_existing and new_accounts_count == 0),
                key="btn_start_batch_login"
            )
            if batch_skip_existing and len(parsed_batch) > 0 and new_accounts_count == 0:
                st.info(":material/check_circle: All pasted accounts are already active in `profiles.json`. Uncheck 'Skip already registered accounts' if you want to re-authenticate them.")
            
            if start_batch_login:
                st.subheader(":material/terminal: Batch Execution Stream")
                batch_progress = st.progress(0.0)
                batch_status_box = st.status(f"Starting batch login for {len(parsed_batch)} account(s) using {batch_concurrency} bots...", expanded=True)
                batch_log_placeholder = st.empty()
                batch_messages = []
                
                def batch_ui_logger(msg):
                    ts = time.strftime("%H:%M:%S")
                    fmsg = f"[{ts}] {msg}"
                    batch_messages.append(fmsg)
                    batch_status_box.write(fmsg)
                    batch_log_placeholder.text_area("Live Batch Output", value="\n".join(batch_messages), height=280)
                    
                def batch_ui_progress(curr, total, status_text):
                    prog_val = curr / total if total > 0 else 1.0
                    batch_progress.progress(prog_val)
                    batch_status_box.update(label=f"[{curr}/{total}] {status_text}", state="running")
                    
                try:
                    summary = account_login.batch_login_accounts(
                        accounts_list=parsed_batch,
                        default_name=batch_default_name if (batch_update_profile and batch_default_name) else None,
                        default_bio=batch_default_bio if (batch_update_profile and batch_default_bio) else None,
                        default_website=batch_website if batch_update_profile else None,
                        use_female_vault=use_female_vault if batch_update_profile else False,
                        update_profile=batch_update_profile,
                        concurrency=batch_concurrency,
                        delay_seconds=batch_delay,
                        skip_existing=batch_skip_existing,
                        log_fn=batch_ui_logger,
                        progress_fn=batch_ui_progress
                    )
                    batch_progress.progress(1.0)
                    
                    succ_cnt = summary.get("success_count", 0)
                    skip_cnt = summary.get("skipped_count", 0)
                    fail_cnt = summary.get("failed_count", 0)
                    
                    if fail_cnt == 0:
                        batch_status_box.update(label=f"Batch Complete: {succ_cnt} authenticated, {skip_cnt} skipped (already active).", state="complete", expanded=False)
                        st.success(f"SUCCESS: Completed {summary['total']} accounts ({succ_cnt} newly authenticated, {skip_cnt} already active).")
                    else:
                        batch_status_box.update(label=f"Batch Finished: {succ_cnt} succeeded, {skip_cnt} skipped, {fail_cnt} failed.", state="error", expanded=True)
                        st.warning(f"Batch completed with {fail_cnt} failure(s). Check logs above.")
                        
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total in Batch", summary["total"])
                    m2.metric("Newly Authenticated", succ_cnt)
                    m3.metric("Skipped (Active)", skip_cnt)
                    m4.metric("Failed", fail_cnt)
                    
                    if summary.get("successful"):
                        st.write("**:material/check_circle: Newly Authenticated Accounts:**")
                        st.dataframe(summary["successful"], use_container_width=True)
                        
                    if summary.get("skipped"):
                        with st.expander(f":material/skip_next: Skipped Active Accounts ({skip_cnt})", expanded=False):
                            st.dataframe(summary["skipped"], use_container_width=True)
                        
                    if summary.get("failed"):
                        st.write("**:material/error: Failed Accounts:**")
                        st.dataframe(summary["failed"], use_container_width=True)
                        
                    st.info("Batch provisioning complete! Switch to the 'Manage Accounts' tab above to view your accounts.")
                except Exception as b_exc:
                    import traceback
                    tb = traceback.format_exc()
                    err_msg = str(b_exc).strip() or type(b_exc).__name__
                    batch_status_box.update(label=f"Batch halted: {err_msg}", state="error", expanded=True)
                    st.error(f"Error during batch execution: {err_msg}")
                    st.code(tb, language="text")

    with tab_auto:
        disp_info = "Windows Native Desktop" if sys.platform == "win32" else "display :0"
        st.subheader(":material/smart_toy: Automated Account Creator (HeroSMS)")
        st.write(f"Autonomous Twitter / X account provisioner. Rents fresh US numbers from HeroSMS, executes registration via Join Flow with Native Google Chrome 155 via Patchright on {disp_info}, verifies SMS with enforced 20s+ delivery pacing, extracts session tokens, and seeds default booster communities.")
        
        st.divider()
        
        # Initialize blueprint state if missing
        if "creator_blueprint" not in st.session_state:
            st.session_state.creator_blueprint = account_creator.generate_random_profile()
            st.session_state.creator_acc_id = account_creator.get_next_account_id()
            
        bp = st.session_state.creator_blueprint
        
        col_cfg1, col_cfg2 = st.columns([0.6, 0.4])
        
        with col_cfg1:
            st.subheader(":material/badge: Account Blueprint")
            c_id, c_name = st.columns(2)
            target_id = c_id.text_input("Profile ID", value=st.session_state.creator_acc_id, help="Identifier used in profiles.json and user_data directory.")
            target_name = c_name.text_input("Full Name", value=bp.get("name", "Jessica Miller"))
            
            c_user, c_pwd = st.columns(2)
            target_username = c_user.text_input("Handle / Username", value=bp.get("username", "jessica_m102"))
            target_password = c_pwd.text_input("Password", value=bp.get("password", "XPromo_Pass!8"), type="password")
            
            c_b1, c_b2, c_b3 = st.columns(3)
            b_month = c_b1.text_input("Birth Month", value=bp.get("birth_month", "5"), disabled=True)
            b_day = c_b2.text_input("Birth Day", value=bp.get("birth_day", "14"), disabled=True)
            b_year = c_b3.text_input("Birth Year (18+)", value=bp.get("birth_year", "1999"), disabled=True)

            target_auto_bio = st.text_area("Profile Bio", value=bp.get("bio", "soft spoken 18yo college girl ♡ your favorite distraction ↓"), height=75, help="Bio that will be populated on Twitter during onboarding or via profile settings.")
            target_auto_website = st.text_input("Website URL", value=bp.get("website", "https://getmysocial.com/uwuscrettt"), help="Website link attached to profile.")
            
        with col_cfg2:
            st.subheader(":material/settings_suggest: Registration Rules")
            st.info("Pacing Rule: Strict minimum 20-second initial wait, then polling HeroSMS for up to 4 minutes (with auto-resends at 60s and 120s).")
            st.info("Service Target: Twitter / X (US virtual phone line).")
            st.info("Profile Setup: Automatically applies Display Name, Bio, and Website link directly via Twitter Settings.")
            st.info("Community Seeding: Automatically pre-populates Free Trade (18+) and Nude Trades (18+).")
            st.info(f"Display Pipeline: Executes stealth Chromium on {disp_info}.")
            single_hero_engine = st.selectbox(
                "Browser Engine",
                ["Google Chrome (Default)", "Microsoft Edge", "Brave Browser"],
                index=0,
                key="single_hero_engine_sb"
            )
            single_hero_map = {
                "Google Chrome (Default)": "chrome",
                "Microsoft Edge": "msedge",
                "Brave Browser": "brave"
            }
            chosen_hero_engine = single_hero_map.get(single_hero_engine, "chrome")
            
        col_act1, col_act2 = st.columns([0.3, 0.7])
        if col_act1.button(":material/shuffle: Randomize Credentials", use_container_width=True):
            st.session_state.creator_blueprint = account_creator.generate_random_profile()
            st.session_state.creator_acc_id = account_creator.get_next_account_id()
            st.rerun()
            
        start_creation = col_act2.button(":material/rocket_launch: Start Automated Account Creation", type="primary", use_container_width=True)
        
        st.divider()
        
        if start_creation:
            st.subheader(":material/terminal: Execution Live Stream")
            status_box = st.status(f"Starting account creation pipeline for [{target_id}]...", expanded=True)
            log_placeholder = st.empty()
            log_messages = []
            
            def ui_logger(msg):
                ts = time.strftime("%H:%M:%S")
                formatted_msg = f"[{ts}] {msg}"
                log_messages.append(formatted_msg)
                status_box.write(formatted_msg)
                log_placeholder.text_area("Live Output Log", value="\n".join(log_messages), height=260)
                
            captcha_placeholder = st.empty()
            
            try:
                if os.path.exists(f"captcha_{target_id}.png"):
                    try: os.remove(f"captcha_{target_id}.png")
                    except Exception: pass
                    
                with st.spinner("Automating HeroSMS rental and X registration..."):
                    import importlib
                    importlib.reload(account_creator)
                    created_profile = account_creator.create_twitter_account(
                        custom_id=target_id,
                        custom_name=target_name,
                        custom_username=target_username,
                        custom_password=target_password,
                        bio=target_auto_bio,
                        website=target_auto_website,
                        log_fn=ui_logger,
                        browser_engine=chosen_hero_engine
                    )
                    
                status_box.update(label=f"Account [{target_id}] successfully created and registered!", state="complete", expanded=False)
                st.success(f"SUCCESS: Account [{target_id}] (@{created_profile['username']}) successfully created!")
                
                # Display results card
                st.subheader(":material/verified: Registered Account Summary")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Profile ID", created_profile.get("id"))
                r2.metric("Handle", f"@{created_profile.get('username')}")
                r3.metric("Phone", created_profile.get("phone", "N/A"))
                r4.metric("Session Token", "Captured" if created_profile.get("auth_token") else "Pending")
                
                # Reset blueprint for next account
                st.session_state.creator_blueprint = account_creator.generate_random_profile()
                st.session_state.creator_acc_id = account_creator.get_next_account_id()
                
                st.info("Account created! Switch to the 'Manage Accounts' tab above to view your new profile.")
                    
            except Exception as exc:
                status_box.update(label=f"Creation pipeline halted: {exc}", state="error", expanded=True)
                st.error(f"Error during account creation: {exc}")
                if os.path.exists(f"captcha_{target_id}.png"):
                    st.warning("Arkose Labs Captcha Challenge was detected:")
                    st.image(f"captcha_{target_id}.png", caption="Captcha Screen Capture", use_container_width=True)

    with tab_email:
        disp_info = "Windows Native Desktop" if sys.platform == "win32" else "display :0"
        st.subheader(":material/alternate_email: Account Creator via Email Alias (Interactive Verification)")
        st.write(f"Provision Twitter / X accounts using email aliases that route directly into your primary Gmail inbox (e.g. Gmail Plus addressing or stealth dot tricks). Powered by the exact native Google Chrome stealth patch pipeline from Multi-Account Batch Onboarding on {disp_info} with hardware GPU rendering.")
        
        email_prov_mode = st.radio(
            "Provisioning Pipeline Mode",
            options=[":material/person: Single Account Creation", ":material/timer: Hourly Paced Batch Provisioning"],
            horizontal=True,
            key="email_prov_mode"
        )
        
        st.divider()
        
        if email_prov_mode == ":material/person: Single Account Creation":
            if "email_creator_blueprint" not in st.session_state:
                st.session_state.email_creator_blueprint = account_creator.generate_random_profile()
                st.session_state.email_creator_acc_id = account_creator.get_next_account_id()
                
            ebp = st.session_state.email_creator_blueprint
            
            col_e1, col_e2 = st.columns([0.55, 0.45])
            
            with col_e1:
                st.subheader(":material/badge: Alias & Blueprint Settings")
                base_email = st.text_input(
                    "Primary Base Gmail Address",
                    value=st.session_state.get("email_base_address", "davidosili93@gmail.com"),
                    help="All verification emails sent to aliases will land in this inbox.",
                    key="input_base_email"
                )
                st.session_state.email_base_address = base_email
                
                strat_choice = st.radio(
                    "Email Alias Strategy",
                    options=["Gmail Plus Addressing (+tag)", "Gmail Dot Trick (d.avido...)", "Custom Alias"],
                    index=1,
                    horizontal=True,
                    help="Plus: user+tag@gmail.com. Dot Trick: stealthy period permutations (no plus sign) that Gmail delivers to the exact same inbox.",
                    key="email_strat_radio"
                )
                
                strat_key = "dot" if "Dot" in strat_choice else ("custom" if "Custom" in strat_choice else "plus")
                
                target_e_id = st.text_input("Profile ID", value=st.session_state.email_creator_acc_id, help="Identifier used in profiles.json and user_data directory.", key="input_email_acc_id")
                
                if strat_key == "custom":
                    custom_alias_val = st.text_input("Custom Email Alias", value=f"davido.sili93+{target_e_id.replace(' ', '_')}@gmail.com")
                    active_alias = custom_alias_val.strip()
                else:
                    active_alias = email_alias_manager.get_or_create_alias_for_account(
                        target_e_id, base_email=base_email, strategy=strat_key
                    )
                    
                c_en1, c_en2 = st.columns(2)
                target_e_name = c_en1.text_input("Full Name", value=ebp.get("name", "Jessica Miller"))
                target_e_user = c_en2.text_input("Desired Handle / Username", value=ebp.get("username", "jessica_m102"))
                
                target_e_pwd = st.text_input("Password", value=ebp.get("password", "XPromo_Pass!8"), type="password")

                default_bio = ebp.get("bio", "")
                if not default_bio:
                    try:
                        default_bio = female_profile_vault.get_random_female_bio()
                    except Exception:
                        default_bio = "Living life with positive vibes ✨ | DM open 💬"
                target_e_bio = st.text_area("Profile Bio", value=default_bio, height=75, help="Bio that will be populated on Twitter during onboarding or via profile edit.")

            with col_e2:
                st.subheader(":material/mail: Live Alias Blueprint")
                st.success(f"**Target Email Alias:** `{active_alias}`")
                st.caption(f"↳ Forwarded/Delivered to primary inbox: **{base_email}**")
                
                st.subheader(":material/tune: Profile Customization & Stealth Stack")
                use_f_vault = st.checkbox("Auto-pick Name & Bio from Female Vault", value=True, help="Picks from 35 curated female names and aesthetic bios.")
                attach_web = st.checkbox("Attach Website Link", value=True, help="Adds promotional link to profile website field.")
                promo_url = st.text_input("Website URL", value="https://getmysocial.com/uwuscrettt", disabled=not attach_web)
                use_hero_fallback = st.checkbox("Auto-rent HeroSMS number if Twitter requests phone verification", value=True, help="If Twitter requires a phone number on web, the bot will automatically rent a fresh US number from HeroSMS and verify.")
                
                single_email_engine = st.selectbox(
                    "Browser Engine",
                    ["Google Chrome (Default)", "Microsoft Edge", "Brave Browser"],
                    index=0,
                    key="single_email_engine_sb"
                )
                single_email_map = {
                    "Google Chrome (Default)": "chrome",
                    "Microsoft Edge": "msedge",
                    "Brave Browser": "brave"
                }
                chosen_email_engine = single_email_map.get(single_email_engine, "chrome")
                st.info(f"**Stealth Patch Engine Active**:\n- Engine: {single_email_engine} via Patchright\n- Hardware GPU {disp_info}\n- `STRIP_AUTOMATION_ARGS` active")
                
            col_btn1, col_btn2 = st.columns([0.35, 0.65])
            if col_btn1.button(":material/shuffle: Randomize Credentials", key="btn_rand_email", use_container_width=True):
                st.session_state.email_creator_blueprint = account_creator.generate_random_profile()
                st.session_state.email_creator_acc_id = account_creator.get_next_account_id()
                st.rerun()
                
            start_email_reg = col_btn2.button(":material/rocket_launch: Start Email Alias Registration", type="primary", key="btn_start_email_reg", use_container_width=True)
            
            st.divider()
            
            # Check active session in session_state
            if "email_reg_session" not in st.session_state:
                st.session_state.email_reg_session = None

            if start_email_reg:
                import importlib
                importlib.reload(account_creator_email)
                session = account_creator_email.EmailRegistrationSession(
                    account_id=target_e_id,
                    base_email=base_email,
                    strategy=strat_key,
                    custom_name=target_e_name,
                    custom_username=target_e_user,
                    custom_password=target_e_pwd,
                    custom_bio=target_e_bio,
                    custom_website=promo_url if attach_web else "",
                    auto_vault=use_f_vault,
                    use_herosms_fallback=use_hero_fallback,
                    use_cdp=(chosen_email_engine == "chrome"),
                    browser_engine=chosen_email_engine,
                    log_fn=lambda msg: print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                )
                session.start_background()
                st.session_state.email_reg_session = session
                st.rerun()

            sess = st.session_state.email_reg_session
            if sess is not None:
                st.subheader(":material/terminal: Execution Live Stream")
                status_state = "complete" if sess.status == "success" else ("error" if sess.status == "failed" else "running")
                status_box = st.status(f"Status: [{sess.status.upper()}] - {sess.status_detail}", expanded=True, state=status_state)
                
                # Interactive verification code entry card
                if sess.status == "awaiting_code":
                    code_type = getattr(sess, "code_type", "email")
                    code_recipient = getattr(sess, "code_recipient", sess.alias_email)
                    if code_type == "sms":
                        st.warning(":material/sms: SMS Verification Code Sent!")
                        st.markdown(f"Twitter / X has dispatched a 6-digit confirmation code via SMS to your rented phone: **`{code_recipient}`** (HeroSMS).")
                        st.markdown("**If you see the incoming code on HeroSMS or in the logs, enter it below to finalize account creation:**")
                    else:
                        st.warning(":material/mark_email_unread: Email Verification Code Sent!")
                        st.markdown(f"Twitter / X has dispatched a 6-digit confirmation code to **`{sess.alias_email}`** (arriving in your **`{sess.base_email}`** inbox).")
                        st.markdown("**Please check your email inbox and enter the code below to finalize account creation:**")
                    
                    code_col1, code_col2, code_col3 = st.columns([0.5, 0.3, 0.2])
                    user_code_input = code_col1.text_input("6-Digit Verification Code", key="input_interactive_code", placeholder="e.g. 583921", max_chars=10)
                    
                    if code_col2.button(":material/send: Submit Verification Code", type="primary", key="btn_submit_verif_code", use_container_width=True):
                        if user_code_input.strip():
                            sess.provide_verification_code(user_code_input.strip())
                            st.rerun()
                        else:
                            st.error("Please enter the verification code first.")
                            
                    if code_col3.button(":material/cancel: Cancel", key="btn_cancel_verif", use_container_width=True):
                        sess.cancel()
                        st.session_state.email_reg_session = None
                        st.rerun()

                    st.caption(":material/smart_toy: Bot is also monitoring HeroSMS autonomously in parallel. If HeroSMS receives the code automatically, it will proceed immediately without requiring manual entry.")
                    
                    if not user_code_input.strip():
                        time.sleep(3)
                        if sess.status != "awaiting_code":
                            st.rerun()
                        
                elif sess.status == "awaiting_phone":
                    st.info(":material/phone_android: Twitter Platform Requirement: Phone Verification Step")
                    st.markdown(f"Twitter JoinFlow accepted your email alias (**`{sess.alias_email}`**) and is requesting a phone number to complete web onboarding.")
                    st.caption(f"You can observe the active Chrome session on {disp_info}, or use HeroSMS for automated phone rentals.")
                    if st.button(":material/cancel: Dismiss / Cancel", key="btn_cancel_phone_step", use_container_width=True):
                        sess.cancel()
                        st.session_state.email_reg_session = None
                        st.rerun()

                elif sess.status in ["running", "completing"]:
                    st.info(f"Bot working: {sess.status_detail}")
                    time.sleep(2)
                    st.rerun()
                    
                elif sess.status == "success":
                    st.success(f"SUCCESS: Account [{sess.account_id}] (@{sess.result_profile.get('username')}) created and registered!")
                    r1, r2, r3, r4 = st.columns(4)
                    r1.metric("Profile ID", sess.result_profile.get("id"))
                    r2.metric("Handle", f"@{sess.result_profile.get('username')}")
                    r3.metric("Email Alias", sess.result_profile.get("email"))
                    r4.metric("Session Token", "Captured" if sess.result_profile.get("auth_token") else "Pending")
                    
                    if st.button(":material/add_circle: Register Another Account", key="btn_reset_email_sess"):
                        st.session_state.email_reg_session = None
                        st.session_state.email_creator_blueprint = account_creator.generate_random_profile()
                        st.session_state.email_creator_acc_id = account_creator.get_next_account_id()
                        st.rerun()
                        
                elif sess.status == "failed":
                    st.error(f"Registration failed: {sess.error_message}")
                    if st.button(":material/refresh: Dismiss & Retry", key="btn_clear_failed_sess"):
                        st.session_state.email_reg_session = None
                        st.rerun()
                        
                # Show screenshot if available
                if sess.last_screenshot and os.path.exists(sess.last_screenshot):
                    st.image(sess.last_screenshot, caption=f"Live Browser Screen ({sess.status})", use_container_width=True)
        else:
            render_batch_creator_ui(default_method="email_alias", key_prefix="batch_email_")

        # Stored Aliases Vault
        with st.expander(":material/list_alt: Stored Email Aliases Vault (`email_aliases.json`)"):
            all_aliases = email_alias_manager.load_aliases()
            if all_aliases:
                st.dataframe(
                    [
                        {
                            "Account ID": v.get("account_id", k),
                            "Email Alias": v.get("alias", ""),
                            "Base Email": v.get("base_email", ""),
                            "Strategy": v.get("strategy", ""),
                            "Created At": v.get("created_at", "")
                        }
                        for k, v in all_aliases.items()
                    ],
                    use_container_width=True
                )
            else:
                st.info("No email aliases registered yet.")

    with tab_batch:
        st.subheader(":material/timer: Paced Batch Account Creator (Hourly Automation)")
        st.write("Autonomous multi-account provisioner with natural anti-detection pacing. Creates accounts at an hourly interval with randomized human jitter to safely build your bot network without triggering IP velocity traps or Arkose verification spikes.")
        st.divider()
        render_batch_creator_ui(default_method="herosms", key_prefix="batch_tab_")

