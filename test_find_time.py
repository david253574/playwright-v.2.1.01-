import json

with open("/home/david/.gemini/antigravity-cli/brain/af30fa91-083d-4867-a305-f59a76bb84d0/.system_generated/logs/transcript_full.jsonl") as f:
    for line in f:
        if 'why is iut looking for proirity table instead of this' in line:
            data = json.loads(line)
            content = data['content']
            # Find the conversation div and the time div
            idx1 = content.find('data-testid="conversation"')
            idx2 = content.find('<time')
            print(f"Index of conversation: {idx1}")
            print(f"Index of time: {idx2}")
            if idx1 != -1 and idx2 != -1:
                if idx2 > idx1:
                    print("time is AFTER conversation, checking if it is inside...")
                    sub = content[idx1:idx2+50]
                    print(f"Substring: {sub}")
