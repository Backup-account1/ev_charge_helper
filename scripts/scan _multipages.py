
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


# ============================================================
# REGEX
# ============================================================

# Malanka charger IDs
ID_RE = re.compile(
    r"^\s*(700\d{3})\s*$"
)

# SOC
SOC_RE = re.compile(
    r"^\s*(\d{1,3})%\s*$"
)


# ============================================================
# CONNECTORS
# ============================================================

CONNECTORS = {
    "GBT",
    "CCS",
    "CHADEMO",
    "TYPE2",
    "TYPE 2",
}


# ============================================================
# CHARGING STATUS
# ============================================================

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
# SNAPSHOT TIME
# ============================================================

def get_snapshot_time(
    path: Path,
    session_dir: Path,
) -> str:

    """
    Try to extract time from:

        page_text_000123_20260831_201503_123456.txt

    If unavailable, use session directory time.
    """

    m = re.search(
        r"(\d{8})_(\d{6})_(\d{6})",
        path.name,
    )

    if m:

        try:

            dt = datetime.strptime(
                m.group(1)
                + m.group(2)
                + m.group(3),
                "%Y%m%d%H%M%S%f",
            )

            return dt.strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3]

        except Exception:
            pass

    return get_session_time(
        session_dir
    )


# ============================================================
# NORMALIZE
# ============================================================

def normalize(value: str) -> str:

    return (
        value
        .replace("\xa0", " ")
        .strip()
    )


# ============================================================
# PARSE ONE CHARGER BLOCK
# ============================================================

def parse_charger_block(
    charger_id: str,
    block,
    source: Path,
):

    """
    Example:

        700207

        50 кВт

        GBT

        0.73 / кВт•ч

        Заряжается

        96%

        CCS

        0.73 / кВт•ч

        Недоступен

        50

        кВт

        6

    We want:

        700207 | GBT | 96%

    NOT:

        700207 | CCS | 96%

    because CCS is not the connector associated
    with the charging SOC.

    """

    # --------------------------------------------------------
    # Find all connector positions
    # --------------------------------------------------------

    connector_positions = []

    for index, value in enumerate(block):

        upper = value.upper()

        if upper in CONNECTORS:

            connector_positions.append(
                (index, upper)
            )

    if not connector_positions:
        return []

    results = []

    # --------------------------------------------------------
    # Analyze every connector separately
    # --------------------------------------------------------

    for connector_index, (
        position,
        connector,
    ) in enumerate(
        connector_positions
    ):

        # End of this connector's section
        if connector_index + 1 < len(
            connector_positions
        ):

            end = connector_positions[
                connector_index + 1
            ][0]

        else:

            end = len(block)

        connector_block = block[
            position + 1:end
        ]

        # ----------------------------------------------------
        # Find charging status
        # ----------------------------------------------------

        charging = False

        for value in connector_block:

            if value in CHARGING_WORDS:

                charging = True
                break

        # ----------------------------------------------------
        # Find SOC
        # ----------------------------------------------------

        soc = None

        for value in connector_block:

            match = SOC_RE.match(
                value
            )

            if not match:
                continue

            candidate = int(
                match.group(1)
            )

            if 0 <= candidate <= 100:

                soc = candidate
                break

        # ----------------------------------------------------
        # IMPORTANT
        #
        # SOC belongs to this connector.
        #
        # We only want an observation when:
        #
        #     SOC exists
        #
        # OR
        #
        #     connector is explicitly charging.
        #
        # For your history, SOC is the strongest signal.
        # ----------------------------------------------------

        if soc is None and not charging:
            continue

        results.append({

            "id":
                charger_id,

            "connector":
                connector,

            "soc":
                ""
                if soc is None
                else soc,

            "charging":
                charging,

            "source":
                str(source),

        })

    return results


# ============================================================
# PARSE PAGE TEXT
# ============================================================

