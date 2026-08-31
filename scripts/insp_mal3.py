import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


# ============================================================
# CONFIG
# ============================================================

AUTH_FILE = Path("data/auth/malanka.json")

MAP_URL = "https://customer.malankabn.by/map/"

TARGET = "700315"

DEBUG_DIR = Path("data/malanka_debug")
REQUEST_DIR = DEBUG_DIR / "requests"
RESPONSE_DIR = DEBUG_DIR / "responses"

REQUEST_DIR.mkdir(parents=True, exist_ok=True)
RESPONSE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

counter = 0
counter_lock = asyncio.Lock()


def safe_filename(value: str, max_length: int = 180) -> str:
    """
    Convert URL/path into a Windows-safe filename.
    """
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
    value = value.strip("._")

    if not value:
        value = "unknown"

    return value[:max_length]


def is_malanka_url(url: str) -> bool:
    """
    We want Malanka API/backend traffic.

    We intentionally ignore:
      - Yandex map tiles
      - CSS
      - JS
      - fonts
      - images
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


def looks_like_api(url: str) -> bool:
    """
    Additional filter for API/backend requests.

    The first check is intentionally broad so we don't miss
    undocumented endpoints.
    """

    if not is_malanka_url(url):
        return False

    url_lower = url.lower()

    api_words = [
        "/api/",
        "apigateway",
        "central-system",
        "marketing",
        "my-garage",
        "reservation",
        "connector",
        "session",
        "device",
        "charger",
        "station",
        "point",
        "transaction",
        "status",
        "user",
    ]

    return any(word in url_lower for word in api_words)


def contains_target(text: str) -> bool:
    return TARGET.lower() in text.lower()


# ============================================================
# SAVE REQUEST
# ============================================================

async def save_request(request):
    """
    Save every interesting Malanka request.

    This includes:
      - URL
      - HTTP method
      - request headers
      - POST/PUT/PATCH body
    """

    if not looks_like_api(request.url):
        return

    timestamp = time.time_ns()

    parsed = urlparse(request.url)

    filename_base = safe_filename(
        f"{request.method}_{parsed.path}_{timestamp}"
    )

    data = {
        "timestamp_ns": timestamp,
        "method": request.method,
        "url": request.url,
        "resource_type": request.resource_type,
        "headers": dict(request.headers),
    }

    try:
        post_data = request.post_data

        if post_data:
            data["post_data"] = post_data

            # Try to parse JSON request bodies.
            try:
                data["post_data_json"] = json.loads(post_data)
            except Exception:
                pass

    except Exception as exc:
        data["post_data_error"] = repr(exc)

    output_file = REQUEST_DIR / f"{filename_base}.json"

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
            f"[REQUEST SAVE ERROR] {request.url}\n"
            f"{exc}"
        )


# ============================================================
# SAVE RESPONSE
# ============================================================

async def save_response(response):
    """
    Save every interesting Malanka response.

    JSON responses:
        *.json
        *.meta.json

    Non-JSON responses:
        *.txt or *.bin
        *.meta.json

    If TARGET is found, print a prominent message.
    """

    global counter

    if not looks_like_api(response.url):
        return

    try:
        body = await response.body()
    except Exception as exc:
        print(
            f"[RESPONSE BODY ERROR] {response.url}\n"
            f"{exc}"
        )
        return

    async with counter_lock:
        counter += 1
        number = counter

    timestamp = time.time_ns()

    parsed = urlparse(response.url)

    filename_base = safe_filename(
        f"{number:05d}_{response.status}_{parsed.path}_{timestamp}"
    )

    content_type = (
        response.headers.get("content-type", "")
        .lower()
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = {
        "number": number,
        "timestamp_ns": timestamp,
        "status": response.status,
        "status_text": response.status_text,
        "url": response.url,
        "method": response.request.method,
        "resource_type": response.request.resource_type,
        "content_type": content_type,
        "request_headers": dict(response.request.headers),
        "response_headers": dict(response.headers),
    }

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    meta_file = RESPONSE_DIR / f"{filename_base}.meta.json"

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
        print(f"[META SAVE ERROR] {exc}")

    # --------------------------------------------------------
    # Decode response
    # --------------------------------------------------------

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

        # Try UTF-8 anyway.
        try:
            decoded = body.decode("utf-8")

            # Only treat it as text if it looks reasonably textual.
            if "\x00" not in decoded:
                text = decoded

        except Exception:
            text = None

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    if json_data is not None:

        output_file = RESPONSE_DIR / f"{filename_base}.json"

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
            print(f"[JSON SAVE ERROR] {exc}")

    # --------------------------------------------------------
    # Save text
    # --------------------------------------------------------

    elif text is not None:

        output_file = RESPONSE_DIR / f"{filename_base}.txt"

        try:
            output_file.write_text(
                text,
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[TEXT SAVE ERROR] {exc}")

    # --------------------------------------------------------
    # Save binary
    # --------------------------------------------------------

    else:

        output_file = RESPONSE_DIR / f"{filename_base}.bin"

        try:
            output_file.write_bytes(body)
        except Exception as exc:
            print(f"[BINARY SAVE ERROR] {exc}")

    # --------------------------------------------------------
    # Search for charger
    # --------------------------------------------------------

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
        print("🔥🔥🔥 FOUND TARGET CHARGER 🔥🔥🔥")
        print("=" * 100)
        print("TARGET :", TARGET)
        print("STATUS :", response.status)
        print("METHOD :", response.request.method)
        print("URL    :", response.url)
        print("FILE   :", output_file)
        print("META   :", meta_file)
        print("=" * 100)
        print()

        # Save a dedicated copy so it is extremely easy to find.
        target_file = DEBUG_DIR / (
            f"FOUND_{TARGET}_{number}_{timestamp}.json"
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
            print(f"[TARGET COPY ERROR] {exc}")


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 100)
    print("MALANKA API DEBUG LOGGER")
    print("=" * 100)

    print("Auth file :", AUTH_FILE)
    print("Map URL   :", MAP_URL)
    print("Target    :", TARGET)
    print("Debug dir :", DEBUG_DIR)
    print()

    if not AUTH_FILE.exists():

        print("❌ AUTH FILE NOT FOUND")
        print()
        print("Expected:")
        print(AUTH_FILE)
        print()

        return

    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        context = await browser.new_context(
            storage_state=str(AUTH_FILE),

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

        # ----------------------------------------------------
        # Network listeners
        # ----------------------------------------------------

        def request_handler(request):

            asyncio.create_task(
                save_request(request)
            )

        def response_handler(response):

            asyncio.create_task(
                save_response(response)
            )

        page.on(
            "request",
            request_handler
        )

        page.on(
            "response",
            response_handler
        )

        # ----------------------------------------------------
        # Console logging
        # ----------------------------------------------------

        def console_handler(msg):

            try:
                print(
                    f"[BROWSER CONSOLE {msg.type}] "
                    f"{msg.text}"
                )
            except Exception:
                pass

        page.on(
            "console",
            console_handler
        )

        # ----------------------------------------------------
        # Page errors
        # ----------------------------------------------------

        def page_error_handler(exc):

            print(
                "\n[BROWSER PAGE ERROR]"
            )
            print(exc)
            print()

        page.on(
            "pageerror",
            page_error_handler
        )

        # ----------------------------------------------------
        # Navigate
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Basic information
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Wait for network traffic
        # ----------------------------------------------------

        print(
            "Waiting 30 seconds for API traffic..."
        )

        await page.wait_for_timeout(30000)

        # ----------------------------------------------------
        # Print page text
        # ----------------------------------------------------

        print()
        print("=" * 100)
        print("PAGE TEXT")
        print("=" * 100)

        try:

            page_text = await page.locator(
                "body"
            ).inner_text()

            print(
                page_text[:30000]
            )

            # Save page text too.
            (
                DEBUG_DIR / "page_text.txt"
            ).write_text(
                page_text,
                encoding="utf-8",
            )

        except Exception as exc:

            print(
                "Could not read page text:",
                exc
            )

        print("=" * 100)

        # ----------------------------------------------------
        # Give asynchronous response handlers time to finish
        # ----------------------------------------------------

        print()
        print(
            "Waiting 10 more seconds for response files..."
        )

        await page.wait_for_timeout(10000)

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary = {
            "target": TARGET,
            "map_url": MAP_URL,
            "auth_file": str(AUTH_FILE),
            "responses_saved": counter,
            "debug_directory": str(DEBUG_DIR.resolve()),
        }

        (
            DEBUG_DIR / "summary.json"
        ).write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print()
        print("=" * 100)
        print("DEBUG CAPTURE FINISHED")
        print("=" * 100)
        print(
            "Responses saved:",
            counter
        )
        print(
            "Debug directory:",
            DEBUG_DIR.resolve()
        )
        print()
        print(
            f"Search for {TARGET} in:"
        )
        print(
            DEBUG_DIR.resolve()
        )
        print("=" * 100)

        # ----------------------------------------------------
        # Keep browser open
        # ----------------------------------------------------

        input(
            "\nPress Enter to close browser..."
        )

        await browser.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
