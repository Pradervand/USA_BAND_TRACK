import streamlit as st
import pandas as pd
from fetch_shows import update_all, get_events
from datetime import datetime

st.title("🎸 USA Band Tracker — Metal / Punk / Goth / Industrial")

if st.button("🔄 Fetch latest shows"):
    n = update_all()
    st.success(f"✅ Added {n} new shows! (Last updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})")

data = get_events()
if not data:
    st.info("No events stored yet — click 'Fetch latest shows' above.")
else:
    df = pd.DataFrame(
    data,
    columns=["Artist", "Genre", "Venue", "City", "State", "Date", "URL", "Source"]
)



    df["URL"] = df["URL"].apply(lambda x: f"[Link]({x})")

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