def parse_page_text(
    path: Path,
):

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

    lines = [
        normalize(line)
        for line in text.splitlines()
    ]

    results = []

    # --------------------------------------------------------
    # Find every charger ID
    # --------------------------------------------------------

    charger_positions = []

    for index, line in enumerate(lines):

        match = ID_RE.fullmatch(
            line
        )

        if match:

            charger_positions.append(
                (
                    index,
                    match.group(1),
                )
            )

    # --------------------------------------------------------
    # Process every charger block
    # --------------------------------------------------------

    for position_index, (
        start,
        charger_id,
    ) in enumerate(
        charger_positions
    ):

        # Next charger
        if position_index + 1 < len(
            charger_positions
        ):

            end = charger_positions[
                position_index + 1
            ][0]

        else:

            end = len(lines)

        block = lines[
            start + 1:end
        ]

        rows = parse_charger_block(
            charger_id,
            block,
            path,
        )

        results.extend(
            rows
        )

    return results


# ============================================================
# FIND ALL PAGE SNAPSHOTS
# ============================================================

def find_page_files(
    session_dir: Path,
):

    files = []

    # Old format
    old_file = (
        session_dir
        / "page_text.txt"
    )

    if old_file.exists():

        files.append(
            old_file
        )

    # New multiple snapshot format
    files.extend(
        sorted(
            session_dir.glob(
                "page_text_*.txt"
            )
        )
    )

    # Remove duplicates
    unique = []
    seen = set()

    for path in files:

        key = str(
            path.resolve()
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            path
        )

    return unique


# ============================================================
# PROCESS SESSION
# ============================================================

def process_session(
    session_dir: Path,
):

    print(
        "Processing:",
        session_dir.name
    )

    page_files = find_page_files(
        session_dir
    )

    print(
        "  Page snapshots:",
        len(page_files)
    )

    results = []

    for page_file in page_files:

        snapshot_time = (
            get_snapshot_time(
                page_file,
                session_dir,
            )
        )

        rows = parse_page_text(
            page_file
        )

        for row in rows:

            row["time"] = (
                snapshot_time
            )

            row["session"] = (
                session_dir.name
            )

            results.append(
                row
            )

    return results


# ============================================================
# REMOVE EXACT DUPLICATES
# ============================================================

def remove_duplicates(
    rows,
):

    unique = {}

    for row in rows:

        key = (

            row["time"],

            row["id"],

            row["connector"],

            row["soc"],

            row["source"],

        )

        unique[key] = row

    return list(
        unique.values()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print(
        "MALANKA ADVANCED MULTI-PAGE CHARGING HISTORY"
    )
    print("=" * 100)

    print(
        "ROOT:",
        ROOT,
    )

    print(
        "OUTPUT:",
        OUTPUT,
    )

    print()

    if not ROOT.exists():

        print(
            "ERROR: directory does not exist"
        )

        return

    # --------------------------------------------------------
    # Sessions
    # --------------------------------------------------------

    sessions = sorted(
        [
            p
            for p in ROOT.iterdir()
            if (
                p.is_dir()
                and re.match(
                    r"^\d{8}_\d{6}",
                    p.name,
                )
            )
        ]
    )

    print(
        "Sessions found:",
        len(sessions),
    )

    print()

    all_rows = []

    # --------------------------------------------------------
    # Process every session
    # --------------------------------------------------------

    for session in sessions:

        rows = process_session(
            session
        )

        all_rows.extend(
            rows
        )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    all_rows = remove_duplicates(
        all_rows
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    all_rows.sort(
        key=lambda row: (
            row["time"],
            row["id"],
            row["connector"],
        )
    )

    # ========================================================
    # PRINT RESULT
    # ========================================================

    print()
    print("=" * 100)
    print(
        "CHARGING CONNECTORS"
    )
    print("=" * 100)

    if not all_rows:

        print(
            "NO CHARGING CONNECTORS FOUND"
        )

    else:

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

            charging = (
                "CHARGING"
                if row["charging"]
                else "-"
            )

            print(
                f'{row["time"]} | '
                f'{row["id"]} | '
                f'{connector:7} | '
                f'{soc:4} | '
                f'{charging}'
            )

    # ========================================================
    # CSV
    # ========================================================

    fieldnames = [
        "time",
        "id",
        "connector",
        "soc",
        "charging",
        "session",
        "source",
    ]

    with OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            all_rows
        )

    # ========================================================
    # SUMMARY
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


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()

