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

    # --- Display ---
    # --- Load and display data ---
    data = get_events()
    
    if not data:
        st.info("No events stored yet — click 'Fetch latest shows' above.")
    else:
        df = pd.DataFrame(
            data,
            columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
        )
    
        df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"].dt.month == 7]
    
        # --- Genre-based coloring ---
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
    
        # --- Try to detect narrow screens ---
        # Streamlit doesn't give direct viewport width, but we can use user preference
        mode = st.radio(
            "Display mode",
            ["📊 Table view", "📱 Card view (responsive)"],
            horizontal=True,
        )
    
        if mode == "📊 Table view":
            # Wrapped text for narrow cells
            df["Artist"] = df["Artist"].apply(lambda x: "\n".join(x[i:i+25] for i in range(0, len(x), 25)))
            df["Venue"] = df["Venue"].apply(lambda x: "\n".join(x[i:i+20] for i in range(0, len(x), 20)))
    
            st.data_editor(
                df.style.map(color_by_genre, subset=["Genre"]),
                use_container_width=True,
                hide_index=True,
                disabled=True
            )
        else:
            # --- Card mode for mobile / vertical screens ---
            for _, row in df.iterrows():
                with st.container():
                    st.markdown(f"""
                    **🎤 {row['Artist']}**
                    - 🎶 *{row['Genre']}*
                    - 📍 {row['Venue']} — {row['City']}, {row['State']}
                    - 🗓️ {row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else 'Unknown'}
                    - 🔗 {row['URL']}
                    ---
                    """)


