"""
queue_syncer.py
Automatic queue synchronization module.
Ensures that all active accounts from profiles.json are automatically injected
into upcoming scheduled jobs with appropriate drafts, media, comments, and community selections.
Also provides utility to update existing scheduled jobs with the latest drafts from promo_vault_drafts.json.
"""

import json
import os
import random
import string
import shutil
import re
from datetime import datetime

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

def lock_file(f):
    if fcntl:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
        except Exception:
            pass
    elif msvcrt:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        except Exception:
            pass

def unlock_file(f):
    if fcntl:
        try:
            fcntl.flock(f, fcntl.LOCK_UN)
        except Exception:
            pass
    elif msvcrt:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass

import community_variator
import url_tracker

def sync_accounts_to_queued_jobs(queue_file="scheduled_queue.json", profiles_file="profiles.json"):
    """
    Ensures newly added or active accounts are injected into pending scheduled jobs in scheduled_queue.json,
    and deleted or disabled accounts are removed from pending jobs.
    Thread-safe and process-safe with file locking.
    """
    if not os.path.exists(queue_file) or not os.path.exists(profiles_file):
        return 0

    try:
        with open(queue_file, "r+") as f:
            lock_file(f)
            try:
                content = f.read().strip()
                if not content:
                    return 0
                jobs = json.loads(content)
                if not jobs:
                    return 0

                # Load profiles
                with open(profiles_file, "r") as pf:
                    profs = json.load(pf)
                active_profs = [p for p in profs if p.get("status") not in ("Disabled", "Suspended")]
                active_ids = [p["id"] for p in active_profs]

                # Load communities cache
                comm_cache = {}
                if os.path.exists("communities_cache.json"):
                    try:
                        with open("communities_cache.json", "r") as cf:
                            comm_cache = json.load(cf)
                    except Exception:
                        pass

                modified = False

                for job in jobs:
                    j_type = job.get("job_type", "")
                    lead_acct = job.get("lead_account")
                    is_promo = ("promo" in str(job.get("id")).lower() or j_type == "individual_promo")
                    vault_file = "promo_vault_drafts.json" if is_promo else "saved_drafts.json"
                    media_dir = "promo_vault_media" if is_promo else "image_vault"

                    vault_payloads = []
                    if os.path.exists(vault_file):
                        try:
                            with open(vault_file, "r") as vf:
                                v_data = json.load(vf)
                                vault_payloads = list(v_data.values()) if isinstance(v_data, dict) else v_data
                        except Exception:
                            pass

                    # 1. Booster Jobs
                    if j_type in ("booster_post", "lead_booster"):
                        b_accounts = job.setdefault("booster_accounts", [])
                        p_sel = job.setdefault("pool_selections", {})
                        b_cmts = job.setdefault("active_comments", {})

                        for aid in active_ids:
                            if aid != lead_acct and aid not in b_accounts:
                                b_accounts.append(aid)
                                modified = True
                            if aid not in p_sel:
                                comm_assignments = {}
                                if os.path.exists("community_assignments.json"):
                                    try:
                                        with open("community_assignments.json", "r") as caf:
                                            comm_assignments = json.load(caf)
                                    except Exception:
                                        pass
                                available = []
                                if aid in comm_cache and comm_cache[aid]:
                                    available = [c for c in comm_cache[aid].keys() if c.lower() not in ("show more", "suggested") and "suggested" not in str(comm_cache[aid][c]).lower()]

                                job_target_comms = [c for o_id, o_comms in p_sel.items() if o_id != aid for c in o_comms]

                                if aid in comm_assignments and comm_assignments[aid]:
                                    p_sel[aid] = comm_assignments[aid]
                                elif job_target_comms and available:
                                    target_set = set(job_target_comms)
                                    matched = [c for c in available if c in target_set]
                                    p_sel[aid] = matched if matched else available[:1]
                                elif available:
                                    p_sel[aid] = available[:1]
                                else:
                                    p_sel[aid] = ["Free Trade (18+)"]
                                modified = True
                            if aid not in b_cmts:
                                b_cmts[aid] = "---".join("".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(14))
                                modified = True

                        orig_len = len(b_accounts)
                        job["booster_accounts"] = [b for b in b_accounts if b in active_ids and b != lead_acct]
                        if len(job["booster_accounts"]) != orig_len:
                            modified = True

                    # 2. Standard / Promo / Recurring Jobs
                    elif j_type not in ("lead_post", "booster_post", "lead_booster"):
                        if "active_drafts" in job:
                            is_clean = bool(job.get("clean_links", False))
                            multi_links = job.get("multi_links", [])

                            # Update bulk_json_drafts if it's a promo job
                            if is_promo and vault_payloads:
                                if multi_links:
                                    job["bulk_json_drafts"] = [community_variator.format_promo_message(x.get("message", ""), custom_link=multi_links[idx % len(multi_links)], clean=is_clean) for idx, x in enumerate(vault_payloads) if isinstance(x, dict) and x.get("message")]
                                else:
                                    job["bulk_json_drafts"] = [community_variator.format_promo_message(x.get("message", ""), clean=is_clean) for x in vault_payloads if isinstance(x, dict) and x.get("message")]
                                modified = True

                            # Check for new accounts
                            for aid in active_ids:
                                if aid not in job["active_drafts"] and vault_payloads:
                                    choice = random.choice(vault_payloads)
                                    raw_msg = choice.get("message", "")
                                    if is_promo:
                                        chosen_link = random.choice(multi_links) if multi_links else None
                                        final_msg = community_variator.format_promo_message(raw_msg, custom_link=chosen_link, clean=is_clean)
                                    else:
                                        final_msg = raw_msg
                                    final_msg = community_variator.resolve_name_placeholders(final_msg, aid)
                                    job["active_drafts"][aid] = final_msg

                                    # Seed communities matching user's explicit assignments or job's targeting
                                    comm_assignments = {}
                                    if os.path.exists("community_assignments.json"):
                                        try:
                                            with open("community_assignments.json", "r") as caf:
                                                comm_assignments = json.load(caf)
                                        except Exception:
                                            pass

                                    job_target_comms = []
                                    for o_id, o_comms in job.get("pool_selections", {}).items():
                                        if o_id != aid and o_comms:
                                            job_target_comms.extend(o_comms)

                                    available = []
                                    if aid in comm_cache and comm_cache[aid]:
                                        available = [c for c in comm_cache[aid].keys() if c.lower() not in ("show more", "suggested") and "suggested" not in str(comm_cache[aid][c]).lower()]

                                    if aid in comm_assignments and comm_assignments[aid]:
                                        job.setdefault("pool_selections", {})[aid] = comm_assignments[aid]
                                    elif job_target_comms and available:
                                        target_set = set(job_target_comms)
                                        matched = [c for c in available if c in target_set]
                                        job.setdefault("pool_selections", {})[aid] = matched if matched else available[:1]
                                    elif available:
                                        job.setdefault("pool_selections", {})[aid] = available[:1]
                                    elif job_target_comms:
                                        job.setdefault("pool_selections", {})[aid] = list(dict.fromkeys(job_target_comms))[:1]
                                    else:
                                        job.setdefault("pool_selections", {})[aid] = ["Free Trade (18+)"]

                                    job.setdefault("active_comments", {})[aid] = choice.get("comments", "").strip() or "---".join("".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(14))

                                    # Sync media if job has uploaded_images
                                    if "uploaded_images" in job and isinstance(job["uploaded_images"], dict) and len(job["uploaded_images"]) > 0:
                                        if os.path.exists(media_dir):
                                            all_media = [f for f in os.listdir(media_dir) if os.path.isfile(os.path.join(media_dir, f))]
                                            # Prefer videos if other accounts use videos
                                            has_vids = any(str(p).lower().endswith(('.mp4', '.mov', '.webm', '.mkv')) for p in job["uploaded_images"].values())
                                            if has_vids:
                                                v_files = [f for f in all_media if f.lower().endswith(('.mp4', '.mov', '.webm', '.mkv'))]
                                            else:
                                                v_files = all_media
                                            if v_files:
                                                chosen_media = random.choice(v_files)
                                                base_id = job.get("id", "job").split("_")[0]
                                                safe_aid = "".join([c for c in aid if c.isalnum()]).rstrip()
                                                dest_path = os.path.join("scheduled_uploads", f"{base_id}_sync_{safe_aid}_{chosen_media}")
                                                try:
                                                    os.makedirs("scheduled_uploads", exist_ok=True)
                                                    shutil.copy2(os.path.join(media_dir, chosen_media), dest_path)
                                                    job["uploaded_images"][aid] = dest_path
                                                except Exception:
                                                    job["uploaded_images"][aid] = os.path.join(media_dir, chosen_media)

                                    modified = True

                                else:
                                    # Existing account in job: resolve name placeholders if still present
                                    curr_msg = job["active_drafts"].get(aid, "")
                                    if "(your name" in curr_msg.lower() or "{name}" in curr_msg.lower():
                                        resolved = community_variator.resolve_name_placeholders(curr_msg, aid)
                                        if resolved != curr_msg:
                                            job["active_drafts"][aid] = resolved
                                            modified = True

                            # Remove deleted or disabled accounts
                            dead_keys = [k for k in job["active_drafts"] if k not in active_ids]
                            for dk in dead_keys:
                                del job["active_drafts"][dk]
                                if "pool_selections" in job and dk in job["pool_selections"]:
                                    del job["pool_selections"][dk]
                                if "uploaded_images" in job and dk in job["uploaded_images"]:
                                    del job["uploaded_images"][dk]
                                modified = True

                if modified:
                    f.seek(0)
                    f.truncate()
                    json.dump(jobs, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())

                return len(active_ids)
            finally:
                unlock_file(f)
    except Exception as e:
        print(f"Error in sync_accounts_to_queued_jobs: {e}")
        return 0

