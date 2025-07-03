import streamlit as st
import folium
from streamlit_folium import st_folium

# Helper to parse input lines to coordinates
def parse_coords(text):
    coords = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        try:
            lat, lon = map(float, line.strip().split(","))
            coords.append((lat, lon))
        except Exception as e:
            st.error(f"Invalid coordinate line: {line}")
            return None
    return coords

def main():
    st.title("Football Field with Polygon and Corner Points")

    if "field_coords" not in st.session_state:
        st.session_state.field_coords = [
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

    if "corner_points" not in st.session_state:
        # Start empty or with example points inside polygon
        st.session_state.corner_points = [
            (43.556000, 27.826500),
            (43.555600, 27.827000)
        ]

    st.subheader("Input Field Coordinates (lat, lon) one per line, comma separated:")
    coord_text = "\n".join(f"{lat}, {lon}" for lat, lon in st.session_state.field_coords)
    user_input = st.text_area("Field Coordinates", coord_text, height=200)

    if st.button("Update Field Polygon"):
        new_coords = parse_coords(user_input)
        if new_coords:
            # Close polygon if not closed
            if new_coords[0] != new_coords[-1]:
                new_coords.append(new_coords[0])
            st.session_state.field_coords = new_coords
            st.success("Polygon updated!")

    st.subheader("Input Corner Points (lat, lon) one per line, comma separated:")
    corners_text = "\n".join(f"{lat}, {lon}" for lat, lon in st.session_state.corner_points)
    corners_input = st.text_area("Corner Points", corners_text, height=150)

    if st.button("Update Corner Points"):
        new_corners = parse_coords(corners_input)
        if new_corners is not None:
            st.session_state.corner_points = new_corners
            st.success("Corner points updated!")

    # Draw map
    m = folium.Map(location=st.session_state.field_coords[0], zoom_start=18)
    folium.Polygon(locations=st.session_state.field_coords, color="green", fill=True, fill_opacity=0.3).add_to(m)

    # Add corner markers in red
    for idx, (lat, lon) in enumerate(st.session_state.corner_points):
        folium.Marker(
            location=(lat, lon),
            popup=f"Corner {idx+1}",
            icon=folium.Icon(color='red', icon='flag')
        ).add_to(m)

    st_folium(m, width=700, height=500)

if __name__ == "__main__":
    main()
