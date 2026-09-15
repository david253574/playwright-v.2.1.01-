import re

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # 1. Remove the Escape key logic
    escape_pattern = r"# SAFETY: Press escape once just in case.*?time\.sleep\(0\.5\)"
    content = re.sub(escape_pattern, "", content, flags=re.DOTALL)

    # 2. Fix the human_typing click position
    # From: element.click(position={"x": random.randint(5, 50), "y": random.randint(5, 20)})
    # To: element.click()
    click_pattern = r'element\.click\(position=\{.*?\}\)'
    content = re.sub(click_pattern, "element.click()", content)

    with open(filepath, "w") as f:
        f.write(content)

update_file("app.py")
update_file("background_worker.py")
print("Fix applied.")
