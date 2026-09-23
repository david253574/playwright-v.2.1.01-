import json
import random
import string

messages = [
    "I'm feeling a little lonely tonight, care to join me? 🥺💦 👇 getmysocial.com/uwuscrettt",
    "Let's see if you can handle all this... 😈🔥 My link ➡️ getmysocial.com/uwuscrettt",
    "Currently bored and wanting to play... who's up? 🎲🥵 Come inside baby 👇 getmysocial.com/uwuscrettt",
    "I dare you to try and resist this... 🍑💦 Join me 👉 getmysocial.com/uwuscrettt",
    "Good things come to those who click... ✨🎁 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "I saved the best view just for you... 📸🤫 My link im bored getmysocial.com/uwuscrettt",
    "I need a late night distraction... 🌙💦 Check out my link 👇 getmysocial.com/uwuscrettt",
    "You know exactly what you want, come get it 😈🔥 Join me here 👉 getmysocial.com/uwuscrettt",
    "Feeling a little bratty, who's gonna put me in my place? 🙈🔥 My link ➡️ getmysocial.com/uwuscrettt",
    "I promise I'm a lot of fun once you get to know me 💋✨ Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "Let's make tonight a little more interesting... 🍷😈 Join me 👇 getmysocial.com/uwuscrettt",
    "Why scroll when you could be having fun with me? 📱💦 My link 👉 getmysocial.com/uwuscrettt",
    "Just a little taste to keep you wanting more... 🍭👅 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "I've got something to show you, but you have to come closer 🤫🎁 Check out my link 👇 getmysocial.com/uwuscrettt",
    "I'm craving some attention, give it to me? 🥺💦 My link im bored getmysocial.com/uwuscrettt",
    "If you want me, you know where to find me 📍😈 Join me here ➡️ getmysocial.com/uwuscrettt",
    "Ready to lose some sleep over me? ⏰🔥 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "I have a secret surprise waiting for you... 🤫🎀 My link 👉 getmysocial.com/uwuscrettt",
    "Don't just stare, come do something about it 😈💦 Join me 👇 getmysocial.com/uwuscrettt",
    "I'm exactly what you need right now 💯🔥 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Let me be your favorite bad habit 🚬💋 My link ➡️ getmysocial.com/uwuscrettt",
    "I've been waiting for you all day... ⏳🥺 Check out my link 👇 getmysocial.com/uwuscrettt",
    "Come see why they call me a handful 🍑👋 Join me here 👉 getmysocial.com/uwuscrettt",
    "I'm feeling a little extra today... want to see? ✨📸 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "You caught my eye, now what are you gonna do about it? 👀😈 My link im bored getmysocial.com/uwuscrettt",
    "I've got a sweet tooth and I'm craving you 🍬👅 Join me 👇 getmysocial.com/uwuscrettt",
    "Let's play pretend... I'll be yours for the night 🎭💋 My link ➡️ getmysocial.com/uwuscrettt",
    "I'm not as innocent as I look... 😇😈 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Need a reason to stay up late? I'll give you a few... 🌙💦 Check out my link 👇 getmysocial.com/uwuscrettt",
    "I'm the prize you've been searching for 🏆✨ Join me here 👉 getmysocial.com/uwuscrettt",
    "I dare you not to fall in love... 💘😈 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "Let's make some bad decisions together 🥂🔥 My link 👉 getmysocial.com/uwuscrettt",
    "I'm in the mood to misbehave... care to join? 😈💦 Join me 👇 getmysocial.com/uwuscrettt",
    "I've got everything you need and more 💯💋 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Stop thinking about it and just come over 🏃‍♂️💨 My link ➡️ getmysocial.com/uwuscrettt",
    "I'm feeling a little lonely, keep me company? 🥺👇 Check out my link getmysocial.com/uwuscrettt",
    "I promise I'm worth the trouble 😈✨ Join me here 👉 getmysocial.com/uwuscrettt",
    "I'm a little bit of heaven with a whole lot of hell 😇🔥 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "You know you want to see what's underneath... 🎁👀 My link im bored getmysocial.com/uwuscrettt",
    "I've got a surprise that will make your jaw drop 😲💦 Join me 👇 getmysocial.com/uwuscrettt"
]

results = []
for msg in messages:
    comments = "---".join("".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(14))
    results.append({
        "message": msg,
        "comments": comments
    })

print(json.dumps(results, indent=4))
