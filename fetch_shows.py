import os
import requests
import sqlite3
import datetime
import time

TM_API_KEY = os.getenv("TM_API_KEY", "")
DB = "events.db"

STATES = ["CA", "AZ", "UT", "CO", "WY", "MT", "WA"]
KEYWORDS = [
    "metal","punk","goth","hardcore","darkwave","industrial","thrash","doom",
    "black metal","atmospheric black metal","raw black metal","depressive black metal","dsbm",
    "melodic black metal","symphonic black metal","post-black metal","ambient black metal",
    "blackened death metal","blackened thrash","blackened hardcore","folk black metal",
    "pagan black metal","viking metal","occult black metal","avant-garde black metal","industrial black metal",
    "doom metal","stoner metal","sludge metal","funeral doom","death doom","black doom","drone","drone metal",
    "hardcore punk","crust","d-beat","anarcho punk","post-punk","dark post-punk","coldwave",
    "goth rock","deathrock","minimal wave","synthwave","new wave",
    "ebm","electro-industrial","power electronics","industrial metal","aggrotech",
    "dark electro","noise","martial industrial","ritual ambient","dark ambient","cyberpunk","techno-industrial",
    "post-metal","shoegaze","blackgaze","post-rock","ambient","noise rock","experimental","avant-garde"
]

START_DATE = "2026-07-01T00:00:00Z"
END_DATE = "2026-07-31T23:59:59Z"

# ─────────────────────────── DB INIT ────────────────────────────

def ensure_genre_column():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(events)")
    cols = [r[1] for r in cur.fetchall()]
    if "genre" not in cols:
        cur.execute("ALTER TABLE events ADD COLUMN genre TEXT")
        conn.commit()
        print("🆕 Added 'genre' column to events table")
    conn.close()

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events(
        id TEXT PRIMARY KEY,
        artist TEXT,
        venue TEXT,
        city TEXT,
        state TEXT,
        genre TEXT,
        date TEXT,
        url TEXT,
        source TEXT,
        inserted_at TEXT
    )
    """)
    conn.commit()
    conn.close()
    ensure_genre_column()

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
        """INSERT OR IGNORE INTO events
           (id, artist, venue, city, state, genre, date, url, source, inserted_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            e["id"], e["artist"], e["venue"], e["city"], e["state"],
            e.get("genre", "Unknown"), e["date"], e["url"],
            e["source"], datetime.datetime.now(datetime.timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()

# ─────────────────────────── API CALL ────────────────────────────

def fetch_ticketmaster():
    """Fetch all music events once per state, then locally filter by subgenres."""
    new_events = 0
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

    for st in STATES:
        params = {
            "apikey": TM_API_KEY,
            "classificationName": "music",
            "stateCode": st,
            "startDateTime": START_DATE,
            "endDateTime": END_DATE,
            "size": 200,
        }

        try:
            r = requests.get(base_url, params=params, timeout=15)
            if r.status_code != 200:
                print(f"⚠️ Error {r.status_code} for {st}")
                continue

            # handle pagination
            data = r.json()
            events = []
            while True:
                chunk = data.get("_embedded", {}).get("events", [])
                events.extend(chunk)
                next_link = data.get("_links", {}).get("next", {}).get("href")
                if not next_link:
                    break
                time.sleep(0.5)
                next_url = f"https://app.ticketmaster.com{next_link}&apikey={TM_API_KEY}"
                data = requests.get(next_url, timeout=15).json()

            for ev in events:
                name = ev.get("name", "").lower()
                classifications = ev.get("classifications", [])
                genre = subgenre = ""
                if classifications:
                    g = classifications[0].get("genre", {}).get("name", "")
                    sg = classifications[0].get("subGenre", {}).get("name", "")
                    genre = g or ""
                    subgenre = sg or ""
                
                text = f"{name} {genre} {subgenre}".lower()
                if not any(k in text for k in KEYWORDS):
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
                        "artist": ev.get("name", ""),
                        "venue": venue,
                        "city": city,
                        "state": state,
                        "genre": f"{genre} / {subgenre}",
                        "date": date,
                        "url": url,
                        "source": "Ticketmaster"
                    })
                    new_events += 1

        except Exception as e:
            print(f"❌ Exception fetching {st}: {e}")

    print(f"✅ Added {new_events} new Ticketmaster events.")
    return new_events

# ─────────────────────────── RETRIEVAL ────────────────────────────

def get_events():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT artist, genre, venue, city, state, date, url, source FROM events ORDER BY date ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def update_all():
    init_db()
    added = fetch_ticketmaster()
    return added

def purge_non_july_events():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM events
        WHERE strftime('%m', date) != '07'
    """)
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"🗑️ Removed {deleted} events outside July.")
    return deleted
