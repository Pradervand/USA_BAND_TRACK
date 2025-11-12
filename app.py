import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from fetch_shows import update_all, get_events, purge_non_july_events, init_db
from crawl_agemdaconcertmetal import crawl_concertsmetal  # make sure this file is in the same folder

# --- Ensure database exists ---
init_db()
purge_non_july_events()

st.set_page_config(page_title="USA Band Tracker", layout="wide")
st.title("🎸 USA Road Trip Gig Tracker")

# --- Unified Fetch + Debug sidebar ---
st.subheader("🎸 Fetch New Shows")
col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🌍 Fetch ALL Sources"):
        st.info("Fetching shows from all sources... please wait ⏳")
        try:
            n_tm = update_all()
        except Exception as exc:
            st.error(f"Ticketmaster fetch failed: {exc}")
            n_tm = 0

        try:
            n_cm = crawl_concertsmetal()
        except Exception as exc:
            st.error(f"Concerts-Metal fetch failed: {exc}")
            n_cm = 0

        try:
            purge_non_july_events()
        except Exception as exc:
            st.warning(f"Warning while purging non-July events: {exc}")

        total = (n_tm or 0) + (n_cm or 0)
        st.success(
            f"✅ Added {total} new shows! "
            f"(Ticketmaster: {n_tm}, Concerts-Metal: {n_cm})\n\n"
            f"(Last updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})"
        )

with col2:
    st.caption("Use sidebar → Debug to test individual sources")

# Sidebar: toggleable debug buttons (default hidden)
st.sidebar.title("⚙️ Developer / Debug Tools")
debug_mode = st.sidebar.checkbox("Show Debug Fetch Buttons", value=False)

if debug_mode:
    st.sidebar.write("🧪 Individual fetch tests")

    if st.sidebar.button("🔄 Fetch Ticketmaster"):
        st.info("Fetching Ticketmaster shows...")
        try:
            n = update_all()
            purge_non_july_events()
            st.success(f"✅ Added {n} new Ticketmaster shows.")
        except Exception as exc:
            st.error(f"Ticketmaster fetch failed: {exc}")

    if st.sidebar.button("🤘 Fetch Concerts-Metal (July only)"):
        st.info("Fetching Concerts-Metal shows...")
        try:
            n = crawl_concertsmetal()
            purge_non_july_events()
            st.success(f"✅ Added {n} new Concerts-Metal shows.")
        except Exception as exc:
            st.error(f"Concerts-Metal fetch failed: {exc}")

# --- Load and display data ---
data = get_events()

if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
else:
    df = pd.DataFrame(
        data,
        columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source", "Image"]
    )

    # --- Format & clean ---
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["Date"].dt.month == 7]  # Only July shows

    # ✅ Keep raw URL for cards, formatted one for table
    df["URL_raw"] = df["URL"]
    df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})" if x else "")

    # --- Filters ---
    col1, col2 = st.columns(2)

    with col1:
        state_filter = st.multiselect(
            "Filter by State",
            options=sorted(df["State"].unique()),
            key="state_filter",
        )

    with col2:
        genre_filter = st.multiselect(
            "Filter by Genre (OR)",
            options=sorted(set(g.strip() for g in ", ".join(df["Genre"].dropna()).split("/") if g)),
            key="genre_filter",
        )

    filtered_df = df.copy()
    if state_filter:
        filtered_df = filtered_df[filtered_df["State"].isin(state_filter)]
    if genre_filter:
        filtered_df = filtered_df[filtered_df["Genre"].apply(
            lambda x: any(g.lower() in x.lower() for g in genre_filter)
        )]

    # --- Color helper for table view ---
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
    show_table = st.toggle("📊 Show table view", value=False, key="view_toggle")

    # --- CARD VIEW (default) ---
    if not show_table:
        st.markdown("### 📅 Upcoming Shows (Card View)")
        if filtered_df.empty:
            st.warning("No shows match your filters.")
        else:
            for _, row in filtered_df.iterrows():
                image_url = row.get("Image", None)
                url = row.get("URL_raw", "")  # ✅ Use raw URL for cards

                st.markdown(f"""
                <div style="
                    background: #1e1e1e;
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 0.8rem;
                    box-shadow: 0 0 10px rgba(0,0,0,0.3);
                    display: flex;
                    align-items: center;
                ">
                    {'<img src="'+image_url+'" style="width:130px;height:auto;border-radius:8px;margin-right:1rem;object-fit:cover;">' if image_url else ''}
                    <div style="flex:1;line-height:1.6;">
                        <b style="font-size:1.05rem;">🎤 {row['Artist']}</b><br>
                        🎶 <i>{row['Genre']}</i><br>
                        📍 {row['Venue']} — {row['City']}, {row['State']}<br>
                        🗓️ {row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else 'Unknown'}<br>
                        <a href="{url}" target="_blank" rel="noopener noreferrer"
                           style="display:inline-block;margin-top:6px;padding:6px 10px;
                           border-radius:8px;background:#2b6cb0;color:white;
                           text-decoration:none;font-weight:600;">
                           🎟️ Tickets / Info
                        </a>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # --- TABLE VIEW (optional) ---
    else:
        st.markdown("### 📊 Table View")
        if filtered_df.empty:
            st.warning("No shows match your filters.")
        else:
            st.dataframe(
                filtered_df.style.map(color_by_genre, subset=["Genre"]),
                use_container_width=True,
                hide_index=True
            )
