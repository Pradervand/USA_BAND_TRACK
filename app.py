import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# Local imports
from fetch_shows import (
    update_all, get_events, purge_non_july_events, init_db
)
from crawl_agemdaconcertmetal import crawl_concertsmetal
from fetch_seatgeek import fetch_seatgeek

# --- SETUP ---
st.set_page_config(page_title="USA Band Tracker", layout="wide")
init_db()

# --- SIDEBAR ---
st.sidebar.header("Data Sources")
use_crawler = st.sidebar.checkbox("Use ConcertsMetal.com Crawler", True)
use_seatgeek = st.sidebar.checkbox("Use SeatGeek API", True)

st.sidebar.header("Date Filters")
start_date = st.sidebar.date_input("Start Date", datetime(2026, 7, 1))
end_date = st.sidebar.date_input("End Date", datetime(2026, 7, 31))

if st.sidebar.button("Purge Non-July Events"):
    purge_non_july_events()
    st.success("🧹 Old events removed.")

# --- MAIN UI ---
st.title("🎸 USA Band Tracker — Live Show Aggregator")

if st.button("🚀 Update All Data"):
    with st.spinner("Fetching and updating events..."):
        total = 0

        if use_crawler:
            total += crawl_concertsmetal()

        if use_seatgeek:
            total += fetch_seatgeek(test_mode=False)

        update_all()
    st.success(f"✅ Update complete. Added {total} new shows.")

# --- DISPLAY EVENTS ---
st.subheader("🎵 Current Shows in Database")

events = pd.DataFrame(get_events())

if not events.empty:
    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    events = events.sort_values(by="date")

    # Quick filters (we’ll expand this next)
    genre_filter = st.selectbox(
        "Filter by Genre", ["All"] + sorted(events["genre"].dropna().unique().tolist())
    )
    state_filter = st.selectbox(
        "Filter by State", ["All"] + sorted(events["state"].dropna().unique().tolist())
    )

    if genre_filter != "All":
        events = events[events["genre"] == genre_filter]
    if state_filter != "All":
        events = events[events["state"] == state_filter]

    st.markdown(f"### {len(events)} Shows Found")

    for _, row in events.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                if pd.notna(row["image"]):
                    st.image(row["image"], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/200x150.png?text=No+Image")
            with col2:
                st.markdown(f"### {row['artist']}")
                st.markdown(f"**Genre:** {row['genre']}")
                st.markdown(f"**Venue:** {row['venue']}, {row['city']}, {row['state']}")
                st.markdown(f"**Date:** {row['date'].strftime('%Y-%m-%d')}")
                st.markdown(f"[🎟 Open Link]({row['url']})")

else:
    st.warning("No events found. Try running an update first.")
