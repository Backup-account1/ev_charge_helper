
import re
import csv
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

ROOT = Path(
    r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug"
)

OUTPUT = ROOT / "charging_history.csv"

# Charger IDs used by Malanka
ID_RE = re.compile(r"\b(700\d{3})\b")

# SOC shown by UI
SOC_RE = re.compile(r"^\s*(\d{1,3})%\s*$")

CONNECTORS = {
    "GBT",
    "CCS",
    "CHADEMO",
    "TYPE2",
    "TYPE 2",
}

CHARGING_WORDS = {
    "Заряжается",
    "Charging",
}


# ============================================================
# SESSION TIME
# ============================================================

def get_session_time(session_dir: Path) -> str:

    m = re.match(
        r"(\d{8})_(\d{6})",
        session_dir.name,
    )

    if not m:
        return session_dir.name

    try:
        dt = datetime.strptime(
            m.group(1) + m.group(2),
            "%Y%m%d%H%M%S",
        )

        return dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    except Exception:
        return session_dir.name


# ============================================================
# PARSE PAGE TEXT
# ============================================================

def parse_page_text(path: Path):

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:

        print(
            "READ ERROR:",
            path,
            exc,
        )

        return []

    lines = text.splitlines()

    results = []

    # --------------------------------------------------------
    # Find every charger ID
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        id_match = ID_RE.fullmatch(
            line.strip()
        )

        if not id_match:
            continue

        charger_id = id_match.group(1)

        # ----------------------------------------------------
        # Only inspect until the next charger ID.
        #
        # This is important:
        #
        # 700202
        # 50 кВт
        # 64%
        #
        # must NOT accidentally take the SOC of 700203.
        # ----------------------------------------------------

        block = []

        for j in range(
            i + 1,
            min(len(lines), i + 30),
        ):

            value = lines[j].strip()

            # Next charger starts
            if ID_RE.fullmatch(value):
                break

            block.append(
                (j, value)
            )

        # ----------------------------------------------------
        # Determine connector
        # ----------------------------------------------------

        connector = ""

        for _, value in block:

            upper = value.upper()

            if upper in CONNECTORS:

                connector = upper
                break

        # ----------------------------------------------------
        # Determine charging
        # ----------------------------------------------------

        charging = False

        for _, value in block:

            if value in CHARGING_WORDS:

                charging = True
                break

        # ----------------------------------------------------
        # Determine SOC
        # ----------------------------------------------------

        soc = None
        soc_line = None

        for line_number, value in block:

            match = SOC_RE.match(value)

            if not match:
                continue

            candidate = int(
                match.group(1)
            )

            if 0 <= candidate <= 100:

                soc = candidate
                soc_line = line_number
                break

        # ----------------------------------------------------
        # We want connectors that are charging.
        #
        # But if SOC is present, that is also strong evidence
        # that this connector is the active one.
        # ----------------------------------------------------

        if not charging and soc is None:
            continue

        results.append({
            "id": charger_id,
            "connector": connector,
            "soc": (
                ""
                if soc is None
                else soc
            ),
            "charging": charging,
            "soc_line": (
                ""
                if soc_line is None
                else soc_line + 1
            ),
            "source": str(path),
        })

    return results


# ============================================================
# PROCESS ONE SESSION
# ============================================================

def process_session(session_dir: Path):

    session_time = get_session_time(
        session_dir
    )

    results = []

    print(
        "Processing:",
        session_dir.name
    )

    # --------------------------------------------------------
    # page_text.txt
    # --------------------------------------------------------

    page_text = (
        session_dir / "page_text.txt"
    )

    if page_text.exists():

        rows = parse_page_text(
            page_text
        )

        for row in rows:

            row["time"] = session_time
            results.append(row)

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print("MALANKA CHARGING HISTORY")
    print("=" * 100)

    print(
        "ROOT:",
        ROOT
    )

    print()

    if not ROOT.exists():

        print(
            "ERROR: directory does not exist"
        )

        return

    # Only timestamp session directories
    sessions = sorted(
        [
            p
            for p in ROOT.iterdir()
            if p.is_dir()
            and re.match(
                r"^\d{8}_\d{6}",
                p.name,
            )
        ]
    )

    print(
        "Sessions found:",
        len(sessions)
    )

    print()

    all_rows = []

    # --------------------------------------------------------
    # Every session
    # --------------------------------------------------------

    for session in sessions:

        rows = process_session(
            session
        )

        all_rows.extend(rows)

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    unique = {}

    for row in all_rows:

        key = (
            row["time"],
            row["id"],
            row["connector"],
            row["soc"],
        )

        unique[key] = row

    all_rows = list(
        unique.values()
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    all_rows.sort(
        key=lambda row: (
            row["time"],
            row["id"],
        )
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 100)
    print("CHARGING CONNECTORS")
    print("=" * 100)

    if not all_rows:

        print(
            "NO CHARGING CONNECTORS FOUND"
        )

    for row in all_rows:

        soc = (
            "-"
            if row["soc"] == ""
            else f'{row["soc"]}%'
        )

        connector = (
            row["connector"]
            if row["connector"]
            else "-"
        )

        print(
            f'{row["time"]} | '
            f'{row["id"]} | '
            f'{connector:7} | '
            f'{soc}'
        )

    # ========================================================
    # CSV
    # ========================================================

    with OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "time",
                "id",
                "connector",
                "soc",
                "charging",
                "soc_line",
                "source",
            ],
        )

        writer.writeheader()

        writer.writerows(
            all_rows
        )

    # ========================================================
    # RESULT
    # ========================================================

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)

    print(
        "Charging observations:",
        len(all_rows),
    )

    print(
        "CSV:",
        OUTPUT,
    )

    print("=" * 100)


if __name__ == "__main__":
    main()

