import os
import sys
import time
import json
import re
import random
import hmac
import hashlib
import struct
import base64
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

STRIP_AUTOMATION_ARGS = [
    "--disable-field-trial-config",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,BlockOriginHeaderModificationOnRedirect,AvoidCorsURLLoaderRestartOnRedirect,Translate,AutoDeElevate,OptimizationHints,NetworkTimeServiceQuerying,AimEnabled,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion",
    "--force-color-profile=srgb",
    "--use-mock-keychain",
    "--disable-renderer-backgrounding",
    "--disable-hang-monitor",
    "--enable-automation",
    "--no-sandbox"
]

try:
    import pyotp
except ImportError:
    pyotp = None

try:
    import female_profile_vault
except ImportError:
    female_profile_vault = None

try:
    from account_creator import handle_post_signup_onboarding
except ImportError:
    handle_post_signup_onboarding = None

try:
    from herosms_client import HeroSMSClient
    from playwright.sync_api import sync_playwright as standard_playwright
except ImportError:
    HeroSMSClient = None
    standard_playwright = None

TARGET_COMMUNITIES = [
    {
        "name": "Free Trade (18+)",
        "full_url": "https://x.com/i/communities/1944294809918685272",
        "relative_url": "/i/communities/1944294809918685272",
        "id": "1944294809918685272",
        "members": 402000
    },
    {
        "name": "Nude Trades (18+)",
        "full_url": "https://x.com/i/communities/1806977501140570599",
        "relative_url": "/i/communities/1806977501140570599",
        "id": "1806977501140570599",
        "members": 343600
    }
]

PROFILE_ID_LOCK = threading.Lock()
FILE_WRITE_LOCK = threading.Lock()

def get_next_account_id(profiles_path="profiles.json", archive_path=None, allocated_ids=None):
    """Finds the lowest available sequential account ID starting from 1, checking active profiles in profiles.json."""
    with PROFILE_ID_LOCK:
        used_nums = set()
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, "r") as f:
                    profiles = json.load(f)
                for p in profiles:
                    p_id = p.get("id", "")
                    match = re.search(r'\d+', p_id)
                    if match:
                        used_nums.add(int(match.group()))
            except Exception:
                pass

        allocated_nums = set()
        if allocated_ids:
            for a_id in allocated_ids:
                m = re.search(r'\d+', str(a_id))
                if m:
                    allocated_nums.add(int(m.group()))

        num = 1
        while True:
            if num not in used_nums and num not in allocated_nums:
                cand = f"account {num}"
                state_file = os.path.join("user_data", cand, "state.json")
                if not os.path.exists(state_file):
                    if allocated_ids is not None:
                        allocated_ids.add(cand)
                    return cand
            num += 1

def cleanup_profile_locks(user_data_dir):
    """Cleans up stale SingletonLock, SingletonSocket, SingletonCookie files."""
    if not os.path.exists(user_data_dir):
        return
    for fname in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        fpath = os.path.join(user_data_dir, fname)
        if os.path.lexists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

def terminate_chrome_processes(user_data_dir=None, port=None, log_fn=print):
    """
    Forcefully and cleanly terminates any running Chrome processes associated with
    the specified user_data_dir or remote debugging port, then cleans up lock files.
    Cross-platform support for Windows and Linux.
    """
    import subprocess
    if sys.platform == "win32":
        if port:
            try:
                out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True, stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 5 and "LISTENING" in line:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True, timeout=5)
            except Exception: pass
        if user_data_dir:
            abs_dir = os.path.abspath(user_data_dir)
            try:
                ps_cmd = f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*user-data-dir={abs_dir}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8)
            except Exception: pass
            cleanup_profile_locks(abs_dir)
    else:
        if port:
            try:
                subprocess.run(["fuser", "-k", "-9", f"{port}/tcp"], capture_output=True, timeout=5)
            except Exception: pass
            try:
                subprocess.run(f"pkill -9 -f 'remote-debugging-port={port}'", shell=True, capture_output=True, timeout=5)
            except Exception: pass
            
        if user_data_dir:
            abs_dir = os.path.abspath(user_data_dir)
            lock_file = os.path.join(abs_dir, "SingletonLock")
            if os.path.islink(lock_file):
                try:
                    target = os.readlink(lock_file)
                    parts = target.split("-")
                    if len(parts) >= 2 and parts[-1].isdigit():
                        pid = int(parts[-1])
                        try:
                            os.kill(pid, 15)
                            time.sleep(0.3)
                            os.kill(pid, 9)
                        except OSError: pass
                except Exception: pass
                
            try:
                subprocess.run(f"pkill -9 -f 'user-data-dir={abs_dir}'", shell=True, capture_output=True, timeout=5)
            except Exception: pass
            
            cleanup_profile_locks(abs_dir)

