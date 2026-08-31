
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

AUTH_FILE = Path(r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\auth\malanka.json")

MAP_URL = "https://customer.malankabn.by/map/"

TARGET = '700202'

BASE_DEBUG_DIR = Path(
    r"C:\Users\1\PycharmProjects\ev_charge_helper2\data\malanka_debug"
)

# ============================================================
# TIMESTAMPED SESSION DIRECTORY
# ============================================================

SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

DEBUG_DIR = BASE_DEBUG_DIR / SESSION_ID
REQUEST_DIR = DEBUG_DIR / "requests"
RESPONSE_DIR = DEBUG_DIR / "responses"

REQUEST_DIR.mkdir(parents=True, exist_ok=True)
RESPONSE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# GLOBALS
# ============================================================

request_counter = 0
response_counter = 0

counter_lock = asyncio.Lock()


# ============================================================
# HELPERS
# ============================================================

def safe_filename(value: str, max_length: int = 180) -> str:
    value = re.sub(r"[^a-zA-Z0-9.\-_]+", "_", value)
    value = value.strip("._")

    if not value:
        value = "unknown"

    return value[:max_length]


def is_malanka_url(url: str) -> bool:
    """
    Capture ALL Malanka traffic.

    We only exclude obvious third-party resources such as:
    - Yandex
    - Google
    - analytics
    - fonts/images/etc are still allowed if served by Malanka
    """

    try:
        host = urlparse(url).netloc.lower()

        return (
            "malankabn.by" in host
            and "yandex" not in host
        )

    except Exception:
        return False


def contains_target(text: str) -> bool:
    return TARGET.lower() in text.lower()


def make_name(prefix: str, number: int, url: str) -> str:
    parsed = urlparse(url)

    path = parsed.path or "root"

    return safe_filename(
        f"{number:06d}_{prefix}_{parsed.netloc}_{path}"
    )


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

    data = {
        "number": number,
        "timestamp_ns": timestamp_ns,
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "url": request.url,
        "resource_type": request.resource_type,
        "headers": dict(request.headers),
    }

    # --------------------------------------------------------
    # POST / PUT / PATCH body
    # --------------------------------------------------------

    try:
        post_data = request.post_data

        if post_data:
            data["post_data"] = post_data

            try:
                data["post_data_json"] = json.loads(post_data)
            except Exception:
                pass

    except Exception as exc:
        data["post_data_error"] = repr(exc)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    filename = make_name(
        "REQUEST",
        number,
        request.url,
    )

    output_file = REQUEST_DIR / f"{filename}.json"

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
            f"[REQUEST SAVE ERROR]\n"
            f"{request.url}\n"
            f"{exc}"
        )


# ============================================================
# SAVE RESPONSE
# ============================================================

