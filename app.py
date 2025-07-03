import streamlit as st
import folium
from streamlit_folium import st_folium

# Your polygon coordinates (lat, lon)
FIELD_BOUNDARY = [
    (43.555830, 27.826090),
    (43.555775, 27.826100),
    (43.555422, 27.826747),
    (43.555425, 27.826786),
    (43.556182, 27.827557),
    (43.556217, 27.827538),
    (43.556559, 27.826893),
    (43.556547, 27.826833),
    (43.555830, 27.826090)  # closing polygon
]

def main():
    st.title("Football Field Visualization")

    # Create folium map centered around first point
    m = folium.Map(location=FIELD_BOUNDARY[0], zoom_start=18)

    # Draw polygon on map
    folium.Polygon(locations=FIELD_BOUNDARY, color='green', fill=True, fill_opacity=0.3).add_to(m)

    # Display map in Streamlit
    st_data = st_folium(m, width=700, height=500)

if __name__ == "__main__":
    main()
