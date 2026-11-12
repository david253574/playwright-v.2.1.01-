import os
import re
import json
import time
import random
import threading
from datetime import datetime, timedelta

STATUS_FILE = "batch_creator_status.json"

def poll_gmail_for_twitter_code(base_email, app_password, timeout_seconds=120, log_fn=print):
    """
    Connects to Gmail via IMAP SSL to autonomously retrieve the 6-digit Twitter verification code.
    Only runs if an App Password is provided.
    """
    import imaplib
    import email
    start_t = time.time()
    log_fn("IMAP: Polling Gmail for incoming Twitter verification email...")
    
    while time.time() - start_t < timeout_seconds:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(base_email.strip(), app_password.strip())
            mail.select("INBOX")
            
            # Search for unread emails from x.com or twitter.com
            status, messages = mail.search(None, '(UNSEEN)')
            if messages and messages[0]:
                for num in reversed(messages[0].split()):
                    status, data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    sender = str(msg.get("From", "")).lower()
                    subject = str(msg.get("Subject", "")).lower()
                    
                    if "x.com" in sender or "twitter" in sender or "code" in subject or "confirmation" in subject:
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body += part.get_payload(decode=True).decode(errors="ignore")
                        else:
                            body = msg.get_payload(decode=True).decode(errors="ignore")
                            
                        match = re.search(r'\b(\d{6})\b', body)
                        if match:
                            code = match.group(1)
                            log_fn(f"IMAP: Auto-extracted 6-digit confirmation code: {code}!")
                            try: mail.logout()
                            except Exception: pass
                            return code
            try: mail.logout()
            except Exception: pass
        except Exception as e:
            # Silent retry
            pass
        time.sleep(4)
    log_fn("IMAP: Timeout reached without detecting verification code.")
    return None

