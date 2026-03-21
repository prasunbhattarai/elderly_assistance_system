import json
import re
from datetime import datetime
def extract_time(text):
    text = text.lower()
    text = text.replace('.', ':')

    match = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    match = re.search(r'\b(\d{1,2})\s+(\d{2})\s*(am|pm)?\b', text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    match = re.search(r'\b(\d{1,2})\s*(am|pm|o\'?clock)?\b', text)
    if match:
        hour = int(match.group(1))
        period = match.group(2)

        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:00"

    return None


def extract_task(text):
    text = text.lower()

    patterns = [
        r"remind me to (.+?) at",
        r"remind me to (.+)",
        r"remind me (.+?) at",
        r"remind to (.+?) ",
        r"remind me (.+?) at",
    ]

    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1).strip()

    return None
def extract_reminder(text):
    task = extract_task(text)
    time = extract_time(text)

    if not task or not time:
        return None

    new_reminder = {
        "task": task,
        "time": time
    }

    json_path = "./reminder.json"

    with open(json_path, "r") as f:
        reminder_list = json.load(f)

    reminder_list.append(new_reminder)

    reminder_list.sort(key=lambda r: r["time"])


    with open(json_path, "w") as f:
        json.dump(reminder_list, f, indent=4)

    return new_reminder


