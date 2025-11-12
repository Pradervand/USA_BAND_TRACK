# fetch_shows.py
import requests, sqlite3, datetime

DB = "events.db"
TM_API_KEY = "YOUR_TICKETMASTER_API_KEY"
STATES = ["CA","AZ","UT","CO","WY","MT","WA"]
KEYWORDS = ["metal","punk","goth","hardcore","darkwave","industrial","thrash","doom"]

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
    """Pull events from Ticketmaster across your states."""
    new = 0
    for st in STATES:
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {"apikey": TM_API_KEY, "classificationName":"music", "stateCode":st, "size":100}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            continue
        data = r.json().get("_embedded",{}).get("events",[])
        for ev in data:
            name = ev.get("name","")
            if not any(k in name.lower() for k in KEYWORDS):
                continue
            venue = ev["_embedded"]["venues"][0]["name"]
            city  = ev["_embedded"]["venues"][0]["city"]["name"]
            state = ev["_embedded"]["venues"][0]["state"]["stateCode"]
            date  = ev["dates"]["start"].get("localDate","")
            url   = ev["url"]
            eid   = "tm_" + ev["id"]
            if not already_seen(eid):
                save_event({
                    "id":eid, "artist":name, "venue":venue,
                    "city":city, "state":state, "date":date,
                    "url":url, "source":"Ticketmaster"
                })
                new += 1
    return new

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
