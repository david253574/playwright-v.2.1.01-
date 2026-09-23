import json
import os
import shutil

# 1. Update text vault (saved_drafts.json)
link = "getmysocial.com/uwuscrettt"
new_texts = [
    f"You looked. I knew you would like to see more🥰🥰\n\nJoin me 👉 {link}",
    f"You’re curious, aren’t you? 👀😏\nI might just have something you’ll want to see… 🔥💋\nCome closer 👇🔒 {link}",
    f"hey virgin 😍\nmy link im bored {link}",
    f"I might have a little surprise waiting for you 🎁 {link}",
    f"I'm horny🥵💦 right now, who wanna give me some D🥒🍑\nText me 👇 {link}",
    f"The free review is cute... but the real stuff is 10x hotter. Come inside baby🥵👇 {link}",
    f"i'm honryyyyyyyy asf🔥🍑🍆\n\nJoin me here. It’s free ➡️ {link}",
    f"Currently horny and soaked… craving thick bwc. Who’s down? My dms wide open 😏 {link}"
]

vault_file = "saved_drafts.json"
vault = []
if os.path.exists(vault_file):
    try:
        with open(vault_file, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                vault = list(data.values())
            elif isinstance(data, list):
                vault = data
    except Exception as e:
        print(f"Error reading vault: {e}")

# Append new ones (with empty comments, or should I leave them empty?)
for text in new_texts:
    vault.append({"message": text, "comments": ""})

with open(vault_file, "w") as f:
    json.dump(vault, f, indent=4)
print(f"Added {len(new_texts)} items to {vault_file}.")

# 2. Copy videos to image_vault
video_paths = [
    '/home/david/Downloads/drive-2081.mp4',
    '/home/david/Downloads/drive-1801.mp4',
    '/home/david/Downloads/drive-1799.mp4',
    '/home/david/Downloads/drive-1800.mp4',
    '/home/david/Downloads/drive-2082.mp4',
    '/home/david/Downloads/drive-2080.mp4',
    '/home/david/Downloads/drive-1797.mp4',
    '/home/david/Downloads/drive-1798.mp4'
]

os.makedirs("image_vault", exist_ok=True)
for path in video_paths:
    if os.path.exists(path):
        filename = os.path.basename(path)
        dest = os.path.join("image_vault", filename)
        shutil.copy2(path, dest)
        print(f"Copied {filename} to image_vault/")
    else:
        print(f"Warning: {path} not found.")

