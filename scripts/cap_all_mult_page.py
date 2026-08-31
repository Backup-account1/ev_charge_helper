import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


# ============================================================
# CONFIG
# ============================================================

AUTH_FILE = Path(
    r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\auth\malanka.json"
)

MAP_URL = "https://customer.malankabn.by/map/"

BASE_DEBUG_DIR = Path(
    r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug"
)

# ------------------------------------------------------------
# Capture settings
# ------------------------------------------------------------

CAPTURE_SECONDS = 300       # 5 minutes
SNAPSHOT_INTERVAL = 5       # page snapshot every 5 sec

# Explore map approximately every N snapshots.
# 6 * 5 sec = every ~30 sec.
EXPLORE_EVERY_SNAPSHOTS = 6

# How long to wait after clicking a point.
CLICK_WAIT_MS = 1500


# ============================================================
# TIMESTAMPED SESSION DIRECTORY
# ============================================================

SESSION_ID = datetime.now().strftime(
    "%Y%m%d_%H%M%S_%f"
)

DEBUG_DIR = (
    BASE_DEBUG_DIR
    / SESSION_ID
)

REQUEST_DIR = (
    DEBUG_DIR
    / "requests"
)

RESPONSE_DIR = (
    DEBUG_DIR
    / "responses"
)

REQUEST_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESPONSE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# GLOBALS
# ============================================================

request_counter = 0
response_counter = 0
snapshot_counter = 0

counter_lock = asyncio.Lock()

# Keep every asynchronous save task alive.
pending_tasks = set()


# ============================================================
# HELPERS
# ============================================================

def safe_filename(
    value: str,
    max_length: int = 180,
) -> str:

    value = re.sub(
        r"[^a-zA-Z0-9.\-_]+",
        "_",
        value,
    )

    value = value.strip("._")

    if not value:
        value = "unknown"

    return value[:max_length]


def is_malanka_url(url: str) -> bool:
    """
    Save ALL traffic belonging to Malanka.

    There is deliberately NO API endpoint whitelist.

    This is important because an endpoint containing SOC,
    charger state, sessions, etc. may have an unexpected URL.
    """

    try:

        parsed = urlparse(url)

        host = parsed.netloc.lower()

        return (
            "malankabn.by" in host
            and "yandex" not in host
        )

    except Exception:

        return False


def make_name(
    prefix: str,
    number: int,
    url: str,
) -> str:

    parsed = urlparse(url)

    path = parsed.path or "root"

    return safe_filename(
        f"{number:08d}_"
        f"{prefix}_"
        f"{parsed.netloc}_"
        f"{path}"
    )


# ============================================================
# TASK TRACKING
# ============================================================

def create_tracked_task(coro):

    task = asyncio.create_task(coro)

    pending_tasks.add(task)

    def done_callback(task):

        pending_tasks.discard(task)

        try:
            task.result()

        except Exception as exc:

            print(
                "[BACKGROUND TASK ERROR]",
                repr(exc),
            )

    task.add_done_callback(
        done_callback
    )

    return task


async def drain_pending_tasks():

    if not pending_tasks:
        return

    print()
    print("=" * 100)
    print("DRAINING PENDING SAVE TASKS")
    print("=" * 100)

    while pending_tasks:

        tasks = list(
            pending_tasks
        )

        print(
            "Pending save tasks:",
            len(tasks),
        )

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        await asyncio.sleep(
            0.1
        )

    print(
        "All network files saved."
    )

    print("=" * 100)


# ============================================================
# SAVE REQUEST
# ============================================================

async def save_request(request):

    global request_counter

    if not is_malanka_url(
        request.url
    ):
        return

    async with counter_lock:

        request_counter += 1

        number = request_counter

    timestamp_ns = time.time_ns()

    timestamp = (
        datetime.now()
        .isoformat()
    )

    data = {

        "number":
            number,

        "timestamp_ns":
            timestamp_ns,

        "timestamp":
            timestamp,

        "method":
            request.method,

        "url":
            request.url,

        "resource_type":
            request.resource_type,

        "headers":
            dict(
                request.headers
            ),
    }

    # --------------------------------------------------------
    # REQUEST BODY
    # --------------------------------------------------------

    try:

        post_data = (
            request.post_data
        )

        if post_data:

            data[
                "post_data"
            ] = post_data

            try:

                data[
                    "post_data_json"
                ] = json.loads(
                    post_data
                )

            except Exception:

                pass

    except Exception as exc:

        data[
            "post_data_error"
        ] = repr(exc)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    filename = make_name(
        "REQUEST",
        number,
        request.url,
    )

    output_file = (
        REQUEST_DIR
        / f"{filename}.json"
    )

    try:

        output_file.write_text(

            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),

            encoding="utf-8",
        )

    except Exception as exc:

        print(
            "[REQUEST SAVE ERROR]",
            request.url,
            repr(exc),
        )


