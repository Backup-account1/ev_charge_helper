
from pathlib import Path
import re
import json


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(
    r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug"
)

MIN_SOC = 31
MAX_SOC = 31

# Optional: set charger number, e.g. "700315"
TARGET = '700202'


# ============================================================
# FIND LAST SESSION
# ============================================================

sessions = [
    p for p in BASE_DIR.iterdir()
    if p.is_dir()
]

if not sessions:
    print("No timestamped sessions found.")
    raise SystemExit

latest = max(
    sessions,
    key=lambda p: p.stat().st_mtime
)

print("=" * 100)
print("LATEST SESSION")
print("=" * 100)
print(latest)
print("=" * 100)


# ============================================================
# SEARCH
# ============================================================

# Matches:
# 62, 63, 64, 65, 66, 67, 68
# with optional %
NUMBER_RE = re.compile(
    r"(?<![\d.])("
    + "|".join(str(x) for x in range(MIN_SOC, MAX_SOC + 1))
    + r")(?![\d.])"
)

SOC_WORD_RE = re.compile(
    r"(soc|state.?of.?charge|charge.?percent|"
    r"battery.?percent|percentage|заряд|заряжен)",
    re.IGNORECASE
)

found = 0


for path in latest.rglob("*"):

    if not path.is_file():
        continue

    # Skip huge/binary files
    if path.suffix.lower() not in {
        ".json",
        ".txt",
        ".log",
    }:
        continue

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        continue

    lines = text.splitlines()

    for i, line in enumerate(lines):

        # If TARGET is specified, require it somewhere
        # in the nearby object/context.
        if TARGET:

            context_start = max(0, i - 30)
            context_end = min(
                len(lines),
                i + 31
            )

            context = "\n".join(
                lines[context_start:context_end]
            )

            if TARGET not in context:
                continue

        match = NUMBER_RE.search(line)

        if not match:
            continue

        value = int(match.group(1))

        # ----------------------------------------------------
        # Prefer lines that look SOC-related
        # ----------------------------------------------------

        is_soc_line = bool(
            SOC_WORD_RE.search(line)
        )

        # Print SOC-looking lines immediately.
        # Also print numeric matches because the API may use
        # an unnamed field.
        found += 1

        print()
        print("-" * 100)
        print(f"FILE: {path}")
        print(f"LINE: {i + 1}")
        print(f"VALUE: {value}%")
        print(
            "SOC-LIKE:",
            "YES" if is_soc_line else "possible"
        )
        print("-" * 100)

        # Show ±3 lines only
        start = max(0, i - 3)
        end = min(len(lines), i + 4)

        for j in range(start, end):
            marker = " >>> " if j == i else "     "
            print(
                f"{marker}{j + 1}: {lines[j]}"
            )


# ============================================================
# RESULT
# ============================================================

print()
print("=" * 100)
print("RESULT")
print("=" * 100)
print(
    f"Found {found} occurrences of "
    f"{MIN_SOC}%–{MAX_SOC}%"
)
print(
    f"Session: {latest}"
)
print("=" * 100)

