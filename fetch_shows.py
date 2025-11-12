# fetch_shows.py
import os
import requests
import sqlite3
import datetime

# read API key securely (set in Streamlit Secrets)
TM_API_KEY = os.getenv("TM_API_KEY", "")
DB = "events.db"

STATES = ["CA", "AZ", "UT", "CO", "WY", "MT", "WA"]
KEYWORDS = [
    "metal","punk","goth","hardcore","darkwave","industrial","thrash","doom",
    # black metal
    "black metal","atmospheric black metal","raw black metal","depressive black metal","dsbm",
    "melodic black metal","symphonic black metal","post-black metal","ambient black metal",
    "blackened death metal","blackened thrash","blackened hardcore","folk black metal",
    "pagan black metal","viking metal","occult black metal","avant-garde black metal","industrial black metal",
    # doom/sludge/drone
    "doom metal","stoner metal","sludge metal","funeral doom","death doom","black doom","drone","drone metal",
    # punk/goth/darkwave
    "hardcore punk","crust","d-beat","anarcho punk","post-punk","dark post-punk","coldwave",
    "goth rock","deathrock","minimal wave","synthwave","new wave",
    # industrial/electronic
    "ebm","electro-industrial","power electronics","industrial metal","aggrotech",
    "dark electro","noise","martial industrial","ritual ambient","dark ambient","cyberpunk","techno-industrial",
    # atmospheric/experimental
    "post-metal","shoegaze","blackgaze","post-rock","ambient","noise rock","experimental","avant-garde"
]

# Date filter for 2026 shows
START_DATE = "2026-07-07T00:00:00Z"
END_DATE = "2026-07-30T23:59:59Z"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events(
        id TEXT PRIMARY KEY,
        artist TEXT,
        venue TEXT,
        city TEXT,
        state TEXT,
        date TEXT,
        url TEXT,
        source TEXT,
        inserted_at TEXT
    )""")
    conn.commit()
    conn.close()

def already_seen(event_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM events WHERE id = ?", (event_id,))
    found = cur.fetchone() is not None
    conn.close()
    return found

def save_event(e):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?)",
        (e['id'], e['artist'], e['venue'], e['city'], e['state'],
         e['date'], e['url'], e['source'], datetime.datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def fetch_ticketmaster():
    """Fetch metal/punk/goth shows from Ticketmaster for 2026 by keyword per state."""
    new_events = 0
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

    for st in STATES:
        for kw in KEYWORDS:
            params = {
                "apikey": TM_API_KEY,
                "classificationName": "music",
                "stateCode": st,
                "keyword": kw,
                "size": 100,
                "startDateTime": START_DATE,
                "endDateTime": END_DATE,
            }
            try:
                r = requests.get(base_url, params=params, timeout=15)
                if r.status_code != 200:
                    print(f"⚠️ Error {r.status_code} for {st}, {kw}")
                    continue

                events = r.json().get("_embedded", {}).get("events", [])
                for ev in events:
                    name = ev.get("name", "")
                    # still double-check keyword match in case of false positives
                    if not any(k in name.lower() for k in KEYWORDS):
                        continue

                    venues = ev.get("_embedded", {}).get("venues", [{}])
                    venue = venues[0].get("name", "Unknown Venue")
                    city = venues[0].get("city", {}).get("name", "Unknown")
                    state = venues[0].get("state", {}).get("stateCode", st)
                    date = ev.get("dates", {}).get("start", {}).get("localDate", "")
                    url = ev.get("url", "")
                    eid = "tm_" + ev.get("id", "")

                    if not already_seen(eid):
                        save_event({
                            "id": eid,
                            "artist": name,
                            "venue": venue,
                            "city": city,
                            "state": state,
                            "date": date,
                            "url": url,
                            "source": "Ticketmaster"
                        })
                        new_events += 1

                # optional: short delay to avoid hitting API rate limits
                # time.sleep(0.3)

            except Exception as e:
                print(f"❌ Exception fetching {st} / {kw}: {e}")

    return new_events
import time




def get_events():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT artist,venue,city,state,date,url,source FROM events ORDER BY date ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_all():
    init_db()
    added = fetch_ticketmaster()
    return added
