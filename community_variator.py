"""
community_variator.py
Utility module to guarantee unique post payloads (distinct text, distinct media,
and distinct comments) when an account posts across multiple communities.
"""

import os
import re
import json
import random
import string
import glob
try:
    from PIL import Image, ImageEnhance
except ImportError:
    Image = None
    ImageEnhance = None

# Text Variation rules and synonym maps
PHRASE_VARIATIONS = [
    (r"\byou definitely don't want to miss\b", ["make sure you don't miss", "trust me, you can't miss", "whatever you do, don't miss", "you really don't wanna miss"]),
    (r"\bcheck my pinned post\b", ["go see my pinned post", "take a look at my pinned post", "look at what's pinned on my profile", "peek at my pinned post", "check what's pinned at the top"]),
    (r"\bpinned to my profile\b", ["pinned on my profile", "pinned right at the top", "at the top of my page", "pinned on my timeline"]),
    (r"\bpinned post\b", ["pinned tweet", "top post", "pinned tweet on my profile", "post pinned at the top"]),
    (r"\bbefore it's gone\b", ["before it gets taken down", "while it's still up", "hurry before it's deleted", "before i take it down"]),
    (r"\bright now\b", ["tonight", "today", "rn", "asap"]),
    (r"\bgo look\b", ["go check", "take a peek", "see for yourself", "check it out"]),
    (r"\byou won't regret it\b", ["you'll thank me later", "you're gonna love it", "trust me on this one", "worth every second"]),
    (r"\bwho's down\b", ["who wants in", "any takers", "who's awake", "who's ready"]),
    (r"\bmy dms wide open\b", ["dms open for everyone", "dms open rn", "slide in my dms", "text me in dms"]),
    (r"\bfirst time posting\b", ["super new here", "just joined", "first post on here", "finally posting"]),
    (r"\blooking for moots\b", ["need new moots", "looking for mutuals", "come be moots", "want some active moots"]),
    (r"\bfind me here\b", ["see more here", "all my links here", "my private link", "exclusive link here"]),
    (r"\bcan't believe\b", ["honestly shocked", "still can't believe", "i really"]),
    (r"\bdropped something crazy\b", ["just left something wild", "posted something insane", "put something crazy"]),
    (r"\bwhat's waiting\b", ["what i left", "what's sitting", "what i posted"]),
]

EMOJI_SWAPS = {
    "👀": ["🤫", "🙈", "✨", "💖", "🤭"],
    "🤫": ["👀", "🙈", "😈", "💋", "🤭"],
    "🙈": ["🤫", "👀", "🥺", "♡", "✨"],
    "💋": ["💖", "♡", "✨", "🤭", "😈"],
    "😈": ["😏", "🔞", "💦", "🤫", "💋"],
    "😏": ["😈", "👀", "🤭", "✨", "💋"],
    "💦": ["😈", "🔞", "😏", "🔥", "💖"],
    "💖": ["♡", "✨", "💋", "🌸", "🥺"],
    "🥺": ["🙈", "♡", "💖", "✨", "🤭"],
}

def extract_link(text):
    if not text:
        return None
    url_pattern = r'(https?://[^\s]+|\b[a-zA-Z0-9.-]+\.(?:com|net|org|io|co|me|ly|gl|link|site|click|info|biz|tv|us|uk|ca|eu|dev|workers\.dev|tg|chat|bio)(?:/[^\s]*)?)'
    m = re.search(url_pattern, text)
    return m.group(0).rstrip('.,;:!?)') if m else None

def format_promo_message(template, custom_link=None, clean=False):
    """Embeds or replaces links in a promo template with a clean or tracked URL."""
    url_pattern = r'(?:https?://[^\s]+)|(?:\b[a-zA-Z0-9.-]+\.(?:com|net|org|io|co|me|ly|gl|link|site|click|info|biz|tv|us|uk|ca|eu|dev|workers\.dev|tg|chat|bio)(?:/[^\s]*)?)'
    target = custom_link.strip() if custom_link and custom_link.strip() else None
    
    if target:
        target_url = target if target.startswith("http") else f"https://{target}"
        if clean:
            final_link = target_url
        else:
            try:
                import url_tracker
                final_link = url_tracker.build_tracked_url(target_url)
            except Exception:
                final_link = target_url
        if re.search(url_pattern, template):
            return re.sub(url_pattern, lambda m: final_link, template, count=1)
        else:
            return f"{template.rstrip()}\n\n{final_link}"
    else:
        # If template already contains a link, run through tracking if clean is False
        if re.search(url_pattern, template):
            if clean:
                return template
            try:
                import url_tracker
                return url_tracker.append_url_to_text(template, "")
            except Exception:
                return template
        else:
            # Fallback: ensure every promo draft has a link attached alongside the text
            default_url = "https://exclusive.uwusocial.workers.dev"
            if clean:
                final_link = default_url
            else:
                try:
                    import url_tracker
                    final_link = url_tracker.build_tracked_url(default_url)
                except Exception:
                    final_link = default_url
            return f"{template.rstrip()}\n\n{final_link}"

