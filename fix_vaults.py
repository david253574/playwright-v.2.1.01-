import json, os, shutil

# 1. Clean saved_drafts.json (remove last 8 items if they match the promo texts)
try:
    with open('saved_drafts.json', 'r') as f:
        drafts = json.load(f)
    promo_texts = drafts[-8:]
    regular_drafts = drafts[:-8]
    with open('saved_drafts.json', 'w') as f:
        json.dump(regular_drafts, f, indent=4)
        
    # Save promo texts to a new dedicated vault file
    with open('promo_vault_drafts.json', 'w') as f:
        json.dump(promo_texts, f, indent=4)
    print("Separated drafts successfully.")
except Exception as e:
    print(f"Error separating drafts: {e}")

# 2. Move videos from image_vault to promo_vault_media
os.makedirs('promo_vault_media', exist_ok=True)
videos = [
    'drive-2081.mp4', 'drive-1801.mp4', 'drive-1799.mp4', 'drive-1800.mp4', 
    'drive-2082.mp4', 'drive-2080.mp4', 'drive-1797.mp4', 'drive-1798.mp4'
]
for v in videos:
    src = os.path.join('image_vault', v)
    dst = os.path.join('promo_vault_media', v)
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Moved {v} to promo_vault_media/")
    else:
        print(f"{v} not found in image_vault/")