# ============================================================
# SAVE RESPONSE
# ============================================================

async def save_response(response):

    global response_counter

    if not is_malanka_url(
        response.url
    ):
        return

    # --------------------------------------------------------
    # READ BODY IMMEDIATELY
    # --------------------------------------------------------

    try:

        body = await response.body()

    except Exception as exc:

        print(
            "[RESPONSE BODY ERROR]",
            response.url,
            repr(exc),
        )

        return

    async with counter_lock:

        response_counter += 1

        number = response_counter

    timestamp_ns = time.time_ns()

    timestamp = (
        datetime.now()
        .isoformat()
    )

    content_type = (
        response.headers
        .get(
            "content-type",
            "",
        )
        .lower()
    )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = {

        "number":
            number,

        "timestamp_ns":
            timestamp_ns,

        "timestamp":
            timestamp,

        "status":
            response.status,

        "status_text":
            response.status_text,

        "url":
            response.url,

        "method":
            response.request.method,

        "resource_type":
            response.request.resource_type,

        "content_type":
            content_type,

        "request_headers":
            dict(
                response.request.headers
            ),

        "response_headers":
            dict(
                response.headers
            ),

        "body_size_bytes":
            len(body),
    }

    filename = make_name(
        "RESPONSE",
        number,
        response.url,
    )

    meta_file = (
        RESPONSE_DIR
        / f"{filename}.meta.json"
    )

    try:

        meta_file.write_text(

            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ),

            encoding="utf-8",
        )

    except Exception as exc:

        print(
            "[META SAVE ERROR]",
            repr(exc),
        )

    # ========================================================
    # DECODE BODY
    # ========================================================

    text = None
    json_data = None

    try:

        decoded = body.decode(
            "utf-8"
        )

        if "\x00" not in decoded:

            text = decoded

    except Exception:

        text = None

    # ========================================================
    # TRY JSON REGARDLESS OF CONTENT-TYPE
    # ========================================================

    if text is not None:

        try:

            json_data = json.loads(
                text
            )

        except Exception:

            json_data = None

    # ========================================================
    # SAVE BODY
    # ========================================================

    if json_data is not None:

        output_file = (
            RESPONSE_DIR
            / f"{filename}.json"
        )

        try:

            output_file.write_text(

                json.dumps(
                    json_data,
                    ensure_ascii=False,
                    indent=2,
                ),

                encoding="utf-8",
            )

        except Exception as exc:

            print(
                "[JSON SAVE ERROR]",
                repr(exc),
            )

    elif text is not None:

        output_file = (
            RESPONSE_DIR
            / f"{filename}.txt"
        )

        try:

            output_file.write_text(
                text,
                encoding="utf-8",
            )

        except Exception as exc:

            print(
                "[TEXT SAVE ERROR]",
                repr(exc),
            )

    else:

        output_file = (
            RESPONSE_DIR
            / f"{filename}.bin"
        )

        try:

            output_file.write_bytes(
                body
            )

        except Exception as exc:

            print(
                "[BINARY SAVE ERROR]",
                repr(exc),
            )


# ============================================================
# SAVE PAGE SNAPSHOT
# ============================================================

async def save_page_snapshot(page):

    global snapshot_counter

    snapshot_counter += 1

    now = datetime.now()

    timestamp = now.strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    try:

        page_text = await page.locator(
            "body"
        ).inner_text()

    except Exception as exc:

        print(
            "[PAGE SNAPSHOT ERROR]",
            repr(exc),
        )

        return

    filename = (
        f"page_text_"
        f"{snapshot_counter:06d}_"
        f"{timestamp}.txt"
    )

    output_file = (
        DEBUG_DIR
        / filename
    )

    try:

        output_file.write_text(
            page_text,
            encoding="utf-8",
        )

        print(
            "[SNAPSHOT]",
            snapshot_counter,
            "->",
            filename,
        )

    except Exception as exc:

        print(
            "[SNAPSHOT SAVE ERROR]",
            repr(exc),
        )


# ============================================================
# SAVE STRUCTURED PAGE INFORMATION
# ============================================================

