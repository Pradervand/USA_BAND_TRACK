import streamlit as st
import pandas as pd
from fetch_shows import update_all, get_events, purge_non_july_events 
from datetime import datetime

st.set_page_config(page_title="USA Band Tracker", layout="wide")

st.title("🎸 Road Trip potential shows")

# --- Fetch new events ---
if st.button("🔄 Fetch latest shows"):
    n = update_all()
    st.success(f"✅ Added {n} new shows! (Last updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})")

# --- Load stored events ---
data = get_events()
if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
else:
    df = pd.DataFrame(
        data,
        columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
    )

    # Clean & format data
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})" if pd.notna(x) else "")
    df["Genre"] = (
        df["Genre"]
        .fillna("")
        .apply(lambda g: ", ".join(sorted(set([x.strip() for x in g.split(",") if x.strip()]))))
    )

    # --- Filters ---
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        states = ["All"] + sorted(df["State"].dropna().unique().tolist())
        selected_state = st.selectbox("🏴 Filter by state", states)

    with col2:
        all_genres = sorted(
            set([g.strip() for genre_list in df["Genre"].dropna() for g in genre_list.split(",") if g.strip()])
        )
        selected_genres = st.multiselect("🎶 Filter by genre(s)", all_genres)

    with col3:
        search_artist = st.text_input("🔍 Search by artist name")

    # --- Filtering logic ---
    filtered_df = df.copy()

    if selected_state != "All":
        filtered_df = filtered_df[filtered_df["State"] == selected_state]

    if selected_genres:
        filtered_df = filtered_df[
            filtered_df["Genre"].apply(
                lambda g: any(genre.lower() in g.lower() for genre in selected_genres)
            )
        ]

    if search_artist:
        filtered_df = filtered_df[
            filtered_df["Artist"].str.contains(search_artist, case=False, na=False)
        ]

    # --- Style by genre ---
    def color_by_genre(val):
        if not val:
            return ""
        val = val.lower()
        if "metal" in val:
            return "background-color: #444; color: white;"
        if "punk" in val:
            return "background-color: #b00; color: white;"
        if any(k in val for k in ["goth", "dark", "wave"]):
            return "background-color: #505050; color: white;"
        if any(k in val for k in ["industrial", "ebm", "electro"]):
            return "background-color: #333366; color: white;"
        return ""

    # --- Display table ---
    st.dataframe(
        filtered_df.style.map(color_by_genre, subset=["Genre"]),
        width="stretch"
    )
