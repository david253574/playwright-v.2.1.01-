import os
import sys
import time
import re
import json
import math
import random
import string
import shutil
try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright
from herosms_client import HeroSMSClient

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

def human_move(page, target_x, target_y, start_x=None, start_y=None):
    """
    Generates a natural Cubic Bezier trajectory with Fitts's law deceleration
    and physiological micro-tremors to avoid Arkose/biometric behavioral traps.
    """
    if start_x is None or start_y is None:
        start_x = random.randint(200, 600)
        start_y = random.randint(200, 450)
        page.mouse.move(start_x, start_y)
        
    dx = target_x - start_x
    dy = target_y - start_y
    dist = math.hypot(dx, dy)
    steps = max(20, min(50, int(dist / 12)))
    
    dev = random.uniform(-0.2, 0.2) * dist
    mid_x = (start_x + target_x) / 2 - (dy / (dist + 1e-5)) * dev
    mid_y = (start_y + target_y) / 2 + (dx / (dist + 1e-5)) * dev
    
    ctrl1_x = start_x + (mid_x - start_x) * random.uniform(0.5, 0.8) + random.uniform(-8, 8)
    ctrl1_y = start_y + (mid_y - start_y) * random.uniform(0.5, 0.8) + random.uniform(-8, 8)
    ctrl2_x = mid_x + (target_x - mid_x) * random.uniform(0.2, 0.5) + random.uniform(-8, 8)
    ctrl2_y = mid_y + (target_y - mid_y) * random.uniform(0.2, 0.5) + random.uniform(-8, 8)
    
    for i in range(1, steps + 1):
        raw_t = i / steps
        t = 1 - (1 - raw_t) ** 2.2
        cx = (1-t)**3 * start_x + 3*(1-t)**2 * t * ctrl1_x + 3*(1-t) * t**2 * ctrl2_x + t**3 * target_x
        cy = (1-t)**3 * start_y + 3*(1-t)**2 * t * ctrl1_y + 3*(1-t) * t**2 * ctrl2_y + t**3 * target_y
        if i < steps:
            cx += random.uniform(-0.8, 0.8)
            cy += random.uniform(-0.8, 0.8)
        page.mouse.move(cx, cy)
        time.sleep(random.uniform(0.008, 0.018))
    return target_x, target_y

def human_click(page, locator):
    """Performs natural mouse movement, pre-click dwell, and realistic mousedown duration."""
    try:
        locator.scroll_into_view_if_needed(timeout=2500)
    except Exception:
        pass
    try:
        box = locator.bounding_box(timeout=2000)
        if not box:
            try: locator.click(force=True, timeout=2500)
            except Exception: pass
            return
        target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
        target_y = box['y'] + box['height'] * random.uniform(0.35, 0.65)
        human_move(page, target_x, target_y)
        time.sleep(random.uniform(0.12, 0.22))
        page.mouse.down()
        time.sleep(random.uniform(0.07, 0.14))
        page.mouse.up()
        time.sleep(random.uniform(0.15, 0.3))
    except Exception:
        try:
            locator.click(force=True, timeout=2500)
        except Exception:
            pass

def human_type(locator, text):
    """Enforces human-like variable keystroke latency instead of uniform delays."""
    try:
        locator.focus()
        time.sleep(random.uniform(0.1, 0.2))
        for ch in text:
            locator.press_sequentially(ch, delay=0)
            time.sleep(random.uniform(0.06, 0.18))
    except Exception:
        try: locator.fill(text)
        except Exception: pass


FIRST_NAMES = [
    "Jessica", "Amber", "Chloe", "Maya", "Hannah", "Sophia", "Olivia", "Emma",
    "Samantha", "Ashley", "Taylor", "Megan", "Brianna", "Kylie", "Lauren", "Rachel"
]

LAST_NAMES = [
    "Miller", "Cole", "Reed", "Brooks", "Davis", "Taylor", "Evans", "Clark",
    "Wilson", "Hayes", "Morgan", "Bennett", "Carter", "Parker", "Bell", "Turner"
]

def get_next_account_id(profiles_path="profiles.json", archive_path=None, allocated_ids=None):
    """Finds the lowest available sequential account ID starting from 1, checking active profiles in profiles.json."""
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

def generate_random_profile():
    """Generates realistic profile credentials."""
    fname = random.choice(FIRST_NAMES)
    lname = random.choice(LAST_NAMES)
    full_name = f"{fname} {lname}"
    
    suffix = "".join(random.choices(string.digits, k=3))
    handle = f"{fname.lower()}_{lname.lower()[:3]}{suffix}"
    
    pwd_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    password = f"XPromo_{pwd_suffix}!8"
    
    b_month = str(random.randint(1, 12))
    b_day = str(random.randint(1, 28))
    b_year = str(random.randint(1996, 2004))
    
    bio = "soft spoken 18yo college girl ♡ your favorite distraction ↓"
    try:
        import female_profile_vault
        bio = female_profile_vault.get_random_female_bio() or bio
    except Exception: pass
    
    return {
        "name": full_name,
        "username": handle,
        "password": password,
        "bio": bio,
        "birth_month": b_month,
        "birth_day": b_day,
        "birth_year": b_year
    }

def fill_birthday_if_present(x_page, creds, log_fn, timeout=4000):
    """Fills birthday selects (Month, Day, Year) if present on current screen."""
    MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    month_select = x_page.locator('#jf-date-date_of_birth-month, select[name="date_of_birth-month"], select[aria-label*="month" i], select:has(option:has-text("January"))').first
    if month_select.is_visible(timeout=timeout):
        m_val = str(creds.get("birth_month", "6"))
        d_val = str(creds.get("birth_day", "14"))
        y_val = str(creds.get("birth_year", "1999"))
        
        log_fn(f"Setting date of birth: Month={m_val}, Day={d_val}, Year={y_val}...")
        
        # 1. Month
        try:
            m_idx = int(m_val) if m_val.isdigit() else 6
            try:
                month_select.select_option(value=str(m_idx))
            except Exception:
                month_select.select_option(label=MONTH_NAMES[m_idx])
        except Exception as e:
            log_fn(f"Note: month selection fallback: {e}")
        time.sleep(0.5)
        
        # 2. Day
        day_select = x_page.locator('#jf-date-date_of_birth-day, select[name="date_of_birth-day"], select[aria-label*="day" i]').first
        if day_select.is_visible():
            try:
                day_select.select_option(value=str(d_val))
            except Exception:
                try: day_select.select_option(label=str(d_val))
                except Exception: pass
            time.sleep(0.5)
            
        # 3. Year (Ensuring 18+ to meet platform age requirements)
        year_select = x_page.locator('#jf-date-date_of_birth-year, select[name="date_of_birth-year"], select[aria-label*="year" i]').first
        if year_select.is_visible():
            try:
                year_select.select_option(value=str(y_val))
            except Exception:
                try: year_select.select_option(label=str(y_val))
                except Exception: pass
            time.sleep(0.5)
            
        # 4. Submit
        bday_submit = x_page.locator('button:has(p:has-text("Continue")), button[type="submit"]:has-text("Continue"), button:has-text("Continue"), button:has-text("Next")').last
        if bday_submit.is_visible(timeout=3000):
            log_fn("Submitting date of birth...")
            human_click(x_page, bday_submit)
            time.sleep(4.0)
        return True
    return False

def safe_type_input(page, locator, text_value):
    """
    Safely and reliably clears and types text into input fields,
    ensuring React synthetic events and controlled component state are triggered.
    """
    try:
        locator.scroll_into_view_if_needed()
        try:
            human_click(page, locator)
        except Exception:
            locator.click(force=True)
        time.sleep(0.15)
        # Clear field completely
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        time.sleep(0.1)
        # Type sequential characters with human-like latency
        locator.press_sequentially(str(text_value), delay=random.randint(25, 55))
        time.sleep(0.2)
        # Dispatch input & change events in DOM as safety net for React state machine
        try:
            locator.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }")
        except Exception: pass
    except Exception:
        try:
            locator.fill(str(text_value))
        except Exception: pass

