import json
import random

templates = [
    "Craving some late night fun... who's awake? 😈 Come see me here 👉 {link}",
    "Just got out of the shower and feeling a bit lonely... 💦 Join me 👇 {link}",
    "I know you're looking... might as well come get a real taste 🍑👅 My link ➡️ {link}",
    "Feeling extra generous today... unlocking some surprises for you 🎁🤫 Join me 👉 {link}",
    "Good girls go to heaven, bad girls bring you here... 🔥😈 Check out my link 👇 {link}",
    "Can't sleep... someone come keep me company and make me purr 🐈‍⬛💋 Join me here ➡️ {link}",
    "Bored out of my mind... let's play a little game? 🎲🥵 Come inside baby 👉 {link}",
    "If you're reading this, it's a sign to come ruin me 💦🙈 My link 👇 {link}",
    "They say curiosity killed the cat, but satisfaction brought it back... 😻 Come closer 👇🔒 {link}",
    "Need a distraction? I'm the best one you'll ever have... 💋✨ Join me here 👉 {link}",
    "Sneaking a quick pic before I take it all off... want to see the rest? 📸🤫 My link im bored {link}",
    "I promise I bite... but you'll like it 🧛‍♀️🦇 Join me 👉 {link}",
    "Why be good when being bad feels this good? 😈🔥 Come inside baby 🥵👇 {link}",
    "Ready to be my next favorite mistake? 🤭👇 {link}",
    "Stop staring at the preview and come see the main event 🎬🍿 My link ➡️ {link}",
    "I'm feeling a little wicked today... who wants to play? 🥀💦 Join me 👉 {link}",
    "Just a tease... the real show is waiting for you 🎭✨ Come closer 👇🔒 {link}",
    "Don't be shy, come say hi... I don't bite hard 💋👋 Join me here ➡️ {link}",
    "Craving some attention right now... who's going to give it to me? 🥺👉 {link}",
    "Let's misbehave together... I'll show you how 😈🔥 My link 👇 {link}",
    "I'm your new favorite addiction... come get a dose 💊🥵 Join me 👉 {link}",
    "Warning: highly addictive content ahead ⚠️💋 Come inside baby 🥵👇 {link}",
    "I've got a secret... want me to whisper it to you? 🤫👂 My link ➡️ {link}",
    "Come find out what's underneath... 🎁🎀 Join me here 👉 {link}",
    "I'm feeling a little naughty... who's going to punish me? 😈👮‍♀️ Come closer 👇🔒 {link}",
    "Just waiting for you to make a move... ♟️💋 My link im bored {link}",
    "I'm the reason you're going to be late tomorrow... ⏰💦 Join me 👉 {link}",
    "Let's skip the small talk and get right to the fun part... 🗣️🚫 My link 👇 {link}",
    "I'm everything you've ever wanted... and more 💫💋 Come inside baby 🥵👇 {link}",
    "Come get lost with me... 🗺️🔥 Join me here ➡️ {link}",
    "I'm feeling a little reckless... want to join? 🏎️💨 My link 👉 {link}",
    "I'm the sweetest sin you'll ever commit... 🍎🐍 Come closer 👇🔒 {link}",
    "Let's make some memories we'll both regret tomorrow... 📸🙈 Join me 👉 {link}",
    "I'm feeling a little wild... who's going to tame me? 🦁💋 My link ➡️ {link}",
    "Come see what all the fuss is about... 🎉👇 {link}",
    "I'm the only treat you need today... 🍭🥵 Come inside baby 🥵👇 {link}",
    "Let's get a little messy... 🎨💦 Join me here 👉 {link}",
    "I'm feeling a little generous... who wants a reward? 🏆💋 My link 👇 {link}",
    "Come get a taste of paradise... 🏝️🔥 Join me 👉 {link}",
    "I'm your wildest dream come true... 💭💫 Come closer 👇🔒 {link}"
]

link = "getmysocial.com/uwuscrettt"

def generate_random_comment():
    chars = "abcdefghijklmnopqrstuvwxyz"
    return "".join(random.choice(chars) for _ in range(5))

promos = []
for template in templates:
    message = template.replace("{link}", link)
    comments = "---".join([generate_random_comment() for _ in range(14)])
    promos.append({"message": message, "comments": comments})

print(json.dumps(promos, indent=4))
