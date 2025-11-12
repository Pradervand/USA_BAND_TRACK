# -*- coding: utf-8 -*-
"""
Concerts-Metal crawler (Spyder-stable version)
Author: antony.praderva
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import fetch_shows

# ---- CONFIG ----
BASE_URL = "https://www.concerts-metal.com"
STATES = ["CA", "AZ", "UT", "CO", "WY", "MT", "WA"]
TIMEOUT = 10
YEAR_FILTER = "2026"
TEST_MODE = False   # ✅ True = print only, False = save to DB
RETRY_LIMIT = 2    # number of retries on fetch failure
THROTTLE_DELAY = 1.0  # seconds between event page fetches
# ----------------


# =====================================================
# FETCH FUNCTIONS (with retry + robust charset fallback)
# =====================================================
async def fetch(session, url, attempt=0):
    """Fetch page with retries, full debug, and decoding fallbacks."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with session.get(url, headers=headers, timeout=TIMEOUT) as r:
            print(f"🌐 Fetching: {url} -> {r.status}")
            if r.status != 200:
                return None

            raw = await r.read()
            for enc in ("utf-8", "cp1252", "latin-1"):
                try:
                    text = raw.decode(enc)
                    print(f"   ✅ Decoded {len(raw)} bytes with {enc}")
                    return text
                except UnicodeDecodeError:
                    continue
            # fallback with replacement
            text = raw.decode("utf-8", errors="replace")
            print(f"   ⚠️ Used utf-8 with replacement characters for {url}")
            return text

    except asyncio.TimeoutError:
        print(f"   ❌ Timeout while fetching {url}")
    except aiohttp.ClientError as e:
        print(f"   ❌ Client error for {url}: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error for {url}: {type(e).__name__}: {e}")

    if attempt < RETRY_LIMIT:
        await asyncio.sleep(2)
        print(f"   🔁 Retrying {url} (attempt {attempt + 1})")
        return await fetch(session, url, attempt + 1)

    print(f"   🚫 Gave up on {url} after {attempt + 1} attempts")
    return None


# ========================
# PARSING EVENT GENRE
# ========================
async def fetch_genre(session, event_url):
    """Fetch genre info from an event page."""
    html = await fetch(session, event_url)
    await asyncio.sleep(THROTTLE_DELAY)
    if not html:
        return "Unknown"

    soup = BeautifulSoup(html, "html.parser")

    # Try carousel first
    genre = None
    divs = soup.find_all("div", class_="carousel-item")
    for div in divs:
        text = div.get_text(" ", strip=True)
        if text and 3 < len(text) < 60 and not text.lower().startswith("202"):
            genre = text
            break

    # Fallback text search
    if not genre:
        for tag in soup.find_all(["p", "span", "div"]):
            txt = tag.get_text(" ", strip=True)
            if any(k in txt.lower() for k in ["metal", "core", "rock", "punk", "doom", "folk"]):
                genre = txt
                break

    return genre or "Unknown"


# ========================
# PARSING STATE PAGES
# ========================
async def parse_state_page(session, state):
    """Parse one state page and extract all concerts."""
    url = f"{BASE_URL}/next_US-{state}_{YEAR_FILTER}.html"
    html = await fetch(session, url)
    if not html:
        print(f"⚠️ No HTML for {state}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    shows = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("concert_-_"):
            continue

        prev_text = a.previous_sibling
        if not prev_text:
            continue
        prev_text = str(prev_text).strip()
        if "/" not in prev_text:
            continue

        try:
            date_str = prev_text.split()[0]
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            continue

        artist = a.get_text(strip=True)
        after_text = a.next_sibling
        city = venue = "Unknown"

        if after_text:
            after_text = after_text.replace("@", "").strip()
            parts = [p.strip() for p in after_text.split(",")]
            if len(parts) >= 1:
                city = parts[0]
            if len(parts) >= 2:
                venue = parts[1]

        eid = "cm_" + href.split("-")[-1].replace(".html", "")
        shows.append({
            "id": eid,
            "artist": artist,
            "venue": venue,
            "city": city,
            "state": state,
            "date": date_obj.strftime("%Y-%m-%d"),
            "url": f"{BASE_URL}/{href}",
            "source": "Concerts-Metal",
        })

    print(f"🎵 Parsed {len(shows)} shows for {state}")
    return shows


# ========================
# MAIN CRAWLER LOGIC
# ========================
async def crawl_concertsmetal_async():
    """Main async crawler entrypoint."""
    if not TEST_MODE:
        fetch_shows.init_db()

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        all_events = []
        for st in STATES:
            print(f"\n🔍 Parsing {st} ...")
            st_events = await parse_state_page(session, st)
            all_events.extend(st_events)

        print(f"\n🎸 Total found before filtering: {len(all_events)} shows")

        # Fetch genres
        tasks, mapping = [], []
        for e in all_events:
            if TEST_MODE or not fetch_shows.already_seen(e["id"]):
                tasks.append(fetch_genre(session, e["url"]))
                mapping.append(e)

        genres = await asyncio.gather(*tasks, return_exceptions=True)

        added = 0
        for e, genre in zip(mapping, genres):
            e["genre"] = genre if isinstance(genre, str) else "Unknown"
            if TEST_MODE:
                print(f"{e['date']} | {e['artist']} | {e['city']} | {e['venue']} | {e['genre']}")
            else:
                fetch_shows.save_event(e)
                added += 1

    if TEST_MODE:
        print(f"\n🧪 TEST MODE: Parsed {len(mapping)} events (no DB write).")
    else:
        print(f"✅ Added {added} new events from Concerts-Metal.")
    return added


def crawl_concertsmetal():
    """Spyder-safe wrapper for async crawler."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            return asyncio.ensure_future(crawl_concertsmetal_async())
    except RuntimeError:
        pass

    return asyncio.run(crawl_concertsmetal_async())


if __name__ == "__main__":
    crawl_concertsmetal()