async def save_response(response):
    global response_counter

    if not is_malanka_url(response.url):
        return

    # --------------------------------------------------------
    # Read body immediately
    # --------------------------------------------------------

    try:
        body = await response.body()

    except Exception as exc:
        print(
            f"[RESPONSE BODY ERROR]\n"
            f"{response.url}\n"
            f"{exc}"
        )
        return

    async with counter_lock:
        response_counter += 1
        number = response_counter

    timestamp_ns = time.time_ns()

    content_type = (
        response.headers
        .get("content-type", "")
        .lower()
    )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = {
        "number": number,
        "timestamp_ns": timestamp_ns,
        "timestamp": datetime.now().isoformat(),

        "status": response.status,
        "status_text": response.status_text,

        "url": response.url,

        "method": response.request.method,
        "resource_type": response.request.resource_type,

        "content_type": content_type,

        "request_headers": dict(
            response.request.headers
        ),

        "response_headers": dict(
            response.headers
        ),
    }

    filename = make_name(
        "RESPONSE",
        number,
        response.url,
    )

    meta_file = RESPONSE_DIR / f"{filename}.meta.json"

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
            f"[META SAVE ERROR] {exc}"
        )

    # ========================================================
    # DECODE BODY
    # ========================================================

    text = None
    json_data = None

    is_json = (
        "application/json" in content_type
        or "application/problem+json" in content_type
        or content_type.endswith("+json")
    )

    if is_json:

        try:
            text = body.decode("utf-8")

            try:
                json_data = json.loads(text)

            except Exception:
                json_data = None

        except Exception:
            text = None

    else:

        # Try UTF-8 for ANY response.
        try:
            decoded = body.decode("utf-8")

            if "\x00" not in decoded:
                text = decoded

        except Exception:
            text = None

    # ========================================================
    # SAVE BODY
    # ========================================================

    if json_data is not None:

        output_file = RESPONSE_DIR / f"{filename}.json"

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
                f"[JSON SAVE ERROR] {exc}"
            )

    elif text is not None:

        output_file = RESPONSE_DIR / f"{filename}.txt"

        try:
            output_file.write_text(
                text,
                encoding="utf-8",
            )

        except Exception as exc:
            print(
                f"[TEXT SAVE ERROR] {exc}"
            )

    else:

        output_file = RESPONSE_DIR / f"{filename}.bin"

        try:
            output_file.write_bytes(body)

        except Exception as exc:
            print(
                f"[BINARY SAVE ERROR] {exc}"
            )

    # ========================================================
    # TARGET DETECTION
    # ========================================================

    searchable_text = ""

    if json_data is not None:

        try:
            searchable_text = json.dumps(
                json_data,
                ensure_ascii=False,
            )

        except Exception:
            searchable_text = ""

    elif text is not None:

        searchable_text = text

    if contains_target(searchable_text):

        print()
        print("=" * 100)
        print("🔥🔥🔥 TARGET FOUND 🔥🔥🔥")
        print("=" * 100)

        print("TARGET :", TARGET)
        print("STATUS :", response.status)
        print("METHOD :", response.request.method)
        print("URL    :", response.url)
        print("FILE   :", output_file)
        print("META   :", meta_file)

        print("=" * 100)
        print()

        # ----------------------------------------------------
        # Save dedicated copy
        # ----------------------------------------------------

        target_file = (
            DEBUG_DIR
            / f"FOUND_{TARGET}_{number}_{timestamp_ns}.json"
        )

        try:

            if json_data is not None:

                target_file.write_text(
                    json.dumps(
                        json_data,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

            elif text is not None:

                target_file.write_text(
                    text,
                    encoding="utf-8",
                )

            else:

                target_file.write_bytes(body)

        except Exception as exc:

            print(
                f"[TARGET COPY ERROR] {exc}"
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 100)
    print("MALANKA FULL NETWORK DEBUG LOGGER")
    print("=" * 100)

    print("Session   :", SESSION_ID)
    print("Auth file :", AUTH_FILE)
    print("Map URL   :", MAP_URL)
    print("Target    :", TARGET)
    print("Debug dir :", DEBUG_DIR.resolve())

    print()

    if not AUTH_FILE.exists():

        print("❌ AUTH FILE NOT FOUND")
        print(AUTH_FILE)

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
        # NETWORK
        # ====================================================

        page.on(
            "request",
            lambda request:
                asyncio.create_task(
                    save_request(request)
                )
        )

        page.on(
            "response",
            lambda response:
                asyncio.create_task(
                    save_response(response)
                )
        )

        # ====================================================
        # CONSOLE
        # ====================================================

        def console_handler(msg):

            try:

                print(
                    f"[BROWSER CONSOLE {msg.type}] "
                    f"{msg.text}"
                )

                with open(
                    DEBUG_DIR / "console.log",
                    "a",
                    encoding="utf-8",
                ) as f:

                    f.write(
                        f"[{datetime.now().isoformat()}] "
                        f"[{msg.type}] "
                        f"{msg.text}\n"
                    )

            except Exception:
                pass

        page.on(
            "console",
            console_handler
        )

        # ====================================================
        # PAGE ERRORS
        # ====================================================

        def page_error_handler(exc):

            print(
                "\n[BROWSER PAGE ERROR]"
            )

            print(exc)

            try:

                with open(
                    DEBUG_DIR / "page_errors.log",
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
            page_error_handler
        )

        # ====================================================
        # NAVIGATE
        # ====================================================

        print()
        print("Opening Malanka map...")
        print()

        try:

            await page.goto(
                MAP_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

        except Exception as exc:

            print()
            print("⚠️ PAGE LOAD ERROR")
            print(exc)
            print()

        # ====================================================
        # PAGE INFO
        # ====================================================

        print()
        print("=" * 100)
        print("PAGE INFORMATION")
        print("=" * 100)

        print(
            "URL:",
            page.url
        )

        try:

            print(
                "TITLE:",
                await page.title()
            )

        except Exception:
            pass

        print("=" * 100)
        print()

        # ====================================================
        # WAIT FOR API TRAFFIC
        # ====================================================

        print(
            "Waiting 60 seconds for network traffic..."
        )

        await page.wait_for_timeout(
            60000
        )

        # ====================================================
        # PAGE TEXT
        # ====================================================

        print()
        print("=" * 100)
        print("SAVING PAGE TEXT")
        print("=" * 100)

        try:

            page_text = await page.locator(
                "body"
            ).inner_text()

            page_text_file = (
                DEBUG_DIR
                / "page_text.txt"
            )

            page_text_file.write_text(
                page_text,
                encoding="utf-8",
            )

            print(
                "Saved:",
                page_text_file
            )

        except Exception as exc:

            print(
                "Could not read page text:",
                exc
            )

        # ====================================================
        # FINAL NETWORK DRAIN
        # ====================================================

        print()
        print(
            "Waiting 15 seconds for remaining responses..."
        )

        await page.wait_for_timeout(
            15000
        )

        # ====================================================
        # SUMMARY
        # ====================================================

        summary = {

            "session_id": SESSION_ID,

            "target": TARGET,

            "map_url": MAP_URL,

            "auth_file": str(
                AUTH_FILE
            ),

            "requests_saved": request_counter,

            "responses_saved": response_counter,

            "debug_directory": str(
                DEBUG_DIR.resolve()
            ),

            "created_at": datetime.now().isoformat(),
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
        print("DEBUG CAPTURE FINISHED")
        print("=" * 100)

        print(
            "Session:",
            SESSION_ID
        )

        print(
            "Requests:",
            request_counter
        )

        print(
            "Responses:",
            response_counter
        )

        print(
            "Directory:",
            DEBUG_DIR.resolve()
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
    asyncio.run(main())

