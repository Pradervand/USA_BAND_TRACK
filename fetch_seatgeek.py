# -*- coding: utf-8 -*-
"""
SeatGeek API Fetcher (Smart Genre + Deduplication)
Author: antony.praderva
"""

import os
import re
import time
import requests
from fetch_shows import save_event, already_seen, init_db, STATES

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
try:
    import streamlit as st
    SEATGEEK_ID = st.secrets.get("SEATGEEK_ID", None)
except Exception:
    SEATGEEK_ID = os.getenv("SEATGEEK_ID", None)

if not SEATGEEK_ID:
    SEATGEEK_ID = "NTQzNDc1Njl8MTc2Mjk2MTcxMS43ODQwNzM4"  # fallback for local test

BASE_URL = "https://api.seatgeek.com/2/events"
START_DATE = "2026-07-01"
END_DATE = "2026-07-31"

TARGET_GENRES = [
    "metal", "heavy metal", "hard rock", "punk", "emo",
    "industrial", "goth", "darkwave", "rock", "alternative", "indie"
]

# Patterns to refine "Rock"/"Alternative" using keywords in title or band name
SMART_KEYWORDS = {
    "metal": r"\bmetal(lica|core|head)?\b",
    "hard rock": r"\bhard\s*rock\b",
    "punk": r"\bpunk|blink[- ]?182|green\s*day|bad\s*religion\b",
    "emo": r"\bemo|my\s*chemical\s*romance|taking\s*back\s*sunday\b",
    "industrial": r"\bindustrial|nine\s*inch\s*nails|ministry\b",
    "goth": r"\bgoth(ic)?|bauhaus|sisters\s*of\s*mercy\b",
    "darkwave": r"\bdarkwave|cold\s*wave|dark\s*synth\b",
}
# ----------------------------------------------------------------------


def smart_label(base_genre: str, text: str) -> str:
    """Refine 'Rock' or 'Alternative' into more specific subgenres."""
    if base_genre.lower() not in ["rock", "alternative", "indie"]:
        return base_genre.title()

    text = text.lower()
    for g, pattern in SMART_KEYWORDS.items():
        if re.search(pattern, text):
            return g.title()
    return base_genre.title()


def match_genre(event):
    """Return best-matched genre based on performer genres and titles."""
    performers = event.get("performers", [])
    text_blob = event.get("title", "")
    for p in performers:
        text_blob += " " + (p.get("name") or "")
        if p.get("genres"):
            for g in p["genres"]:
                name = g.get("name", "").lower()
                if name in [t.lower() for t in TARGET_GENRES]:
                    return g.get("name", "").title()
                if name in ["rock", "alternative", "indie"]:
                    text_blob += " " + name

    label = smart_label("Rock", text_blob)
    if label.lower() != "rock":
        return label

    # fallback: keyword in title
    title = event.get("title", "").lower()
    for tg in TARGET_GENRES:
        if tg in title:
            return tg.title()

    return None


def fetch_seatgeek(test_mode=False):
    """
    Fetch SeatGeek concerts for target states within date range.
    test_mode=True prints preview and summary instead of saving to DB.
    """
    init_db()
    total_added = 0
    collected = []
    seen_keys = set()  # prevent duplicates (artist + city + date)

    for state in STATES:
        page = 1
        while True:
            params = {
                "client_id": SEATGEEK_ID,
                "taxonomies.name": "concert",
                "venue.state": state,
                "datetime_utc.gte": f"{START_DATE}T00:00:00Z",
                "datetime_utc.lte": f"{END_DATE}T23:59:59Z",
                "per_page": 100,
                "page": page,
            }

            r = requests.get(BASE_URL, params=params, timeout=20)
            if r.status_code != 200:
                print(f"⚠️ {state} → {r.status_code}: {r.text[:180]}")
                break

            data = r.json()
            events = data.get("events", [])
            if not events:
                break

            for ev in events:
                genre = match_genre(ev)
                if not genre:
                    continue

                title = ev.get("title", "")
                date = ev.get("datetime_local", "")[:10]
                venue = ev.get("venue", {}).get("name", "Unknown Venue")
                city = ev.get("venue", {}).get("city", "Unknown")
                state_code = ev.get("venue", {}).get("state", state)
                url = ev.get("url", "")
                image = None
                performers = ev.get("performers", [])
                if performers:
                    image = performers[0].get("image")

                # ----- DEDUPLICATION -----
                dedupe_key = f"{title.lower()}_{city.lower()}_{date}"
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                # -------------------------

                eid = f"sg_{ev.get('id')}"
                if already_seen(eid) and not test_mode:
                    continue

                collected.append({
                    "id": eid,
                    "artist": title,
                    "venue": venue,
                    "city": city,
                    "state": state_code,
                    "genre": genre,
                    "image": image,
                    "date": date,
                    "url": url,
                    "source": "SeatGeek",
                })

            if not data.get("meta", {}).get("has_next"):
                break

            page += 1
            time.sleep(0.3)

        print(f"🎸 {state}: collected {len(collected)} genre-matched events so far")

    # ---- TEST / SAVE OUTPUT ----
    import pandas as pd
    df = pd.DataFrame(collected)
    if test_mode:
        summary = df.groupby(["state", "genre"]).size().unstack(fill_value=0)
        print("\n📊 Events by State & Genre:")
        print(summary)
        print(f"\n🪩 Total unique concerts: {len(df)}")
        print(df.head(25).to_string(index=False))
        return df

    for ev in collected:
        save_event(ev)
        total_added += 1

    print(f"✅ Added {total_added} new SeatGeek shows (unique).")
    return total_added


if __name__ == "__main__":
    # Run in Spyder for preview (does not write to DB)
    fetch_seatgeek(test_mode=True)
