import json
import random

templates = [
    "Thinking about doing something bad today... want to watch? 😈👇 {link}",
    "Need a reason to smile today? I've got plenty right here 💦✨ My link ➡️ {link}",
    "I'm feeling a little lonely... come keep me company? 🥺👉 {link}",
    "Ready to see what I'm hiding under here? 🎀🤫 Join me 👇 {link}",
    "Warning: You might get addicted to what's inside ⚠️💋 Come closer 👇🔒 {link}",
    "Let's play a game... loser has to do whatever the winner wants 🎲😈 Join me 👉 {link}",
    "Craving some late night company... who's up? 🌙💦 My link im bored {link}",
    "I've got a secret... and I only want to share it with you 🤫👂 Come inside baby 🥵👇 {link}",
    "They say I'm trouble, but I promise I'm worth it... 🔥😈 Check out my link 👇 {link}",
    "Just a little taste of what you're missing out on 🍑👅 Join me here ➡️ {link}",
    "Feeling extra spicy today... who wants to handle me? 🌶️🥵 My link 👉 {link}",
    "Come see the side of me I don't show everyone else 📸🙈 Join me 👇 {link}",
    "I'm the sweetest mistake you'll ever make... 🍎🐍 Come closer 👇🔒 {link}",
    "Ready to misbehave? I'll lead the way 😈🔥 My link ➡️ {link}",
    "Need some stress relief? I know exactly what to do 🧘‍♀️💦 Join me 👉 {link}",
    "I'm feeling a little wild... who's going to tame me? 🦁💋 Come inside baby 🥵👇 {link}",
    "Let's make some memories we'll both regret tomorrow... 📸🙈 My link 👇 {link}",
    "I'm the only treat you need today... 🍭🥵 Join me here 👉 {link}",
    "Come get lost with me... 🗺️🔥 My link im bored {link}",
    "I'm feeling a little reckless... want to join? 🏎️💨 Check out my link 👇 {link}",
    "Let's skip the small talk and get right to the fun part... 🗣️🚫 Join me ➡️ {link}",
    "I'm the reason you're going to be late tomorrow... ⏰💦 Come closer 👇🔒 {link}",
    "Just waiting for you to make a move... ♟️💋 My link 👉 {link}",
    "I'm feeling a little naughty... who's going to punish me? 😈👮‍♀️ Come inside baby 🥵👇 {link}",
    "Come find out what's underneath... 🎁🎀 Join me 👇 {link}",
    "I'm your new favorite addiction... come get a dose 💊🥵 My link ➡️ {link}",
    "Let's get a little messy... 🎨💦 Join me here 👉 {link}",
    "I'm feeling a little generous... who wants a reward? 🏆💋 Come closer 👇🔒 {link}",
    "Come get a taste of paradise... 🏝️🔥 My link 👇 {link}",
    "I'm your wildest dream come true... 💭💫 Join me 👉 {link}",
    "Don't be shy, come say hi... I don't bite hard 💋👋 My link im bored {link}",
    "Just a tease... the real show is waiting for you 🎭✨ Come inside baby 🥵👇 {link}",
    "I'm feeling a little wicked today... who wants to play? 🥀💦 Check out my link 👇 {link}",
    "Stop staring at the preview and come see the main event 🎬🍿 Join me ➡️ {link}",
    "Ready to be my next favorite mistake? 🤭👇 My link 👉 {link}",
    "Why be good when being bad feels this good? 😈🔥 Come closer 👇🔒 {link}",
    "I promise I bite... but you'll like it 🧛‍♀️🦇 Join me 👇 {link}",
    "Sneaking a quick pic before I take it all off... want to see the rest? 📸🤫 My link ➡️ {link}",
    "Need a distraction? I'm the best one you'll ever have... 💋✨ Come inside baby 🥵👇 {link}",
    "If you're reading this, it's a sign to come ruin me 💦🙈 Join me here 👉 {link}"
]

link = "getmysocial.com/uwuscrettt"

def generate_random_comment():
    chars = "abcdefghijklmnopqrstuvwxyz"
    return "".join(random.choice(chars) for _ in range(5))

new_promos = []
for template in templates:
    message = template.replace("{link}", link)
    comments = "---".join([generate_random_comment() for _ in range(14)])
    new_promos.append({"message": message, "comments": comments})

try:
    with open("promo_vault_drafts.json", "r") as f:
        existing = json.load(f)
except Exception:
    existing = []

existing.extend(new_promos)

with open("promo_vault_drafts.json", "w") as f:
    json.dump(existing, f, indent=4)

print(f"Total drafts now: {len(existing)}")
