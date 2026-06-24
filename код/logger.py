import os, logging

os.makedirs("logs", exist_ok=True)

with open("logs/app.log", "w", encoding="utf-8"):
    pass

logging.basicConfig(filename="logs/app.log", level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s",
                    encoding="utf-8")

logger = logging.getLogger("thermal_monitor")

