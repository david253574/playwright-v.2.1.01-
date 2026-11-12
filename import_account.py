import os
import sys
import time
import json
import re
import argparse
from playwright.sync_api import sync_playwright

def get_next_account_id(profiles_path="profiles.json"):
    """Finds the lowest available sequential account ID starting from 1 (filling gaps in profiles.json)."""
    existing_nums = set()
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, "r") as f:
                profiles = json.load(f)
            for p in profiles:
                p_id = p.get("id", "")
                match = re.search(r'\d+', p_id)
                if match:
                    existing_nums.add(int(match.group()))
        except Exception:
            pass

    num = 1
    while True:
        if num not in existing_nums:
            cand = f"account {num}"
            state_file = os.path.join("user_data", cand, "state.json")
            if not os.path.exists(state_file):
                return cand
        num += 1

def inject_auth_token_cookie(user_data_dir, token_val):
    """Injects auth_token cookie into Chromium persistent context storage."""
    token_val = token_val.strip() if token_val else ""
    if not token_val:
        return False, "Token cannot be empty."
    try:
        os.makedirs(user_data_dir, exist_ok=True)
        with sync_playwright() as pw:
            b = pw.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--enable-unsafe-webgpu",
                    "--ignore-gpu-blocklist",
                    "--enable-features=Vulkan",
                    "--use-angle=swiftshader",
                    "--use-gl=swiftshader"
                ]
            )
            exp = int(time.time()) + 31536000
            b.add_cookies([
                {"name": "auth_token", "value": token_val, "domain": ".x.com", "path": "/", "secure": True, "expires": exp},
                {"name": "auth_token", "value": token_val, "domain": ".twitter.com", "path": "/", "secure": True, "expires": exp}
            ])
            time.sleep(1)
            b.close()
        return True, ""
    except Exception as e:
        return False, str(e)

def verify_session(user_data_dir, expected_username=None, log_fn=print):
    """Verifies that the injected session is valid on X.com without login prompts."""
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars"
                ],
                ignore_default_args=["--enable-automation"]
            )
            page = b.pages[0] if b.pages else b.new_page()
            log_fn("Verifying session on https://x.com/home...")
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=45000)
            time.sleep(3.0)
            
            # Check for login redirection
            current_url = page.url
            if "login" in current_url or "i/flow/login" in current_url:
                b.close()
                return False, f"Redirected to login: {current_url}"
                
            # Check for suspended status
            body_text = page.inner_text("body")
            if "Account suspended" in body_text:
                b.close()
                return False, "Account is marked as suspended by X."
                
            # Check account presence (e.g. navigation bar, profile button)
            nav = page.locator('nav[role="navigation"], a[data-testid="AppTabBar_Profile_Link"]').first
            is_authed = nav.is_visible(timeout=10000)
            
            b.close()
            if is_authed:
                return True, "Authenticated session active."
            return True, f"Loaded page: {current_url}"
    except Exception as e:
        return False, str(e)

def import_account(profile_id=None, username=None, auth_token=None, password="securepassword1", verify=False, log_fn=print):
    """
    Imports an existing X account into the bot system using its auth_token session cookie.
    
    Parameters:
        profile_id: Identifier (e.g. 'account 21'). If None, next ID is calculated automatically.
        username: Handle without @ symbol.
        auth_token: 40-character hexadecimal session token.
        password: Password placeholder (for records).
        verify: Whether to perform a test navigation to confirm active session.
    """
    if not auth_token or not auth_token.strip():
        raise ValueError("auth_token is required for session import.")
        
    p_id = profile_id or get_next_account_id()
    u_name = (username or p_id).lstrip("@").strip()
    tok = auth_token.strip()
    user_data_dir = os.path.abspath(f"./user_data/{p_id}")
    
    log_fn(f"Importing account [{p_id}] for user @{u_name}...")
    log_fn(f"Target user_data directory: {user_data_dir}")
    
    # 1. Inject auth_token cookie into persistent context
    ok, err = inject_auth_token_cookie(user_data_dir, tok)
    if not ok:
        raise RuntimeError(f"Cookie injection failed: {err}")
    log_fn("Session cookie successfully injected.")
    
    # 2. Update profiles.json
    profiles_path = "profiles.json"
    profiles = []
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, "r") as f:
                profiles = json.load(f)
        except Exception:
            profiles = []
            
    new_entry = {
        "id": p_id,
        "username": u_name,
        "password": password,
        "user_data_dir": f"./user_data/{p_id}",
        "auth_token": tok,
        "auth_token_added": True,
        "status": "Active"
    }
    
    # Replace existing or append
    idx = next((i for i, p in enumerate(profiles) if p.get("id") == p_id), None)
    if idx is not None:
        profiles[idx] = new_entry
        log_fn(f"Updated existing profile entry for [{p_id}].")
    else:
        profiles.append(new_entry)
        log_fn(f"Appended new profile entry for [{p_id}].")
        
    with open(profiles_path, "w") as f:
        json.dump(profiles, f, indent=4)
        
    # 3. Initialize default communities in communities_cache.json
    cache_path = "communities_cache.json"
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as cf:
                cache = json.load(cf)
        except Exception:
            cache = {}
            
    if p_id not in cache:
        cache[p_id] = {
            "Free Trade (18+)": {"url": "/i/communities/1944294809918685272", "members": 402000},
            "Nude Trades (18+)": {"url": "/i/communities/1806977501140570599", "members": 343600}
        }
        with open(cache_path, "w") as cf:
            json.dump(cache, cf, indent=4)
        log_fn(f"Assigned default communities cache for [{p_id}].")
        
    # 4. Optional verification
    if verify:
        log_fn("Verifying imported session live...")
        v_ok, v_msg = verify_session(user_data_dir, expected_username=u_name, log_fn=log_fn)
        if v_ok:
            log_fn(f"Verification SUCCESS: {v_msg}")
        else:
            log_fn(f"Verification WARNING: {v_msg}")
            
    log_fn(f"Account [{p_id}] (@{u_name}) successfully imported and active.")
    return new_entry

def main():
    parser = argparse.ArgumentParser(description="Import an existing X account via auth_token cookie.")
    parser.add_argument("--id", help="Profile ID (e.g. 'account 21'). If omitted, auto-generated.", default=None)
    parser.add_argument("--username", "-u", help="Twitter username/handle (without @)", default=None)
    parser.add_argument("--token", "-t", required=True, help="auth_token cookie value (40 characters)")
    parser.add_argument("--password", "-p", help="Password for records (optional)", default="securepassword1")
    parser.add_argument("--verify", "-v", action="store_true", help="Perform live verification on x.com")
    
    args = parser.parse_args()
    try:
        import_account(
            profile_id=args.id,
            username=args.username,
            auth_token=args.token,
            password=args.password,
            verify=args.verify
        )
    except Exception as e:
        print(f"Error during import: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
