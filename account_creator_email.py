import os
import sys
import time
import re
import json
import math
import random
import string
import threading
import queue
import shutil

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

import email_alias_manager
from herosms_client import HeroSMSClient
import subprocess
import urllib.request

try:
    import female_profile_vault
except ImportError:
    female_profile_vault = None

from account_login import (
    STRIP_AUTOMATION_ARGS,
    cleanup_profile_locks,
    update_twitter_profile,
    terminate_chrome_processes,
    join_target_communities_in_browser
)
from account_creator import (
    human_move,
    human_click,
    human_type,
    safe_type_input,
    generate_random_profile,
    get_next_account_id,
    fill_birthday_if_present,
    prepare_phone_input_dialog,
    handle_post_signup_onboarding,
    fill_unified_setup_if_present,
    fill_individual_setup_screens_if_present,
    dismiss_error_retry_modals_if_present,
    handle_privacy_and_settings_review,
    handle_full_post_sms_flow
)

def is_cdp_ready(port=9222):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1) as res:
            return res.status == 200
    except Exception:
        return False

def get_cdp_user_data_dir():
    if sys.platform == "win32":
        return os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'google-chrome-cdp')
    return os.path.expanduser('~/.config/google-chrome-cdp')

def get_chrome_binary():
    import browser_manager
    bin_path = browser_manager.find_browser_binary("chrome")
    if bin_path:
        return bin_path
    if sys.platform == "win32":
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local"), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "chrome.exe"
    return "/opt/google/chrome/chrome"

