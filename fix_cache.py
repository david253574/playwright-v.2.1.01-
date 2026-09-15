import json

with open("communities_cache.json", "r") as f:
    cache = json.load(f)

for acc, comms in cache.items():
    for c_name, c_info in comms.items():
        if c_info.get("members") == "N/A":
            c_info["members"] = 0

with open("communities_cache.json", "w") as f:
    json.dump(cache, f, indent=4)

print("Cache fixed!")
