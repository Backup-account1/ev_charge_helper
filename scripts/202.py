import re
from pathlib import Path

ROOT = Path(r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug")

TARGET = "700202"
MIN_SOC = 62
MAX_SOC = 68
CONTEXT = 12

SOC_RE = re.compile(r"\b(6[2-8])%")


def main():
    print("=" * 100)
    print("WHOLE DIRECTORY SEARCH")
    print("=" * 100)
    print("ROOT  :", ROOT)
    print("TARGET:", TARGET)
    print("SOC   :", f"{MIN_SOC}%–{MAX_SOC}%")
    print("=" * 100)

    if not ROOT.exists():
        print("ROOT NOT FOUND")
        return

    found = 0

    # Scan EVERY text/json file in EVERY session
    for file in ROOT.rglob("*"):

        if not file.is_file():
            continue

        if file.suffix.lower() not in {
            ".txt", ".json", ".log", ".html", ".csv"
        }:
            continue

        try:
            text = file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines):

            match = SOC_RE.search(line)

            if not match:
                continue

            soc = int(match.group(1))

            if not (MIN_SOC <= soc <= MAX_SOC):
                continue

            found += 1

            start = max(0, i - CONTEXT)
            end = min(len(lines), i + CONTEXT + 1)

            context_text = "\n".join(lines[start:end])

            target_nearby = TARGET in context_text

            print()
            print("-" * 100)
            print(f"FOUND SOC: {soc}%")
            print(f"TARGET NEARBY: {target_nearby}")
            print(f"FILE: {file}")
            print(f"LINE: {i + 1}")
            print("-" * 100)

            for n in range(start, end):
                marker = " >>> " if n == i else "     "
                print(f"{marker}{n + 1}: {lines[n]}")

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)
    print("Total SOC occurrences:", found)
    print("=" * 100)


if __name__ == "__main__":
    main()