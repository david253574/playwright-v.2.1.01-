import os
import re

def add_sidebar_to_app():
    with open("app.py", "r") as f:
        content = f.read()
    
    sidebar_code = """
import json
import os

with st.sidebar:
    st.header("⚙️ Global Settings")
    config_data = {"block_videos": False}
    if os.path.exists("global_config.json"):
        try:
            with open("global_config.json", "r") as _f:
                config_data = json.load(_f)
        except: pass
        
    block_videos = st.toggle("Block Heavy Media & Ads (Saves 80% Data)", value=config_data.get("block_videos", False), help="Blocks MP4 streams, heavy post images, and background trackers to massively save bandwidth while keeping profile pictures to remain stealthy.")
    
    if block_videos != config_data.get("block_videos", False):
        config_data["block_videos"] = block_videos
        with open("global_config.json", "w") as _f:
            json.dump(config_data, _f)
"""
    if "⚙️ Global Settings" not in content:
        content = content.replace("import streamlit as st", "import streamlit as st" + sidebar_code)
        with open("app.py", "w") as f:
            f.write(content)
        print("Added Streamlit Sidebar.")

def patch_file_for_media(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    injection = """
"""
    for line in lines:
        new_lines.append(line)
        if "page = context.new_page()" in line or "page = context.pages[0] if context.pages else context.new_page()" in line:
        try:
            import json, os
            if os.path.exists('global_config.json'):
                with open('global_config.json', 'r') as __f:
                    if json.load(__f).get('block_videos', False):
                        def smart_route(route):
                            req = route.request
                            r_type = req.resource_type
                            url = req.url.lower()
                            if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
                            if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
                            try: is_chat_page = 'messages' in page.url.lower()
                            except: is_chat_page = False
                            if r_type == 'image' and not is_chat_page:
                                if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
                            route.continue_()
                        page.route('**/*', smart_route)
        except: pass
            # check if next line is already patched
            # we will just blindly add it if not already there, but let's be careful
            indent = line[:len(line) - len(line.lstrip())]
            injected = injection.format(indent=indent)
            new_lines.append(injected)
            
    # Clean up double injections just in case
    result = "".join(new_lines)
    # Remove older patches if they existed
    result = result.replace('try: page.route("**/*", lambda route: route.abort() if route.request.resource_type == "media" else route.continue_())\n            except: pass\n', '')
    
    with open(filepath, "w") as f:
        f.write(result)
    print(f"Patched {filepath}")

add_sidebar_to_app()
patch_file_for_media("app.py")
patch_file_for_media("background_worker.py")
patch_file_for_media("auto_responder_bg.py")