class BatchAccountRunner:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = BatchAccountRunner()
            return cls._instance

    def __init__(self):
        self.thread = None
        self.stop_requested = threading.Event()
        self.state_lock = threading.RLock()
        self.active_session = None
        self.state = self._load_persisted_state()
        self._save_state()

    def _default_state(self):
        return {
            "is_running": False,
            "method": "herosms",  # "herosms" or "email_alias"
            "base_email": "davidosili93@gmail.com",
            "strategy": "dot",
            "target_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "current_index": 0,
            "current_account_id": None,
            "current_alias": None,
            "current_phase": "idle",  # "idle", "creating", "awaiting_code", "cooldown", "completed", "stopped", "error"
            "status_message": "Ready to launch batch creation.",
            "code_type": "email",
            "code_recipient": "",
            "current_screenshot": None,
            "next_run_timestamp": None,
            "cooldown_seconds_total": 0,
            "created_accounts": [],
            "logs": [],
            "start_time": None,
            "end_time": None
        }

    def _load_persisted_state(self):
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("is_running"):
                        data["is_running"] = False
                        data["current_phase"] = "stopped"
                        data["status_message"] = "Previous batch was interrupted."
                    return data
            except Exception:
                pass
        return self._default_state()

    def _save_state(self):
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(self.state, f, indent=4)
        except Exception:
            pass

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        print(entry, flush=True)
        with self.state_lock:
            self.state["logs"].append(entry)
            if len(self.state["logs"]) > 250:
                self.state["logs"] = self.state["logs"][-250:]
            self._save_state()

    def get_status(self):
        with self.state_lock:
            now = time.time()
            next_t = self.state.get("next_run_timestamp")
            if next_t and self.state.get("current_phase") == "cooldown":
                rem = max(0, int(next_t - now))
                self.state["cooldown_seconds_remaining"] = rem
            else:
                self.state["cooldown_seconds_remaining"] = 0
                
            # If an active email registration session is waiting for a code, reflect it
            if self.active_session and self.state.get("current_phase") == "creating":
                if getattr(self.active_session, "status", None) == "awaiting_code":
                    self.state["current_phase"] = "awaiting_code"
                    self.state["code_type"] = getattr(self.active_session, "code_type", "email")
                    self.state["code_recipient"] = getattr(self.active_session, "code_recipient", self.state.get("current_alias"))
                    self.state["status_message"] = f"Verification code sent to {self.state['code_recipient']}! Enter code to finalize."
                    self._save_state()

            return dict(self.state)

    def is_active(self):
        return self.state.get("is_running", False)

    def submit_verification_code(self, code):
        """Passes the user-entered 6-digit code into the running session."""
        cleaned = str(code).strip()
        if not cleaned:
            return False, "Code cannot be empty."
            
        with self.state_lock:
            sess = self.active_session
            
        if sess and getattr(sess, "status", None) == "awaiting_code":
            self.log(f"Submitting interactive verification code: {cleaned}")
            sess.provide_verification_code(cleaned)
            with self.state_lock:
                self.state["current_phase"] = "creating"
                self.state["status_message"] = f"Code submitted! Finalizing registration for [{sess.account_id}]..."
                self._save_state()
            return True, "Verification code sent to browser engine."
        return False, "No active session is currently awaiting a verification code."

    def stop(self):
        self.log("Cancellation signal received. Halting batch runner...")
        self.stop_requested.set()
        try:
            with open("batch_creator.stop", "w") as f:
                f.write("stop")
        except Exception:
            pass
        if self.active_session:
            try: self.active_session.cancel()
            except Exception: pass
            
        with self.state_lock:
            self.state["is_running"] = False
            self.state["current_phase"] = "stopped"
            self.state["status_message"] = "Batch creation stopped by user."
            self.state["next_run_timestamp"] = None
            self._save_state()

    def start_batch(self, count=3, base_interval_mins=60, jitter_mins=10,
                    method="herosms", base_email="davidosili93@gmail.com",
                    strategy="dot", use_female_vault=True,
                    website_url="https://getmysocial.com/uwuscrettt",
                    gmail_app_password="", rotate_vpn=False, max_retries=3, browser_engine="chrome"):
        if self.is_active():
            return False, "A batch creation run is already in progress."

        if os.path.exists("batch_creator.stop"):
            try: os.remove("batch_creator.stop")
            except Exception: pass
        self.stop_requested.clear()
        self.active_session = None

        with self.state_lock:
            self.state = {
                "is_running": True,
                "method": method,
                "base_email": base_email.strip(),
                "strategy": strategy,
                "browser_engine": browser_engine,
                "target_count": int(count),
                "max_retries": int(max_retries),
                "completed_count": 0,
                "failed_count": 0,
                "current_index": 0,
                "current_account_id": None,
                "current_alias": None,
                "current_phase": "starting",
                "status_message": f"Starting batch creation of {count} account(s) via {method} at ~{base_interval_mins}m interval (engine: {browser_engine}, max {max_retries} retries on failure)...",
                "code_type": "email",
                "code_recipient": "",
                "next_run_timestamp": None,
                "cooldown_seconds_total": 0,
                "created_accounts": [],
                "logs": [],
                "start_time": datetime.now().isoformat(),
                "end_time": None
            }
            self._save_state()

        self.thread = threading.Thread(
            target=self._run_loop,
            args=(count, base_interval_mins, jitter_mins, method, base_email, strategy,
                  use_female_vault, website_url, gmail_app_password, rotate_vpn, max_retries, browser_engine),
            daemon=True
        )
        self.thread.start()
        return True, "Batch account creator started."

    def _run_loop(self, total_count, base_interval, jitter, method, base_email, strategy,
                  use_vault, website, gmail_app_password, rotate_vpn, max_retries=3, browser_engine="chrome"):
        max_retries = max(1, int(max_retries))
        self.log(f"=== Starting Paced Batch Account Creator ===")
        self.log(f"Method: {method.upper()} | Target: {total_count} account(s) | Browser Engine: {browser_engine.upper()} | Retries on Failure: {max_retries}")
        self.log(f"Base Email: {base_email} (Strategy: {strategy}) | Interval: {base_interval}m (±{jitter}m)")

        import importlib
        import account_creator
        importlib.reload(account_creator)
        import account_creator_email
        importlib.reload(account_creator_email)
        import email_alias_manager
        import female_profile_vault

        try:
            for idx in range(1, total_count + 1):
                if self.stop_requested.is_set() or os.path.exists("batch_creator.stop"):
                    self.log("Batch loop stopped early.")
                    break

                acc_id = account_creator.get_next_account_id()
                
                # Determine email alias if email method
                target_alias = None
                if method == "email_alias":
                    target_alias = email_alias_manager.get_or_create_alias_for_account(
                        acc_id, base_email=base_email, strategy=strategy
                    )

                with self.state_lock:
                    self.state["current_index"] = idx
                    self.state["current_account_id"] = acc_id
                    self.state["current_alias"] = target_alias
                    self.state["current_phase"] = "creating"
                    self.state["status_message"] = f"Provisioning account {idx} of {total_count} [{acc_id}]..."
                    self._save_state()

                created_profile = None

                for attempt in range(1, max_retries + 1):
                    if self.stop_requested.is_set() or os.path.exists("batch_creator.stop"):
                        break

                    if attempt == 1:
                        self.log(f"--- [Account {idx}/{total_count}] Initiating provisioning for {acc_id} ---")
                    else:
                        self.log(f"--- [Account {idx}/{total_count}] Retry Attempt {attempt}/{max_retries} for {acc_id} ---")
                        with self.state_lock:
                            self.state["status_message"] = f"Retrying account {idx} of {total_count} [{acc_id}] (attempt {attempt}/{max_retries})..."
                            self._save_state()

                    if target_alias and attempt == 1:
                        self.log(f"Target Email Alias: {target_alias} (Forwarding to: {base_email})")

                    # Profile blueprint
                    if use_vault:
                        disp_name = female_profile_vault.get_random_female_name()
                        bio_text = female_profile_vault.get_random_female_bio()
                    else:
                        rand_p = account_creator.generate_random_profile()
                        disp_name = rand_p["name"]
                        bio_text = None

                    # Optional VPN rotate
                    if rotate_vpn:
                        try:
                            self.log("Rotating VPN location via Windscribe CLI...")
                            import subprocess
                            subprocess.run(["windscribe-cli", "connect"], capture_output=True, text=True, timeout=20)
                            time.sleep(5)
                        except Exception as ve:
                            self.log(f"VPN rotation note: {ve}")

                    # Determine browser engine (direct or rotation)
                    import browser_manager
                    available_engines = browser_manager.get_available_engines()
                    if browser_engine in ["auto", "rotate"]:
                        current_engine = available_engines[(idx - 1) % len(available_engines)]
                    else:
                        current_engine = browser_engine
                    self.log(f"Assigned Browser Engine for {acc_id}: {current_engine.upper()}")

                    # --- EXECUTION: EMAIL ALIAS STRATEGY ---
                    if method == "email_alias":
                        session = account_creator_email.EmailRegistrationSession(
                            account_id=acc_id,
                            base_email=base_email,
                            strategy=strategy,
                            custom_name=disp_name,
                            custom_bio=bio_text,
                            custom_website=website,
                            auto_vault=use_vault,
                            use_herosms_fallback=True,
                            use_cdp=(current_engine == "chrome"),
                            browser_engine=current_engine,
                            log_fn=self.log
                        )
                        self.active_session = session

                        # Launch session in background thread so runner can orchestrate IMAP or code waits
                        session.start_background()

                        # Ensure background thread has started
                        for _ in range(20):
                            if (session.thread and session.thread.is_alive()) or session.status != "idle":
                                break
                            time.sleep(0.1)

                        # Monitor session
                        imap_attempted = False
                        while (session.thread and session.thread.is_alive()) and session.status not in ["success", "failed", "cancelled"]:
                            if self.stop_requested.is_set():
                                session.cancel()
                                break

                            # If waiting for verification code
                            if session.status == "awaiting_code":
                                with self.state_lock:
                                    self.state["current_phase"] = "awaiting_code"
                                    self.state["code_type"] = session.code_type
                                    recipient = getattr(session, "code_recipient", target_alias)
                                    self.state["code_recipient"] = recipient
                                    if session.code_type == "sms":
                                        self.state["status_message"] = f"HeroSMS is actively polling for incoming SMS code on +1 {recipient} (or enter manually)..."
                                    else:
                                        self.state["status_message"] = f"Code sent to {recipient}! Waiting for auto-retrieval (or enter manually)..."
                                    if hasattr(session, "last_screenshot") and session.last_screenshot:
                                        self.state["current_screenshot"] = session.last_screenshot
                                    self._save_state()

                                # Check IMAP auto-extraction if app password provided
                                if gmail_app_password and not imap_attempted and session.code_type == "email":
                                    imap_attempted = True
                                    self.log("IMAP: Attempting automatic verification code extraction from Gmail...")
                                    extracted_code = poll_gmail_for_twitter_code(
                                        base_email, gmail_app_password, timeout_seconds=60, log_fn=self.log
                                    )
                                    if extracted_code:
                                        session.provide_verification_code(extracted_code)
                            elif session.status_detail:
                                with self.state_lock:
                                    self.state["current_phase"] = "creating"
                                    self.state["status_message"] = session.status_detail
                                    if hasattr(session, "last_screenshot") and session.last_screenshot:
                                        self.state["current_screenshot"] = session.last_screenshot
                                    self._save_state()

                            time.sleep(1.5)

                        # Wait for background thread to cleanly exit before evaluating outcome or retrying
                        if session.thread and session.thread.is_alive():
                            session.thread.join(timeout=8)

                        if session.status == "success":
                            created_profile = session.result_profile
                            break
                        else:
                            last_err = session.error_message or session.status
                            self.log(f"[Attempt {attempt}/{max_retries}] Session failed for {acc_id}: {last_err}")
                            if attempt < max_retries and not self.stop_requested.is_set():
                                self.log(f"Cooling down 15 seconds before retry attempt {attempt + 1}/{max_retries} for {acc_id}...")
                                time.sleep(15)

                    # --- EXECUTION: HEROSMS STRATEGY ---
                    else:
                        try:
                            created_profile = account_creator.create_twitter_account(
                                custom_id=acc_id,
                                custom_name=disp_name,
                                bio=bio_text,
                                website=website,
                                log_fn=self.log,
                                browser_engine=current_engine
                            )
                            if created_profile:
                                break
                            else:
                                if attempt < max_retries and not self.stop_requested.is_set():
                                    self.log(f"[Attempt {attempt}/{max_retries}] Registration incomplete. Retrying {acc_id} in 15 seconds (attempt {attempt + 1}/{max_retries})...")
                                    time.sleep(15)
                        except Exception as exc:
                            self.log(f"[Attempt {attempt}/{max_retries}] ERROR creating {acc_id}: {exc}")
                            import traceback
                            self.log(traceback.format_exc())
                            if attempt < max_retries and not self.stop_requested.is_set():
                                self.log(f"Cooling down 15 seconds before retry attempt {attempt + 1}/{max_retries} for {acc_id}...")
                                time.sleep(15)

                # Outcome handling
                # Outcome handling
                with self.state_lock:
                    if created_profile:
                        self.state["completed_count"] += 1
                        self.state["created_accounts"].append({
                            "id": acc_id,
                            "username": created_profile.get("username"),
                            "email": created_profile.get("email") or target_alias or "",
                            "display_name": created_profile.get("display_name") or disp_name,
                            "phone": created_profile.get("phone"),
                            "status": "Success",
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        self.state["failed_count"] += 1
                        self.state["created_accounts"].append({
                            "id": acc_id,
                            "status": "Failed",
                            "timestamp": datetime.now().isoformat()
                        })
                    self._save_state()

                try:
                    from activity_logger import log_activity
                    if created_profile:
                        log_activity(
                            action=f"Created & Registered profile (@{created_profile.get('username')})",
                            account=acc_id,
                            status="Success",
                            details=f"Method: {method} | Phone: {created_profile.get('phone', 'N/A')}"
                        )
                    else:
                        last_err_text = session.error_message if ('session' in locals() and hasattr(session, 'error_message')) else "Creation error"
                        log_activity(
                            action=f"Batch Provisioning Failed ({max_retries} attempts)",
                            account=acc_id,
                            status="Failed",
                            details=f"{last_err_text}"
                        )
                except Exception: pass

                if created_profile:
                    self.log(f"SUCCESS: Account {acc_id} (@{created_profile.get('username')}) successfully registered!")
                    try:
                        import queue_syncer
                        synced_c = queue_syncer.sync_accounts_to_queued_jobs()
                        self.log(f"Auto-synced account {acc_id} across {synced_c} active scheduled queue jobs.")
                    except Exception as se:
                        self.log(f"Note: Queue sync note: {se}")
                else:
                    self.log(f"FAILED: Account {acc_id} could not be completed after {max_retries} attempts.")

                self.active_session = None

                # Cooldown interval before next account
                if idx < total_count and not self.stop_requested.is_set():
                    min_mins = max(5, base_interval - jitter)
                    max_mins = base_interval + jitter
                    chosen_mins = random.uniform(min_mins, max_mins)
                    cooldown_sec = int(chosen_mins * 60)
                    next_time = time.time() + cooldown_sec

                    next_dt_str = (datetime.now() + timedelta(seconds=cooldown_sec)).strftime("%H:%M:%S")
                    status_desc = f"Account {idx} ({acc_id}) registered successfully" if created_profile else f"Account {idx} ({acc_id}) failed"
                    self.log(f"Resting for {int(chosen_mins)} minutes (~{chosen_mins:.1f}m) to maintain natural IP pacing.")
                    self.log(f"Next account creation will trigger at {next_dt_str}.")

                    with self.state_lock:
                        self.state["current_phase"] = "cooldown"
                        self.state["status_message"] = f"{status_desc}. Cooling down for {int(chosen_mins)}m before next creation (at {next_dt_str})."
                        self.state["next_run_timestamp"] = next_time
                        self.state["cooldown_seconds_total"] = cooldown_sec
                        self._save_state()

                    elapsed = 0
                    while elapsed < cooldown_sec:
                        if self.stop_requested.is_set() or os.path.exists("batch_creator.stop"):
                            self.log("Cooldown interrupted by cancellation.")
                            break
                        time.sleep(1)
                        elapsed += 1
        except Exception as e:
            self.log(f"FATAL ERROR in batch loop: {e}")
            import traceback
            self.log(traceback.format_exc())
            with self.state_lock:
                self.state["current_phase"] = "error"
                self.state["status_message"] = f"Fatal error: {e}"
        finally:
            with self.state_lock:
                self.state["is_running"] = False
                self.state["next_run_timestamp"] = None
                self.state["end_time"] = datetime.now().isoformat()
                if self.state.get("current_phase") not in ["error", "stopped"]:
                    if self.stop_requested.is_set():
                        self.state["current_phase"] = "stopped"
                        self.state["status_message"] = f"Batch stopped. Completed: {self.state['completed_count']}, Failed: {self.state['failed_count']}."
                    else:
                        self.state["current_phase"] = "completed"
                        self.state["status_message"] = f"Batch finished! Successfully created {self.state['completed_count']} of {total_count} accounts."
                self._save_state()
            self.log(f"=== Batch Account Provisioning Finished [{self.state.get('current_phase', '').upper()}] ===")
