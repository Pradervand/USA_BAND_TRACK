# app.py
import streamlit as st
from fetch_shows import update_all, get_events
import pandas as pd
import datetime
import os

st.set_page_config(page_title="🤘 Metal / Punk / Goth Show Radar", layout="wide")

st.title("🤘 Metal / Punk / Goth Show Radar (2026)")
st.caption("Tracking heavy music shows in CA, AZ, UT, CO, WY, MT, WA using Ticketmaster API")

# Ensure API key is set
if not os.getenv("TM_API_KEY"):
    st.error("❌ No Ticketmaster API key found. Add it under Settings → Secrets as TM_API_KEY.")
    st.stop()

# Refresh button
if st.button("🔄 Fetch new events"):
    with st.spinner("Fetching latest shows from Ticketmaster..."):
        n = update_all()
        st.success(f"✅ Added {n} new shows! (Last updated {datetime.datetime.now().strftime('%H:%M:%S')})")

# Load events
data = get_events()
if not data:
    st.info("No events stored yet — click 'Fetch new events' above to start.")
else:
    df = pd.DataFrame(data, columns=["Artist", "Venue", "City", "State", "Date", "URL", "Source"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date")

    # Filters
    states = sorted(df["State"].dropna().unique())
    selected_states = st.multiselect("Filter by state", states, default=states)
    filtered_df = df[df["State"].isin(selected_states)]

    st.markdown(f"### 🎸 Upcoming Shows ({len(filtered_df)} total)")
    st.dataframe(filtered_df, use_container_width=True)
