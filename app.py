import streamlit as st
import pandas as pd
from fetch_shows import update_all, get_events
from datetime import datetime

# --- Page config ---
st.set_page_config(
    page_title="USA Band Tracker",
    page_icon="🎸",
    layout="wide",  # full browser width
)

# --- Title ---
st.title("🎸 USA Band Tracker — Metal / Punk / Goth / Industrial")

# --- Top bar ---
col1, col2 = st.columns([2, 1])
with col1:
    st.caption("Tracking underground shows across the western USA.")
with col2:
    if st.button("🔄 Fetch latest shows"):
        n = update_all()
        st.success(f"✅ Added {n} new shows! (Last updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})")

# --- Load events ---
data = get_events()
if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
    st.stop()

# --- Create DataFrame ---
df = pd.DataFrame(
    data,
    columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
)

# --- Format + sort ---
df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})" if x else "")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.sort_values("Date")

# --- Filters row ---
st.markdown("### 🎚️ Filters")

fcol1, fcol2, fcol3 = st.columns([1, 1, 1])
with fcol1:
    state_filter = st.selectbox("Filter by state", options=["All"] + sorted(df["State"].dropna().unique().tolist()))
with fcol2:
    genre_filter = st.selectbox("Filter by genre", options=["All"] + sorted(df["Genre"].dropna().unique().tolist()))
with fcol3:
    upcoming_only = st.toggle("Show only upcoming events", value=True)

# --- Apply filters ---
filtered_df = df.copy()
if state_filter != "All":
    filtered_df = filtered_df[filtered_df["State"] == state_filter]
if genre_filter != "All":
    filtered_df = filtered_df[filtered_df["Genre"] == genre_filter]
if upcoming_only:
    filtered_df = filtered_df[filtered_df["Date"] >= pd.Timestamp.today()]

# --- Define color scheme for genres ---
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

# --- Display results ---
st.markdown("### 🎤 Shows")
st.dataframe(
    filtered_df.style.map(color_by_genre, subset=["Genre"]),
    width="stretch"
)

# --- Footer ---
st.markdown(
    "<p style='text-align:center; color:gray;'>Built with ❤️ using Streamlit — auto-refreshes daily.</p>",
    unsafe_allow_html=True
)
