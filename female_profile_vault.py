import os
import json
import random

NAMES_VAULT_FILE = "female_names_vault.json"
BIOS_VAULT_FILE = "female_bios_vault.json"
DEFAULT_WEBSITE = "https://getmysocial.com/uwuscrettt"

DEFAULT_FEMALE_NAMES = [
    "Chloe", "Mia", "Sophia", "Hailey", "Emma",
    "Bella", "Lily", "Zoe", "Maya", "Elena",
    "Ava", "Scarlett", "Harper", "Aria", "Layla",
    "Ella", "Luna", "Stella", "Nora", "Hazel",
    "Aurora", "Penelope", "Ivy", "Willow", "Claire",
    "Ruby", "Alice", "Daisy", "Fiona", "Serena",
    "Hannah", "Amber", "Jade", "Brooke", "Sienna"
]

DEFAULT_FEMALE_BIOS = [
    "18 ☆ college is ruining me",
    "₍ᐢ. .ᐢ₎♡ soft purrs & sweet thoughts 18 ♡ i reply here ↓",
    "18 ⋆˙⟡ innocent face, mischievous mind ౨ৎ",
    "just an 18yo college girl trying her best ♡ i reply faster here ↓",
    "18 ☆ sleepy college freshman ⋆˙⟡ whispers & sweet secrets ↓",
    "₍ᐢ. .ᐢ₎ shy 18yo student ♡ always texting back here ↓",
    "18 ⋆ student by day, sweet mess by night ☆ link below ↓",
    "college is tough but i'm sweeter 18 ♡ click below ↓",
    "₍ᐢ. .ᐢ₎♡ 18 | cute, clumsy & a little needy ☆ say hi ↓",
    "18 ⋆˙⟡ study breaks & cute thoughts ♡ all my secrets below ↓",
    "dorm room diaries 18 ☆ check out the link ↓",
    "₍ᐢ. .ᐢ₎ soft babygirl vibes 18 ♡ exclusively chatting here ↓",
    "18 ⋆ tired student, sweet sweetheart ♡ let's talk below ↓",
    "18 ☆ too shy for college, just right for you ♡ link ↓",
    "sweet & petite 18 ౨ৎ i'm waiting for you here ↓",
    "18 ⋆˙⟡ college girl by day, cute kitten by night ₍ᐢ. .ᐢ₎♡ ↓",
    "18 ☆ surviving finals on iced coffee and attention ♡ click below ↓",
    "soft spoken 18yo college girl ♡ your favorite distraction ↓",
    "18 ⋆ sweet smiles & cozy dorm nights ☆ reply here ↓",
    "₍ᐢ. .ᐢ₎♡ 18 | sweet little secret ↓",
    "18 ⋆ dorm room angel ౨ৎ tap the link below ↓",
    "just 18 ☆ soft blankets & sweet dreams ♡ chat with me ↓"
]

def load_female_names():
    if os.path.exists(NAMES_VAULT_FILE):
        try:
            with open(NAMES_VAULT_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass
    # Save default if missing
    save_female_names(DEFAULT_FEMALE_NAMES)
    return list(DEFAULT_FEMALE_NAMES)

def save_female_names(names):
    with open(NAMES_VAULT_FILE, "w") as f:
        json.dump(names, f, indent=4)

def load_female_bios():
    if os.path.exists(BIOS_VAULT_FILE):
        try:
            with open(BIOS_VAULT_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass
    # Save default if missing
    save_female_bios(DEFAULT_FEMALE_BIOS)
    return list(DEFAULT_FEMALE_BIOS)

def save_female_bios(bios):
    with open(BIOS_VAULT_FILE, "w") as f:
        json.dump(bios, f, indent=4)

def get_random_female_name():
    names = load_female_names()
    return random.choice(names) if names else "Chloe"

def get_random_female_bio():
    bios = load_female_bios()
    return random.choice(bios) if bios else "18 ☆ college is ruining me"