def ensure_cdp_chrome_running(port=9222, log_fn=print):
    if is_cdp_ready(port):
        log_fn(f"Native Google Chrome CDP session verified active on port {port}.")
        return True
        
    cdp_dir = get_cdp_user_data_dir()
    os.makedirs(cdp_dir, exist_ok=True)
    cleanup_profile_locks(cdp_dir)
        
    env = dict(os.environ)
    if sys.platform != "win32":
        if os.path.exists('/tmp/.X11-unix/X0'):
            env['DISPLAY'] = ':0'
            if os.path.exists('/run/user/1000/gdm/Xauthority'):
                env['XAUTHORITY'] = '/run/user/1000/gdm/Xauthority'
            elif os.path.exists(os.path.expanduser('~/.Xauthority')):
                env['XAUTHORITY'] = os.path.expanduser('~/.Xauthority')
        elif 'DISPLAY' not in env:
            env['DISPLAY'] = ':99'
        
    disp_info = env.get('DISPLAY', 'Windows Native' if sys.platform == 'win32' else ':0')
    log_fn(f"Spawning native Google Chrome on port {port} (display {disp_info}) with Incognito & Media streaming...")
    
    chrome_bin = get_chrome_binary()
    popen_kwargs = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen([
        chrome_bin,
        f'--remote-debugging-port={port}',
        '--remote-allow-origins=*',
        f'--user-data-dir={cdp_dir}',
        '--incognito',
        '--use-fake-ui-for-media-stream',
        '--no-first-run',
        '--no-default-browser-check',
        '--start-maximized'
    ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
    
    for _ in range(12):
        time.sleep(1)
        if is_cdp_ready(port):
            log_fn(f"Native Chrome CDP bound and listening on port {port}!")
            return True
            
    log_fn(f"Warning: CDP port {port} did not respond within timeout.")
    return False

def stop_cdp_chrome(port=9222, log_fn=print):
    """Cleanly terminates the CDP Chrome instance so the next account starts in a pristine browser."""
    cdp_dir = get_cdp_user_data_dir()
    terminate_chrome_processes(user_data_dir=cdp_dir, port=port, log_fn=log_fn)

ACTIVE_EMAIL_SESSIONS = {}

class EmailRegistrationSession:
    """
    Manages an interactive or automated email-based X account registration.
    Uses native Google Chrome via Patchright on display :0 (Hardware GPU) with
    the exact stealth patches from Multi-Account Batch Onboarding.
    If Twitter requests a phone number, automatically rents a US line from HeroSMS.
    """
    def __init__(self, account_id=None, base_email="davidosili93@gmail.com", strategy="dot",
                 custom_name=None, custom_username=None, custom_password=None,
                 custom_bio=None, custom_website="https://getmysocial.com/uwuscrettt",
                 auto_vault=True, use_herosms_fallback=True, use_cdp=True, browser_engine="chrome", log_fn=print):
        self.account_id = account_id or get_next_account_id()
        self.base_email = base_email.strip()
        self.strategy = strategy
        self.browser_engine = browser_engine
        self.alias_email = email_alias_manager.get_or_create_alias_for_account(
            self.account_id, base_email=self.base_email, strategy=self.strategy
        )
        self.use_herosms_fallback = use_herosms_fallback
        self.use_cdp = use_cdp
        self.rented_phone = None
        
        self.creds = generate_random_profile()
        if custom_name: self.creds["name"] = custom_name
        elif auto_vault and female_profile_vault:
            self.creds["name"] = female_profile_vault.get_random_female_name()
            
        if custom_username: self.creds["username"] = custom_username
        if custom_password: self.creds["password"] = custom_password
        
        self.bio = custom_bio
        if not self.bio and auto_vault and female_profile_vault:
            self.bio = female_profile_vault.get_random_female_bio()
            
        self.website = custom_website
        
        self.log_fn = log_fn
        self.status = "idle" # idle, running, awaiting_code, completing, success, failed
        self.status_detail = ""
        self.code_queue = queue.Queue()
        self.cancel_requested = False
        self.last_screenshot = None
        self.result_profile = None
        self.error_message = None
        self.thread = None
        self.rented_phone = None
        self.browser = None
        self.context = None
        self.code_type = "email" # "email" or "sms"
        self.code_recipient = self.alias_email

    def log(self, msg):
        self.status_detail = msg
        self.log_fn(msg)

    def provide_verification_code(self, code):
        """Called by Streamlit UI or CLI when the user inputs the received code."""
        cleaned = code.strip()
        self.log(f"Verification code received: {cleaned}")
        self.code_queue.put(cleaned)

    def cancel(self):
        self.cancel_requested = True
        self.log("Cancellation requested by user.")
        self.code_queue.put(None)

    def start_background(self):
        """Starts registration in a background thread for non-blocking UI."""
        ACTIVE_EMAIL_SESSIONS[self.account_id] = self
        self.status = "running"
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        self.status = "running"
        user_data_dir = os.path.abspath(f"./user_data/{self.account_id}")
        if os.path.exists(user_data_dir) and not os.path.exists(os.path.join(user_data_dir, "state.json")):
            shutil.rmtree(user_data_dir, ignore_errors=True)
        os.makedirs(user_data_dir, exist_ok=True)
        
        self.log(f"Starting Email Alias Registration for [{self.account_id}]...")
        self.log(f"Target Alias: {self.alias_email} (Base: {self.base_email})")
        self.log(f"Profile Blueprint: Name='{self.creds['name']}', Handle='@{self.creds['username']}'")
        
        with sync_playwright() as p:
            x_context = None
            hero_context = None
            try:
                # 1. Setup Display & Hardware GPU Xauthority (identical to Multi-Account Batch setup)
                if sys.platform != "win32":
                    if os.path.exists("/tmp/.X11-unix/X0"):
                        os.environ["DISPLAY"] = ":0"
                        if os.path.exists("/run/user/1000/gdm/Xauthority"):
                            os.environ["XAUTHORITY"] = "/run/user/1000/gdm/Xauthority"
                        elif os.path.exists(os.path.expanduser("~/.Xauthority")):
                            os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
                    elif "DISPLAY" not in os.environ:
                        os.environ["DISPLAY"] = ":99"

                disp_target = os.environ.get('DISPLAY', 'Windows Native Desktop' if sys.platform == 'win32' else ':0')
                if self.use_cdp and self.browser_engine == "chrome":
                    self.log(f"Browser Engine: Native Google Chrome via CDP (localhost:9222) on display {disp_target} (No automation flags)")
                    ensure_cdp_chrome_running(port=9222, log_fn=self.log)
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    self.browser = browser
                    x_context = browser.contexts[0]
                    self.context = x_context
                    # Mask navigator.gpu so Prelude anti-bot runs CPU fallback cleanly
                    x_context.add_init_script("""
                        try {
                            Object.defineProperty(Navigator.prototype, 'gpu', {
                                get: () => undefined,
                                configurable: true
                            });
                        } catch(e) {}
                    """)
                    x_page = x_context.pages[0] if x_context.pages else x_context.new_page()
                else:
                    import browser_manager
                    x_context, active_engine = browser_manager.launch_persistent_context_with_fallback(
                        playwright_instance=p,
                        engine=self.browser_engine,
                        user_data_dir=user_data_dir,
                        headless=False,
                        extra_args=["--test-type"],
                        log_fn=self.log
                    )
                    self.log(f"Browser Engine: {active_engine.upper()} via Patchright on display {disp_target} (Hardware GPU active)")

                    x_context.add_init_script("""
                        try {
                            Object.defineProperty(Navigator.prototype, 'gpu', {
                                get: () => undefined,
                                configurable: true
                            });
                        } catch(e) {}
                    """)
                    x_page = x_context.pages[0] if x_context.pages else x_context.new_page()
                
                # 2. Navigate to X signup flow
                self.log("Navigating to https://x.com/i/flow/signup...")
                x_page.goto("https://x.com/i/flow/signup", wait_until="domcontentloaded", timeout=45000)
                time.sleep(4.0)
                
                # Dismiss cookie banner upfront if present so it doesn't trigger reloads or intercept clicks later
                try:
                    cookie_btn = x_page.locator('button:text-is("Accept all cookies"):visible, button:text-is("Refuse non-essential cookies"):visible, div[role="button"]:text-is("Accept all cookies"):visible').first
                    if cookie_btn.is_visible(timeout=3000):
                        self.log("Dismissing cookie banner upfront...")
                        cookie_btn.click(force=True)
                        time.sleep(1.0)
                except Exception: pass
                
                # Check for dialog visibility
                dialog = x_page.locator('div[role="dialog"]').first
                try:
                    dialog.wait_for(state="visible", timeout=15000)
                except Exception:
                    self.log("Notice: Waiting for JoinFlow dialog...")
                    
                # 2. Wait for JoinFlow modal to settle and detect stage
                self.log("Detecting active JoinFlow stage...")
                stage = None
                for poll in range(25): # up to 25s
                    dialog = x_page.locator('div[role="dialog"]').first
                    if dialog.is_visible():
                        dialog_text = dialog.inner_text().lower()
                        phone_input = dialog.locator('#jf-phone-input-phone, input[name="phone"], input[type="tel"]').first
                        phone_btn = dialog.locator('button:has-text("Continue with phone")').first
                        face_btn = dialog.locator('button:has-text("Confirm with Face"), div[role="button"]:has-text("Confirm with Face")').first
                        code_inp = dialog.locator('input[name="code"], input[name="verfication_code"], input[autocomplete="one-time-code"]').first

                        if "confirm with face" in dialog_text or "confirm you're a human" in dialog_text or face_btn.is_visible():
                            stage = "face_challenge"
                            break
                        elif "enter your phone number" in dialog_text or phone_input.is_visible():
                            stage = "phone_entry"
                            break
                        elif phone_btn.is_visible():
                            stage = "landing_choice"
                            break
                        elif "verification code" in dialog_text or "we sent you a code" in dialog_text or code_inp.is_visible():
                            stage = "code_entry"
                            break
                    time.sleep(1.0)

                self.log(f"Active JoinFlow Stage detected: [{stage}]")
                screenshot_stage = f"email_signup_{self.account_id}_stage_{stage}.png"
                x_page.screenshot(path=screenshot_stage)
                self.last_screenshot = screenshot_stage

                # Handle Face Challenge if present
                face_btn = dialog.locator('button:has-text("Confirm with Face"), div[role="button"]:has-text("Confirm with Face")').first
                if stage == "face_challenge" or face_btn.is_visible(timeout=2000):
                    self.log("Facial Liveness Challenge detected ('Confirm you\\'re a human'). Clicking 'Confirm with Face'...")
                    human_click(x_page, face_btn)
                    time.sleep(2.0)
                    self.log(">>> CAMERA VERIFICATION ACTIVE: Please look directly into your webcam to complete facial verification <<<")
                    x_page.screenshot(path=f"face_challenge_{self.account_id}.png")
                    for f_wait in range(30):
                        time.sleep(2)
                        dialog_text = dialog.inner_text().lower() if dialog.is_visible() else ""
                        if "confirm with face" not in dialog_text and "confirm you're a human" not in dialog_text:
                            self.log("Facial verification cleared successfully! Proceeding...")
                            break
                    time.sleep(2.0)
                    if dialog.locator('#jf-phone-input-phone, input[name="phone"], input[type="tel"]').first.is_visible():
                        stage = "phone_entry"

                # If on landing choice screen, click Continue with phone to proceed to phone registration
                if stage == "landing_choice":
                    phone_btn = dialog.locator('button:has-text("Continue with phone")').first
                    if phone_btn.is_visible(timeout=3000):
                        self.log("Clicking 'Continue with phone' to open phone registration...")
                        human_click(x_page, phone_btn)
                        time.sleep(3.0)
                        stage = "phone_entry"

                # Check phone entry screen
                dialog = x_page.locator('div[role="dialog"]').first
                phone_input = dialog.locator('#jf-phone-input-phone, input[name="phone"], input[type="tel"]').first
                dialog_text = dialog.inner_text().lower() if dialog.is_visible() else ""

                if (stage == "phone_entry" or "enter your phone number" in dialog_text or phone_input.is_visible(timeout=3000)) and self.use_herosms_fallback:
                    self.log("Twitter JoinFlow requested phone verification. Engaging HeroSMS autonomous phone rental...")
                    hero = HeroSMSClient(min_wait_secs=15, max_wait_secs=180)
                    
                    cleanup_profile_locks("./user_data/herosms_session")
                    hero_context = p.chromium.launch_persistent_context(
                        user_data_dir="./user_data/herosms_session",
                        headless=True
                    )
                    hero_page = hero_context.pages[0] if hero_context.pages else hero_context.new_page()
                    
                    phone_allocated = None
                    sms_retrieved = None
                    for p_try in range(4):
                        self.log(f"HeroSMS: Requesting fresh US number (attempt {p_try+1}/4)...")
                        try:
                            phone_allocated = hero.request_phone_number(hero_page, log_fn=self.log)
                        except Exception as ne:
                            self.log(f"HeroSMS allocation note: {ne}")
                            time.sleep(3.0)
                            continue
                            
                        if not phone_allocated:
                            continue
                            
                        digits = re.sub(r'\D', '', phone_allocated)
                        us_phone_10 = digits[-10:] if len(digits) >= 10 else digits
                        self.log(f"Entering rented phone into Twitter: +1 {us_phone_10}...")
                        self.rented_phone = phone_allocated
                        
                        # Prepare phone input dialog reliably
                        dialog, phone_input = prepare_phone_input_dialog(x_page, log_fn=self.log)
                        
                        human_click(x_page, phone_input)
                        time.sleep(0.2)
                        phone_input.press("Control+A")
                        phone_input.press("Backspace")
                        time.sleep(0.3)
                        human_type(phone_input, us_phone_10)
                        time.sleep(random.uniform(0.8, 1.5))
                        
                        # Submit phone
                        p_cont = x_page.locator('button:has-text("Continue"):visible, button[type="submit"]:has-text("Continue"):visible').last
                        if p_cont.is_visible(timeout=3000):
                            human_click(x_page, p_cont)
                        time.sleep(3.0)
                        
                        # Check rejection
                        flag_el = x_page.locator('text="Sorry, something is not right", text="Please try using a different method", text="We couldn\'t send you a text message", text="Please enter a valid phone number", text="Unsupported phone number", text="This phone number has already been used", text="Phone number already in use"').first
                        if flag_el.is_visible(timeout=2000):
                            self.log(f"[Notice] Phone +1 {us_phone_10} flagged by Twitter. Requesting replacement...")
                            hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=self.log)
                            phone_allocated = None
                            time.sleep(2.0)
                            continue
                        else:
                            self.log(f"Phone +1 {us_phone_10} accepted by registration system!")
                            
                        # Dismiss confirmation modal (OK)
                        # Note: must match exact text "OK" so it never mistakenly clicks "Accept all cookies"!
                        ok_modal = x_page.locator('button[data-testid="confirmationSheetConfirm"]:visible, button:text-is("OK"):visible, button:text-is("Ok"):visible, div[role="button"]:text-is("OK"):visible').first
                        if ok_modal.is_visible(timeout=3000):
                            self.log("Dismissing Twitter phone verification dispatch modal (OK)...")
                            human_click(x_page, ok_modal)
                            time.sleep(2.0)
                            
                        # Handle Arkose Captcha if prompted
                        captcha_frame = x_page.locator('iframe[src*="arkoselabs"], iframe[title*="challenge" i], div:has-text("Authenticate your account")').first
                        if captcha_frame.is_visible(timeout=3000):
                            self.log("[Security Check] Arkose Labs Captcha challenge detected. Pausing for clearance...")
                            x_page.screenshot(path=f"captcha_{self.account_id}.png")
                            for _ in range(24):
                                time.sleep(5)
                                if not captcha_frame.is_visible():
                                    self.log("Captcha cleared, proceeding!")
                                    break
                                    
                        # Phone accepted and verification SMS dispatched by Twitter!
                        # Break out of phone retry loop immediately so we can receive and enter the code.
                        self.log(f"SMS code dispatched to +1 {us_phone_10}! Advancing to verification code entry...")
                        break

                # 4.5 Detection of Verification Code Screen (Email or SMS)
                code_input = x_page.locator('input.jf-code-input-field, input[autocomplete="one-time-code"], input[name="code"], input[name="verfication_code"], input[name="verification_code"], input[data-testid="ocfEnterTextTextInput"], input[placeholder*="code" i], input[aria-label*="verification code" i], input[inputmode="numeric"], input[type="tel"], input[maxlength="6"], input[maxlength="8"]').first
                
                is_code_screen = False
                for code_poll in range(35):
                    try:
                        if code_input.is_visible(timeout=500):
                            is_code_screen = True
                            break
                        # Dismiss intermediate confirmation dialog if present
                        ok_modal = x_page.locator('button[data-testid="confirmationSheetConfirm"]:visible, button:text-is("OK"):visible, button:text-is("Ok"):visible, div[role="button"]:text-is("OK"):visible, button:has-text("Verify"):visible').first
                        if ok_modal.is_visible(timeout=500):
                            self.log("Confirming phone verification dispatch modal (OK)...")
                            try: human_click(x_page, ok_modal)
                            except Exception: ok_modal.click(force=True)
                            time.sleep(1.5)
                    except Exception: pass
                    time.sleep(1.0)
                
                if not is_code_screen and self.rented_phone:
                    # Final check before failing
                    try:
                        if code_input.is_visible(timeout=3000):
                            is_code_screen = True
                    except Exception: pass
                
                if not is_code_screen:
                    screenshot_err = f"email_signup_{self.account_id}_code_prompt_failed.png"
                    try:
                        x_page.screenshot(path=screenshot_err)
                        self.last_screenshot = screenshot_err
                    except Exception: pass
                    cur_url = getattr(x_page, "url", "unknown")
                    self.log(f"ERROR: Verification code screen was not detected on Twitter JoinFlow within 35s. Page URL: {cur_url}")
                    raise RuntimeError("Verification code screen was not detected on Twitter JoinFlow within timeout.")

                if is_code_screen:
                    # Detect whether Twitter sent code to SMS or Email
                    if self.rented_phone:
                        self.code_type = "sms"
                        self.code_recipient = self.rented_phone
                        self.status_detail = f"Awaiting SMS verification code sent to {self.rented_phone} (HeroSMS)"
                        self.log(f"Verification code screen active! Twitter dispatched SMS code to {self.rented_phone} (HeroSMS).")
                    else:
                        self.code_type = "email"
                        self.code_recipient = self.alias_email
                        self.status_detail = f"Awaiting email verification code sent to {self.alias_email}"
                        self.log(f"Verification code screen active! Please enter the code sent to {self.base_email} (Alias: {self.alias_email}).")
                    
                    self.status = "awaiting_code"
                    screenshot_code = f"email_signup_{self.account_id}_code_prompt.png"
                    try:
                        x_page.screenshot(path=screenshot_code)
                        self.last_screenshot = screenshot_code
                    except Exception: pass
                    
                    # Concurrently poll HeroSMS in parallel with interactive user queue from Streamlit
                    user_code = None
                    poll_start = time.time()
                    last_hero_reload = time.time()
                    last_progress_log = time.time()
                    resends_done = set()
                    phone_replacement_attempts = 0
                    active_rental_id = getattr(hero, "current_rental_id", None) if ('hero' in locals()) else None

                    while time.time() - poll_start < 300:
                        elapsed = int(time.time() - poll_start)

                        # Periodic progress logging every 15s so logs and UI stay active
                        if time.time() - last_progress_log >= 15:
                            last_progress_log = time.time()
                            if self.code_type == "sms" and self.rented_phone:
                                self.log(f"HeroSMS: Actively polling for SMS verification code on +1 {self.rented_phone}... ({elapsed}s / 300s)")
                            else:
                                self.log(f"Awaiting email verification code sent to {self.base_email} (Alias: {self.alias_email})... ({elapsed}s / 300s)")

                        # 1. Check interactive user input queue from Streamlit
                        try:
                            user_code = self.code_queue.get_nowait()
                            if user_code:
                                self.log(f"Received verification code from interactive user input: {user_code}")
                                break
                        except queue.Empty: pass

                        # 2. Check HeroSMS autonomously if SMS was dispatched
                        if self.code_type == "sms" and self.rented_phone and 'hero' in locals() and 'hero_page' in locals():
                            try:
                                h_code = hero.check_code_once(hero_page, self.rented_phone, log_fn=self.log)
                                if h_code:
                                    self.log(f"HeroSMS: Intercepted verification code autonomously: {h_code}!")
                                    user_code = h_code
                                    break
                            except Exception: pass

                            # Mid-cycle resends after 35s and 65s if code has not arrived yet
                            active_rental_id = getattr(hero, "current_rental_id", None)
                            if elapsed >= 35 and 1 not in resends_done and active_rental_id:
                                resends_done.add(1)
                                hero.resend_sms(hero_page, active_rental_id, log_fn=self.log)
                                try:
                                    resend_btn = x_page.locator('button:has-text("Send again"):visible, a:has-text("Send again"):visible, span:has-text("Send again"):visible, div[role="button"]:has-text("Send again"):visible, button:has-text("Didn\'t receive code"):visible, span:has-text("Didn\'t receive code"):visible, button:has-text("Resend"):visible, span:has-text("Resend"):visible').first
                                    if resend_btn.is_visible(timeout=1000):
                                        self.log("Triggering 'Send again' on Twitter interface...")
                                        try: human_click(x_page, resend_btn)
                                        except Exception: resend_btn.click(force=True)
                                except Exception: pass

                            elif elapsed >= 65 and 2 not in resends_done and active_rental_id:
                                resends_done.add(2)
                                hero.resend_sms(hero_page, active_rental_id, log_fn=self.log)
                                try:
                                    resend_btn = x_page.locator('button:has-text("Send again"):visible, a:has-text("Send again"):visible, span:has-text("Send again"):visible, div[role="button"]:has-text("Send again"):visible, button:has-text("Didn\'t receive code"):visible, span:has-text("Didn\'t receive code"):visible, button:has-text("Resend"):visible, span:has-text("Resend"):visible').first
                                    if resend_btn.is_visible(timeout=1000):
                                        self.log("Triggering 'Send again' on Twitter interface (attempt 2)...")
                                        try: human_click(x_page, resend_btn)
                                        except Exception: resend_btn.click(force=True)
                                except Exception: pass

                            # Fallback replacement number after 85s if code never delivered
                            if elapsed >= 85 and phone_replacement_attempts < 2 and active_rental_id:
                                self.log(f"[Notice] Code delivery timeout on +1 {self.rented_phone} after {elapsed}s. Attempting fresh replacement line from HeroSMS (Attempt {phone_replacement_attempts + 1}/2)...")
                                try:
                                    hero.cancel_rental(hero_page, active_rental_id, log_fn=self.log)
                                except Exception: pass
                                
                                back_btn = x_page.locator('button[aria-label="Back"]:visible, div[aria-label="Back"]:visible, button[data-testid="app-bar-back"]:visible, div[data-testid="app-bar-back"]:visible').first
                                if back_btn.is_visible(timeout=2000):
                                    try:
                                        self.log("Navigating back to phone number entry screen for replacement attempt...")
                                        human_click(x_page, back_btn)
                                        time.sleep(2.5)
                                        
                                        # Rent fresh phone
                                        new_phone = hero.request_phone_number(hero_page, log_fn=self.log)
                                        if new_phone:
                                            digits = re.sub(r'\D', '', new_phone)
                                            us_phone_10 = digits[-10:] if len(digits) >= 10 else digits
                                            self.log(f"Entering replacement phone into Twitter: +1 {us_phone_10}...")
                                            self.rented_phone = new_phone
                                            self.code_recipient = new_phone
                                            
                                            dialog, phone_input = prepare_phone_input_dialog(x_page, log_fn=self.log)
                                            human_click(x_page, phone_input)
                                            time.sleep(0.2)
                                            phone_input.press("Control+A")
                                            phone_input.press("Backspace")
                                            time.sleep(0.3)
                                            human_type(phone_input, us_phone_10)
                                            time.sleep(random.uniform(0.8, 1.2))
                                            
                                            p_cont = x_page.locator('button:has-text("Continue"):visible, button[type="submit"]:has-text("Continue"):visible').last
                                            if p_cont.is_visible(timeout=3000):
                                                human_click(x_page, p_cont)
                                            time.sleep(3.0)
                                            
                                            ok_modal = x_page.locator('button[data-testid="confirmationSheetConfirm"]:visible, button:text-is("OK"):visible, button:text-is("Ok"):visible, div[role="button"]:text-is("OK"):visible').first
                                            if ok_modal.is_visible(timeout=3000):
                                                human_click(x_page, ok_modal)
                                                time.sleep(2.0)
                                                
                                            # Reset polling timer for replacement number
                                            poll_start = time.time()
                                            resends_done.clear()
                                            phone_replacement_attempts += 1
                                            active_rental_id = getattr(hero, "current_rental_id", None)
                                            self.status_detail = f"Awaiting SMS verification code sent to replacement +1 {new_phone} (HeroSMS)"
                                            self.log(f"Now actively polling replacement line +1 {new_phone}...")
                                            continue
                                    except Exception as rep_err:
                                        self.log(f"Phone replacement note: {rep_err}")

                            # Refresh HeroSMS tab every 25s so dashboard cards update
                            if time.time() - last_hero_reload > 25:
                                last_hero_reload = time.time()
                                try:
                                    hero_page.reload(wait_until="domcontentloaded", timeout=10000)
                                except Exception: pass

                        if self.cancel_requested:
                            break
                        time.sleep(2.0)
                        
                    if not user_code or self.cancel_requested:
                        # Auto-cancel HeroSMS rental on timeout or cancellation so slot is released & balance refunded
                        if self.code_type == "sms" and 'hero' in locals() and 'hero_page' in locals():
                            try:
                                hero.cancel_rental(hero_page, getattr(hero, "current_rental_id", None), log_fn=self.log)
                            except Exception: pass

                        if self.cancel_requested:
                            raise RuntimeError("Registration was cancelled by user.")
                        raise TimeoutError("Timed out waiting for verification code entry (5-minute limit exceeded).")
                        
                    self.status = "completing"
                    self.log(f"Injecting verification code: {user_code}...")
                    
                    code_input = x_page.locator('input.jf-code-input-field, input[autocomplete="one-time-code"], input[name="code"], input[name="verfication_code"], input[name="verification_code"], input[data-testid="ocfEnterTextTextInput"], input[placeholder*="code" i]').first
                    if code_input.is_visible(timeout=5000):
                        human_click(x_page, code_input)
                        human_type(code_input, user_code)
                        time.sleep(1.0)
                        try: code_input.press("Enter")
                        except: pass
                        
                    code_submit = x_page.locator('button:has(p:has-text("Continue")), button[type="submit"]:has-text("Continue"), button:has-text("Continue"), div[role="button"]:has-text("Continue"), div:has-text("Continue"):visible, button:has-text("Next"), button:has-text("Verify")').last
                    if code_submit.is_visible(timeout=3000):
                        human_click(x_page, code_submit)
                    time.sleep(4.0)

                # 4.6 Handle Name / Email entry if prompted after verification or on JoinFlow form
                name_inp = x_page.locator('input[name="name"], input[autocomplete="name"]').first
                if name_inp.is_visible(timeout=2000):
                    self.log(f"Entering profile name: '{self.creds['name']}'...")
                    human_click(x_page, name_inp)
                    human_type(name_inp, self.creds["name"])
                    time.sleep(0.5)

                post_email_inp = x_page.locator('input[name="email"], input[type="email"]').first
                if post_email_inp.is_visible(timeout=2000):
                    self.log(f"Entering target email alias: {self.alias_email}...")
                    human_click(x_page, post_email_inp)
                    human_type(post_email_inp, self.alias_email)
                    time.sleep(0.5)
                    step_btn = x_page.locator('button[type="submit"]:has-text("Next"):visible, button:has-text("Next"):visible, button:has-text("Continue"):visible').first
                    if step_btn.is_visible(timeout=2000):
                        human_click(x_page, step_btn)
                        time.sleep(3.0)

                # 4.7 Patiently orchestrate all post-verification setup and onboarding stages:
                # - Birthday ('When's your birthday?')
                # - 'Set up your account' popup modal (Name, Username, Password)
                # - Consent & Review Settings ('Keeping your trust' / 'Review your current settings')
                # - Post-Signup Onboarding (Interests, Suggested, Bio, Avatar, Notifications)
                self.log("Orchestrating post-verification account setup & onboarding pipeline...")
                self.creds["bio"] = self.bio
                self.creds["website"] = self.website
                handle_full_post_sms_flow(x_page, x_context, self.creds, log_fn=self.log, max_wait_sec=180)
                time.sleep(2.0)

                # 8.5. Ensure Session Finalization on Home Feed
                # Crucial: Twitter only finalizes the full session cookies when the user enters /home
                if "/home" not in x_page.url:
                    has_auth = False
                    try:
                        for c in x_context.cookies():
                            if c.get("name") in ["auth_token", "twid", "ct0"]:
                                has_auth = True
                                break
                    except Exception: pass
                    
                    if has_auth:
                        self.log("Finalizing onboarding: navigating to https://x.com/home...")
                        try:
                            x_page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
                            time.sleep(3.0)
                        except Exception as e:
                            self.log(f"Navigation to home note: {e}")
                    else:
                        self.log("Registration pipeline complete. Verifying session state...")

                # Confirm authenticated state and verified user handle on screen
                confirmed_user = None
                for _ in range(8):
                    try:
                        switcher = x_page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').first
                        if switcher.is_visible(timeout=1500):
                            confirmed_user = switcher.inner_text().replace('\n', ' ')
                            self.log(f"Verified authenticated profile on screen: {confirmed_user}")
                            break
                    except Exception:
                        pass
                    time.sleep(1.0)

                # 9. Extract Final Session Tokens (auth_token, ct0) IMMEDIATELY after reaching authenticated state
                self.log("Extracting verified authentication tokens (auth_token, ct0)...")
                auth_token_val = None
                ct0_val = None
                raw_cookies = []

                for poll_attempt in range(12):
                    try:
                        raw_cookies = x_context.cookies()
                    except Exception:
                        raw_cookies = []

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
                    if self.status == "awaiting_code":
                        self.log("Session paused at Verification Code step.")
                        return None
                    else:
                        raise RuntimeError(f"Registration flow did not establish a session: auth_token missing from cookies.")

                self.log(f"SUCCESS: Extracted verified auth_token: {auth_token_val[:8]}... (ct0: {ct0_val[:8] if ct0_val else 'Pending'}...)")

                # 10. Persist authenticated session state into the account's user_data directory IMMEDIATELY
                try:
                    os.makedirs(user_data_dir, exist_ok=True)
                    state_file = os.path.join(user_data_dir, "state.json")
                    with open(state_file, "w") as sf:
                        json.dump({"cookies": raw_cookies, "origins": []}, sf, indent=2)
                    self.log(f"Saved authenticated browser state into {state_file}")
                except Exception as se:
                    self.log(f"State persistence note: {se}")

                # 10.5 Directly inject session cookies into Chromium storage on disk
                try:
                    from import_account import inject_auth_token_cookie
                    inject_auth_token_cookie(user_data_dir, auth_token_val)
                    self.log(f"Injected verified auth_token directly into Chromium persistent storage for [{self.account_id}].")
                except Exception as ie:
                    self.log(f"Chromium cookie storage note: {ie}")

                # 11. Register Profile in profiles.json IMMEDIATELY
                new_profile = {
                    "id": self.account_id,
                    "user_data_dir": user_data_dir,
                    "username": self.creds["username"],
                    "password": self.creds["password"],
                    "email": self.alias_email,
                    "base_email": self.base_email,
                    "phone": self.rented_phone or "",
                    "display_name": self.creds.get("name", ""),
                    "bio": self.bio or "",
                    "website": self.website or "",
                    "auth_token": auth_token_val,
                    "ct0": ct0_val or "",
                    "auth_token_added": True,
                    "status": "Active"
                }

                profiles = []
                if os.path.exists("profiles.json"):
                    try:
                        with open("profiles.json", "r") as pf:
                            profiles = json.load(pf)
                    except Exception: pass

                existing_idx = next((i for i, p in enumerate(profiles) if p["id"] == self.account_id), None)
                if existing_idx is not None:
                    profiles[existing_idx] = new_profile
                else:
                    profiles.append(new_profile)

                with open("profiles.json", "w") as pf:
                    json.dump(profiles, pf, indent=4)
                self.log(f"SUCCESS: Account [{self.account_id}] (@{self.creds['username']}) successfully registered in profiles.json!")

                try:
                    from activity_logger import log_activity
                    log_activity(
                        action=f"Created & Registered profile (@{self.creds['username']})",
                        account=self.account_id,
                        status="Success",
                        details=f"Email: {self.alias_email} | Phone: {self.rented_phone or 'N/A'}"
                    )
                except Exception: pass

                # 12. Optional Post-Registration Tasks (Customizations & Community Joins in isolated try/except)
                if self.creds.get("name") or self.bio or self.website:
                    try:
                        self.log("Applying profile customization (Name, Bio, Website)...")
                        update_twitter_profile(
                            page=x_page,
                            display_name=self.creds.get("name"),
                            bio=self.bio,
                            website=self.website,
                            log_fn=self.log
                        )
                    except Exception as pe:
                        self.log(f"Profile customization note: {pe}")
                    time.sleep(2.5)

                joined_comms = {}
                try:
                    self.log("Joining target booster communities (Free Trade & Nude Trades) in browser...")
                    joined_comms = join_target_communities_in_browser(x_page, self.account_id, log_fn=self.log)
                except Exception as ce:
                    self.log(f"Community joining note: {ce}")

                screenshot_final = f"email_signup_{self.account_id}_final.png"
                try:
                    x_page.screenshot(path=screenshot_final, timeout=5000)
                    self.last_screenshot = screenshot_final
                except Exception:
                    pass

                existing_idx = next((i for i, p in enumerate(profiles) if p["id"] == self.account_id), None)
                if existing_idx is not None:
                    profiles[existing_idx] = new_profile
                else:
                    profiles.append(new_profile)

                with open("profiles.json", "w") as pf:
                    json.dump(profiles, pf, indent=4)
                    
                # 12. Seed Default Communities
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
                cache_data[self.account_id] = joined_comms if joined_comms else default_seeded
                with open(cache_file, "w") as cf:
                    json.dump(cache_data, cf, indent=4)
                    
                # 13. Auto-sync new profile into any created scheduled jobs
                try:
                    import queue_syncer
                    synced_cnt = queue_syncer.sync_accounts_to_queued_jobs()
                    self.log(f"Auto-synced new profile [{self.account_id}] into scheduled queue jobs (Total synced accounts: {synced_cnt}).")
                except Exception as sync_e:
                    self.log(f"Note: Auto-syncing to queue encountered: {sync_e}")
                    
                self.result_profile = new_profile
                self.status = "success"
                self.log(f"SUCCESS: Account [{self.account_id}] (@{self.creds['username']}) successfully created via email alias & HeroSMS!")
                return new_profile
                
            except Exception as e:
                self.status = "failed"
                self.error_message = str(e)
                self.log(f"Registration Error: {e}")
                raise e
            finally:
                self.log("Closing browser and releasing resources...")
                if x_context:
                    try:
                        for page in list(x_context.pages):
                            try: page.close()
                            except Exception: pass
                    except Exception: pass
                    try: x_context.close()
                    except Exception: pass

                if getattr(self, "browser", None):
                    try:
                        cdp_session = self.browser.new_browser_cdp_session()
                        cdp_session.send("Browser.close")
                    except Exception: pass
                    try: self.browser.close()
                    except Exception: pass
                    self.browser = None

                if hero_context:
                    try:
                        for page in list(hero_context.pages):
                            try: page.close()
                            except Exception: pass
                    except Exception: pass
                    try: hero_context.close()
                    except Exception: pass

                if self.use_cdp:
                    stop_cdp_chrome(port=9222, log_fn=self.log)

                terminate_chrome_processes(user_data_dir=user_data_dir, log_fn=self.log)
                terminate_chrome_processes(user_data_dir=get_cdp_user_data_dir(), log_fn=self.log)
                terminate_chrome_processes(user_data_dir="./user_data/herosms_session", log_fn=self.log)

def run_cli_interactive():
    """Runs interactive email alias registration from CLI."""
    print("=== X / Twitter Email Alias Provisioner ===")
    base_email = input("Enter base Gmail [default: davido.sili93@gmail.com]: ").strip() or "davido.sili93@gmail.com"
    strategy = input("Choose alias strategy (plus/dot) [default: plus]: ").strip().lower() or "plus"
    
    session = EmailRegistrationSession(base_email=base_email, strategy=strategy)
    session.start_background()
    
    while session.status in ["running", "completing"]:
        time.sleep(2)
        if session.status == "awaiting_code":
            print(f"\n>>> VERIFICATION REQUIRED <<<")
            print(f"Code dispatched to: {session.alias_email} (Inbox: {session.base_email})")
            code = input("Enter the 6-digit verification code: ").strip()
            session.provide_verification_code(code)
            break
            
    if session.thread:
        session.thread.join(timeout=180)
        
    print("\nSession finished with status:", session.status)
    if session.result_profile:
        print("Created Profile:", json.dumps(session.result_profile, indent=2))

if __name__ == "__main__":
    run_cli_interactive()
