import os
import json
import time
import re

ALIASES_FILE = "email_aliases.json"

def clean_gmail_username(email):
    """Extracts username without dots if Gmail."""
    parts = email.split("@")
    if len(parts) != 2:
        return email, ""
    user, domain = parts[0], parts[1].lower()
    return user, domain

def generate_dot_aliases(email, max_count=100):
    """
    Generates stealthy dot-based aliases for Gmail.
    Gmail delivers all period variations to the exact same inbox.
    """
    user, domain = clean_gmail_username(email)
    clean_user = user.replace(".", "")
    n = len(clean_user)
    if n <= 1:
        return [email]
        
    aliases = []
    # Up to 2^(n-1) variations
    limit = min(2**(n - 1), 2048)
    for i in range(1, limit):
        parts = []
        for j in range(n):
            parts.append(clean_user[j])
            if (i >> j) & 1 and j < n - 1:
                parts.append(".")
        candidate = "".join(parts) + "@" + domain
        if candidate not in aliases:
            aliases.append(candidate)
        if len(aliases) >= max_count:
            break
    return aliases

def generate_plus_alias(email, tag):
    """
    Generates a plus-addressed alias: user+tag@domain
    """
    parts = email.split("@")
    if len(parts) != 2:
        return email
    user, domain = parts[0], parts[1]
    # Remove existing plus if any
    base_user = user.split("+")[0]
    # Sanitize tag for email compatibility
    clean_tag = re.sub(r'[^a-zA-Z0-9_.-]', '', str(tag))
    return f"{base_user}+{clean_tag}@{domain}"

def load_aliases():
    """Loads stored aliases from email_aliases.json."""
    if not os.path.exists(ALIASES_FILE):
        return {}
    try:
        with open(ALIASES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_aliases(aliases_dict):
    """Saves aliases dictionary to email_aliases.json."""
    with open(ALIASES_FILE, "w") as f:
        json.dump(aliases_dict, f, indent=4)

def get_or_create_alias_for_account(account_id, base_email="davidosili93@gmail.com", strategy="dot"):
    """
    Retrieves the existing alias for an account or generates a new one.
    strategy: 'plus' or 'dot' / 'dot_trick'
    """
    # Force base email to remove unwanted internal dots from base
    user_part, domain = base_email.split("@")[0].replace(".", ""), base_email.split("@")[1]
    base_email = f"{user_part}@{domain}"

    aliases = load_aliases()
    if account_id in aliases and aliases[account_id].get("base_email") == base_email:
        return aliases[account_id]["alias"]
        
    used_aliases = {v.get("alias") for v in aliases.values() if isinstance(v, dict)}
    
    clean_id = account_id.replace(" ", "_").lower()
    
    if strategy in ("dot", "dot_trick"):
        candidates = generate_dot_aliases(base_email, max_count=200)
        chosen = None
        for c in candidates:
            if c not in used_aliases:
                chosen = c
                break
        if not chosen:
            chosen = generate_plus_alias(base_email, clean_id)
    else:
        chosen = generate_plus_alias(base_email, clean_id)
        if chosen in used_aliases:
            chosen = generate_plus_alias(base_email, f"{clean_id}_{int(time.time()) % 10000}")
            
    aliases[account_id] = {
        "account_id": account_id,
        "base_email": base_email,
        "alias": chosen,
        "strategy": strategy,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_aliases(aliases)
    return chosen
