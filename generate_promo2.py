import json
import random
import string

messages = [
    "Thinking about me yet? Because I can't stop thinking about you 🥺💦 👇 getmysocial.com/uwuscrettt",
    "I know you're stressed... let me help you relax 😈🔥 My link ➡️ getmysocial.com/uwuscrettt",
    "Let's play a game... I promise you'll love the prize 🎲🥵 Come inside baby 👇 getmysocial.com/uwuscrettt",
    "I'm feeling extra generous tonight... want a taste? 🍑💦 Join me 👉 getmysocial.com/uwuscrettt",
    "You won't believe what I'm wearing under this... ✨🎁 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "I'm waiting for someone to tell me what to do... 📸🤫 My link im bored getmysocial.com/uwuscrettt",
    "Craving a little midnight snack? 🌙💦 Check out my link 👇 getmysocial.com/uwuscrettt",
    "If you think the preview is good, wait until you see the rest 😈🔥 Join me here 👉 getmysocial.com/uwuscrettt",
    "Who wants to see me make a mess? 🙈🔥 My link ➡️ getmysocial.com/uwuscrettt",
    "I'm the sweetest mistake you're ever gonna make 💋✨ Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "Let's get a little dirty... I don't mind 🍷😈 Join me 👇 getmysocial.com/uwuscrettt",
    "Stop staring at the screen and come talk to me 📱💦 My link 👉 getmysocial.com/uwuscrettt",
    "I have a secret, but I'll only whisper it to you... 🍭👅 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Sneaking away to make some content... want to watch? 🤫🎁 Check out my link 👇 getmysocial.com/uwuscrettt",
    "I need someone to keep me up all night 🥺💦 My link im bored getmysocial.com/uwuscrettt",
    "Come find out why I'm everyone's favorite addiction 📍😈 Join me here ➡️ getmysocial.com/uwuscrettt",
    "Ready to ruin your sleep schedule for me? ⏰🔥 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "I've got a surprise that will definitely make you smile 🤫🎀 My link 👉 getmysocial.com/uwuscrettt",
    "Don't be shy, I bite but you'll like it 😈💦 Join me 👇 getmysocial.com/uwuscrettt",
    "I'm feeling a little wild today, who's going to tame me? 💯🔥 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Let me show you what a real treat looks like 🚬💋 My link ➡️ getmysocial.com/uwuscrettt",
    "I've been a bad girl... who's going to punish me? ⏳🥺 Check out my link 👇 getmysocial.com/uwuscrettt",
    "Come see what all the hype is about 🍑👋 Join me here 👉 getmysocial.com/uwuscrettt",
    "I'm feeling a little lonely in this big bed... ✨📸 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "You caught me right before I took this off 👀😈 My link im bored getmysocial.com/uwuscrettt",
    "I'm craving something thick and sweet... 🍬👅 Join me 👇 getmysocial.com/uwuscrettt",
    "Let's make a memory we'll both regret tomorrow 🎭💋 My link ➡️ getmysocial.com/uwuscrettt",
    "I might look sweet, but I'm nothing but trouble 😇😈 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Need a reason to lock your door? I'll give you one... 🌙💦 Check out my link 👇 getmysocial.com/uwuscrettt",
    "I'm the ultimate distraction you've been looking for 🏆✨ Join me here 👉 getmysocial.com/uwuscrettt",
    "I dare you to try and keep your hands off me 💘😈 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "Let's get a little messy together 🥂🔥 My link 👉 getmysocial.com/uwuscrettt",
    "I'm in the mood to do something reckless... 😈💦 Join me 👇 getmysocial.com/uwuscrettt",
    "I've got everything you're craving and more 💯💋 Come closer 👇🔒 getmysocial.com/uwuscrettt",
    "Stop hesitating and just come see me 🏃‍♂️💨 My link ➡️ getmysocial.com/uwuscrettt",
    "I'm feeling needy tonight, who's going to spoil me? 🥺👇 Check out my link getmysocial.com/uwuscrettt",
    "I promise I'm exactly what you've been looking for 😈✨ Join me here 👉 getmysocial.com/uwuscrettt",
    "I'm the perfect combination of sweet and sinful 😇🔥 Come inside baby 🥵👇 getmysocial.com/uwuscrettt",
    "You know you're curious about what's underneath... 🎁👀 My link im bored getmysocial.com/uwuscrettt",
    "I've got a surprise that will leave you speechless 😲💦 Join me 👇 getmysocial.com/uwuscrettt"
]

results = []
for msg in messages:
    comments = "---".join("".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(14))
    results.append({
        "message": msg,
        "comments": comments
    })

print(json.dumps(results, indent=4))
