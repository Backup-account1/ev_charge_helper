from pathlib import Path
import re

ROOT = Path(r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug")

patterns = [
    r'56',
    r'"soc"\s*:\s*56',
    r'"SOC"\s*:\s*56',
    r'"batteryLevel"\s*:\s*56',
    r'"chargeLevel"\s*:\s*56',
    r'"stateOfCharge"\s*:\s*56',
]

for file in ROOT.rglob("*"):
    if not file.is_file():
        continue

    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except:
        continue

    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            print("=" * 100)
            print("FILE:", file)
            print("MATCH:", m.group())
            print(text[max(0, m.start()-500):m.end()+500])