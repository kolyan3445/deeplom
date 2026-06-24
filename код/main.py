import json
from session_selector import SessionSelector

with open("config/settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

if __name__ == "__main__":
    SessionSelector(settings).run()