def generate_totp_pin(secret):
    """
    Computes standard RFC 6238 6-digit TOTP pin for 2FA verification.
    Matches browser tools such as https://www.browserscan.net/2fa and Google Authenticator.
    Returns (pin_code, remaining_seconds).
    """
    clean_secret = secret.replace(" ", "").strip().upper()
    remaining = 30 - (int(time.time()) % 30)
    
    if pyotp:
        try:
            totp = pyotp.TOTP(clean_secret)
            return totp.now(), remaining
        except Exception:
            pass
            
    # Pure Python fallback
    try:
        # Pad base32 if missing padding
        padding = (8 - len(clean_secret) % 8) % 8
        padded_secret = clean_secret + ("=" * padding)
        key = base64.b32decode(padded_secret, casefold=True)
        counter = int(time.time() // 30)
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[19] & 15
        pin = str((struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000).zfill(6)
        return pin, remaining
    except Exception as e:
        raise ValueError(f"Invalid 2FA secret key '{secret}': {e}")

def parse_single_account_block(text):
    """
    Parses a single account from key-value lines or delimiter format.
    Fields detected: username, password, two_factor, display_name, bio.
    """
    result = {"username": "", "password": "", "two_factor": "", "display_name": "", "bio": ""}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        lower = line.lower()
        if any(lower.startswith(k) for k in ["username:", "user:", "handle:", "login:", "account:"]):
            parts = line.split(":", 1)
            result["username"] = parts[1].strip().lstrip("@")
        elif any(lower.startswith(k) for k in ["password:", "pass:", "pwd:"]):
            parts = line.split(":", 1)
            result["password"] = parts[1].strip()
        elif any(lower.startswith(k) for k in ["2fa:", "two_factor:", "2fa_secret:", "totp:", "secret:", "authenticator:"]):
            parts = line.split(":", 1)
            result["two_factor"] = parts[1].replace(" ", "").strip().upper()
        elif any(lower.startswith(k) for k in ["name:", "display_name:", "profile_name:"]):
            parts = line.split(":", 1)
            result["display_name"] = parts[1].strip()
        elif any(lower.startswith(k) for k in ["bio:", "description:", "profile_bio:"]):
            parts = line.split(":", 1)
            result["bio"] = parts[1].strip()
            
    if not (result["username"] and result["password"]):
        for sep in [":", "|", "\t", "----", "---"]:
            if sep in text:
                chunks = [c.strip() for c in text.split(sep)]
                if len(chunks) >= 3:
                    result["username"] = chunks[0].lstrip("@").strip()
                    result["password"] = chunks[1].strip()
                    result["two_factor"] = chunks[2].replace(" ", "").strip().upper()
                    if len(chunks) > 3:
                        result["display_name"] = chunks[3].strip()
                    if len(chunks) > 4:
                        result["bio"] = chunks[4].strip()
                    break
                elif len(chunks) == 2:
                    result["username"] = chunks[0].lstrip("@").strip()
                    result["password"] = chunks[1].strip()
                    break
    return result

def parse_credentials_text(raw_text):
    """Parses a single credential block with backwards compatibility."""
    return parse_single_account_block(raw_text)

KNOWN_FIELD_KEYS = {
    'username', 'user', 'handle', 'login', 'account',
    'password', 'pass', 'pwd',
    '2fa', 'two_factor', 'totp', 'secret', 'authenticator',
    'name', 'display_name', 'profile_name',
    'bio', 'description', 'profile_bio',
    'location', 'url', 'website', 'http', 'https'
}

def parse_single_line_combo(line):
    """Parses a single delimiter-separated account combo line."""
    for sep in [':', '|', '\t', ',']:
        if sep in line:
            chunks = [c.strip() for c in line.split(sep)]
            first_label = chunks[0].lower().rstrip(':')
            if first_label in KNOWN_FIELD_KEYS:
                return None
            if len(chunks) >= 3:
                return {
                    'username': chunks[0].lstrip('@').strip(),
                    'password': chunks[1].strip(),
                    'two_factor': chunks[2].replace(' ', '').strip().upper(),
                    'display_name': chunks[3].strip() if len(chunks) > 3 else '',
                    'bio': sep.join(chunks[4:]).strip() if len(chunks) > 4 else ''
                }
            elif len(chunks) == 2 and sep in ['|', '\t']:
                return {
                    'username': chunks[0].lstrip('@').strip(),
                    'password': chunks[1].strip(),
                    'two_factor': '',
                    'display_name': '',
                    'bio': ''
                }
    return None

def parse_bulk_accounts_text(raw_text):
    """
    Parses multiple accounts from a raw text block.
    Supports:
    - Line-by-line delimiter: username:password:2fa[:name][:bio] or pipe-delimited
    - Multi-line blocks separated by blank lines or next username (Username: ..., Password: ..., 2FA: ...)
    - JSON array of objects
    Returns list of dicts with keys: username, password, two_factor, display_name, bio.
    """
    text = (raw_text or "").strip()
    if not text:
        return []

    # 1. Try JSON Array
    if text.startswith("[") and text.endswith("]"):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                res = []
                for item in data:
                    if isinstance(item, dict) and item.get("username") and item.get("password"):
                        res.append({
                            "username": item.get("username", "").lstrip("@").strip(),
                            "password": item.get("password", "").strip(),
                            "two_factor": (item.get("two_factor") or item.get("2fa") or item.get("two_factor_secret") or "").replace(" ", "").strip().upper(),
                            "display_name": item.get("display_name") or item.get("name") or "",
                            "bio": item.get("bio") or item.get("description") or ""
                        })
                if res:
                    return res
        except Exception:
            pass

    # 2. Check for multi-account Discord/Telegram bot logs or messy Key-Value dumps
    if len(re.findall(r'(?i)(?:\*{0,2}(?:username|user|handle):?\*{0,2}):?', text)) >= 1:
        kv_pattern = re.compile(
            r"(?:\*{0,2}(?:Username|User|Handle):?\*{0,2}):?\s*([^\s\r\n\*]+)[\s\S]*?"
            r"(?:\*{0,2}(?:Password|Pass|Pwd):?\*{0,2}):?\s*([^\s\r\n\*]+)[\s\S]*?"
            r"(?:\*{0,2}(?:2FA|Two_Factor|TOTP|Secret):?\*{0,2}):?\s*([A-Za-z0-9][A-Za-z0-9 ]{8,38}[A-Za-z0-9]|[A-Za-z0-9]{10,40})",
            re.IGNORECASE
        )
        triplets = kv_pattern.findall(text)
        if len(triplets) >= 1:
            res = []
            for u, p, t in triplets:
                clean_totp = re.sub(r'[^A-Za-z0-9]', '', t).upper()
                res.append({
                    "username": u.lstrip("@").strip(),
                    "password": p.strip(),
                    "two_factor": clean_totp,
                    "display_name": "",
                    "bio": ""
                })
            return res

    # 3. Sequential line-by-line & block scanner
    accounts = []
    current_block = []

    for line in text.splitlines():
        l_strip = line.strip()
        if not l_strip or l_strip.startswith('#') or l_strip.startswith('//'):
            if current_block:
                p = parse_single_account_block('\n'.join(current_block))
                if p.get('username') and p.get('password'):
                    accounts.append(p)
                current_block = []
            continue
            
        combo = parse_single_line_combo(l_strip)
        if combo:
            if current_block:
                p = parse_single_account_block('\n'.join(current_block))
                if p.get('username') and p.get('password'):
                    accounts.append(p)
                current_block = []
            accounts.append(combo)
        else:
            first_word = l_strip.split(':', 1)[0].strip().lower()
            if first_word in ['username', 'user', 'handle', 'account'] and current_block:
                p = parse_single_account_block('\n'.join(current_block))
                if p.get('username') and p.get('password'):
                    accounts.append(p)
                current_block = []
            current_block.append(l_strip)

    if current_block:
        p = parse_single_account_block('\n'.join(current_block))
        if p.get('username') and p.get('password'):
            accounts.append(p)

    return accounts

def update_twitter_profile(page, display_name=None, bio=None, location=None, website=None, log_fn=print):
    """
    Updates the account's Display Name, Bio, Location, or Website on X/Twitter.
    Navigates directly to https://x.com/settings/profile, fills the requested fields,
    and submits via Profile_Save_Button.
    """
    # 0. Check and clear any blocking privacy / settings review modals first
    try:
        from account_creator import handle_privacy_and_settings_review
        handle_privacy_and_settings_review(page, log_fn=log_fn)
    except Exception: pass

    name_el = page.locator('input[name="displayName"], input[autocomplete="name"]').first
    bio_el = page.locator('textarea[name="description"], textarea[data-testid*="bio" i], textarea[placeholder*="bio" i]').first
    loc_el = page.locator('input[name="location"], input[placeholder*="location" i]').first
    url_el = page.locator('input[name="url"], input[name="website"], input[placeholder*="website" i]').first

    # 1. Check if Edit Profile inputs are already visible on the current page
    modal_open = False
    try:
        modal_open = bio_el.is_visible(timeout=1000) or name_el.is_visible(timeout=1000)
    except Exception:
        pass

    if not modal_open:
        log_fn("Navigating directly to profile settings (https://x.com/settings/profile)...")
        try:
            page.goto("https://x.com/settings/profile", wait_until="domcontentloaded", timeout=25000)
            time.sleep(3.0)
        except Exception as ge:
            log_fn(f"Navigation to settings/profile note: {ge}")

        # Clear any modal that might have appeared
        try:
            from account_creator import handle_privacy_and_settings_review
            handle_privacy_and_settings_review(page, log_fn=log_fn)
        except Exception: pass

        # Check for error / retry on page
        try:
            retry_btn = page.locator('button:has-text("Retry"), [role="button"]:has-text("Retry")').first
            if retry_btn.is_visible(timeout=1000):
                log_fn("Dismissing error retry button on settings page...")
                retry_btn.click()
                time.sleep(2.0)
        except Exception: pass

        for _ in range(12):
            if bio_el.is_visible(timeout=500) or name_el.is_visible(timeout=500):
                modal_open = True
                break
            time.sleep(0.5)

        # Fallback: Check if 'Edit profile' button is visible on page
        if not modal_open:
            edit_btn = page.locator('button[data-testid="editProfileButton"]:visible, a[data-testid="editProfileButton"]:visible, button:has-text("Edit profile"):visible, a:has-text("Edit profile"):visible').first
            if edit_btn.is_visible(timeout=1500):
                log_fn("Clicking visible 'Edit profile' button fallback...")
                try: human_click(page, edit_btn)
                except Exception: edit_btn.click(force=True)
                time.sleep(2.5)
    else:
        log_fn("Edit Profile modal already open on screen.")

    # Check if we landed inside Twitter onboarding setup flow (/i/flow/setup_profile)
    for _ in range(6):
        skip_step = page.locator('button:has-text("Skip for now"):visible, [role="button"]:has-text("Skip for now"):visible').first
        flow_bio = page.locator('textarea[data-testid="ocfEnterTextTextInput"]:visible, textarea[name="bio"]:visible').first
        if skip_step.is_visible(timeout=500) and not flow_bio.is_visible(timeout=500):
            log_fn("Onboarding setup flow: Skipping avatar/header step...")
            try: human_click(page, skip_step)
            except Exception: skip_step.click(force=True)
            time.sleep(2.0)
            continue
        break
    
    # Helper function to type with React synthetic event compatibility
    def set_react_input(locator, text):
        try:
            locator.scroll_into_view_if_needed()
            try: human_click(page, locator)
            except Exception: locator.click(force=True)
            time.sleep(0.15)
            # Select all and delete existing content
            page.keyboard.press("Control+A")
            time.sleep(0.05)
            page.keyboard.press("Backspace")
            time.sleep(0.1)
            # Type characters sequentially to trigger React keydown/keypress/input events
            locator.press_sequentially(text, delay=15)
            time.sleep(0.2)
            # Dispatch native input/change/blur to finalize React form state
            try:
                locator.evaluate("""el => {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }""")
            except Exception: pass
            time.sleep(0.2)
        except Exception:
            try: locator.fill(text)
            except Exception: pass

    updated_fields = []
    
    if display_name:
        for _ in range(8):
            if name_el.is_visible():
                break
            time.sleep(0.5)
            
        if name_el.is_visible():
            log_fn(f"Setting Display Name to: '{display_name}'...")
            set_react_input(name_el, str(display_name).strip())
            updated_fields.append("Display Name")
            time.sleep(0.3)
        else:
            log_fn("Warning: Display Name input field not found on page.")
            
    if bio is not None and str(bio).strip():
        clean_bio = str(bio).strip()
        flow_bio = page.locator('textarea[data-testid="ocfEnterTextTextInput"]:visible').first
        target_bio_el = flow_bio if flow_bio.is_visible(timeout=500) else bio_el

        for _ in range(8):
            if target_bio_el.is_visible():
                break
            time.sleep(0.5)
            
        if target_bio_el.is_visible():
            log_fn(f"Setting Profile Bio ({len(clean_bio)} characters): '{clean_bio}'...")
            set_react_input(target_bio_el, clean_bio)
            updated_fields.append("Bio")
            time.sleep(0.3)
        else:
            log_fn("Warning: Bio textarea not found on page.")
            
    if location and loc_el.is_visible():
        log_fn(f"Setting Location to: '{location}'...")
        set_react_input(loc_el, str(location).strip())
        updated_fields.append("Location")
        time.sleep(0.3)
        
    if website and url_el.is_visible():
        log_fn(f"Setting Website to: '{website}'...")
        set_react_input(url_el, str(website).strip())
        updated_fields.append("Website")
        time.sleep(0.3)
        
    if updated_fields:
        save_btn = page.locator(
            'button[data-testid="Profile_Save_Button"]:visible, '
            'div[data-testid="Profile_Save_Button"]:visible, '
            '[data-testid="Profile_Save_Button"]:visible, '
            'button:has-text("Save changes"):visible, '
            'button:has-text("Save"):visible, '
            'div[role="button"]:has-text("Save changes"):visible, '
            'div[role="button"]:has-text("Save"):visible, '
            'button:has-text("Next"):visible, '
            'div[role="button"]:has-text("Next"):visible'
        ).first

        if save_btn.is_visible(timeout=6000):
            # Unblock disabled or aria-disabled state
            try:
                page.evaluate("""() => {
                    const btns = document.querySelectorAll('[data-testid="Profile_Save_Button"], button:has-text("Save"), button:has-text("Save changes"), [role="button"]:has-text("Save"), button:has-text("Next")');
                    for (const b of btns) {
                        b.removeAttribute('disabled');
                        b.removeAttribute('aria-disabled');
                        b.setAttribute('aria-disabled', 'false');
                        b.style.pointerEvents = 'auto';
                    }
                }""")
            except Exception: pass

            log_fn(f"Submitting profile updates for: {', '.join(updated_fields)}. Clicking Save button...")
            try: human_click(page, save_btn)
            except Exception: pass
            try: save_btn.evaluate("b => b.click()")
            except Exception: pass

            # Verification: Ensure the Edit Profile modal closes or changes apply
            modal_closed = False
            for attempt in range(8):
                time.sleep(1.0)
                still_open = False
                try:
                    still_open = page.locator('button[data-testid="Profile_Save_Button"]:visible, textarea[name="description"]:visible').count() > 0
                except Exception: pass

                if not still_open or page.url.endswith("/home"):
                    modal_closed = True
                    log_fn(f"SUCCESS: Edit profile dismissed. Profile changes saved on X ({', '.join(updated_fields)})!")
                    return True

                log_fn(f"Profile modal still open (attempt {attempt+1}/8), re-clicking Save button...")
                try:
                    save_btn.evaluate("b => { b.removeAttribute('disabled'); b.removeAttribute('aria-disabled'); b.click(); }")
                except Exception: pass

            if modal_closed:
                return True
            else:
                log_fn("Note: Profile Save clicked, proceeding...")
                return True
        else:
            log_fn("Warning: Profile Save button not visible.")
            return False
    else:
        log_fn("No profile fields provided to update.")
        return True

def update_account_profile_standalone(account_id, display_name=None, bio=None, location=None, website=None, log_fn=print):
    """
    Connects to an existing profile's browser context and updates its Display Name, Bio, Location, or Website.
    """
    profiles_path = "profiles.json"
    if not os.path.exists(profiles_path):
        return False, "profiles.json not found."
    try:
        with open(profiles_path, "r") as f:
            profiles = json.load(f)
    except Exception as e:
        return False, f"Failed to load profiles.json: {e}"
        
    prof = next((p for p in profiles if p.get("id") == account_id), None)
    if not prof:
        return False, f"Profile '{account_id}' not found."
        
    user_data_dir = os.path.abspath(prof.get("user_data_dir", f"./user_data/{account_id}"))
    if not os.path.exists(user_data_dir):
        return False, f"User data directory '{user_data_dir}' does not exist."
        
    cleanup_profile_locks(user_data_dir)
    
    if sys.platform != "win32":
        if os.path.exists("/tmp/.X11-unix/X0"):
            os.environ["DISPLAY"] = ":0"
            if os.path.exists("/run/user/1000/gdm/Xauthority"):
                os.environ["XAUTHORITY"] = "/run/user/1000/gdm/Xauthority"
            elif os.path.exists(os.path.expanduser("~/.Xauthority")):
                os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
        elif "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
        
    log_fn(f"Connecting to [{account_id}] to update profile...")
    with sync_playwright() as p:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--start-maximized"
        ]
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=args,
            ignore_default_args=STRIP_AUTOMATION_ARGS,
            no_viewport=True
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            ok = update_twitter_profile(
                page=page,
                display_name=display_name,
                bio=bio,
                location=location,
                website=website,
                log_fn=log_fn
            )
            if ok:
                if display_name is not None:
                    prof["display_name"] = display_name
                if bio is not None:
                    prof["bio"] = bio
                if website is not None:
                    prof["website"] = website
                with open(profiles_path, "w") as f:
                    json.dump(profiles, f, indent=4)
                return True, f"Successfully updated profile for [{account_id}] on X."
            else:
                return False, "Profile editor did not confirm changes."
        except Exception as e:
            return False, f"Failed updating profile: {e}"
        finally:
            try:
                for pg in list(context.pages):
                    try: pg.close()
                    except Exception: pass
            except Exception: pass
            try: context.close()
            except Exception: pass
            terminate_chrome_processes(user_data_dir=user_data_dir, log_fn=log_fn)

def dismiss_welcome_to_communities(page, log_fn=print, max_wait_ms=1500):
    """
    Dismisses the 'Welcome to Communities' modal ('Check it out')
    whenever it appears before, during, or after community joining.
    """
    try:
        cio_locators = [
            page.locator('button:has-text("Check it out"):visible'),
            page.locator('div[role="button"]:has-text("Check it out"):visible'),
            page.locator('[role="button"]:has-text("Check it out"):visible'),
            page.locator('span:has-text("Check it out"):visible'),
            page.locator('button:has-text("Got it"):visible'),
            page.get_by_role("button", name="Check it out", exact=False)
        ]
        for cio in cio_locators:
            try:
                if cio.first.is_visible(timeout=max_wait_ms):
                    log_fn("  -> 'Welcome to Communities' modal detected. Dismissing ('Check it out')...")
                    try:
                        try:
                            from account_creator import human_click
                            human_click(page, cio.first)
                        except Exception:
                            cio.first.click(force=True)
                    except Exception:
                        pass
                    time.sleep(2.0)
                    return True
            except Exception:
                pass

        # Fallback via JavaScript if overlay/z-index prevented locator match or standard click
        dismissed_js = page.evaluate('''() => {
            const spans = Array.from(document.querySelectorAll('span, div, button'));
            const checkSpan = spans.find(el => el.innerText && el.innerText.trim() === 'Check it out');
            if (checkSpan) {
                const btn = checkSpan.closest('button, [role="button"]') || checkSpan;
                btn.click();
                return true;
            }
            const hasWelcome = document.body && document.body.innerText.includes('Welcome to Communities');
            if (hasWelcome) {
                const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
                const cioBtn = buttons.find(b => b.innerText && (b.innerText.includes('Check it out') || b.innerText.includes('Got it')));
                if (cioBtn) {
                    const target = cioBtn.closest('button, [role="button"]') || cioBtn;
                    target.click();
                    return true;
                }
            }
            return false;
        }''')
        if dismissed_js:
            log_fn("  -> 'Welcome to Communities' modal dismissed via JS fallback.")
            time.sleep(2.0)
            return True
    except Exception:
        pass
    return False

def join_target_communities_in_browser(page, account_id, log_fn=print):
    """
    Navigates to each target booster community in the active browser session,
    bypasses sensitive 18+ warnings, clicks 'Join', confirms rules / 'Agree and join',
    and returns a dict of verified joined communities with relative URLs.
    """
    joined_comms = {}
    time.sleep(3.0)  # Settle ongoing profile save / route transitions before navigating
    
    for comm in TARGET_COMMUNITIES:
        c_name = comm["name"]
        c_full_url = comm["full_url"]
        c_rel_url = comm["relative_url"]
        joined_comms[c_name] = {"url": c_rel_url, "members": comm["members"]}
        
        try:
            try:
                if page.is_closed():
                    log_fn("Notice: Browser window was closed. Communities cached; skipping remaining browser checks.")
                    break
            except Exception:
                break

            log_fn(f"Joining [{account_id}] -> '{c_name}'...")
            
            # Tolerant navigation with retry for ongoing SPA requests / net::ERR_ABORTED
            for nav_try in range(3):
                try:
                    page.goto(c_full_url, wait_until="domcontentloaded", timeout=35000)
                    break
                except Exception as ne:
                    if ("abort" in str(ne).lower() or "navigation" in str(ne).lower()) and nav_try < 2:
                        time.sleep(2.5)
                        continue
                    raise

            time.sleep(4.0)
            
            try:
                cookie_accept = page.locator('button:has-text("Accept all cookies"):visible, button:has-text("Refuse non-essential cookies"):visible').first
                if cookie_accept.is_visible(timeout=1500):
                    cookie_accept.click(force=True)
                    time.sleep(1.0)
            except Exception: pass

            # Dismiss Welcome / Check it out overlay if present initially
            dismiss_welcome_to_communities(page, log_fn=log_fn, max_wait_ms=2000)
            
            # Check sensitive warning
            for _ in range(3):
                try:
                    adult_btn = page.locator('button:has-text("Yes, view"):visible, button:has-text("View"):visible, button:has-text("Adult content"):visible, button:has-text("Show content"):visible, div[role="button"]:has-text("View"):visible, div[role="button"]:has-text("Yes, view"):visible').first
                    if adult_btn.is_visible(timeout=2500):
                        log_fn(f"  -> Bypassing sensitive warning...")
                        try:
                            from account_creator import human_click
                            human_click(page, adult_btn)
                        except Exception:
                            adult_btn.click(force=True)
                        time.sleep(2.0)
                        # Sensitive bypass often immediately triggers 'Welcome to Communities' modal
                        dismiss_welcome_to_communities(page, log_fn=log_fn, max_wait_ms=2500)
                except Exception: pass

            dismiss_welcome_to_communities(page, log_fn=log_fn, max_wait_ms=1000)
                    
            # Check already joined
            if page.locator('button:has-text("Joined"):visible, [aria-label*="Joined"]:visible, button[data-testid*="Joined"]:visible').first.is_visible(timeout=3000):
                log_fn(f"  -> Already a member of '{c_name}'.")
                continue
                
            # Join button - wait up to 8s for community header to render
            j_btn = page.locator('button:has-text("Join"):visible, [aria-label*="Join" i]:visible, button[data-testid*="Join"]:visible, div[role="button"]:has-text("Join"):visible').first
            try:
                j_btn.wait_for(state="visible", timeout=8000)
            except Exception: pass

            # If Join button not visible, check if 'Welcome to Communities' is blocking it
            if not j_btn.is_visible(timeout=1000):
                if dismiss_welcome_to_communities(page, log_fn=log_fn, max_wait_ms=2000):
                    time.sleep(1.5)
                    try:
                        j_btn.wait_for(state="visible", timeout=5000)
                    except Exception: pass

            if j_btn.is_visible(timeout=1000):
                log_fn(f"  -> Clicking Join...")
                try:
                    from account_creator import human_click
                    human_click(page, j_btn)
                except Exception:
                    j_btn.click(force=True)
                time.sleep(2.5)
                
                # Check if Welcome to Communities popped up on clicking Join
                dismiss_welcome_to_communities(page, log_fn=log_fn, max_wait_ms=2000)

                agree = page.locator('button:has-text("Agree and join"):visible, div[role="button"]:has-text("Agree and join"):visible, button:has-text("Agree"):visible, button[data-testid="ocfSettingsListNextButton"]:visible, div[role="dialog"] button:has-text("Join"):visible').last
                try:
                    agree.wait_for(state="visible", timeout=4000)
                except Exception: pass

                if agree.is_visible(timeout=1000):
                    log_fn(f"  -> Agreeing to community rules...")
                    try:
                        from account_creator import human_click
                        human_click(page, agree)
                    except Exception:
                        agree.click(force=True)
                    time.sleep(2.5)
                    dismiss_welcome_to_communities(page, log_fn=log_fn, max_wait_ms=2000)
                    
                time.sleep(1.5)
                if page.locator('button:has-text("Joined"):visible, [aria-label*="Joined"]:visible').first.is_visible(timeout=3000):
                    log_fn(f"  -> SUCCESS: Joined '{c_name}'!")
                else:
                    log_fn(f"  -> Join confirmed for '{c_name}'.")
            else:
                log_fn(f"  -> Join button not visible for '{c_name}'.")
        except Exception as ce:
            if "closed" in str(ce).lower():
                log_fn("Notice: Browser window was closed before completing community verification. Skipping remaining browser steps.")
                break
            else:
                log_fn(f"  -> Notice on community '{c_name}': {ce}")
            
        time.sleep(2.0)
    return joined_comms

def login_twitter_with_credentials(
    account_id=None,
    username=None,
    password=None,
    two_factor_secret=None,
    display_name=None,
    bio=None,
    location=None,
    website=None,
    log_fn=print
):
    """
    Automates login on Twitter/X using username, password, and 2FA TOTP secret.
    Extracts session tokens (auth_token, ct0), updates profile display name/bio if requested,
    actively joins booster communities in-browser, and registers profile in profiles.json.
    """
    if not username or not password:
        raise ValueError("Username and password are required for login.")
        
    p_id = account_id or get_next_account_id()
    clean_user = username.lstrip("@").strip()
    clean_pwd = password.strip()
    clean_2fa = (two_factor_secret or "").replace(" ", "").strip().upper()
    
    user_data_dir = os.path.abspath(f"./user_data/{p_id}")
    os.makedirs(user_data_dir, exist_ok=True)
    cleanup_profile_locks(user_data_dir)
    
    # Configure display and stealth environment:
    # Prefer desktop display :0 with native GPU hardware acceleration if available, fallback to :99
    if sys.platform != "win32":
        if os.path.exists("/tmp/.X11-unix/X0"):
            os.environ["DISPLAY"] = ":0"
            if os.path.exists("/run/user/1000/gdm/Xauthority"):
                os.environ["XAUTHORITY"] = "/run/user/1000/gdm/Xauthority"
            elif os.path.exists(os.path.expanduser("~/.Xauthority")):
                os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
        elif "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
    
    log_fn(f"Initiating credential login for [{p_id}] (@{clean_user})...")
    log_fn(f"Target profile folder: {user_data_dir}")
    disp_target = os.environ.get('DISPLAY', 'Windows Native Desktop' if sys.platform == 'win32' else ':0')
    log_fn(f"Display target: {disp_target} (Native hardware GPU enabled)")
    if clean_2fa:
        pin, rem = generate_totp_pin(clean_2fa)
        log_fn(f"2FA Authenticator secret registered (Current live PIN: {pin}, {rem}s window).")
    
    with sync_playwright() as p:
        log_fn("Browser Engine: Native Google Chrome 155 via Patchright (channel='chrome')")
        
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--start-maximized"
        ]
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=args,
            ignore_default_args=STRIP_AUTOMATION_ARGS,
            no_viewport=True
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            log_fn("Navigating to https://x.com/login...")
            for nav_try in range(2):
                try:
                    page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=45000)
                    break
                except Exception as ne:
                    if nav_try == 0:
                        log_fn(f"Navigation retry notice: {ne}")
                        time.sleep(2.0)
                    else:
                        raise
            time.sleep(3.0)
            
            # Check if already authenticated from previous session
            cookies = context.cookies()
            auth_token_val = next((c["value"] for c in cookies if c["name"] == "auth_token"), None)
            ct0_val = next((c["value"] for c in cookies if c["name"] == "ct0"), None)
            
            if not auth_token_val:
                # Step 1: Locate username input
                u_inp = page.locator('input[autocomplete="username"], input[name="text"], input[type="text"]').first
                u_inp.wait_for(state="visible", timeout=25000)
                u_inp.click(force=True)
                time.sleep(0.3)
                u_inp.fill(clean_user)
                time.sleep(0.5)
                page.keyboard.press("Enter")
                log_fn(f"Entered username: @{clean_user}. Waiting for response...")
                time.sleep(5.0)
                
                # Check for rate limit or account not found
                body_text = page.inner_text("body").lower()
                url_current = page.url.lower()
                if "temporarily limited your login" in body_text:
                    page.screenshot(path=f"rate_limit_{p_id}.png")
                    raise RuntimeError("Twitter Notice: 'We’ve temporarily limited your login. Please try again later.' (IP or account is on a temporary cooldown).")
                if "couldn't find an active x account" in body_text:
                    raise ValueError(f"Twitter Notice: No active X account found for handle '@{clean_user}'.")
                
                # Step 2: Check for Phone Challenge vs Password
                phone_input = page.locator('input[placeholder="Phone number"], input[aria-label="Phone number"], input[type="tel"], #jf-phone-input-phone').first
                if ("enter your phone number" in body_text or "signup_phone" in url_current or phone_input.is_visible(timeout=2000)) and HeroSMSClient and standard_playwright:
                    log_fn("Phone binding prompt detected. Engaging HeroSMS fallback...")
                    hero = HeroSMSClient(min_wait_secs=15, max_wait_secs=180)
                    cleanup_profile_locks("./user_data/herosms_session")
                    
                    with standard_playwright() as sp:
                        hero_context = sp.chromium.launch_persistent_context(
                            user_data_dir="./user_data/herosms_session",
                            headless=True
                        )
                        hero_page = hero_context.pages[0] if hero_context.pages else hero_context.new_page()
                        phone_allocated = None
                        sms_code = None
                        
                        for p_try in range(3):
                            log_fn(f"HeroSMS: Requesting US number (try {p_try+1}/3)...")
                            try:
                                phone_allocated = hero.request_phone_number(hero_page, log_fn=log_fn)
                            except Exception as he:
                                log_fn(f"HeroSMS error: {he}")
                                time.sleep(3)
                                continue
                            if not phone_allocated:
                                continue
                                
                            digits = re.sub(r'\D', '', phone_allocated)
                            us_10 = digits[-10:] if len(digits) >= 10 else digits
                            log_fn(f"Entering phone +1 {us_10} into Twitter...")
                            
                            phone_input = page.locator('input[placeholder="Phone number"], input[aria-label="Phone number"], input[type="tel"], #jf-phone-input-phone').first
                            phone_input.click(force=True)
                            time.sleep(0.2)
                            phone_input.fill("")
                            for d in us_10:
                                page.keyboard.press(d)
                                time.sleep(0.04)
                            time.sleep(0.6)
                            
                            cont_btn = page.locator('button:has-text("Continue"), button[type="submit"]:has-text("Continue"), button:has-text("Next")').last
                            cont_btn.click()
                            time.sleep(3.0)
                            
                            flag_el = page.locator('text="Sorry, something is not right", text="Please try using a different method", text="We couldn\'t send you a text message"').first
                            if flag_el.is_visible(timeout=2000):
                                log_fn(f"Phone +1 {us_10} rejected. Canceling rental...")
                                hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=log_fn)
                                phone_allocated = None
                                time.sleep(2)
                                continue
                                
                            ok_modal = page.locator('button[data-testid="confirmationSheetConfirm"]:visible, button:text-is("OK"):visible, button:text-is("Ok"):visible, div[role="button"]:text-is("OK"):visible').first
                            if ok_modal.is_visible(timeout=3000):
                                ok_modal.click()
                                time.sleep(2.0)
                                
                            log_fn(f"Waiting for SMS on +1 {us_10}...")
                            try:
                                sms_code = hero.wait_for_verification_code(hero_page, phone_allocated, log_fn=log_fn)
                                if sms_code:
                                    break
                            except Exception as we:
                                log_fn(f"SMS wait exception: {we}")
                                hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=log_fn)
                                phone_allocated = None
                                time.sleep(2)
                                continue
                                
                        hero_context.close()
                        
                        if not sms_code:
                            raise RuntimeError("HeroSMS failed to supply verification code.")
                            
                        log_fn(f"Submitting SMS code: {sms_code}...")
                        code_inp = page.locator('input.jf-code-input-field, input[autocomplete="one-time-code"], input[name="code"], input[name="verfication_code"], input[placeholder*="code" i], input[data-testid="ocfEnterTextTextInput"]').first
                        code_inp.wait_for(state="visible", timeout=10000)
                        code_inp.click(force=True)
                        time.sleep(0.2)
                        code_inp.fill(sms_code)
                        time.sleep(0.5)
                        page.keyboard.press("Enter")
                        time.sleep(5.0)

                # Step 3: Handle Unusual Activity Check / Handle confirmation
                unusual_input = page.locator('input[data-testid="ocfEnterTextTextInput"]').first
                pwd_input = page.locator('input[name="password"], input[type="password"]').first
                if not pwd_input.is_visible(timeout=4000) and unusual_input.is_visible(timeout=2000):
                    log_fn("Twitter requested handle confirmation. Entering username...")
                    unusual_input.fill(clean_user)
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(4.0)
                    pwd_input = page.locator('input[name="password"], input[type="password"]').first

                # Step 4: Enter Password
                if not pwd_input.is_visible(timeout=12000):
                    page.screenshot(path=f"pwd_fail_{p_id}.png")
                    raise RuntimeError("Password input field did not appear.")

                log_fn("Entering account password...")
                pwd_input.click(force=True)
                time.sleep(0.3)
                pwd_input.fill(clean_pwd)
                time.sleep(0.5)
                page.keyboard.press("Enter")
                log_fn("Submitted password. Waiting for 2FA challenge...")
                time.sleep(6.0)

                # Step 5: Enter 2FA TOTP code
                totp_input = page.locator('input[data-testid="ocfEnterTextTextInput"], input[name="text"], input[type="text"]').first
                body_after = page.inner_text("body").lower()
                if "two-factor" in body_after or "authenticator" in body_after or totp_input.is_visible(timeout=3000):
                    if not clean_2fa:
                        page.screenshot(path=f"2fa_required_{p_id}.png")
                        raise ValueError("2FA PIN required by Twitter, but no 2FA Secret key was supplied.")
                    pin, rem = generate_totp_pin(clean_2fa)
                    if rem < 6:
                        log_fn(f"TOTP expiring in {rem}s, waiting for next window...")
                        time.sleep(rem + 1)
                        pin, rem = generate_totp_pin(clean_2fa)
                    log_fn(f"Entering TOTP code: {pin} ({rem}s valid)...")
                    totp_input.wait_for(state="visible", timeout=10000)
                    totp_input.click(force=True)
                    time.sleep(0.2)
                    totp_input.fill("")
                    for digit in pin:
                        page.keyboard.press(digit)
                        time.sleep(0.05)
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    log_fn("Submitted TOTP code. Awaiting home screen authorization...")
                    time.sleep(6.0)

                # Step 6: Post-login interstitials
                if handle_post_signup_onboarding:
                    try:
                        handle_post_signup_onboarding(page, log_fn=log_fn, max_steps=8)
                    except Exception as e:
                        log_fn(f"Notice: handle_post_signup_onboarding: {e}")

                for _ in range(3):
                    try:
                        skip = page.locator('button:has-text("Skip for now"), button:has-text("Maybe later"), button:has-text("Not now")').first
                        if skip.is_visible(timeout=2000):
                            skip.click()
                            time.sleep(2.0)
                    except Exception: pass

                cookies = context.cookies()
                auth_token_val = next((c["value"] for c in cookies if c["name"] == "auth_token"), None)
                ct0_val = next((c["value"] for c in cookies if c["name"] == "ct0"), None)

            if not auth_token_val:
                time.sleep(3.0)
                cookies = context.cookies()
                auth_token_val = next((c["value"] for c in cookies if c["name"] == "auth_token"), None)
                ct0_val = next((c["value"] for c in cookies if c["name"] == "ct0"), None)

            if not auth_token_val:
                page.screenshot(path=f"auth_fail_{p_id}.png")
                raise RuntimeError(f"Failed to capture auth_token cookie. Current URL: {page.url}")

            log_fn(f"SUCCESS: Session authorized! auth_token: {auth_token_val[:10]}... | ct0: {ct0_val[:10] if ct0_val else 'None'}...")

            # Step 7: PERSIST IMMEDIATELY before profile edit & community joins
            state_file = os.path.join(user_data_dir, "state.json")
            with open(state_file, "w") as sf:
                json.dump({"cookies": cookies, "origins": []}, sf, indent=2)
            log_fn(f"Saved authenticated state into {state_file}.")

            new_profile = {
                "id": p_id,
                "username": clean_user,
                "password": clean_pwd,
                "user_data_dir": user_data_dir,
                "auth_token": auth_token_val,
                "ct0": ct0_val or "",
                "auth_token_added": True,
                "two_factor_secret": clean_2fa,
                "display_name": display_name or "",
                "bio": bio or "",
                "website": website or "https://getmysocial.com/uwuscrettt",
                "status": "Active"
            }

            profiles_path = "profiles.json"
            cache_file = "communities_cache.json"

            with FILE_WRITE_LOCK:
                profiles = []
                if os.path.exists(profiles_path):
                    try:
                        with open(profiles_path, "r") as f:
                            profiles = json.load(f)
                    except Exception:
                        profiles = []
                        
                idx = next((i for i, p in enumerate(profiles) if p.get("id") == p_id), None)
                if idx is not None:
                    profiles[idx] = new_profile
                else:
                    profiles.append(new_profile)
                    
                with open(profiles_path, "w") as f:
                    json.dump(profiles, f, indent=4)
                log_fn(f"Saved [{p_id}] to profiles.json.")

            # Step 7.5: Profile Customization on X (Display Name & Bio & Website) if requested
            if display_name or (bio is not None and bio.strip()) or location or website:
                try:
                    update_twitter_profile(
                        page=page,
                        display_name=display_name,
                        bio=bio,
                        location=location,
                        website=website,
                        log_fn=log_fn
                    )
                except Exception as e:
                    log_fn(f"Warning: Failed to update profile details on X: {e}")

            # Step 8: Actually Join Communities in the browser session!
            joined_comms = []
            try:
                joined_comms = join_target_communities_in_browser(page, p_id, log_fn=log_fn)
            except Exception as jce:
                log_fn(f"Notice: Community join error: {jce}")

            # Re-save fresh cookies & communities_cache
            try:
                fresh_cookies = context.cookies()
                with open(state_file, "w") as sf:
                    json.dump({"cookies": fresh_cookies, "origins": []}, sf, indent=2)
            except Exception as ce:
                log_fn(f"Notice: Could not refresh post-join cookies (browser may have closed early): {ce}")

            with FILE_WRITE_LOCK:
                try:
                    cache_data = {}
                    if os.path.exists(cache_file):
                        try:
                            with open(cache_file, "r") as cf:
                                cache_data = json.load(cf)
                        except Exception:
                            pass
                    cache_data[p_id] = joined_comms
                    with open(cache_file, "w") as cf:
                        json.dump(cache_data, cf, indent=4)
                    log_fn(f"Updated communities cache for [{p_id}] with {len(joined_comms)} joined communities.")
                except Exception as ce:
                    log_fn(f"Notice: Failed updating communities cache: {ce}")

            # Auto-sync newly authenticated profile into any created scheduled jobs
            try:
                import queue_syncer
                synced_cnt = queue_syncer.sync_accounts_to_queued_jobs()
                log_fn(f"Auto-synced [{p_id}] into scheduled queue jobs (Total synced accounts: {synced_cnt}).")
            except Exception as sync_e:
                log_fn(f"Note: Queue sync note: {sync_e}")

            log_fn(f"SUCCESS: Account [{p_id}] (@{clean_user}) is active, communities joined, and ready to post!")
            return new_profile

        finally:
            try:
                for pg in list(context.pages):
                    try: pg.close()
                    except Exception: pass
            except Exception: pass
            try: context.close()
            except Exception: pass
            terminate_chrome_processes(user_data_dir=user_data_dir, log_fn=log_fn)

