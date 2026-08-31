
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


# ============================================================
# NEW TIMESTAMPED SESSION
# ============================================================

SESSION_ID = datetime.now().strftime(
    "%Y%m%d_%H%M%S_%f"
)

DEBUG_DIR = BASE_DEBUG_DIR / SESSION_ID

REQUEST_DIR = DEBUG_DIR / "requests"
RESPONSE_DIR = DEBUG_DIR / "responses"

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

counter_lock = asyncio.Lock()

# IMPORTANT:
# Keep references to every asynchronous save operation.
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
    SAVE ALL traffic belonging to Malanka.

    No API endpoint whitelist here.

    This is important because an undocumented endpoint
    containing SOC/charger/session information might not
    contain words like /api/, charger, connector, etc.
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
        f"{number:08d}_{prefix}_"
        f"{parsed.netloc}_{path}"
    )


# ============================================================
# TASK TRACKING
# ============================================================

def create_tracked_task(coro):
    """
    Create an asyncio task and keep it alive until finished.

    This prevents response files from being lost when the
    browser closes immediately after the last request.
    """

    task = asyncio.create_task(coro)

    pending_tasks.add(task)

    def done_callback(t):

        pending_tasks.discard(t)

        try:
            t.result()
        except Exception as exc:
            print(
                "[BACKGROUND TASK ERROR]",
                repr(exc),
            )

    task.add_done_callback(done_callback)

    return task


async def drain_pending_tasks():
    """
    Wait until all currently scheduled request/response
    saving tasks have finished.
    """

    if not pending_tasks:
        return

    print()
    print("=" * 100)
    print("DRAINING PENDING SAVE TASKS")
    print("=" * 100)

    while pending_tasks:

        tasks = list(pending_tasks)

        print(
            "Pending save tasks:",
            len(tasks),
        )

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        await asyncio.sleep(0.1)

    print(
        "All network files saved."
    )

    print("=" * 100)


# ============================================================
# SAVE REQUEST
# ============================================================

async def save_request(request):

    global request_counter

    if not is_malanka_url(request.url):
        return

    async with counter_lock:

        request_counter += 1

        number = request_counter

    timestamp_ns = time.time_ns()

    timestamp = datetime.now().isoformat()

    data = {

        "number": number,

        "timestamp_ns": timestamp_ns,

        "timestamp": timestamp,

        "method": request.method,

        "url": request.url,

        "resource_type": request.resource_type,

        "headers": dict(
            request.headers
        ),
    }

    # --------------------------------------------------------
    # REQUEST BODY
    # --------------------------------------------------------

    try:

        post_data = request.post_data

        if post_data:

            data["post_data"] = post_data

            try:

                data["post_data_json"] = (
                    json.loads(post_data)
                )

            except Exception:

                pass

    except Exception as exc:

        data["post_data_error"] = repr(exc)

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

    if not is_malanka_url(response.url):
        return

    # --------------------------------------------------------
    # READ BODY
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

    timestamp = datetime.now().isoformat()

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

        "number": number,

        "timestamp_ns": timestamp_ns,

        "timestamp": timestamp,

        "status": response.status,

        "status_text": response.status_text,

        "url": response.url,

        "method": response.request.method,

        "resource_type": (
            response.request.resource_type
        ),

        "content_type": content_type,

        "request_headers": dict(
            response.request.headers
        ),

        "response_headers": dict(
            response.headers
        ),

        "body_size_bytes": len(body),
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
    # DECODE
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
# MAIN
# ============================================================

async def main():

    print("=" * 100)
    print("MALANKA FULL NETWORK LOGGER")
    print("=" * 100)

    print(
        "SESSION:",
        SESSION_ID,
    )

    print(
        "DEBUG:",
        DEBUG_DIR.resolve(),
    )

    print()

    if not AUTH_FILE.exists():

        print(
            "AUTH FILE NOT FOUND:"
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
                "latitude": 53.9006,
                "longitude": 27.5590,
            },

            viewport={
                "width": 1920,
                "height": 1080,
            },
        )

        page = await context.new_page()

        # ====================================================
        # NETWORK HANDLERS
        # ====================================================

        def request_handler(request):

            create_tracked_task(
                save_request(request)
            )

        def response_handler(response):

            create_tracked_task(
                save_response(response)
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
                    DEBUG_DIR / "console.log",
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

        def page_error_handler(exc):

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
                exc,
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
        # CAPTURE PERIOD
        # ====================================================

        print()
        print("=" * 100)
        print("CAPTURING ALL MALANKA TRAFFIC")
        print("=" * 100)

        print(
            "Duration: 60 seconds"
        )

        print(
            "Nothing is filtered by charger ID."
        )

        print(
            "Nothing is filtered by connector."
        )

        print()

        await page.wait_for_timeout(
            60000
        )

        # ====================================================
        # PAGE TEXT
        # ====================================================

        try:

            page_text = await page.locator(
                "body"
            ).inner_text()

            (
                DEBUG_DIR
                / "page_text.txt"
            ).write_text(
                page_text,
                encoding="utf-8",
            )

            print(
                "Saved page_text.txt"
            )

        except Exception as exc:

            print(
                "PAGE TEXT ERROR:",
                exc,
            )

        # ====================================================
        # NETWORK DRAIN
        # ====================================================

        await page.wait_for_timeout(
            3000
        )

        await drain_pending_tasks()

        # ====================================================
        # SUMMARY
        # ========================================================

        summary = {

            "session_id":
                SESSION_ID,

            "created_at":
                datetime.now().isoformat(),

            "map_url":
                MAP_URL,

            "auth_file":
                str(AUTH_FILE),

            "requests_saved":
                request_counter,

            "responses_saved":
                response_counter,

            "debug_directory":
                str(
                    DEBUG_DIR.resolve()
                ),

            "capture_mode":
                "ALL_MALANKA_TRAFFIC",
        }

        (
            DEBUG_DIR
            / "summary.json"
        ).write_text(
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

