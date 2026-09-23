import os

new_injection = """
{indent}try:
{indent}    import json, os
{indent}    if os.path.exists('global_config.json'):
{indent}        with open('global_config.json', 'r') as __f:
{indent}            if json.load(__f).get('block_videos', False):
{indent}                def smart_route(route):
{indent}                    req = route.request
{indent}                    r_type = req.resource_type
{indent}                    url = req.url.lower()
{indent}                    if 'analytics' in url or 'ads-twitter.com' in url: return route.abort()
{indent}                    if r_type == 'media' and 'ton.twimg.com' not in url: return route.abort()
{indent}                    try: is_chat_page = 'messages' in page.url.lower()
{indent}                    except: is_chat_page = False
{indent}                    if r_type == 'image' and not is_chat_page:
{indent}                        if 'pbs.twimg.com/media/' in url or 'video.twimg.com' in url or 'ext_tw_video_thumb' in url: return route.abort()
{indent}                    route.continue_()
{indent}                page.route('**/*', smart_route)
{indent}except: pass
"""

def update_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    cleaned_lines = []
    skip_next = 0
    for i, line in enumerate(lines):
        if skip_next > 0:
            skip_next -= 1
            continue
            
        # Clean old lambda route
        if "try:" in line and i+7 < len(lines):
            if "if json.load(__f).get('block_videos', False):" in lines[i+4]:
                if "page.route('**/*', lambda route: route.abort()" in lines[i+5]:
                    skip_next = 6
                    if "except: pass" in lines[i+7]: skip_next = 7
                    continue
        
        # Clean existing smart route (if run multiple times)
        if "try:" in line and i+12 < len(lines):
            if "def smart_route(route):" in lines[i+5]:
                # find where it ends
                j = i
                while j < len(lines) and "except: pass" not in lines[j]:
                    j += 1
                skip_next = j - i
                continue
                
        cleaned_lines.append(line)
        
    final_lines = []
    for line in cleaned_lines:
        final_lines.append(line)
        if "page = context.new_page()" in line or "page = context.pages[0] if context.pages else context.new_page()" in line:
            indent = line[:len(line) - len(line.lstrip())]
            final_lines.append(new_injection.format(indent=indent).lstrip('\n'))
            
    with open(filepath, 'w') as f:
        f.writelines(final_lines)
    print(f"Updated {filepath}")

update_file('app.py')
update_file('background_worker.py')
update_file('auto_responder_bg.py')
update_file('apply_video_block.py')
