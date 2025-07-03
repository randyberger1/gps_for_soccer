import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import numpy as np

# Utility: parse coordinates from multiline text input
def parse_coords(text):
    coords = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        try:
            lat, lon = map(float, line.strip().split(","))
            coords.append((lat, lon))
        except Exception:
            st.error(f"Invalid coordinate line: {line}")
            return None
    return coords

# Calculate length (longest side) and width (max perpendicular distance)
def polygon_dimensions(coords):
    # Longest distance between any two points (length)
    max_dist = 0
    pt1 = pt2 = None
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            d = geodesic(coords[i], coords[j]).meters
            if d > max_dist:
                max_dist = d
                pt1, pt2 = coords[i], coords[j]

    # Convert lat/lon to local Cartesian approx (meters)
    def to_xy(latlon):
        lat0, lon0 = pt1
        R = 6371000  # Earth radius in meters
        x = R * np.radians(latlon[1] - lon0) * np.cos(np.radians(lat0))
        y = R * np.radians(latlon[0] - lat0)
        return np.array([x, y])

    p1 = to_xy(pt1)
    p2 = to_xy(pt2)
    line_vec = p2 - p1
    line_len = np.linalg.norm(line_vec)
    line_unitvec = line_vec / line_len

    def point_line_dist(point):
        p = to_xy(point)
        vec = p - p1
        proj_len = np.dot(vec, line_unitvec)
        proj_point = p1 + proj_len * line_unitvec
        dist_vec = p - proj_point
        return np.linalg.norm(dist_vec)

    widths = [point_line_dist(pt) for pt in coords]
    max_width = max(widths)

    return max_dist, max_width

def main():
    st.title("Football Field Boundary and Validation")

    # Default polygon coordinates (8 vertices + close polygon)
    default_coords = [
        (43.555830, 27.826090),
        (43.555775, 27.826100),
        (43.555422, 27.826747),
        (43.555425, 27.826786),
        (43.556182, 27.827557),
        (43.556217, 27.827538),
        (43.556559, 27.826893),
        (43.556547, 27.826833),
        (43.555830, 27.826090),  # close polygon
    ]

    if "field_coords" not in st.session_state:
        st.session_state.field_coords = default_coords

    st.subheader("Input Field Coordinates (lat, lon):")
    coord_text = "\n".join(f"{lat}, {lon}" for lat, lon in st.session_state.field_coords)
    user_input = st.text_area("Edit field coordinates (one pair per line)", coord_text, height=200)

    if st.button("Update Polygon"):
        new_coords = parse_coords(user_input)
        if new_coords:
            # Close polygon if not closed
            if new_coords[0] != new_coords[-1]:
                new_coords.append(new_coords[0])
            st.session_state.field_coords = new_coords
            st.success("Polygon updated!")

    # Validate FIFA dimension checkbox
    validate = st.checkbox("Validate FIFA Standard Dimensions (105×68 m)")

    if validate:
        length, width = polygon_dimensions(st.session_state.field_coords)
        st.write(f"Estimated Field Length: **{length:.2f} m**")
        st.write(f"Estimated Field Width: **{width:.2f} m**")

        length_ok = 100 <= length <= 110  # ±5 meters tolerance
        width_ok = 63 <= width <= 73

        if length_ok and width_ok:
            st.success("Field dimensions comply with FIFA standards (±5 m tolerance).")
        else:
            st.error("Field dimensions do NOT comply with FIFA standards.")

    # Show map with polygon
    m = folium.Map(location=st.session_state.field_coords[0], zoom_start=18)
    folium.Polygon(locations=st.session_state.field_coords, color="green", fill=True, fill_opacity=0.3).add_to(m)
    st_folium(m, width=700, height=500)

if __name__ == "__main__":
    main()