def batch_login_accounts(
    accounts_list,
    default_name=None,
    default_bio=None,
    default_website="https://getmysocial.com/uwuscrettt",
    use_female_vault=True,
    update_profile=True,
    concurrency=2,
    delay_seconds=8,
    skip_existing=True,
    log_fn=print,
    progress_fn=None
):
    """
    Batch logs in a list of accounts using 1 or multiple concurrent bots (default: 2 bots).
    For each account:
    - Calculates 2FA TOTP PIN
    - Logs in using stealth native Google Chrome on DISPLAY=:0
    - Extracts session auth_token
    - If update_profile is True: sets Female Display Name, Aesthetic Bio, and Website link
    - Saves profile to profiles.json and initializes booster communities
    - If skip_existing is True: checks profiles.json and immediately skips accounts that are already registered
    """
    total = len(accounts_list)
    successful = []
    skipped = []
    failed = []
    completed_count = 0
    allocated_ids = set()
    progress_lock = threading.Lock()
    
    # Bound concurrency between 1 and min(4, total)
    actual_concurrency = max(1, min(concurrency, total, 4))
    
    log_fn(f"Initiating batch login for {total} account(s) using {actual_concurrency} parallel bot worker(s) (Skip existing: {skip_existing})...")
    if update_profile and use_female_vault and female_profile_vault:
        log_fn(f"Female Profile Vault active: randomizing from 35 names, aesthetic bios, and website '{default_website}'.")
        
    event_queue = queue.Queue() if actual_concurrency > 1 else None

    def emit_log(msg):
        if event_queue is not None:
            event_queue.put(("log", msg))
        else:
            log_fn(msg)

    def emit_progress(curr, tot, status_txt):
        if event_queue is not None:
            event_queue.put(("progress", (curr, tot, status_txt)))
        elif progress_fn:
            progress_fn(curr, tot, status_txt)

    def process_item(item_info):
        nonlocal completed_count
        idx, acc, bot_id = item_info
        
        try:
            username = acc.get("username", "")
            password = acc.get("password", "")
            two_fa = acc.get("two_factor", "")
            
            # Thread-safe check for existing registered profile in profiles.json
            existing_prof = None
            if os.path.exists("profiles.json"):
                try:
                    with open("profiles.json", "r") as pf:
                        curr_profs = json.load(pf)
                    for p in curr_profs:
                        if p.get("username", "").strip().lower() == username.strip().lower():
                            existing_prof = p
                            break
                except Exception:
                    pass

            if existing_prof and existing_prof.get("id"):
                acc_id = existing_prof.get("id")
                if skip_existing:
                    emit_log(f"[Bot {bot_id}] [{idx}/{total}] SKIP: @{username} is already active as [{acc_id}] in profiles.json. Skipping login.")
                    with progress_lock:
                        skipped.append({
                            "id": acc_id,
                            "username": username,
                            "status": "Skipped (Already Active)",
                            "display_name": existing_prof.get("display_name", ""),
                            "bio": existing_prof.get("bio", ""),
                            "website": existing_prof.get("website", ""),
                            "auth_token": (existing_prof.get("auth_token", "")[:8] + "...") if existing_prof.get("auth_token") else ""
                        })
                        completed_count += 1
                        emit_progress(completed_count, total, f"[Bot {bot_id}] Skipped @{username} (Already Active)")
                    return
                else:
                    emit_log(f"[Bot {bot_id}] Detected existing registered profile [{acc_id}] for @{username}. Re-authenticating existing profile...")
            else:
                acc_id = acc.get("id") or get_next_account_id(allocated_ids=allocated_ids)
            
            # Stagger startup between parallel bots so Chrome doesn't launch at the identical sub-second
            if bot_id > 1 and idx <= actual_concurrency:
                stagger = (bot_id - 1) * 4.0
                emit_log(f"[Bot {bot_id}] Staggering browser startup by {stagger:.1f}s...")
                time.sleep(stagger)

            # Resolve Display Name: account-specific -> default_name -> female vault random pick
            if acc.get("display_name"):
                disp_name = acc.get("display_name")
            elif default_name:
                disp_name = default_name
            elif use_female_vault and female_profile_vault:
                disp_name = female_profile_vault.get_random_female_name()
            else:
                disp_name = None
                
            # Resolve Bio: account-specific -> default_bio -> female vault random pick
            if acc.get("bio"):
                bio_text = acc.get("bio")
            elif default_bio:
                bio_text = default_bio
            elif use_female_vault and female_profile_vault:
                bio_text = female_profile_vault.get_random_female_bio()
            else:
                bio_text = None
                
            # Resolve Website: account-specific -> default_website ("https://getmysocial.com/uwuscrettt")
            site_link = acc.get("website") or default_website or None

            emit_log(f"\n[Bot {bot_id}] [{idx}/{total}] Processing @{username} (Profile ID: {acc_id}). Target Name: '{disp_name}', Website: '{site_link}'...")
            emit_progress(completed_count, total, f"[Bot {bot_id}] Authenticating @{username}...")
                
            try:
                profile = login_twitter_with_credentials(
                    account_id=acc_id,
                    username=username,
                    password=password,
                    two_factor_secret=two_fa,
                    display_name=disp_name if update_profile else None,
                    bio=bio_text if update_profile else None,
                    website=site_link if update_profile else None,
                    log_fn=lambda m: emit_log(f"[Bot {bot_id}] {m}")
                )
                with progress_lock:
                    successful.append({
                        "id": acc_id,
                        "username": username,
                        "status": "Success",
                        "display_name": profile.get("display_name", ""),
                        "bio": profile.get("bio", ""),
                        "website": profile.get("website", ""),
                        "auth_token": (profile.get("auth_token", "")[:8] + "...") if profile.get("auth_token") else ""
                    })
                    completed_count += 1
                    emit_progress(completed_count, total, f"[Bot {bot_id}] Completed @{username} ({completed_count}/{total})")
                emit_log(f"[Bot {bot_id}] SUCCESS: [{acc_id}] (@{username}) successfully authenticated and saved!")
            except Exception as e:
                err_msg = str(e)
                with progress_lock:
                    failed.append({"id": acc_id, "username": username, "error": err_msg})
                    completed_count += 1
                    emit_progress(completed_count, total, f"[Bot {bot_id}] Failed @{username} ({completed_count}/{total})")
                emit_log(f"[Bot {bot_id}] ERROR: [{acc_id}] (@{username}) failed: {err_msg}")
                
            # Pacing cooldown if more accounts remain for this bot
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        except Exception as top_e:
            err_msg = str(top_e)
            with progress_lock:
                failed.append({"id": acc.get("id", f"account_idx_{idx}"), "username": acc.get("username", "unknown"), "error": err_msg})
                completed_count += 1
                emit_progress(completed_count, total, f"[Bot {bot_id}] Errored on task ({completed_count}/{total})")
            emit_log(f"[Bot {bot_id}] CRITICAL ERROR on item {idx}: {err_msg}")

    if actual_concurrency <= 1:
        # Sequential execution
        for i, acc in enumerate(accounts_list, 1):
            process_item((i, acc, 1))
    else:
        # Concurrent parallel bots execution with queue drained on the main thread
        tasks = []
        for i, acc in enumerate(accounts_list, 1):
            bot_num = ((i - 1) % actual_concurrency) + 1
            tasks.append((i, acc, bot_num))
            
        with ThreadPoolExecutor(max_workers=actual_concurrency) as executor:
            futures = [executor.submit(process_item, t) for t in tasks]
            while not all(f.done() for f in futures) or not event_queue.empty():
                try:
                    ev_type, ev_data = event_queue.get(timeout=0.1)
                    if ev_type == "log":
                        log_fn(ev_data)
                    elif ev_type == "progress":
                        if progress_fn:
                            progress_fn(ev_data[0], ev_data[1], ev_data[2])
                except queue.Empty:
                    pass
            for f in futures:
                try:
                    f.result()
                except Exception:
                    pass
            
    summary = {
        "total": total,
        "success_count": len(successful),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "successful": successful,
        "skipped": skipped,
        "failed": failed
    }
    log_fn(f"\nBatch Provisioning Complete ({actual_concurrency} bot(s)): {len(successful)} newly authenticated, {len(skipped)} skipped (already registered), {len(failed)} failed (out of {total} total).")
    return summary

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Log in to Twitter/X with username, password, and 2FA TOTP secret, with profile customization and multi-bot parallel execution.")
    parser.add_argument("--paste", help="Raw pasted text containing Username, Password, 2FA credentials", default=None)
    parser.add_argument("--batch", help="Raw multi-account text or path to accounts file", default=None)
    parser.add_argument("--id", help="Profile ID (default: auto)", default=None)
    parser.add_argument("--username", "-u", help="Username / handle", default=None)
    parser.add_argument("--password", "-p", help="Password", default=None)
    parser.add_argument("--two-factor", "-2fa", help="2FA TOTP Secret Key", default=None)
    parser.add_argument("--name", help="Display Name to set on X (leave blank to pick from Female Vault)", default=None)
    parser.add_argument("--bio", help="Profile Bio to set on X (leave blank to pick from Aesthetic Vault)", default=None)
    parser.add_argument("--website", help="Website URL to set on X profile", default="https://getmysocial.com/uwuscrettt")
    parser.add_argument("--concurrency", "-c", type=int, help="Number of concurrent bots to run in parallel (default: 2)", default=2)
    parser.add_argument("--delay", type=int, help="Cooldown delay between batch logins in seconds", default=8)
    parser.add_argument("--no-vault", action="store_true", help="Disable random female name/bio vault fallback")
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false", help="Disable skipping of accounts already active in profiles.json")
    parser.set_defaults(skip_existing=True)
    
    args = parser.parse_args()
    
    if args.batch:
        raw_text = args.batch
        if os.path.exists(raw_text):
            with open(raw_text, "r") as f:
                raw_text = f.read()
        parsed_list = parse_bulk_accounts_text(raw_text)
        print(f"Loaded {len(parsed_list)} accounts for batch login.")
        res = batch_login_accounts(
            parsed_list,
            default_name=args.name,
            default_bio=args.bio,
            default_website=args.website,
            use_female_vault=not args.no_vault,
            update_profile=True,
            concurrency=args.concurrency,
            delay_seconds=args.delay,
            skip_existing=args.skip_existing
        )
        print("Batch Result:", res)
        sys.exit(0)
        
    u = args.username
    p = args.password
    two_fa = args.two_factor
    name = args.name
    bio = args.bio
    website = args.website
    
    if args.paste:
        parsed = parse_single_account_block(args.paste)
        u = u or parsed.get("username")
        p = p or parsed.get("password")
        two_fa = two_fa or parsed.get("two_factor")
        name = name or parsed.get("display_name")
        bio = bio or parsed.get("bio")
        website = website or parsed.get("website", "https://getmysocial.com/uwuscrettt")
        
    if not u or not p:
        print("Error: Username and password are required. Provide --username and --password, use --paste, or use --batch.", file=sys.stderr)
        sys.exit(1)
        
    if not name and not args.no_vault and female_profile_vault:
        name = female_profile_vault.get_random_female_name()
    if not bio and not args.no_vault and female_profile_vault:
        bio = female_profile_vault.get_random_female_bio()
        
    res = login_twitter_with_credentials(
        account_id=args.id,
        username=u,
        password=p,
        two_factor_secret=two_fa,
        display_name=name,
        bio=bio,
        website=website
    )
    print("Result:", res)
