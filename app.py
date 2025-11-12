import os
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from fetch_shows import update_all, get_events, purge_non_july_events, init_db
from crawl_agemdaconcertmetal import crawl_concertsmetal
from drive_sync import init_drive, upload_db, download_db


# --- Streamlit setup ---
st.set_page_config(page_title="USA Band Tracker", layout="wide")
st.title("🎸 USA Road Trip Gig Tracker")

# --- Google Drive setup ---
st.info("🔄 Initializing Drive connection...")
try:
    drive_service = init_drive()
    folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
    os.makedirs("data", exist_ok=True)

    # Download DB from Drive (if available)
    if download_db(drive_service, folder_id):
        st.success("✅ Synced latest database from Google Drive.")
    else:
        st.warning("⚠️ No remote DB found on Drive — starting fresh.")
except Exception as e:
    st.error(f"❌ Drive initialization failed: {e}")
    drive_service = None
    folder_id = None

# --- Ensure database exists locally ---
init_db()
purge_non_july_events()


# --- Fetch all sources ---
if st.button("🌍 Fetch ALL Sources"):
    st.info("Fetching shows from all sources... please wait ⏳")

    total_tm = total_cm = 0

    try:
        total_tm = update_all()
    except Exception as exc:
        st.error(f"Ticketmaster fetch failed: {exc}")

    try:
        total_cm = crawl_concertsmetal()
    except Exception as exc:
        st.error(f"Concerts-Metal fetch failed: {exc}")

    try:
        purge_non_july_events()
    except Exception as exc:
        st.warning(f"Warning while purging non-July events: {exc}")

    total = (total_tm or 0) + (total_cm or 0)
    st.success(
        f"✅ Added {total} new shows! "
        f"(Ticketmaster: {total_tm}, Concerts-Metal: {total_cm})\n\n"
        f"(Last updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})"
    )

    # Upload updated DB to Google Drive
    if drive_service and folder_id:
        try:
            upload_db(drive_service, folder_id)
            st.success("☁️ Database synced to Google Drive.")
        except Exception as e:
            st.warning(f"Drive upload failed: {e}")


# --- Load and display data ---
data = get_events()

if not data:
    st.info("No events stored yet — click 'Fetch ALL Sources' above.")
else:
    df = pd.DataFrame(
        data,
        columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source", "Image"],
    )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["Date"].dt.month == 7]
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
        filtered_df = filtered_df[
            filtered_df["Genre"].apply(lambda x: any(g.lower() in x.lower() for g in genre_filter))
        ]

    # --- Table color helper ---
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

    # --- View toggle ---
    show_table = st.toggle("📊 Show table view", value=False, key="view_toggle")

    # --- CARD VIEW ---
    if not show_table:
        st.markdown("### 📅 Upcoming Shows (Card View)")
        if filtered_df.empty:
            st.warning("No shows match your filters.")
        else:
            for _, row in filtered_df.iterrows():
                image_url = row.get("Image", "")
                url = row.get("URL_raw", "")
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
    # --- TABLE VIEW ---
    else:
        st.markdown("### 📊 Table View")
        if filtered_df.empty:
            st.warning("No shows match your filters.")
        else:
            st.dataframe(
                filtered_df.style.map(color_by_genre, subset=["Genre"]),
                use_container_width=True,
                hide_index=True,
            )