def dismiss_error_retry_modals_if_present(x_page, log_fn=print):
    """
    Detects and dismisses Twitter transient error popups like
    'Something went wrong. Try reloading.' by clicking 'Retry'.
    """
    try:
        dialog = x_page.locator('div[role="dialog"]').first
        d_text = dialog.inner_text().lower() if dialog.is_visible(timeout=500) else ""
        if "something went wrong" in d_text or "try reloading" in d_text or "try again" in d_text:
            retry_btn = x_page.locator('button:has-text("Retry"):visible, div[role="button"]:has-text("Retry"):visible, button:has-text("Try again"):visible').first
            if retry_btn.is_visible(timeout=1500):
                log_fn("Transient error modal detected ('Something went wrong'). Clicking 'Retry'...")
                try: human_click(x_page, retry_btn)
                except Exception: retry_btn.click(force=True)
                time.sleep(3.0)
                return True
    except Exception: pass
    return False

def fill_individual_setup_screens_if_present(x_page, creds, log_fn=print):
    """
    Handles Twitter/X when Name, Username, or Password prompts are presented on separate single-field screens.
    """
    try:
        dialog = x_page.locator('div[role="dialog"]').first
        dialog_text = dialog.inner_text().lower() if dialog.is_visible(timeout=500) else x_page.inner_text("body").lower()

        name_inp = x_page.locator('input[name="name"], input[autocomplete="name"]').first
        user_inp = x_page.locator('input[name="username"], input[placeholder*="username" i]').first
        pwd_inp = x_page.locator('input[name="password"], input[type="password"]:visible').first

        # Case 1: Separate Password screen ("You'll need a password")
        if pwd_inp.is_visible(timeout=800) and not user_inp.is_visible() and not name_inp.is_visible():
            target_pwd = creds.get("password", "XPromo_Pass!8")
            log_fn("Single Password setup screen active. Entering password...")
            safe_type_input(x_page, pwd_inp, target_pwd)
            time.sleep(0.5)
            next_btn = x_page.locator('button:has-text("Next"):visible, button:has-text("Continue"):visible, button[type="submit"]:visible').last
            if next_btn.is_visible(timeout=2000):
                try: human_click(x_page, next_btn)
                except Exception: next_btn.click(force=True)
                time.sleep(3.0)
                return True

        # Case 2: Separate Username screen ("What should we call you?")
        if user_inp.is_visible(timeout=800) and not pwd_inp.is_visible():
            current_user = creds.get("username", "user123")[:15]
            log_fn(f"Single Username setup screen active. Entering @{current_user}...")
            safe_type_input(x_page, user_inp, current_user)
            time.sleep(1.0)
            next_btn = x_page.locator('button:has-text("Next"):visible, button:has-text("Continue"):visible, button[type="submit"]:visible').last
            if next_btn.is_visible(timeout=2000):
                try: human_click(x_page, next_btn)
                except Exception: next_btn.click(force=True)
                time.sleep(3.0)
                return True

        # Case 3: Separate Name screen ("What's your name?")
        if name_inp.is_visible(timeout=800) and not pwd_inp.is_visible() and not user_inp.is_visible():
            target_name = creds.get("name", "Jessica Miller")
            log_fn(f"Single Name setup screen active. Entering '{target_name}'...")
            safe_type_input(x_page, name_inp, target_name)
            time.sleep(0.5)
            next_btn = x_page.locator('button:has-text("Next"):visible, button:has-text("Continue"):visible, button[type="submit"]:visible').last
            if next_btn.is_visible(timeout=2000):
                try: human_click(x_page, next_btn)
                except Exception: next_btn.click(force=True)
                time.sleep(3.0)
                return True
    except Exception as e:
        log_fn(f"Single setup screen note: {e}")
    return False

