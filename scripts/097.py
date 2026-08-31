from pathlib import Path
import re

ROOT = Path(r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug")

for file in ROOT.rglob("*"):
    if not file.is_file():
        continue

    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except:
        continue

    if "700097" not in text:
        continue

    lines = text.splitlines()

    for i, line in enumerate(lines):
        if "700097" in line:
            print("=" * 100)
            print("FILE:", file)
            print("700097 at line:", i + 1)

            # Search nearby lines for 78
            start = max(0, i - 50)
            end = min(len(lines), i + 51)

            for j in range(start, end):
                if re.search(r"(?<!\d)78(?!\d)", lines[j]):
                    print(f"\n>>> 78 FOUND at line {j + 1}")
                    print("\n".join(
                        f"{k + 1}: {lines[k]}"
                        for k in range(max(0, j - 5), min(len(lines), j + 6))
                    ))