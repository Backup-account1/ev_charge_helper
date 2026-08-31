from pathlib import Path
import re

ROOT = Path(r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug")

TARGET = "700288"
PERCENT_VALUES = set(range(53, 60))  # 53% ... 59%

for file in ROOT.rglob("*"):
    if not file.is_file():
        continue

    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if TARGET not in text:
        continue

    # Find percentage-looking values
    matches = list(re.finditer(r'(?<![\d.])(\d{1,3})(?:\s*%)?(?![\d.])', text))

    for m in matches:
        value = int(m.group(1))

        if value not in PERCENT_VALUES:
            continue

        # Search around the number for 700288
        nearby = text[max(0, m.start() - 2000):m.end() + 2000]

        if TARGET not in nearby:
            continue

        print("=" * 100)
        print("FILE:", file)
        print("POSSIBLE SOC/PERCENT:", value)

        # Show useful context
        print(nearby)