def fill_unified_setup_if_present(x_page, creds, log_fn=print, max_wait_sec=25):
    """
    Handles Twitter/X 'Set up your account' popup modal / screen:
    Fields:
      - Name: 'Full name'
      - Username: '@Username'
      - Password: 'Password'
    Fills all credentials with realistic keystroke emulation, actively validates
    that username is accepted (automatically resolving taken/invalid username errors),
    and waits for the Continue button to become enabled before submitting and verifying dismissal.
    """
    start_t = time.time()
    while time.time() - start_t < max_wait_sec:
        try:
            # Check for transient error reload dialog first
            dismiss_error_retry_modals_if_present(x_page, log_fn=log_fn)

            dialog_text = ""
            try:
                d = x_page.locator('div[role="dialog"]').first
                dialog_text = d.inner_text().lower() if d.is_visible() else x_page.inner_text("body").lower()
            except Exception: pass

            name_inp = x_page.locator('input[name="name"], input[autocomplete="name"], input[placeholder*="full name" i], input#jf-input-name').first
            user_inp = x_page.locator('input[name="username"], input[placeholder*="username" i], input#jf-input-username, input[autocomplete="username"]').first
            pwd_inp = x_page.locator('input[name="password"], input[type="password"]:visible, input[autocomplete="new-password"], input#jf-input-password').first

            is_setup_screen = (
                "set up your account" in dialog_text or 
                "choose a name, username" in dialog_text or 
                "choose a name" in dialog_text or
                (name_inp.is_visible() and pwd_inp.is_visible()) or
                (user_inp.is_visible() and pwd_inp.is_visible())
            )

            if is_setup_screen:
                log_fn(f"Unified 'Set up your account' screen active! Filling credentials for {creds.get('name')} (@{creds.get('username')})...")

                # 1. Fill Name
                if name_inp.is_visible():
                    target_name = creds.get("name", "Jessica Miller")
                    cur_name = ""
                    try: cur_name = name_inp.input_value()
                    except Exception: pass
                    if cur_name != target_name:
                        log_fn(f"Entering display name: '{target_name}'...")
                        safe_type_input(x_page, name_inp, target_name)
                        time.sleep(0.3)

                # 2. Fill Password
                if pwd_inp.is_visible():
                    target_pwd = creds.get("password", "XPromo_Pass!8")
                    cur_pwd = ""
                    try: cur_pwd = pwd_inp.input_value()
                    except Exception: pass
                    if len(cur_pwd) < 8:
                        log_fn("Entering account password...")
                        safe_type_input(x_page, pwd_inp, target_pwd)
                        time.sleep(0.3)

                # 3. Fill Username & Handle Dynamic Validation
                if user_inp.is_visible():
                    current_user = creds.get("username", "user123")[:15]
                    username_accepted = False

                    for attempt in range(5):
                        log_fn(f"Entering username: @{current_user} (attempt {attempt+1}/5)...")
                        safe_type_input(x_page, user_inp, current_user)
                        time.sleep(0.5)

                        # Trigger validation blur
                        try:
                            x_page.keyboard.press("Tab")
                        except Exception: pass

                        # Wait for Twitter's async validation check (up to 4 seconds)
                        is_taken = False
                        is_available = False
                        for _ in range(8):
                            time.sleep(0.5)
                            check_text = ""
                            try:
                                d = x_page.locator('div[role="dialog"]').first
                                check_text = d.inner_text().lower() if d.is_visible() else x_page.inner_text("body").lower()
                            except Exception: pass

                            # Check for error indicators
                            if any(err in check_text for err in [
                                "has been taken", 
                                "already been taken", 
                                "not available", 
                                "choose another", 
                                "shorter than 15 characters",
                                "can only contain"
                            ]):
                                is_taken = True
                                break

                            # Check for success indicators
                            if (
                                "is available" in check_text or 
                                "username is available" in check_text or 
                                x_page.locator('svg[data-icon="icon-check"], svg[color*="green"]').first.is_visible()
                            ):
                                is_available = True
                                break

                        if is_taken:
                            # Generate alternative handle <= 15 chars
                            raw_base = re.sub(r'[^a-zA-Z0-9]', '', creds.get("username", "user"))
                            raw_base = re.sub(r'\d+$', '', raw_base)[:8]
                            if len(raw_base) < 3: raw_base = "maya"
                            alt_suffix = str(random.randint(100, 9999))
                            alt_user = f"{raw_base}_{alt_suffix}"[:15]
                            log_fn(f"Username @{current_user} is taken. Adjusting to @{alt_user}...")
                            current_user = alt_user
                            creds["username"] = alt_user
                        else:
                            log_fn(f"Username @{current_user} is valid and accepted!")
                            username_accepted = True
                            break

                time.sleep(1.0)

                # 4. Wait for Continue button to be ENABLED
                submit_btn = None
                for _ in range(6):
                    btns = x_page.locator(
                        'button[type="submit"]:has-text("Continue"):visible, '
                        'button:has-text("Continue"):visible, '
                        'button:has(p:has-text("Continue")):visible, '
                        'div[role="button"]:has-text("Continue"):visible, '
                        'div[role="button"]:has(p:has-text("Continue")):visible, '
                        'button[data-testid*="next" i]:visible, '
                        'button[data-testid*="continue" i]:visible, '
                        'button[type="submit"]:has-text("Next"):visible, '
                        'button:has-text("Next"):visible, '
                        'div[role="button"]:has-text("Next"):visible'
                    ).all()

                    for b in reversed(btns):
                        try:
                            if b.is_visible():
                                disabled_attr = b.get_attribute("disabled")
                                aria_disabled = b.get_attribute("aria-disabled")
                                if disabled_attr is None and aria_disabled != "true":
                                    submit_btn = b
                                    break
                        except Exception: pass
                    if submit_btn:
                        break
                    time.sleep(0.8)

                # 5. Submit form
                if submit_btn:
                    log_fn("Submitting unified setup form (Continue)...")
                    try:
                        human_click(x_page, submit_btn)
                    except Exception:
                        try: submit_btn.click(force=True)
                        except Exception: pass
                else:
                    log_fn("Continue button still awaiting trigger. Pressing Enter & dispatching form submit...")
                    try: pwd_inp.press("Enter")
                    except Exception: pass
                    try:
                        x_page.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('button, div[role="button"], div.jf-element'));
                            for (let b of btns) {
                                if (b.innerText && (b.innerText.trim() === "Continue" || b.innerText.trim() === "Next")) {
                                    b.removeAttribute('disabled');
                                    b.setAttribute('aria-disabled', 'false');
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                    except Exception: pass

                # 6. Verify that "Set up your account" dialog actually dismissed
                for _ in range(6):
                    time.sleep(1.0)
                    check_dismiss = ""
                    try:
                        d = x_page.locator('div[role="dialog"]').first
                        if d.is_visible():
                            check_dismiss = d.inner_text().lower()
                        else:
                            log_fn("SUCCESS: 'Set up your account' dialog cleared!")
                            return True
                    except Exception:
                        log_fn("SUCCESS: 'Set up your account' dialog cleared!")
                        return True

                    if "set up your account" not in check_dismiss and "choose a name, username" not in check_dismiss:
                        log_fn("SUCCESS: 'Set up your account' dialog cleared and transitioned!")
                        return True

                log_fn("Unified setup dialog still visible. Will retry...")
                return False

        except Exception as e:
            log_fn(f"Unified setup handler note: {e}")
            return False

        time.sleep(1.0)

    return False

def cleanup_profile_locks(user_data_dir):
    """
    Cleans up any stale SingletonLock, SingletonSocket, SingletonCookie files
    and terminates any orphaned processes associated with user_data_dir.
    """
    if not os.path.exists(user_data_dir):
        return

    if sys.platform == "win32":
        try:
            import subprocess
            abs_dir = os.path.abspath(user_data_dir)
            ps_cmd = f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*user-data-dir={abs_dir}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8)
        except Exception:
            pass
    else:
        lock_file = os.path.join(user_data_dir, "SingletonLock")
        if os.path.lexists(lock_file):
            try:
                target = os.readlink(lock_file)
                parts = target.rsplit('-', 1)
                if len(parts) == 2:
                    pid = int(parts[1])
                    try:
                        os.kill(pid, 9)
                        time.sleep(0.5)
                    except OSError:
                        pass
            except Exception:
                pass

    for fname in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        fpath = os.path.join(user_data_dir, fname)
        if os.path.lexists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

def prepare_phone_input_dialog(x_page, log_fn=print):
    """
    Ensures that the X phone signup dialog is active and ready for input
    using natural human cursor movement and interaction.
    Prevents unwanted page reloads or back-navigation once inside the JoinFlow session.
    """
    try:
        if x_page.is_closed():
            ctx = x_page.context
            x_page = ctx.pages[0] if ctx.pages else ctx.new_page()
    except Exception: pass

    phone_input = x_page.locator('#jf-phone-input-phone, input[name="phone"], input[type="tel"]').first
    dialog = x_page.locator('div[role="dialog"]').first

    # 1. First check if phone input is ALREADY visible
    try:
        if phone_input.is_visible(timeout=1500):
            return dialog if dialog.is_visible() else x_page, phone_input
    except Exception: pass

    # 2. If sitting on verification code screen, click Back to return to phone entry
    code_inp = x_page.locator('input.jf-code-input-field, input[autocomplete="one-time-code"], input[name="code"], input[name="verfication_code"], input[name="verification_code"], input[data-testid="ocfEnterTextTextInput"]').first
    try:
        if code_inp.is_visible(timeout=1000):
            log_fn("Active page is on verification code screen; clicking Back to return to phone entry...")
            back_btn = x_page.locator('button:has(svg[data-icon="icon-arrow-left"]):visible, button[aria-label="Back"]:visible, div[aria-label="Back"]:visible, button[data-testid="app-bar-back"]:visible, div[data-testid="app-bar-back"]:visible').first
            if back_btn.is_visible(timeout=2000):
                human_click(x_page, back_btn)
                time.sleep(2.0)
                
                # Check for "Discard changes?" or similar confirmation modal
                discard_btn = x_page.locator('button[data-testid="confirmationSheetConfirm"]:visible, button:has-text("Discard"):visible, div[role="button"]:has-text("Discard"):visible').first
                if discard_btn.is_visible(timeout=1500):
                    log_fn("Confirming discard of incomplete registration attempt...")
                    human_click(x_page, discard_btn)
                    time.sleep(2.0)

                if phone_input.is_visible(timeout=3000):
                    return dialog if dialog.is_visible() else x_page, phone_input
    except Exception: pass

    # 3. Dismiss any close or discard button if an blocking overlay is present
    try:
        close_btn = x_page.locator('button[aria-label="Close"]:visible, div[role="dialog"] [data-testid="app-bar-close"]:visible, button:has-text("Discard"):visible').first
        if close_btn.is_visible(timeout=1500):
            human_click(x_page, close_btn)
            time.sleep(1.5)
    except Exception: pass

    # 4. Check if 'Continue with phone' / 'Create account' button is present on landing
    p_btn = x_page.locator('button:has-text("Continue with phone"):visible, a:has-text("Continue with phone"):visible, div[role="button"]:has-text("Continue with phone"):visible, button:has-text("Create account"):visible, a:has-text("Create account"):visible').first
    try:
        if p_btn.is_visible(timeout=3000):
            log_fn("Found phone entry button. Dispatching click...")
            human_click(x_page, p_btn)
            time.sleep(3.0)
            if phone_input.is_visible(timeout=5000):
                return dialog if dialog.is_visible() else x_page, phone_input
    except Exception: pass

    # 5. Fallback: navigate cleanly to signup flow
    log_fn("Restoring https://x.com/i/flow/signup...")
    x_page.goto("https://x.com/i/flow/signup", wait_until="domcontentloaded", timeout=45000)
    time.sleep(3.0)

    # Dismiss cookie banner if present
    try:
        cookie_btn = x_page.locator('button:text-is("Accept all cookies"):visible, button:text-is("Refuse non-essential cookies"):visible').first
        if cookie_btn.is_visible(timeout=2000):
            cookie_btn.click(force=True)
            time.sleep(1.0)
    except Exception: pass

    p_btn = x_page.locator('button:has-text("Continue with phone"):visible, a:has-text("Continue with phone"):visible, div[role="button"]:has-text("Continue with phone"):visible, button:has-text("Create account"):visible, a:has-text("Create account"):visible').first
    try:
        if p_btn.is_visible(timeout=4000):
            human_click(x_page, p_btn)
            time.sleep(3.0)
    except Exception: pass

    try:
        phone_input.wait_for(state="visible", timeout=10000)
    except Exception: pass

    return dialog if dialog.is_visible() else x_page, phone_input

def handle_privacy_and_settings_review(page, log_fn=print, max_attempts=6):
    """
    Handles Twitter/X mandatory privacy agreement and settings review flow:
    1. 'Keeping your trust by protecting your privacy' -> clicks 'Agree and continue' (OCF_CallToAction_Button).
    2. 'Review your current settings' -> clicks 'Continue your review' (Ocf_Scroll_Prompt_Container),
       scrolls data-viewportview container to bottom, dispatches 'scroll' event,
       removes disabled attribute, and clicks 'Agree' (ocfSettingsListNextButton).
    """
    did_handle_any = False
    for attempt in range(max_attempts):
        handled = False
        dialog_text = ""
        try:
            d = page.locator('div[role="dialog"]').first
            dialog_text = d.inner_text().lower() if d.is_visible() else page.inner_text("body").lower()
        except Exception: pass

        # Screen 1: 'Keeping your trust by protecting your privacy'
        agree_cta = page.locator('button[data-testid="OCF_CallToAction_Button"]:visible, button:has-text("Agree and continue"):visible, button:has(span:has-text("Agree and continue")):visible').first
        if agree_cta.is_visible(timeout=1000) or "protecting your privacy" in dialog_text or "keeping your trust" in dialog_text:
            log_fn("Privacy Consent: 'Keeping your trust by protecting your privacy' detected. Clicking 'Agree and continue'...")
            try:
                human_click(page, agree_cta)
            except Exception:
                try: agree_cta.click(force=True)
                except Exception: pass
            time.sleep(2.5)
            handled = True
            did_handle_any = True

        # Screen 2: 'Review your current settings'
        review_header = page.locator('[data-testid="ocfSettingsListPrimaryText"]:visible, h1:has-text("Review your current settings"):visible').first
        review_btn = page.locator('button[data-testid="ocfSettingsListNextButton"]:visible, button:has-text("Agree"):visible, button:has(span:has-text("Agree")):visible').last
        scroll_prompt = page.locator('div[data-testid="Ocf_Scroll_Prompt_Container"] button:visible, button:has-text("Continue your review"):visible').first
        
        if review_header.is_visible(timeout=1000) or review_btn.is_visible(timeout=1000) or scroll_prompt.is_visible(timeout=1000) or "review your current settings" in dialog_text or "current selections" in dialog_text:
            log_fn("Privacy Consent: 'Review your current settings' detected. Advancing review scroll...")
            
            # Click 'Continue your review' prompt buttons sequentially until cleared
            for p_step in range(5):
                prompt_el = page.locator('div[data-testid="Ocf_Scroll_Prompt_Container"] button:visible, button:has-text("Continue your review"):visible').first
                if prompt_el.is_visible(timeout=1200):
                    log_fn(f"Clicking 'Continue your review' scroll prompt (step {p_step+1})...")
                    try:
                        human_click(page, prompt_el)
                    except Exception:
                        try: prompt_el.click(force=True)
                        except Exception: pass
                    time.sleep(1.0)
                else:
                    break

            # Force complete scroll in DOM and dispatch synthetic scroll event to update React state
            try:
                page.evaluate("""() => {
                    const containers = document.querySelectorAll('div[data-viewportview="true"], div[role="dialog"], section, div[role="group"]');
                    containers.forEach(c => {
                        c.scrollTop = c.scrollHeight;
                        c.dispatchEvent(new Event('scroll', { bubbles: true }));
                    });
                    window.scrollTo(0, document.body.scrollHeight);
                }""")
            except Exception: pass
            time.sleep(1.5)

            # Click the enabled 'Agree' button
            submit_btn = page.locator('button[data-testid="ocfSettingsListNextButton"]:visible, button:has-text("Agree"):visible, button:has(span:has-text("Agree")):visible').last
            if submit_btn.is_visible(timeout=2500):
                log_fn("Submitting settings review ('Agree')...")
                # Ensure disabled attribute is removed if still set by React delay
                try:
                    page.evaluate("""() => {
                        const btn = document.querySelector('button[data-testid="ocfSettingsListNextButton"]');
                        if (btn) {
                            btn.removeAttribute('disabled');
                            btn.setAttribute('aria-disabled', 'false');
                        }
                    }""")
                except Exception: pass
                
                try:
                    human_click(page, submit_btn)
                except Exception:
                    try: submit_btn.click(force=True)
                    except Exception: pass
                time.sleep(3.0)
                handled = True
                did_handle_any = True

        if not handled:
            break
            
    return did_handle_any

def handle_post_signup_onboarding(x_page, log_fn=print, max_steps=15, bio=None, creds=None):
    """
    Handles Twitter / X post-signup onboarding stages:
    1. Mandatory Privacy & Settings Review ('Keeping your trust' / 'Review your current settings')
    2. 'Pick your interests' ('Select 3 topics to continue') -> picks at least 3 topics, then clicks Continue.
    3. 'Suggested for you' ('Follow accounts to personalize your timeline') -> clicks Continue.
    4. 'People you may know' ('Follow people you know on X') -> clicks Continue.
    5. 'Describe yourself' / Profile Bio setup screen -> fills bio if provided, or clicks Skip for now / Next.
    6. 'Pick a profile picture' -> clicks Skip for now / Next.
    7. Optional notification/app/privacy prompts -> clicks Skip for now / Maybe later / Not now.
    """
    log_fn("Starting post-signup onboarding handler...")
    consecutive_idle = 0
    
    for step in range(max_steps):
        time.sleep(2.0)
        
        # Check if already reached home feed
        if "/home" in x_page.url:
            log_fn("Onboarding: Home feed (/home) reached! Onboarding complete.")
            break
            
        # Check for transient error reload dialog
        dismiss_error_retry_modals_if_present(x_page, log_fn=log_fn)

        # Check for unified credential setup or birthday if prompted
        if creds:
            if fill_birthday_if_present(x_page, creds, log_fn):
                consecutive_idle = 0
                continue
            if fill_unified_setup_if_present(x_page, creds, log_fn, max_wait_sec=15):
                consecutive_idle = 0
                continue
            if fill_individual_setup_screens_if_present(x_page, creds, log_fn=log_fn):
                consecutive_idle = 0
                continue

        # Check and handle Privacy / Terms Agreement and Settings Review
        if handle_privacy_and_settings_review(x_page, log_fn=log_fn):
            consecutive_idle = 0
            continue

        dialog_text = ""
        try:
            dialog = x_page.locator('div[role="dialog"]').first
            if dialog.is_visible(timeout=1000):
                dialog_text = dialog.inner_text().lower()
            else:
                dialog_text = x_page.inner_text("body").lower()
        except Exception: pass

        action_taken = False

        # Welcome to Communities modal ("Welcome to Communities" / "Check it out")
        if "welcome to communities" in dialog_text or "check it out" in dialog_text:
            cio_btn = x_page.locator('button:has-text("Check it out"):visible, div[role="button"]:has-text("Check it out"):visible').first
            if cio_btn.is_visible(timeout=1000):
                log_fn("Onboarding: 'Welcome to Communities' modal detected. Dismissing ('Check it out')...")
                try: human_click(x_page, cio_btn)
                except Exception: cio_btn.click(force=True)
                time.sleep(2.0)
                action_taken = True
                consecutive_idle = 0
                continue

        # 1. Interests Step ("Pick your interests" / "Select 3 topics to continue")
        if "pick your interests" in dialog_text or "select 3 topics" in dialog_text or "what do you want to see" in dialog_text:
            log_fn("Onboarding: 'Pick your interests' screen detected.")
            # Prefer clicking 'Skip' if present
            skip_interests = x_page.locator('button:has-text("Skip"):visible, div[role="button"]:has-text("Skip"):visible').first
            if skip_interests.is_visible(timeout=1000):
                log_fn("Onboarding: 'Pick your interests' has Skip button. Skipping...")
                try: human_click(x_page, skip_interests)
                except Exception: skip_interests.click(force=True)
                time.sleep(2.5)
                action_taken = True
                consecutive_idle = 0
                continue

            log_fn("Onboarding: Selecting 3 topic buttons...")
            topic_buttons = x_page.locator('button:has(svg[data-icon^="icon-topic-"]):visible').all()
            if not topic_buttons:
                topic_buttons = x_page.locator('button:has(p.jf-element):visible').all()
                
            selected = 0
            for btn in topic_buttons:
                try:
                    btn_text = btn.inner_text().strip().lower()
                    if any(w in btn_text for w in ["continue", "next", "back", "cancel", "skip"]):
                        continue
                    if btn.is_visible():
                        human_click(x_page, btn)
                        selected += 1
                        time.sleep(0.4)
                        if selected >= 3:
                            break
                except Exception: continue
                
            log_fn(f"Onboarding: Picked {selected} interests.")
            time.sleep(1.0)
            
            cont_btn = x_page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible, button[type="submit"]:has-text("Continue"):visible').last
            if cont_btn.is_visible(timeout=3000):
                log_fn("Onboarding: Submitting selected interests (Continue)...")
                human_click(x_page, cont_btn)
                time.sleep(3.0)
            action_taken = True
            consecutive_idle = 0
            continue

        # 2. Suggested for you ("Suggested for you" / "Follow accounts to personalize your timeline")
        if "suggested for you" in dialog_text or "follow accounts to personalize" in dialog_text:
            log_fn("Onboarding: 'Suggested for you' screen detected. Clicking Continue...")
            cont_btn = x_page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible').last
            try:
                if cont_btn.is_visible() and not cont_btn.is_enabled():
                    log_fn("Onboarding: Continue button disabled. Following 1 suggested account first...")
                    f_btn = x_page.locator('button:has-text("Follow"):visible').first
                    if f_btn.is_visible():
                        human_click(x_page, f_btn)
                        time.sleep(1.0)
            except Exception: pass
            
            if cont_btn.is_visible(timeout=3000):
                human_click(x_page, cont_btn)
                time.sleep(3.0)
            action_taken = True
            consecutive_idle = 0
            continue

        # 3. People you may know ("People you may know" / "Follow people you know on X")
        if "people you may know" in dialog_text or "follow people you know" in dialog_text:
            log_fn("Onboarding: 'People you may know' screen detected. Clicking Continue...")
            cont_btn = x_page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible').last
            if cont_btn.is_visible(timeout=3000):
                human_click(x_page, cont_btn)
                time.sleep(3.0)
            action_taken = True
            consecutive_idle = 0
            continue

        # 4. Profile Bio / "Describe yourself" screen
        bio_textarea = x_page.locator('textarea:visible, textarea[name="description"]:visible, textarea[placeholder*="bio" i]:visible, textarea[data-testid="ocfEnterTextTextInput"]:visible').first
        if "describe yourself" in dialog_text or "your bio" in dialog_text or (bio_textarea.is_visible(timeout=1000) and "/settings" not in x_page.url):
            log_fn("Onboarding: Bio / 'Describe yourself' screen detected.")
            if bio and bio.strip() and bio_textarea.is_visible(timeout=2000):
                log_fn(f"Onboarding: Typing profile bio ({len(bio)} chars): '{bio}'...")
                try: human_click(x_page, bio_textarea)
                except Exception: bio_textarea.click(force=True)
                time.sleep(0.3)
                try:
                    bio_textarea.press_sequentially(bio, delay=15)
                except Exception:
                    bio_textarea.fill(bio)
                time.sleep(0.5)
            # Look for Next / Save / Continue or Skip for now
            next_btn = x_page.locator('button[data-testid="Profile_Save_Button"]:visible, button:has-text("Next"):visible, button:has-text("Continue"):visible, button:has-text("Save"):visible').last
            skip_btn = x_page.locator('button:has-text("Skip for now"):visible, button:has-text("Maybe later"):visible').first
            if bio and bio.strip() and next_btn.is_visible(timeout=2000):
                log_fn("Onboarding: Submitting Bio (Next/Continue)...")
                human_click(x_page, next_btn)
                time.sleep(3.0)
            elif skip_btn.is_visible(timeout=2000):
                log_fn("Onboarding: Skipping Bio (Skip for now)...")
                human_click(x_page, skip_btn)
                time.sleep(2.0)
            elif next_btn.is_visible(timeout=2000):
                human_click(x_page, next_btn)
                time.sleep(2.0)
            action_taken = True
            consecutive_idle = 0
            continue

        # 5. Profile Picture / Avatar prompt ("Pick a profile picture")
        if "pick a profile picture" in dialog_text or "upload a profile picture" in dialog_text:
            log_fn("Onboarding: 'Pick a profile picture' prompt detected.")
            skip_pic = x_page.locator('button:has-text("Skip for now"):visible, button:has-text("Maybe later"):visible, button:has-text("Next"):visible, button:has-text("Continue"):visible').first
            if skip_pic.is_visible(timeout=2000):
                log_fn("Onboarding: Skipping profile picture upload...")
                human_click(x_page, skip_pic)
                time.sleep(2.5)
                action_taken = True
                consecutive_idle = 0
                continue

        # 4. Standard dismissal prompts (Skip for now, Maybe later, Not now)
        skip_btn = x_page.locator('button:has-text("Skip for now"):visible, button:has-text("Maybe later"):visible, button:has-text("Not now"):visible, button:has-text("Skip"):visible').first
        if skip_btn.is_visible(timeout=1000):
            log_fn("Onboarding: Dismissing optional prompt (Skip / Maybe later)...")
            human_click(x_page, skip_btn)
            time.sleep(2.0)
            action_taken = True
            consecutive_idle = 0
            continue

        # 5. Generic dialog continuation (Continue / Next)
        dialog_cont = x_page.locator('div[role="dialog"] button:has-text("Continue"):visible, div[role="dialog"] button:has-text("Next"):visible, button[type="submit"]:has-text("Continue"):visible').last
        if dialog_cont.is_visible(timeout=1000):
            log_fn("Onboarding: Clicking generic dialog progression button (Continue)...")
            human_click(x_page, dialog_cont)
            time.sleep(2.5)
            action_taken = True
            consecutive_idle = 0
            continue

        if not action_taken:
            consecutive_idle += 1
            if consecutive_idle >= 2:
                log_fn("Onboarding: No further onboarding modals detected.")
                break

def handle_full_post_sms_flow(x_page, x_context, creds, log_fn=print, max_wait_sec=180):
    """
    Unified post-SMS registration pipeline.
    Patiently handles:
    1. Birthday ('When's your birthday?')
    2. Unified Credentials Setup ('Set up your account': Name, Username, Password)
    3. Consent / Privacy ('Keeping your trust by protecting your privacy')
    4. Review Settings ('Review your current settings')
    5. Onboarding stages (Interests, Suggested, Bio, Avatar, Notifications)
    Monitors cookies continuously for auth_token.
    NEVER navigates away to /home unless credentials and auth_token are confirmed!
    """
    start_t = time.time()
    log_fn("Beginning unified post-SMS registration pipeline...")
    
    consecutive_idle = 0
    dob_done = False
    creds_done = False
    
    while time.time() - start_t < max_wait_sec:
        # Check if auth_token is captured in cookies or URL reached /home
        cookies = x_context.cookies(["https://x.com", "https://twitter.com"]) if hasattr(x_context, "cookies") else []
        auth_cookie = next((c for c in cookies if c.get("name") == "auth_token" and c.get("value")), None)
        if not auth_cookie:
            try:
                cdp = x_context.new_cdp_session(x_page)
                cdp_cookies = cdp.send("Network.getCookies", {"urls": ["https://x.com", "https://twitter.com"]})
                for c in cdp_cookies.get("cookies", []):
                    if c.get("name") == "auth_token" and c.get("value"):
                        auth_cookie = c
                        break
            except Exception: pass

        if "/home" in x_page.url:
            log_fn("Registration fully complete! Browser arrived on home feed.")
            return True

        if auth_cookie:
            log_fn(f"Verified auth_token detected in browser context: {auth_cookie['value'][:12]}...")
            if "/home" in x_page.url or creds_done:
                log_fn("Registration fully complete! Session verified.")
                return True
        
        # 0. Check transient error modals
        dismiss_error_retry_modals_if_present(x_page, log_fn=log_fn)

        dialog_text = ""
        try:
            d = x_page.locator('div[role="dialog"]').first
            dialog_text = d.inner_text().lower() if d.is_visible() else x_page.inner_text("body").lower()
        except Exception: pass

        # Welcome to Communities modal
        if "welcome to communities" in dialog_text or "check it out" in dialog_text:
            cio_btn = x_page.locator('button:has-text("Check it out"):visible, div[role="button"]:has-text("Check it out"):visible').first
            if cio_btn.is_visible(timeout=1000):
                log_fn("Post-SMS Flow: 'Welcome to Communities' modal detected. Dismissing ('Check it out')...")
                try: human_click(x_page, cio_btn)
                except Exception: cio_btn.click(force=True)
                time.sleep(2.0)
                consecutive_idle = 0
                continue

        # 1. Birthday step
        bday_el = x_page.locator('#jf-date-date_of_birth-month, select[name="date_of_birth-month"]').first
        if not dob_done and ("birthday" in dialog_text or bday_el.is_visible(timeout=1000)):
            if fill_birthday_if_present(x_page, creds, log_fn, timeout=2000):
                dob_done = True
                consecutive_idle = 0
                time.sleep(3.0)
                continue

        # 2. Unified Setup (Name, Username, Password) or Individual Setup Screens
        name_inp = x_page.locator('input[name="name"], input[autocomplete="name"]').first
        pwd_inp = x_page.locator('input[name="password"], input[type="password"]:visible').first
        user_inp = x_page.locator('input[name="username"], input[placeholder*="username" i]').first

        is_setup_active = (
            "set up your account" in dialog_text or 
            "choose a name, username" in dialog_text or 
            "choose a name" in dialog_text or
            (name_inp.is_visible() and pwd_inp.is_visible()) or
            (user_inp.is_visible() and pwd_inp.is_visible())
        )
        if is_setup_active:
            if fill_unified_setup_if_present(x_page, creds, log_fn, max_wait_sec=20):
                creds_done = True
                consecutive_idle = 0
                time.sleep(3.0)
                continue
        elif not creds_done:
            if fill_individual_setup_screens_if_present(x_page, creds, log_fn=log_fn):
                consecutive_idle = 0
                time.sleep(3.0)
                continue

        # 3 & 4. Privacy Consent & Review Settings ("Keeping your trust" / "Review your current settings")
        if handle_privacy_and_settings_review(x_page, log_fn=log_fn):
            consecutive_idle = 0
            continue

        # 5. Interests / Topics ("Pick your interests" / "Select 3 topics to continue")
        if "pick your interests" in dialog_text or "select 3 topics" in dialog_text or "what do you want to see" in dialog_text:
            log_fn("Onboarding: 'Pick your interests' screen detected.")
            # Prefer clicking 'Skip' if present
            skip_interests = x_page.locator('button:has-text("Skip"):visible, div[role="button"]:has-text("Skip"):visible').first
            if skip_interests.is_visible(timeout=1000):
                log_fn("Onboarding: 'Pick your interests' has Skip button. Skipping...")
                try: human_click(x_page, skip_interests)
                except Exception: skip_interests.click(force=True)
                time.sleep(2.5)
                consecutive_idle = 0
                continue

            log_fn("Onboarding: Selecting 3 topic buttons...")
            topic_buttons = x_page.locator('button:has(svg[data-icon^="icon-topic-"]):visible, button:has(p.jf-element):visible').all()
            selected = 0
            for btn in topic_buttons:
                try:
                    btn_text = btn.inner_text().strip().lower()
                    if any(w in btn_text for w in ["continue", "next", "back", "cancel", "skip"]):
                        continue
                    if btn.is_visible():
                        human_click(x_page, btn)
                        selected += 1
                        time.sleep(0.3)
                        if selected >= 3:
                            break
                except Exception: continue
            time.sleep(1.0)
            cont_btn = x_page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible').last
            if cont_btn.is_visible(timeout=3000):
                human_click(x_page, cont_btn)
                time.sleep(3.0)
            consecutive_idle = 0
            continue

        # 6. Suggested accounts ("Suggested for you" / "Follow 1 or more accounts")
        if "suggested for you" in dialog_text or "follow 1 or more accounts" in dialog_text:
            log_fn("Onboarding: 'Suggested for you' detected. Selecting follow and clicking Continue...")
            f_btn = x_page.locator('button[data-testid*="-follow"]:visible, button:has-text("Follow"):visible').first
            if f_btn.is_visible(timeout=1500):
                try: human_click(x_page, f_btn); time.sleep(0.5)
                except Exception: pass
            cont_btn = x_page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible').last
            if cont_btn.is_visible(timeout=3000):
                try: human_click(x_page, cont_btn)
                except Exception: pass
                time.sleep(3.0)
            consecutive_idle = 0
            continue

        # 7. Standard dismissals (Skip for now, Maybe later, Not now)
        skip_btn = x_page.locator('button:has-text("Skip for now"):visible, button:has-text("Maybe later"):visible, button:has-text("Not now"):visible').first
        if skip_btn.is_visible(timeout=1000):
            log_fn("Onboarding: Dismissing optional prompt (Skip / Maybe later)...")
            try: human_click(x_page, skip_btn)
            except Exception: pass
            time.sleep(2.0)
            consecutive_idle = 0
            continue

        # 8. Generic continue / next (only if creds already submitted)
        if creds_done:
            dialog_cont = x_page.locator('div[role="dialog"] button:has-text("Continue"):visible, div[role="dialog"] button:has-text("Next"):visible, button[type="submit"]:has-text("Continue"):visible').last
            if dialog_cont.is_visible(timeout=1000):
                log_fn("Onboarding: Advancing progression button (Continue)...")
                try: human_click(x_page, dialog_cont)
                except Exception: pass
                time.sleep(3.0)
                consecutive_idle = 0
                continue

        # Check idle
        consecutive_idle += 1
        if consecutive_idle >= 2:
            if "/home" in x_page.url or auth_cookie:
                log_fn("Onboarding settled and account active on X. Advancing to profile customization...")
                break
            elif creds_done:
                log_fn("Credentials completed; advancing to /home...")
                try:
                    x_page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
                    time.sleep(2.5)
                except Exception: pass
                break
            else:
                log_fn("Waiting for next registration stage...")
                consecutive_idle = 0
                
        time.sleep(2.0)
        
    return bool(auth_cookie) or ("/home" in x_page.url)

def create_twitter_account(custom_id=None, custom_name=None, custom_username=None, custom_password=None, bio=None, website=None, log_fn=print, browser_engine="chrome"):
    """
    Executes the full automated account creation pipeline:
    1. Obtains a US phone number via HeroSMS.
    2. Opens X Join Flow on virtual display :99.
    3. Fills phone number and random adult birthday.
    4. Enforces minimum 20s wait before capturing SMS code from HeroSMS.
    5. Fills SMS code, Name, Username, and Password.
    6. Saves session into user_data and registers account in profiles.json.
    """
    account_id = custom_id or get_next_account_id()
    user_data_dir = os.path.abspath(f"./user_data/{account_id}")
    if os.path.exists(user_data_dir) and not os.path.exists(os.path.join(user_data_dir, "state.json")):
        shutil.rmtree(user_data_dir, ignore_errors=True)
    os.makedirs(user_data_dir, exist_ok=True)
    
    creds = generate_random_profile()
    if custom_name: creds["name"] = custom_name
    if custom_username: creds["username"] = custom_username
    if custom_password: creds["password"] = custom_password
    if bio: creds["bio"] = bio
    if website: creds["website"] = website
    
    log_fn(f"Starting account creation for [{account_id}]...")
    log_fn(f"Profile blueprint: Name='{creds['name']}', Handle='@{creds['username']}'")
    
    # Initialize HeroSMS client (mandatory 20s minimum wait, 240s / 4-minute max wait with auto-resend)
    hero = HeroSMSClient(min_wait_secs=20, max_wait_secs=240)
    
    with sync_playwright() as p:
        hero_context = None
        x_context = None
        
        try:
            # 1. Setup HeroSMS Browser Context
            cleanup_profile_locks("./user_data/herosms_session")
            hero_context = p.chromium.launch_persistent_context(
                user_data_dir="./user_data/herosms_session",
                headless=True
            )
            hero_page = hero_context.pages[0] if hero_context.pages else hero_context.new_page()
            
            # 2. Launch Registration Context on Display :0 (Hardware GPU) or :99
            if sys.platform != "win32":
                if os.path.exists("/tmp/.X11-unix/X0"):
                    os.environ["DISPLAY"] = ":0"
                    if os.path.exists("/run/user/1000/gdm/Xauthority"):
                        os.environ["XAUTHORITY"] = "/run/user/1000/gdm/Xauthority"
                    elif os.path.exists(os.path.expanduser("~/.Xauthority")):
                        os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
                elif "DISPLAY" not in os.environ:
                    os.environ["DISPLAY"] = ":99"

            import browser_manager
            x_context, active_engine = browser_manager.launch_persistent_context_with_fallback(
                playwright_instance=p,
                engine=browser_engine,
                user_data_dir=user_data_dir,
                headless=False,
                permissions=["camera", "microphone"],
                log_fn=log_fn
            )
            disp_target = os.environ.get('DISPLAY', 'Windows Native Desktop' if sys.platform == 'win32' else ':0')
            log_fn(f"Registration Engine: {active_engine.upper()} via Patchright on display {disp_target}")

            x_page = x_context.pages[0] if x_context.pages else x_context.new_page()
            
            # 3. Open X Phone Signup Dialog
            log_fn("Opening X phone signup dialog...")
            dialog, phone_input = prepare_phone_input_dialog(x_page, log_fn=log_fn)
                
            # 4. Acquire Number & Submit with Auto-Retry
            phone_number = None
            sms_code = None
            for p_try in range(4):
                log_fn(f"HeroSMS: Requesting fresh US number (attempt {p_try+1}/4)...")
                try:
                    phone_number = hero.request_phone_number(hero_page, log_fn=log_fn)
                except Exception as ne:
                    log_fn(f"HeroSMS: Allocation note: {ne}")
                    time.sleep(3.0)
                    continue
                    
                if not phone_number:
                    continue
                    
                digits = re.sub(r'\D', '', phone_number)
                us_phone_10 = digits[-10:] if len(digits) >= 10 else digits
                log_fn(f"Entering target phone: +1 {us_phone_10}...")
                
                # Ensure x_context and x_page are alive before operating
                try:
                    if x_page.is_closed():
                        x_page = x_context.pages[0] if (x_context and x_context.pages) else x_context.new_page()
                except Exception:
                    log_fn("[Notice] Browser session was closed. Re-launching context...")
                    cleanup_profile_locks(user_data_dir)
                    x_context, active_engine = browser_manager.launch_persistent_context_with_fallback(
                        playwright_instance=p,
                        engine=browser_engine,
                        user_data_dir=user_data_dir,
                        headless=False,
                        permissions=["camera", "microphone"],
                        log_fn=log_fn
                    )
                    x_page = x_context.pages[0] if x_context.pages else x_context.new_page()

                # Ensure phone input is active and genuine
                dialog, phone_input = prepare_phone_input_dialog(x_page, log_fn=log_fn)
                if not phone_input.is_visible(timeout=3000):
                    log_fn("[Warning] Phone input not visible; attempting to restore signup dialog...")
                    x_page.goto("https://x.com/i/flow/signup", wait_until="domcontentloaded", timeout=45000)
                    time.sleep(3.0)
                    dialog, phone_input = prepare_phone_input_dialog(x_page, log_fn=log_fn)
                
                if not phone_input.is_visible(timeout=3000):
                    x_page.screenshot(path=f"missing_phone_{account_id}.png")
                    log_fn("[Error] Phone input is not visible on page. Canceling rental and trying replacement...")
                    hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=log_fn)
                    phone_number = None
                    time.sleep(2.0)
                    continue

                human_click(x_page, phone_input)
                time.sleep(0.2)
                phone_input.press("Control+A")
                phone_input.press("Backspace")
                time.sleep(0.3)
                human_type(phone_input, us_phone_10)
                time.sleep(random.uniform(0.8, 1.5))
                
                # Submit phone via active button on dialog
                cont_btn = x_page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible, button[type="submit"]:visible').last
                if cont_btn.is_visible(timeout=3000):
                    human_click(x_page, cont_btn)
                time.sleep(4.0)
                
                # Check for rejection or risk flags
                err_el = x_page.locator('text="Sorry, something is not right", text="Please try using a different method", text="We couldn\'t send you a text message", text="Please enter a valid phone number", text="Unsupported phone number", text="This phone number has already been used", text="Phone number already in use"').first
                if err_el.is_visible(timeout=2000):
                    log_fn(f"[Notice] Phone +1 {us_phone_10} flagged by Twitter. Canceling rental & requesting replacement...")
                    hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=log_fn)
                    phone_number = None
                    time.sleep(2.0)
                    continue
                else:
                    log_fn(f"Phone +1 {us_phone_10} accepted by registration system!")
                    
                # Dismiss confirmation modal (e.g. "We'll text your verification code...")
                # Note: must match exact text "OK" so it never mistakenly clicks "Accept all cookies"!
                ok_modal = x_page.locator('button[data-testid="confirmationSheetConfirm"]:visible, button:text-is("OK"):visible, button:text-is("Ok"):visible, div[role="button"]:text-is("OK"):visible').first
                if ok_modal.is_visible(timeout=3000):
                    log_fn("Confirming phone verification dispatch modal (OK)...")
                    human_click(x_page, ok_modal)
                    time.sleep(2.0)
                
                # Birthday Step (if prompted before or around verification)
                fill_birthday_if_present(x_page, creds, log_fn)
                    
                # Check for Security Verification (Face Liveness or Captcha)
                dialog_text = dialog.inner_text() if dialog.is_visible() else ""
                face_btn = x_page.locator('button:has-text("Confirm with Face"), div[role="button"]:has-text("Confirm with Face")').first
                if "Confirm with Face" in dialog_text or "Confirm you're a human" in dialog_text or face_btn.is_visible():
                    log_fn("[Security Notice] Twitter Prelude Biometric / Face verification challenge detected ('Confirm you\\'re a human').")
                    x_page.screenshot(path=f"captcha_{account_id}.png")
                    x_page.screenshot(path="captcha_alert.png")
                    try:
                        with open("bot_status.json", "w") as sf:
                            json.dump({"profile": account_id, "username": creds["username"], "status": "Biometric / Face Challenge"}, sf)
                    except Exception: pass
                    
                    if face_btn.is_visible(timeout=2000):
                        log_fn("Clicking 'Confirm with Face'...")
                        human_click(x_page, face_btn)
                        time.sleep(2.0)
                        log_fn(">>> CAMERA VERIFICATION ACTIVE: Please look directly into webcam to complete facial verification <<<")
                        for f_wait in range(30):
                            time.sleep(2)
                            try:
                                if x_page.is_closed():
                                    break
                                d_txt = dialog.inner_text() if dialog.is_visible() else ""
                                if "confirm with face" not in d_txt.lower() and "confirm you're a human" not in d_txt.lower():
                                    log_fn("Facial verification cleared successfully! Proceeding...")
                                    break
                            except Exception:
                                break

                try:
                    captcha_frame = x_page.locator('iframe[src*="arkoselabs"], iframe[title*="challenge" i], div:has-text("Authenticate your account")').first
                    if not x_page.is_closed() and captcha_frame.is_visible(timeout=3000):
                        log_fn("[Security Check] Arkose Labs Captcha detected. Capturing screenshot...")
                        x_page.screenshot(path=f"captcha_{account_id}.png")
                        x_page.screenshot(path="captcha_alert.png")
                        try:
                            with open("bot_status.json", "w") as sf:
                                json.dump({"profile": account_id, "username": creds["username"], "status": "Captcha Challenge"}, sf)
                        except Exception: pass
                        log_fn("Pausing up to 120s for puzzle resolution...")
                        for _ in range(24):
                            time.sleep(5)
                            if x_page.is_closed() or not captcha_frame.is_visible():
                                log_fn("Captcha cleared, proceeding!")
                                if os.path.exists("captcha_alert.png"):
                                    try: os.remove("captcha_alert.png")
                                    except Exception: pass
                                break
                except Exception: pass
                            
                # SMS Verification Code Retrieval
                log_fn(f"Waiting for SMS verification code dispatch to {phone_number}...")
                try:
                    sms_code = hero.wait_for_verification_code(hero_page, phone_number, log_fn=log_fn)
                    if sms_code:
                        break
                except Exception as ce:
                    log_fn(f"[Notice] Code delivery timeout on +1 {us_phone_10}: {ce}")
                    hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=log_fn)
                    phone_number = None
                    time.sleep(2.0)
                    try:
                        back_btn = x_page.locator('button[aria-label="Back"]:visible, div[aria-label="Back"]:visible, button[data-testid="app-bar-back"]:visible, div[data-testid="app-bar-back"]:visible').first
                        if back_btn.is_visible(timeout=2000):
                            log_fn("Navigating back to phone number entry screen for replacement attempt...")
                            human_click(x_page, back_btn)
                            time.sleep(2.0)
                    except Exception: pass
                    continue
                    
            if not sms_code:
                raise Exception("Failed to acquire SMS verification code after multiple attempts.")
            
            code_input = x_page.locator('input.jf-code-input-field, input[name="code"], input[autocomplete="one-time-code"], input[placeholder*="code" i], input[data-testid="ocfEnterTextTextInput"]').first
            code_input.wait_for(state="visible", timeout=20000)
            log_fn(f"Injecting SMS verification code: {sms_code}...")
            human_click(x_page, code_input)
            human_type(code_input, sms_code)
            time.sleep(1.0)
            try: code_input.press("Enter")
            except: pass
            
            code_submit = x_page.locator('button:has(p:has-text("Continue")), button[type="submit"]:has-text("Continue"), button:has-text("Continue"), button:has-text("Next"), button:has-text("Verify")').last
            if code_submit.is_visible(timeout=3000):
                human_click(x_page, code_submit)
            time.sleep(4.0)
            
            # Execute unified post-SMS registration pipeline
            handle_full_post_sms_flow(x_page, x_context, creds, log_fn=log_fn)
            time.sleep(2.0)

            # 11. Extract and Verify Authentication Tokens (with polling)
            auth_token_val = None
            ct0_val = None
            raw_cookies = []

            for poll_attempt in range(12):
                raw_cookies = x_context.cookies()
                for c in raw_cookies:
                    c_name = c.get("name")
                    c_val = c.get("value")
                    c_domain = c.get("domain", "")
                    if c_name == "auth_token" and c_val:
                        if not auth_token_val or ".x.com" in c_domain:
                            auth_token_val = c_val
                    elif c_name == "ct0" and c_val:
                        if not ct0_val or ".x.com" in c_domain:
                            ct0_val = c_val
                
                if auth_token_val:
                    break

                # Fallback to CDP extraction if context cookies not yet populated
                try:
                    cdp = x_context.new_cdp_session(x_page)
                    all_cookies = cdp.send("Network.getCookies", {"urls": ["https://x.com", "https://twitter.com"]})
                    for c in all_cookies.get("cookies", []):
                        if c.get("name") == "auth_token" and c.get("value"):
                            auth_token_val = c.get("value")
                        elif c.get("name") == "ct0" and c.get("value"):
                            ct0_val = c.get("value")
                except Exception: pass

                if auth_token_val:
                    break
                time.sleep(1.5)

            if not auth_token_val:
                try:
                    from extract_cookies import extract_auth_token_from_cookies
                    auth_token_val = extract_auth_token_from_cookies(user_data_dir)
                except Exception: pass

            if not auth_token_val:
                raise Exception("Account creation failed: Twitter did not issue a verified auth_token. Aborting to avoid registering broken profile.")

            log_fn(f"Session established! auth_token captured: True (ct0: {bool(ct0_val)})")

            # 12. IMMEDIATELY Persist Authenticated Session State and Register in profiles.json
            try:
                os.makedirs(user_data_dir, exist_ok=True)
                state_file = os.path.join(user_data_dir, "state.json")
                with open(state_file, "w") as sf:
                    json.dump({"cookies": raw_cookies, "origins": []}, sf, indent=2)
                log_fn(f"Saved authenticated browser state into {state_file}")
            except Exception as se:
                log_fn(f"State persistence note: {se}")

            # Directly inject session cookies into Chromium storage on disk
            try:
                from import_account import inject_auth_token_cookie
                inject_auth_token_cookie(user_data_dir, auth_token_val)
                log_fn(f"Injected verified auth_token directly into Chromium persistent storage for [{account_id}].")
            except Exception as ie:
                log_fn(f"Chromium cookie storage note: {ie}")

            new_profile = {
                "id": account_id,
                "user_data_dir": user_data_dir,
                "username": creds["username"],
                "password": creds["password"],
                "display_name": creds.get("name", ""),
                "bio": creds.get("bio", ""),
                "website": creds.get("website", ""),
                "phone": phone_number,
                "auth_token": auth_token_val,
                "ct0": ct0_val or "",
                "auth_token_added": True,
                "status": "Active"
            }

            profiles = []
            if os.path.exists("profiles.json"):
                try:
                    with open("profiles.json", "r") as f:
                        profiles = json.load(f)
                except Exception: pass

            existing_idx = next((i for i, p in enumerate(profiles) if p["id"] == account_id), None)
            if existing_idx is not None:
                profiles[existing_idx] = new_profile
            else:
                profiles.append(new_profile)

            with open("profiles.json", "w") as f:
                json.dump(profiles, f, indent=4)
            log_fn(f"SUCCESS: Account [{account_id}] (@{creds['username']}) successfully registered in profiles.json!")

            try:
                from activity_logger import log_activity
                log_activity(
                    action=f"Created & Registered profile (@{creds['username']})",
                    account=account_id,
                    status="Success",
                    details=f"Phone: {phone_number}"
                )
            except Exception: pass

            # Auto-sync into scheduled queue jobs immediately
            try:
                import queue_syncer
                synced_cnt = queue_syncer.sync_accounts_to_queued_jobs()
                log_fn(f"Auto-synced new profile [{account_id}] into scheduled queue jobs (Total synced accounts: {synced_cnt}).")
            except Exception as q_err:
                log_fn(f"Queue auto-sync note: {q_err}")

            # 13. Optional Post-Registration Tasks (Customizations & Community Joins in isolated try/except)
            if creds.get("bio") or creds.get("website") or creds.get("name"):
                try:
                    import account_login
                    log_fn("Applying profile customizations (name, bio, website) on X...")
                    account_login.update_twitter_profile(
                        x_page,
                        display_name=creds.get("name"),
                        bio=creds.get("bio"),
                        website=creds.get("website"),
                        log_fn=log_fn
                    )
                except Exception as up_err:
                    log_fn(f"Profile customization note: {up_err}")
                time.sleep(2.5)

            joined_comms = {}
            try:
                import account_login
                log_fn("Joining target booster communities (Free Trade & Nude Trades) in browser...")
                joined_comms = account_login.join_target_communities_in_browser(x_page, account_id, log_fn=log_fn)
            except Exception as jc_err:
                log_fn(f"Community joining note: {jc_err}")

            # Pre-populate default community cache
            cache_file = "communities_cache.json"
            cache_data = {}
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as cf:
                        cache_data = json.load(cf)
                except Exception: pass
            default_seeded = {
                "Free Trade (18+)": {"url": "/i/communities/1944294809918685272", "members": 402000},
                "Nude Trades (18+)": {"url": "/i/communities/1806977501140570599", "members": 343600}
            }
            cache_data[account_id] = joined_comms if joined_comms else default_seeded
            with open(cache_file, "w") as cf:
                json.dump(cache_data, cf, indent=4)
                
            # 14. Auto-sync new profile into any created scheduled jobs
            try:
                import queue_syncer
                synced_cnt = queue_syncer.sync_accounts_to_queued_jobs()
                log_fn(f"Auto-synced new profile [{account_id}] into scheduled queue jobs (Total synced accounts: {synced_cnt}).")
            except Exception as sync_e:
                log_fn(f"Note: Auto-syncing to queue encountered: {sync_e}")

            log_fn(f"SUCCESS: [{account_id}] created and integrated into system!")
            return new_profile
            
        finally:
            if x_context:
                try:
                    for page in list(x_context.pages):
                        try: page.close()
                        except Exception: pass
                except Exception: pass
                try: x_context.close()
                except Exception: pass
            if hero_context:
                try:
                    for page in list(hero_context.pages):
                        try: page.close()
                        except Exception: pass
                except Exception: pass
                try: hero_context.close()
                except Exception: pass
            try:
                from account_login import terminate_chrome_processes
                terminate_chrome_processes(user_data_dir=user_data_dir, log_fn=log_fn)
                terminate_chrome_processes(user_data_dir="./user_data/herosms_session", log_fn=log_fn)
            except Exception:
                cleanup_profile_locks(user_data_dir)

if __name__ == "__main__":
    result = create_twitter_account()
    print("Execution completed with profile:", result)