def resolve_name_placeholders(text, p_id_or_profile=None):
    """
    Dynamically substitutes name placeholders like '(your name- should be changed based on your x name)',
    '{name}', '{username}' with the active account's actual name or clean username.
    """
    if not text:
        return text

    display_name = ""
    if isinstance(p_id_or_profile, dict):
        display_name = p_id_or_profile.get("name") or p_id_or_profile.get("username", "")
    elif isinstance(p_id_or_profile, str) and os.path.exists("profiles.json"):
        try:
            with open("profiles.json", "r") as pf:
                profs = json.load(pf)
                p = next((x for x in profs if x.get("id") == p_id_or_profile or x.get("username") == p_id_or_profile), None)
                if p:
                    display_name = p.get("name") or p.get("username", "")
        except Exception:
            pass

    if display_name:
        part = re.split(r'[_0-9]', display_name)[0].strip()
        if len(part) >= 3:
            display_name = part.capitalize()
    else:
        display_name = "me"

    res = re.sub(r'\((?:your name[^\)]*|name)\)', display_name, text, flags=re.IGNORECASE)
    res = re.sub(r'\{(?:name|username)\}', display_name, res, flags=re.IGNORECASE)
    return res

def generate_text_variation(text, variant_index=1):
    """
    Intelligently generates a natural variation of text by replacing phrases,
    swapping equivalent emojis, or adding light contextual hooks.
    Preserves all URLs, hashtags, and mentions.
    """
    if not text:
        return text
        
    res = text
    
    # 1. Apply phrase variations
    for pattern, replacements in PHRASE_VARIATIONS:
        if re.search(pattern, res, flags=re.IGNORECASE):
            rep = replacements[variant_index % len(replacements)]
            res = re.sub(pattern, rep, res, count=1, flags=re.IGNORECASE)
            
    # 2. Swap emojis
    for emo, swaps in EMOJI_SWAPS.items():
        if emo in res:
            new_emo = swaps[variant_index % len(swaps)]
            res = res.replace(emo, new_emo, 1)
            
    # 3. Fallback prefix if no phrase matched to ensure text is never identical
    if res.strip() == text.strip():
        prefixes = [
            "pssst... ",
            "quick reminder: ",
            "hey you... ",
            "before you scroll past: ",
            "just between us... ",
            "don't say i didn't warn you: "
        ]
        res = prefixes[variant_index % len(prefixes)] + res
        
    return res