async def save_page_html(page):

    """
    Save HTML too.

    This is useful because the visible text can contain SOC,
    while the DOM may contain data attributes or station IDs
    that are not obvious from inner_text().
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_file = (
        DEBUG_DIR
        / f"page_{timestamp}.html"
    )

    try:

        html = await page.content()

        output_file.write_text(
            html,
            encoding="utf-8",
        )

    except Exception as exc:

        print(
            "[HTML SAVE ERROR]",
            repr(exc),
        )


# ============================================================
# DISCOVER CLICKABLE ELEMENTS
# ============================================================

async def discover_clickable_elements(page):

    """
    Find likely Malanka map/station elements.

    We do NOT assume one exact CSS class.
    """

    selectors = [

        '[class*="station"]',

        '[class*="charger"]',

        '[class*="location"]',

        '[class*="marker"]',

        '[class*="point"]',

        '[data-testid*="station"]',

        '[data-testid*="charger"]',

        '[data-testid*="location"]',

        '[data-testid*="marker"]',

        '[data-cy*="station"]',

        '[data-cy*="charger"]',

        '[aria-label*="700"]',

    ]

    found = []

    seen = set()

    for selector in selectors:

        try:

            elements = await page.locator(
                selector
            ).all()

        except Exception:

            continue

        for index, element in enumerate(
            elements
        ):

            try:

                if not await element.is_visible():

                    continue

                box = await element.bounding_box()

                if not box:

                    continue

                # Avoid repeatedly returning the
                # exact same element/position.
                key = (
                    round(box["x"]),
                    round(box["y"]),
                    round(box["width"]),
                    round(box["height"]),
                )

                if key in seen:

                    continue

                seen.add(key)

                found.append(
                    (
                        selector,
                        index,
                        element,
                        key,
                    )
                )

            except Exception:

                continue

    return found


# ============================================================
# EXPLORE MAP
# ============================================================

async def explore_map(page):

    print()
    print("=" * 100)
    print("EXPLORING MAP POINTS")
    print("=" * 100)

    elements = (
        await discover_clickable_elements(
            page
        )
    )

    print(
        "Possible clickable elements:",
        len(elements),
    )

    clicked = 0

    for (
        selector,
        index,
        element,
        key,
    ) in elements:

        try:

            if not await element.is_visible():

                continue

            print(
                "[CLICK]",
                selector,
                "#",
                index,
                "position=",
                key,
            )

            await element.click(
                timeout=2500
            )

            clicked += 1

            # Give the frontend time to request
            # station details / SOC information.
            await page.wait_for_timeout(
                CLICK_WAIT_MS
            )

            # Save state immediately after click.
            await save_page_snapshot(
                page
            )

        except Exception as exc:

            print(
                "[CLICK FAILED]",
                selector,
                "#",
                index,
                type(exc).__name__,
            )

    print(
        "Clicked:",
        clicked,
    )

    print("=" * 100)


# ============================================================
# CAPTURE LOOP
# ============================================================

async def capture_loop(page):

    start = time.monotonic()

    iteration = 0

    while True:

        elapsed = (
            time.monotonic()
            - start
        )

        if elapsed >= CAPTURE_SECONDS:

            break

        iteration += 1

        print()
        print("=" * 100)
        print(
            "CAPTURE",
            iteration,
        )

        print(
            "Elapsed:",
            round(elapsed, 1),
            "sec",
        )

        print(
            "Requests:",
            request_counter,
        )

        print(
            "Responses:",
            response_counter,
        )

        print("=" * 100)

        # ----------------------------------------------------
        # Save visible state
        # ----------------------------------------------------

        await save_page_snapshot(
            page
        )

        # Save HTML periodically.
        if iteration % 6 == 1:

            await save_page_html(
                page
            )

        # ----------------------------------------------------
        # Explore points periodically
        # ----------------------------------------------------

        if (
            iteration
            % EXPLORE_EVERY_SNAPSHOTS
            == 0
        ):

            try:

                await explore_map(
                    page
                )

            except Exception as exc:

                print(
                    "[EXPLORE ERROR]",
                    repr(exc),
                )

        # ----------------------------------------------------
        # Wait until next snapshot
        # ----------------------------------------------------

        remaining = (
            CAPTURE_SECONDS
            - (
                time.monotonic()
                - start
            )
        )

        if remaining <= 0:

            break

        await asyncio.sleep(
            min(
                SNAPSHOT_INTERVAL,
                remaining,
            )
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 100)
    print("MALANKA FULL NETWORK + PAGE HISTORY LOGGER")
    print("=" * 100)

    print(
        "SESSION:",
        SESSION_ID,
    )

    print(
        "DEBUG:",
        DEBUG_DIR.resolve(),
    )

    print(
        "CAPTURE:",
        CAPTURE_SECONDS,
        "seconds",
    )

    print(
        "SNAPSHOT:",
        SNAPSHOT_INTERVAL,
        "seconds",
    )

    print()

    # ========================================================
    # AUTH CHECK
    # ========================================================

    if not AUTH_FILE.exists():

        print(
            "❌ AUTH FILE NOT FOUND:"
        )

        print(
            AUTH_FILE
        )

        return

    # ========================================================
    # PLAYWRIGHT
    # ========================================================

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        context = await browser.new_context(

            storage_state=str(
                AUTH_FILE
            ),

            permissions=[
                "geolocation"
            ],

            geolocation={

                "latitude":
                    53.9006,

                "longitude":
                    27.5590,
            },

            viewport={

                "width":
                    1920,

                "height":
                    1080,
            },
        )

        page = await context.new_page()

        # ====================================================
        # NETWORK
        # ====================================================

        def request_handler(
            request
        ):

            create_tracked_task(
                save_request(
                    request
                )
            )

        def response_handler(
            response
        ):

            create_tracked_task(
                save_response(
                    response
                )
            )

        page.on(
            "request",
            request_handler,
        )

        page.on(
            "response",
            response_handler,
        )

        # ====================================================
        # CONSOLE
        # ====================================================

        def console_handler(msg):

            line = (
                f"[{datetime.now().isoformat()}] "
                f"[{msg.type}] "
                f"{msg.text}\n"
            )

            print(
                "[CONSOLE]",
                msg.type,
                msg.text,
            )

            try:

                with open(

                    DEBUG_DIR
                    / "console.log",

                    "a",

                    encoding="utf-8",

                ) as f:

                    f.write(line)

            except Exception:

                pass

        page.on(
            "console",
            console_handler,
        )

        # ====================================================
        # PAGE ERRORS
        # ====================================================

        def page_error_handler(
            exc
        ):

            print(
                "[PAGE ERROR]",
                exc,
            )

            try:

                with open(

                    DEBUG_DIR
                    / "page_errors.log",

                    "a",

                    encoding="utf-8",

                ) as f:

                    f.write(

                        f"[{datetime.now().isoformat()}] "
                        f"{exc}\n"

                    )

            except Exception:

                pass

        page.on(
            "pageerror",
            page_error_handler,
        )

        # ====================================================
        # NAVIGATE
        # ====================================================

        print(
            "Opening Malanka map..."
        )

        try:

            await page.goto(

                MAP_URL,

                wait_until="domcontentloaded",

                timeout=60000,
            )

        except Exception as exc:

            print(
                "PAGE LOAD ERROR:",
                repr(exc),
            )

        print()

        print(
            "URL:",
            page.url,
        )

        try:

            print(
                "TITLE:",
                await page.title(),
            )

        except Exception:

            pass

        # ====================================================
        # INITIAL WAIT
        # ====================================================

        print()
        print("=" * 100)
        print("INITIAL MAP LOAD")
        print("=" * 100)

        # Let initial station requests happen.
        await page.wait_for_timeout(
            10000
        )

        # Save initial state.
        await save_page_snapshot(
            page
        )

        await save_page_html(
            page
        )

        # ====================================================
        # MAIN CAPTURE
        # ====================================================

        print()
        print("=" * 100)
        print("CAPTURING ALL MALANKA TRAFFIC")
        print("=" * 100)

        print(
            "No charger ID filter."
        )

        print(
            "No connector filter."
        )

        print(
            "Multiple page snapshots."
        )

        print(
            "Automatic map exploration."
        )

        print()

        await capture_loop(
            page
        )

        # ====================================================
        # FINAL WAIT
        # ====================================================

        print()
        print(
            "Waiting 5 seconds for remaining responses..."
        )

        await page.wait_for_timeout(
            5000
        )

        # ====================================================
        # DRAIN ALL SAVE TASKS
        # ====================================================

        await drain_pending_tasks()

        # ====================================================
        # FINAL PAGE SNAPSHOT
        # ====================================================

        await save_page_snapshot(
            page
        )

        # ====================================================
        # SUMMARY
        # ====================================================

        summary = {

            "session_id":
                SESSION_ID,

            "created_at":
                datetime.now()
                .isoformat(),

            "map_url":
                MAP_URL,

            "auth_file":
                str(
                    AUTH_FILE
                ),

            "requests_saved":
                request_counter,

            "responses_saved":
                response_counter,

            "page_snapshots":
                snapshot_counter,

            "capture_seconds":
                CAPTURE_SECONDS,

            "snapshot_interval":
                SNAPSHOT_INTERVAL,

            "automatic_exploration":
                True,

            "debug_directory":
                str(
                    DEBUG_DIR.resolve()
                ),

            "capture_mode":
                "ALL_MALANKA_TRAFFIC",

        }

        summary_file = (
            DEBUG_DIR
            / "summary.json"
        )

        summary_file.write_text(

            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            ),

            encoding="utf-8",
        )

        # ====================================================
        # FINISHED
        # ====================================================

        print()
        print("=" * 100)
        print("CAPTURE FINISHED")
        print("=" * 100)

        print(
            "Session:",
            SESSION_ID,
        )

        print(
            "Requests:",
            request_counter,
        )

        print(
            "Responses:",
            response_counter,
        )

        print(
            "Page snapshots:",
            snapshot_counter,
        )

        print(
            "Directory:",
            DEBUG_DIR.resolve(),
        )

        print("=" * 100)

        input(
            "\nPress Enter to close browser..."
        )

        await browser.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )