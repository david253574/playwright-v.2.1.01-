import json
import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import re
import time
import random
import string

def get_tracking_config():
    config = {
        "enabled": True,
        "base_url": "",
        "utm_source": "x",
        "utm_medium": "social",
        "utm_campaign": "social_post",
        "posting_delay_ms": 4000,
        "post_timeout_ms": 35000,
        "overwrite_existing": False
    }
    
    if os.path.exists("global_config.json"):
        try:
            with open("global_config.json", "r") as f:
                file_config = json.load(f)
                config["enabled"] = file_config.get("tracking_enabled", config["enabled"])
                config["base_url"] = file_config.get("base_website_url", config["base_url"])
                config["utm_source"] = file_config.get("utm_source", config["utm_source"])
                config["utm_medium"] = file_config.get("utm_medium", config["utm_medium"])
                config["utm_campaign"] = file_config.get("utm_campaign", config["utm_campaign"])
                config["posting_delay_ms"] = file_config.get("posting_delay_ms", config["posting_delay_ms"])
                config["post_timeout_ms"] = file_config.get("post_timeout_ms", config["post_timeout_ms"])
                config["overwrite_existing"] = file_config.get("overwrite_existing", config["overwrite_existing"])
        except Exception:
            pass
            
    return config

def build_tracked_url(base_url, campaign=None):
    config = get_tracking_config()
    
    if not config["enabled"]:
        return base_url
        
    if "getmysocial.com" in base_url.lower():
        base_url = "https://exclusive.uwusocial.workers.dev"
        
    parsed = urlparse(base_url)
    if parsed.scheme != "https" and parsed.scheme != "http":
        raise ValueError("The configured website URL must use HTTP/HTTPS.")

    if "workers.dev" in parsed.netloc.lower():
        prefixes = ["vip", "exclusive", "secret", "join", "chat", "link", "post", "view", "access"]
        prefix = random.choice(prefixes)
        rand_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        slug = f"{prefix}_{rand_id}"
        return urlunparse(parsed._replace(path=f"/{slug}", query=""))
        
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    
    overwrite = config["overwrite_existing"]
    if overwrite:
        query_params = [p for p in query_params if p[0] not in ("utm_source", "utm_medium", "utm_campaign")]
        
    current_keys = {p[0] for p in query_params}
    
    if "utm_source" not in current_keys:
        query_params.append(("utm_source", config["utm_source"]))
    if "utm_medium" not in current_keys:
        query_params.append(("utm_medium", config["utm_medium"]))
    if "utm_campaign" not in current_keys:
        query_params.append(("utm_campaign", campaign or config["utm_campaign"]))
        
    unique_id = f"{int(time.time())}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
    
    if "utm_content" not in current_keys:
        query_params.append(("utm_content", unique_id))
    else:
        query_params = [p for p in query_params if p[0] != "utm_content"]
        query_params.append(("utm_content", unique_id))
        
    new_query = urlencode(query_params)
    return urlunparse(parsed._replace(query=new_query))

def append_url_to_text(text, default_url):
    config = get_tracking_config()
    if not config["enabled"]:
        return text
        
    url_pattern = r'(?:https?://[^\s]+)|(?:\b[a-zA-Z0-9.-]+\.(?:com|net|org|io|co|me|ly|gl|link|site|click|info|biz|tv|us|uk|ca|eu|dev|workers\.dev)(?:/[^\s]*)?)'
    urls_found = re.findall(url_pattern, text)
    
    if urls_found:
        def replacer(match):
            url = match.group(0)
            clean_url = url.lower()
            if "x.com" in clean_url or "twitter.com" in clean_url:
                return url
            clean_domains = [
                "dms.tg", "textmehere.chat", "msgme.click", "babe.bio",
                "fanstack.link", "mommy.bio", "morespicy.link", "morespicy.site",
                "shameless.bio", "spicyside.link", "tht.bio", "t.me"
            ]
            if any(cd in clean_url for cd in clean_domains):
                return url
            tracked_url = url
            if not url.startswith('http'):
                tracked_url = 'https://' + url
            try:
                return build_tracked_url(tracked_url)
            except Exception:
                return url
        return re.sub(url_pattern, replacer, text)
    else:
        if default_url and default_url not in text and "example.com" not in default_url:
            return f"{text}\n\n{default_url}"
        return text