def get_unique_community_draft(p_id, comm_index, initial_draft, job=None, used_drafts=None):
    """
    Returns a unique draft text for this community index.
    For comm_index == 0: returns initial_draft.
    For comm_index > 0: finds an unused distinct draft from job bulk drafts,
    vault drafts, or generates an intelligent paraphrase if pools are exhausted.
    """
    if used_drafts is None:
        used_drafts = set()
        
    initial_clean = (initial_draft or "").strip()
    if initial_clean:
        used_drafts.add(initial_clean)
        
    if comm_index == 0 and initial_clean:
        return resolve_name_placeholders(initial_clean, p_id)

    candidate_pool = []
    job = job or {}
    job_type = job.get("job_type", "")
    job_id = str(job.get("id", "")).lower()

    # 1. Job-level bulk drafts
    bulk = job.get("bulk_json_drafts", [])
    if bulk:
        candidate_pool.extend([x.get("message", "") if isinstance(x, dict) else str(x) for x in bulk if x])

    # 2. Vault-level drafts based on job type
    link_in_initial = extract_link(initial_draft)
    is_clean = bool(job.get("clean_links", False)) if job else False

    if ("teaser" in job_type or "teaser" in job_id) and os.path.exists("teaser_vault_drafts.json"):
        try:
            with open("teaser_vault_drafts.json", "r") as tf:
                td = json.load(tf)
                candidate_pool.extend([x.get("message", "") if isinstance(x, dict) else str(x) for x in td if x])
        except Exception:
            pass
    elif ("promo" in job_type or "promo" in job_id) and os.path.exists("promo_vault_drafts.json"):
        try:
            with open("promo_vault_drafts.json", "r") as pf:
                pd = json.load(pf)
                for x in pd:
                    msg = x.get("message", "") if isinstance(x, dict) else str(x)
                    if msg:
                        # Re-format with profile's specific link if present
                        if link_in_initial:
                            msg = format_promo_message(msg, link_in_initial, clean=is_clean)
                        candidate_pool.append(msg)
        except Exception:
            pass
    elif os.path.exists("saved_drafts.json"):
        try:
            with open("saved_drafts.json", "r") as sf:
                sd = json.load(sf)
                candidate_pool.extend([x.get("message", "") if isinstance(x, dict) else str(x) for x in sd if x])
        except Exception:
            pass

    # Filter unused candidates
    avail = [d for d in candidate_pool if d.strip() and d.strip() not in used_drafts]
    
    if avail:
        chosen = random.choice(avail)
        used_drafts.add(chosen.strip())
        return resolve_name_placeholders(chosen, p_id)

    # 3. If no candidate found or all used, generate a high-quality variation
    var_text = generate_text_variation(initial_clean or "check out my profile!", variant_index=comm_index)
    used_drafts.add(var_text.strip())
    return resolve_name_placeholders(var_text, p_id)

def get_unique_community_media(p_id, comm_index, initial_media_path, used_media=None):
    """
    Returns a unique media path for this community index.
    For comm_index == 0: returns initial_media_path.
    For comm_index > 0: finds an unused alternative media file from vaults,
    or creates a subtly tweaked image copy so hash-matching is prevented.
    """
    if used_media is None:
        used_media = set()

    if initial_media_path:
        used_media.add(initial_media_path)

    if comm_index == 0:
        return initial_media_path

    if not initial_media_path or not os.path.exists(initial_media_path):
        return None

    is_video = initial_media_path.lower().endswith((".mp4", ".mov", ".webm", ".mkv"))
    is_image = initial_media_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))

    # Search media vaults for alternative files
    candidate_media = []
    search_dirs = ["promo_vault_media", "image_vault", "scheduled_uploads"]
    for sdir in search_dirs:
        if os.path.exists(sdir):
            for fname in os.listdir(sdir):
                fpath = os.path.join(sdir, fname)
                if not os.path.isfile(fpath):
                    continue
                if is_video and fpath.lower().endswith((".mp4", ".mov", ".webm")):
                    candidate_media.append(fpath)
                elif is_image and fpath.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    candidate_media.append(fpath)

    avail_media = [m for m in candidate_media if m not in used_media and os.path.exists(m)]
    if avail_media:
        # Prioritize files from promo_vault_media if available
        promo_vault_candidates = [m for m in avail_media if "promo_vault_media" in m]
        chosen_media = random.choice(promo_vault_candidates if promo_vault_candidates else avail_media)
        used_media.add(chosen_media)
        return chosen_media

    # If no other media file exists in vaults:
    # For images, create a unique copy with subtle 1px adjustment and altered hash
    if is_image and Image is not None:
        try:
            os.makedirs("temp_uploads", exist_ok=True)
            safe_name = os.path.basename(initial_media_path)
            out_path = os.path.join("temp_uploads", f"comm_var_{comm_index}_{safe_name}")
            with Image.open(initial_media_path) as im:
                # Subtly crop 1 pixel from width/height
                w, h = im.size
                if w > 10 and h > 10:
                    im = im.crop((0, 0, w - 1, h - 1))
                # Micro-tweak brightness by 0.2%
                if ImageEnhance is not None:
                    enhancer = ImageEnhance.Brightness(im)
                    im = enhancer.enhance(1.002)
                im.save(out_path, quality=95)
            used_media.add(out_path)
            return out_path
        except Exception:
            pass

    return initial_media_path

def get_unique_community_comment(comm_index, initial_comment=None):
    """
    Returns distinct comments for each community post.
    """
    if comm_index == 0 and initial_comment and initial_comment.strip():
        return initial_comment
    return "---".join("".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(14))
