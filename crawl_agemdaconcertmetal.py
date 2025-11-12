# -*- coding: utf-8 -*-
"""
Concerts-Metal crawler (Streamlit + Spyder stable version)
Author: antony.praderva
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import fetch_shows
import pandas as pd
import nest_asyncio

# ---- CONFIG ----
BASE_URL = "https://www.concerts-metal.com"
STATES = ["CA", "AZ", "UT", "CO", "WY", "MT", "WA"]
TIMEOUT = 10
YEAR_FILTER = "2026"
TEST_MODE = False
RETRY_LIMIT = 2
THROTTLE_DELAY = 1.0
# ----------------


# =============================
# HTTP FETCH WITH RETRIES
# =============================
async def fetch(session, url, attempt=0):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with session.get(url, headers=headers, timeout=TIMEOUT) as r:
            if r.status != 200:
                return None
            raw = await r.read()
            for enc in ("utf-8", "cp1252", "latin-1"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
    except Exception:
        if attempt < RETRY_LIMIT:
            await asyncio.sleep(2)
            return await fetch(session, url, attempt + 1)
    return None


# =============================
# FETCH DETAILS (GENRE + IMAGE)
# =============================
async def fetch_details(session, event_url):
    """Fetch genre + image from individual gig page."""
    html = await fetch(session, event_url)
    await asyncio.sleep(THROTTLE_DELAY)
    if not html:
        return {"Genre": "Unknown", "Image": ""}

    soup = BeautifulSoup(html, "html.parser")

    # --- Genre ---
    genre = "Unknown"
    for div in soup.find_all("div", itemtype="https://schema.org/MusicGroup"):
        txt = div.get_text(" ", strip=True)
        if "-" in txt:
            genre = txt.split("-")[-1].strip()
            break

    # --- Image ---
    image_meta = soup.find("meta", {"property": "og:image"})
    image_url = image_meta["content"].strip() if image_meta else ""

    return {"Genre": genre, "Image": image_url}


# =============================
# PARSE STATE PAGE
# =============================
async def parse_state_page(session, state):
    """Parse one state page and extract all concerts."""
    url = f"{BASE_URL}/next_US-{state}_{YEAR_FILTER}.html"
    html = await fetch(session, url)
    if not html:
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

        # placeholders for later
        genre = "Unknown"
        image_url = ""

        eid = "cm_" + href.split("-")[-1].replace(".html", "")
        shows.append({
            "id": eid,
            "artist": artist,
            "genre": genre,
            "venue": venue,
            "city": city,
            "state": state,
            "date": date_obj.strftime("%Y-%m-%d"),
            "url": f"{BASE_URL}/{href}",
            "source": "Concerts-Metal",
            "image": image_url,
        })

    return shows


# =============================
# MAIN ASYNC CRAWLER
# =============================
async def crawl_concertsmetal_async():
    if not TEST_MODE:
        fetch_shows.init_db()

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        all_events = []
        for st in STATES:
            state_events = await parse_state_page(session, st)
            all_events.extend(state_events)

        # Fetch genre + image for each event
        tasks, mapping = [], []
        for e in all_events:
            tasks.append(fetch_details(session, e["url"]))  # ✅ lowercase
            mapping.append(e)

        details = await asyncio.gather(*tasks, return_exceptions=True)

        events = []
        for e, d in zip(mapping, details):
            if isinstance(d, dict):
                e["genre"] = d["Genre"]
                e["image"] = d["Image"]
            else:
                e["genre"], e["image"] = "Unknown", ""
            events.append(e)

        if TEST_MODE:
            df = pd.DataFrame(events, columns=[
                "artist", "genre", "venue", "city", "state", "date", "url", "source", "image"
            ])
            print("\n🧪 TEST MODE — Preview table:\n")
            print(df.to_string(index=False))
        else:
            for e in events:
                fetch_shows.save_event(e)

    return len(events)


# =============================
# WRAPPER FOR STREAMLIT SAFETY
# =============================
def crawl_concertsmetal():
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            return asyncio.ensure_future(crawl_concertsmetal_async())
    except RuntimeError:
        pass
    nest_asyncio.apply()
    return asyncio.get_event_loop().run_until_complete(crawl_concertsmetal_async())


if __name__ == "__main__":
    crawl_concertsmetal()
