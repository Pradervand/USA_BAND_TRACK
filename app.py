import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from fetch_shows import update_all, get_events, purge_non_july_events, init_db

# --- Ensure database exists ---
init_db()
purge_non_july_events()

st.set_page_config(page_title="USA Band Tracker", layout="wide")
st.title("🎸 USA Band Tracker — Metal / Punk / Goth / Industrial")

# --- Fetch new events ---
if st.button("🔄 Fetch latest shows"):
    n = update_all()
    purge_non_july_events()
    st.success(
        f"✅ Added {n} new shows! "
        f"(Last updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})"
    )

# --- Load and display events ---
data = get_events()

if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
else:
    # Create DataFrame
    df = pd.DataFrame(
        data,
        columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
    )

    # Format URL and Date
    df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})" if x else "")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Keep only July events
    df = df[df["Date"].dt.month == 7]

    # --- Filters ---
    col1, col2 = st.columns(2)
    with col1:
        state_filter = st.multiselect(
            "Filter by State", sorted(df["State"].unique()), default=None
        )
    with col2:
        genre_filter = st.multiselect(
            "Filter by Genre (OR)", sorted(set(g for g in df["Genre"].dropna().unique() if g))
        )

    if state_filter:
        df = df[df["State"].isin(state_filter)]
    if genre_filter:
        df = df[df["Genre"].apply(lambda x: any(g in x for g in genre_filter))]

    # --- Style by genre ---
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

# --- Load and display data ---
data = get_events()

if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
else:
    df = pd.DataFrame(
        data,
        columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
    )

    # Format & clean
    df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["Date"].dt.month == 7]  # Only July shows

    # --- Filters ---
    col1, col2 = st.columns(2)

    with col1:
        state_filter = st.multiselect(
            "Filter by State",
            options=sorted(df["State"].unique()),
            default=[],
        )

    with col2:
        genre_filter = st.multiselect(
            "Filter by Genre (OR)",
            options=sorted(set(g.strip() for g in ", ".join(df["Genre"].dropna()).split("/") if g)),
            default=[],
        )

    filtered_df = df.copy()
    if state_filter:
        filtered_df = filtered_df[filtered_df["State"].isin(state_filter)]
    if genre_filter:
        filtered_df = filtered_df[filtered_df["Genre"].apply(
            lambda x: any(g.lower() in x.lower() for g in genre_filter)
        )]

    # --- Genre color styling for table view ---
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

    # --- Toggle for Table view ---
    show_table = st.toggle("📊 Show table view", value=False)

    # --- CARD VIEW (default) ---
    if not show_table:
        st.markdown("### 📅 Upcoming Shows (Card View)")
        for _, row in filtered_df.iterrows():
            st.markdown(f"""
            <div style="
                background: #1e1e1e;
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 0.7rem;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
            ">
                <b style="font-size:1.1rem;">🎤 {row['Artist']}</b><br>
                🎶 <i>{row['Genre']}</i><br>
                📍 {row['Venue']} — {row['City']}, {row['State']}<br>
                🗓️ {row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else 'Unknown'}<br>
                🔗 {row['URL']}
            </div>
            """, unsafe_allow_html=True)

    # --- TABLE VIEW (optional) ---
    else:
        st.markdown("### 📊 Table View")
        st.dataframe(
            filtered_df.style.map(color_by_genre, subset=["Genre"]),
            use_container_width=True,
            hide_index=True
        )