def update_pending_jobs_with_latest_vault(queue_file="scheduled_queue.json", vault_file="promo_vault_drafts.json"):
    """
    Updates pending jobs in scheduled_queue.json with the latest drafts from promo_vault_drafts.json.
    Ensures newly added drafts (and name placeholder resolutions) are distributed into active_drafts
    and bulk_json_drafts across all upcoming waves.
    """
    if not os.path.exists(queue_file) or not os.path.exists(vault_file):
        return 0

    try:
        with open(vault_file, "r") as vf:
            v_data = json.load(vf)
            vault_payloads = list(v_data.values()) if isinstance(v_data, dict) else v_data
        if not vault_payloads:
            return 0

        with open(queue_file, "r+") as f:
            lock_file(f)
            try:
                content = f.read().strip()
                if not content:
                    return 0
                jobs = json.loads(content)
                if not jobs:
                    return 0

                now = datetime.now()
                modified_jobs_count = 0

                for job in jobs:
                    # Only modify jobs that haven't started or are scheduled for future
                    try:
                        job_dt = datetime.fromisoformat(job.get("scheduled_datetime", ""))
                    except Exception:
                        job_dt = now

                    is_promo = ("promo" in str(job.get("id")).lower() or job.get("job_type") == "individual_promo")
                    if not is_promo:
                        continue

                    # Update bulk_json_drafts with all latest drafts
                    is_clean = bool(job.get("clean_links", False))
                    multi_links = job.get("multi_links", [])

                    if multi_links:
                        job["bulk_json_drafts"] = [community_variator.format_promo_message(x.get("message", ""), custom_link=multi_links[idx % len(multi_links)], clean=is_clean) for idx, x in enumerate(vault_payloads) if isinstance(x, dict) and x.get("message")]
                    else:
                        job["bulk_json_drafts"] = [community_variator.format_promo_message(x.get("message", ""), clean=is_clean) for x in vault_payloads if isinstance(x, dict) and x.get("message")]

                    # If job is in the future, refresh active_drafts to include new drafts
                    if job_dt > now and "active_drafts" in job:
                        accounts = list(job["active_drafts"].keys())
                        shuffled_vault = list(vault_payloads)
                        random.shuffle(shuffled_vault)
                        shuffled_links = list(multi_links)
                        if shuffled_links: random.shuffle(shuffled_links)

                        for idx, aid in enumerate(accounts):
                            choice = shuffled_vault[idx % len(shuffled_vault)]
                            raw_msg = choice.get("message", "")
                            chosen_link = shuffled_links[idx % len(shuffled_links)] if shuffled_links else None
                            f_msg = community_variator.format_promo_message(raw_msg, custom_link=chosen_link, clean=is_clean)
                            resolved_msg = community_variator.resolve_name_placeholders(f_msg, aid)
                            job["active_drafts"][aid] = resolved_msg
                            job.setdefault("active_comments", {})[aid] = choice.get("comments", "").strip() or "---".join("".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(14))

                        modified_jobs_count += 1

                f.seek(0)
                f.truncate()
                json.dump(jobs, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

                return modified_jobs_count
            finally:
                unlock_file(f)
    except Exception as e:
        print(f"Error in update_pending_jobs_with_latest_vault: {e}")
        return 0
