import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from fetch_shows import update_all, get_events, purge_non_july_events, init_db

# --- Make sure DB exists ---
init_db()
purge_non_july_events()

st.title("🎸 USA Band Tracker — Metal / Punk / Goth / Industrial")

# --- Fetch new events ---
if st.button("🔄 Fetch latest shows"):
    n = update_all()
    purge_non_july_events()
    st.success(f"✅ Added {n} new shows! (Last updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")


# --- Load and display data ---
data = get_events()

if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
else:
    # columns now include genre
    df = pd.DataFrame(
        data,
        columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
    )

    # cleanup & formatting
    df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # filter July only (in-memory safety)
    df = df[df["Date"].dt.month == 7]

    # simple genre-based coloring
    def color_by_genre(val):
        if not val:
            return ""
        val = str(val).lower()
        if "metal" in val:
            return "background-color: #444; color: white;"
        if "punk" in val:
            return "background-color: #c00; color: white;"
        if "goth" in val or "dark" in val or "wave" in val:
            return "background-color: #505050; color: white;"
        if "industrial" in val or "ebm" in val or "electro" in val:
            return "background-color: #333366; color: white;"
        return ""

    st.dataframe(
        df.style.map(color_by_genre, subset=["Genre"]),
        width="stretch"
    )
