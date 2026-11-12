import os
import time
import re
import random
import string
from playwright.sync_api import sync_playwright

HEROSMS_DASHBOARD_URL = "https://herosms-va-portal.vercel.app/dashboard"
HEROSMS_LOGIN_URL = "https://herosms-va-portal.vercel.app/login"
HEROSMS_REGISTER_URL = "https://herosms-va-portal.vercel.app/register"

class HeroSMSClient:
    def __init__(self, email=None, password=None, min_wait_secs=20, max_wait_secs=240, user_data_dir="./user_data/herosms_session"):
        self.email = email
        self.password = password
        self.min_wait_secs = max(20, min_wait_secs)
        self.max_wait_secs = max(self.min_wait_secs + 10, max_wait_secs)
        self.user_data_dir = user_data_dir

    def register_random_account(self, page, service="Twitter / X", log_fn=print):
        """Creates a fresh throwaway account on HeroSMS portal and navigates directly to dashboard."""
        rand_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        name = f"Agent {rand_id}"
        email = f"agent_{rand_id}@vaworker.org"
        pwd = f"Pass_{rand_id}!123"
        
        log_fn(f"HeroSMS: Auto-registering new account ({email})...")
        page.goto(HEROSMS_REGISTER_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2.0)
        
        page.locator('input').first.fill(name)
        page.locator('input[type="email"]').fill(email)
        page.locator('input[type="password"]').fill(pwd)
        
        svc_btn = page.locator(f'button:has-text("{service}")').first
        if svc_btn.is_visible(timeout=3000):
            svc_btn.click()
            time.sleep(0.5)
            
        page.locator('button[type="submit"]').click()
        try:
            page.locator('button:has-text("Get new number"), button:has-text("Sign out")').first.wait_for(state="visible", timeout=20000)
        except Exception:
            time.sleep(4.0)
        
        self.email = email
        self.password = pwd
        log_fn(f"HeroSMS: Account created and session established for {email}!")

    def ensure_authenticated(self, page, log_fn=print):
        """Ensures the page is logged in to HeroSMS portal."""
        page.goto(HEROSMS_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2.0)
        
        # If redirected to /login or unauthenticated
        if "/login" in page.url or page.locator('input[type="email"]').is_visible(timeout=3000):
            if self.email and self.password:
                log_fn("HeroSMS: Login required. Authenticating with stored credentials...")
                page.locator('input[type="email"]').fill(self.email)
                page.locator('input[type="password"]').fill(self.password)
                page.locator('button[type="submit"]').click()
                time.sleep(3.0)
            else:
                log_fn("HeroSMS: Unauthenticated session. Creating fresh account automatically...")
                self.register_random_account(page, service="Twitter / X", log_fn=log_fn)
        else:
            log_fn("HeroSMS: Active session verified.")

    def request_phone_number(self, page, log_fn=print):
        """
        Clicks 'Get new number' and captures the newest rented phone number.
        Returns: raw_number (e.g. '19453473166')
        """
        self.ensure_authenticated(page, log_fn)
        
        # 1. Snapshot all existing rental IDs and numbers from API & DOM before requesting
        existing_rental_ids = set()
        existing_numbers = set()
        try:
            pre_rentals = page.evaluate('''async () => {
                try {
                    const r = await fetch('/api/rentals');
                    return await r.json();
                } catch(e) { return null; }
            }''')
            if pre_rentals and "rentals" in pre_rentals:
                for r in pre_rentals["rentals"]:
                    if r.get("id"): existing_rental_ids.add(r.get("id"))
                    pnum = re.sub(r'\D', '', str(r.get("phoneNumber", "")))
                    if pnum: existing_numbers.add(pnum)
        except Exception: pass

        for p_elem in page.locator('p.font-mono.text-lg').all():
            try:
                num = re.sub(r'\D', '', p_elem.inner_text().strip())
                if num: existing_numbers.add(num)
            except Exception: pass
            
        get_btn = page.locator('button:has-text("Get new number")').first
        if not get_btn.is_visible(timeout=5000):
            raise Exception("HeroSMS: 'Get new number' button not found on dashboard.")
            
        log_fn("HeroSMS: Requesting fresh US number...")
        get_btn.click()
        time.sleep(2.5)
        
        # 2. Wait up to 15s for the newly created active rental
        new_number = None
        for _ in range(15):
            # Check API for fresh active rental with a brand new ID
            try:
                rentals_data = page.evaluate('''async () => {
                    try {
                        const r = await fetch('/api/rentals');
                        return await r.json();
                    } catch(e) { return null; }
                }''')
                if rentals_data and "rentals" in rentals_data and len(rentals_data["rentals"]) > 0:
                    for r in rentals_data["rentals"]:
                        rid = r.get("id")
                        rstatus = str(r.get("status", "")).upper()
                        # Strict requirement: MUST be a new rental ID and MUST NOT be cancelled
                        if rid and rid not in existing_rental_ids and rstatus in ["WAITING", "RECEIVED", "ACTIVE"]:
                            num = re.sub(r'\D', '', str(r.get("phoneNumber", "")))
                            if num:
                                new_number = num
                                self.current_rental_id = rid
                                break
            except Exception: pass
            
            if new_number:
                break

            # Fallback check on dashboard cards (only active cards, never Cancelled)
            try:
                for card in page.locator('div.rounded-2xl').all():
                    c_txt = card.inner_text()
                    if "Waiting for code" in c_txt and "Cancelled" not in c_txt:
                        for p_elem in card.locator('p.font-mono.text-lg').all():
                            num = re.sub(r'\D', '', p_elem.inner_text().strip())
                            if num and num not in existing_numbers:
                                new_number = num
                                break
                    if new_number: break
            except Exception: pass

            if new_number:
                break
            time.sleep(1.0)
            
        # 3. Final fallback: Select the single newest active WAITING rental from API
        if not new_number:
            try:
                rentals_data = page.evaluate('''async () => {
                    try {
                        const r = await fetch('/api/rentals');
                        return await r.json();
                    } catch(e) { return null; }
                }''')
                if rentals_data and "rentals" in rentals_data:
                    waiting = [
                        r for r in rentals_data["rentals"]
                        if str(r.get("status", "")).upper() in ["WAITING", "RECEIVED"]
                    ]
                    if waiting:
                        # Sort by createdAt descending
                        waiting = sorted(waiting, key=lambda x: str(x.get("createdAt", "")), reverse=True)
                        new_number = re.sub(r'\D', '', str(waiting[0].get("phoneNumber", "")))
                        self.current_rental_id = waiting[0].get("id")
            except Exception: pass
                
        if not new_number:
            raise Exception("HeroSMS: Failed to obtain a new phone number from dashboard.")
            
        log_fn(f"HeroSMS: Acquired US phone number: {new_number} (Rental ID: {getattr(self, 'current_rental_id', 'N/A')})")
        return new_number

    def resend_sms(self, page, rental_id, log_fn=print):
        """Calls HeroSMS resend endpoint for active rental."""
        if not rental_id: return False
        try:
            log_fn(f"HeroSMS: Triggering SMS resend for rental {rental_id}...")
            page.evaluate(f'''async () => {{
                try {{ await fetch('/api/rentals/{rental_id}/resend', {{ method: 'POST' }}); }} catch(e) {{}}
            }}''')
            return True
        except Exception:
            return False

    def cancel_rental(self, page, rental_id, log_fn=print):
        """Cancels rental on HeroSMS to free the slot and refund balance."""
        if not rental_id: return False
        try:
            log_fn(f"HeroSMS: Canceling inactive rental {rental_id}...")
            page.evaluate(f'''async () => {{
                try {{ await fetch('/api/rentals/{rental_id}/cancel', {{ method: 'POST' }}); }} catch(e) {{}}
            }}''')
            return True
        except Exception:
            return False

    def finish_rental(self, page, rental_id, log_fn=print):
        """Marks rental as finished on HeroSMS to release resources."""
        if not rental_id: return False
        try:
            page.evaluate(f'''async () => {{
                try {{ await fetch('/api/rentals/{rental_id}/finish', {{ method: 'POST' }}); }} catch(e) {{}}
            }}''')
            return True
        except Exception:
            return False

    def poll_rental_status(self, page, rental_id, log_fn=print):
        """
        Directly queries /api/rentals/{rental_id}/status.
        This is the exact API endpoint used by HeroSMS frontend that triggers
        the backend to query the upstream SMS provider for incoming SMS codes.
        """
        if not rental_id: return None
        try:
            return page.evaluate(f'''async () => {{
                try {{
                    const res = await fetch('/api/rentals/{rental_id}/status');
                    if (!res.ok) return null;
                    const data = await res.json();
                    return data.rental || null;
                }} catch(e) {{ return null; }}
            }}''')
        except Exception:
            return None

    def check_code_once(self, page, phone_number, log_fn=print):
        """Checks HeroSMS API and dashboard once for incoming verification code without blocking."""
        clean_target = re.sub(r'\D', '', str(phone_number))
        clean_10 = clean_target[-10:] if len(clean_target) >= 10 else clean_target
        active_rental_id = getattr(self, "current_rental_id", None)
        
        # 1. First priority: Check targeted /status endpoint on active rental ID
        # This actively triggers the backend to poll upstream for incoming SMS
        if active_rental_id:
            try:
                rental_info = self.poll_rental_status(page, active_rental_id, log_fn=log_fn)
                if rental_info and str(rental_info.get("status", "")).upper() not in ["CANCELLED"]:
                    r_pnum = re.sub(r'\D', '', str(rental_info.get("phoneNumber", "")))
                    if clean_10 in r_pnum:
                        code = rental_info.get("smsCode")
                        if code and re.match(r'^\d{6}$', str(code).strip()):
                            c = str(code).strip()
                            self.finish_rental(page, active_rental_id, log_fn=log_fn)
                            return c
                        txt = rental_info.get("smsText") or ""
                        c_match = re.search(r'\b\d{6}\b', txt)
                        if c_match:
                            c = c_match.group(0)
                            self.finish_rental(page, active_rental_id, log_fn=log_fn)
                            return c
                    else:
                        active_rental_id = None
                        self.current_rental_id = None
            except Exception: pass

        # 2. Check full rentals list from /api/rentals
        try:
            rentals_data = page.evaluate('''async () => {
                try {
                    const r = await fetch('/api/rentals');
                    return await r.json();
                } catch(e) { return null; }
            }''')
            if rentals_data and "rentals" in rentals_data:
                for r in rentals_data["rentals"]:
                    if str(r.get("status", "")).upper() in ["CANCELLED"]:
                        continue
                    r_num = re.sub(r'\D', '', str(r.get("phoneNumber", "")))
                    if clean_10 in r_num:
                        rid = r.get("id")
                        if rid:
                            self.current_rental_id = rid
                            # Poll status on this newly found ID
                            r_status = self.poll_rental_status(page, rid, log_fn=log_fn)
                            if r_status:
                                r = r_status
                        code = r.get("smsCode")
                        if code and re.match(r'^\d{6}$', str(code).strip()):
                            c = str(code).strip()
                            if rid: self.finish_rental(page, rid, log_fn=log_fn)
                            return c
                        txt = r.get("smsText") or ""
                        c_match = re.search(r'\b\d{6}\b', txt)
                        if c_match:
                            c = c_match.group(0)
                            if rid: self.finish_rental(page, rid, log_fn=log_fn)
                            return c
        except Exception: pass
        
        # 3. Check cards on dashboard (ignore cancelled cards)
        try:
            for card in page.locator('div.rounded-2xl').all():
                c_text = card.inner_text()
                if "Cancelled" in c_text:
                    continue
                c_digits = re.sub(r'\D', '', c_text)
                if clean_10 in c_digits:
                    candidate_codes = re.findall(r'\b\d{6}\b', c_text)
                    for candidate in candidate_codes:
                        if candidate not in clean_target:
                            if active_rental_id: self.finish_rental(page, active_rental_id, log_fn=log_fn)
                            return candidate
        except Exception: pass
        return None

    def wait_for_verification_code(self, page, phone_number, log_fn=print):
        """
        Waits at least min_wait_secs (default 20s) before checking, then polls for the SMS code.
        Returns: 6-digit code string (e.g. '920567')
        """
        log_fn(f"HeroSMS: Enforcing mandatory {self.min_wait_secs}s wait before polling for code on {phone_number}...")
        for remaining in range(self.min_wait_secs, 0, -5):
            log_fn(f"HeroSMS: Pacing... {remaining}s remaining before code check...")
            time.sleep(min(5, remaining))
            
        clean_target = re.sub(r'\D', '', str(phone_number))
        clean_10 = clean_target[-10:] if len(clean_target) >= 10 else clean_target
        start_time = time.time()
        resends_done = set()
        active_rental_id = getattr(self, "current_rental_id", None)
        
        while time.time() - start_time < self.max_wait_secs:
            # 1. First priority: Query targeted /status endpoint on active rental ID
            # This triggers backend upstream synchronization for the rental
            if active_rental_id:
                try:
                    rental_info = self.poll_rental_status(page, active_rental_id, log_fn=log_fn)
                    if rental_info and str(rental_info.get("status", "")).upper() not in ["CANCELLED"]:
                        r_pnum = re.sub(r'\D', '', str(rental_info.get("phoneNumber", "")))
                        if clean_10 in r_pnum:
                            code = rental_info.get("smsCode")
                            if code and re.match(r'^\d{6}$', str(code).strip()):
                                c = str(code).strip()
                                log_fn(f"HeroSMS (/status API): Intercepted verification code: {c} for {phone_number}!")
                                self.finish_rental(page, active_rental_id, log_fn=log_fn)
                                return c
                            txt = rental_info.get("smsText") or ""
                            c_match = re.search(r'\b\d{6}\b', txt)
                            if c_match:
                                c = c_match.group(0)
                                log_fn(f"HeroSMS (/status text): Intercepted verification code: {c} for {phone_number}!")
                                self.finish_rental(page, active_rental_id, log_fn=log_fn)
                                return c
                        else:
                            active_rental_id = None
                            self.current_rental_id = None
                except Exception: pass

            # 2. Check full rentals list from /api/rentals
            try:
                rentals_data = page.evaluate('''async () => {
                    try {
                        const r = await fetch('/api/rentals');
                        return await r.json();
                    } catch(e) { return null; }
                }''')
                if rentals_data and "rentals" in rentals_data:
                    for r in rentals_data["rentals"]:
                        r_num = re.sub(r'\D', '', str(r.get("phoneNumber", "")))
                        if clean_10 in r_num:
                            active_rental_id = r.get("id")
                            self.current_rental_id = active_rental_id
                            code = r.get("smsCode")
                            if code and re.match(r'^\d{6}$', str(code).strip()):
                                log_fn(f"HeroSMS (API): Intercepted verification code: {code} for {phone_number}!")
                                if active_rental_id: self.finish_rental(page, active_rental_id, log_fn=log_fn)
                                return str(code).strip()
                            txt = r.get("smsText") or ""
                            c_match = re.search(r'\b\d{6}\b', txt)
                            if c_match:
                                log_fn(f"HeroSMS (API text): Intercepted verification code: {c_match.group(0)} for {phone_number}!")
                                if active_rental_id: self.finish_rental(page, active_rental_id, log_fn=log_fn)
                                return c_match.group(0)
            except Exception: pass

            # 2. Check cards on dashboard
            cards = page.locator('div.rounded-2xl').all()
            for card in cards:
                try:
                    card_text = card.inner_text()
                    card_digits = re.sub(r'\D', '', card_text)
                    if clean_target in card_digits:
                        candidate_codes = re.findall(r'\b\d{6}\b', card_text)
                        for candidate in candidate_codes:
                            if candidate not in clean_target:
                                log_fn(f"HeroSMS: Intercepted verification code: {candidate} for {phone_number}!")
                                try:
                                    finish_btn = card.locator('button:has-text("Mark as finished")').first
                                    if finish_btn.is_visible(timeout=1000):
                                        finish_btn.click()
                                        time.sleep(1.0)
                                except Exception: pass
                                return candidate
                                
                        code_elems = card.locator('span.font-mono, p.font-mono, div.font-mono').all()
                        for el in code_elems:
                            t = el.inner_text().strip()
                            clean_t = re.sub(r'\D', '', t)
                            if len(clean_t) == 6 and clean_t not in clean_target:
                                log_fn(f"HeroSMS: Intercepted verification code: {clean_t} for {phone_number}!")
                                try:
                                    finish_btn = card.locator('button:has-text("Mark as finished")').first
                                    if finish_btn.is_visible(timeout=1000):
                                        finish_btn.click()
                                        time.sleep(1.0)
                                except Exception: pass
                                return clean_t
                except Exception:
                    continue
            
            elapsed = int(time.time() - start_time)
            
            # Mid-cycle resends after 60s and 120s if code has not arrived yet
            if elapsed >= 60 and 1 not in resends_done and active_rental_id:
                resends_done.add(1)
                self.resend_sms(page, active_rental_id, log_fn=log_fn)
            elif elapsed >= 120 and 2 not in resends_done and active_rental_id:
                resends_done.add(2)
                self.resend_sms(page, active_rental_id, log_fn=log_fn)
                
            log_fn(f"HeroSMS: Waiting for code on {phone_number}... ({elapsed}s / {self.max_wait_secs}s)")
            time.sleep(5.0)
            try:
                page.reload(wait_until="domcontentloaded", timeout=15000)
            except Exception: pass
            
        if active_rental_id:
            self.cancel_rental(page, active_rental_id, log_fn=log_fn)
        raise TimeoutError(f"HeroSMS: Timed out waiting for SMS code on {phone_number} after {self.max_wait_secs}s.")
