```powershell
@'
import json
import re
from pathlib import Path

root = Path("data/malanka_debug")

patterns = re.compile(
    r"(700315|700316|700317|700318|700319|700320|"
    r"soc|state.?of.?charge|battery|charge.?level|"
    r"connector|evse|device|charger)",
    re.I
)

for p in sorted(root.rglob("*")):
    if not p.is_file():
        continue

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    if not patterns.search(text):
        continue

    # Only show response/request files likely to contain API data
    if "responses" not in str(p).lower() and "request" not in p.name.lower():
        continue

    print()
    print("=" * 120)
    print("FILE:", p)
    print("=" * 120)

    # Print URL-like lines first
    for line in text.splitlines():
        if re.search(r"(api|locations|devices|connectors|evse|charger)", line, re.I):
            print(line[:1000])
'@ | python -
```
