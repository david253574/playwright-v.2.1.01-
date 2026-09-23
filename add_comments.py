import json, random

# 1. Get comments from saved_drafts.json
try:
    with open('saved_drafts.json', 'r') as f:
        drafts = json.load(f)
        
    if isinstance(drafts, dict):
        drafts = list(drafts.values())
        
    available_comments = [d.get("comments", "") for d in drafts if d.get("comments", "").strip()]
    
    if not available_comments:
        print("No previously saved comments found in saved_drafts.json")
    else:
        # 2. Add them to promo_vault_drafts.json
        with open('promo_vault_drafts.json', 'r') as f:
            promo_drafts = json.load(f)
            
        for promo in promo_drafts:
            if not promo.get("comments", "").strip():
                # Pick a random comment from the previously saved ones
                promo["comments"] = random.choice(available_comments)
                
        with open('promo_vault_drafts.json', 'w') as f:
            json.dump(promo_drafts, f, indent=4)
            
        print(f"Successfully added random comments to the {len(promo_drafts)} promo posts.")
except Exception as e:
    print(f"Error: {e}")
