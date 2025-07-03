import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString
import numpy as np
import simplekml

def parse_coords(text):
    coords = []
    for line in text.strip().split('\n'):
        parts = line.strip().split(',')
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                coords.append((lat, lon))
            except:
                continue
    return coords

def generate_waypoints(field_coords, mower_width):
    polygon = Polygon([(lon, lat) for lat, lon in field_coords])
    coords = list(polygon.exterior.coords)
    edges = [(np.linalg.norm(np.array(coords[i]) - np.array(coords[i-1])), (coords[i-1], coords[i])) for i in range(1, len(coords))]
    longest_edge = max(edges, key=lambda x: x[0])[1]

    dx = longest_edge[1][0] - longest_edge[0][0]
    dy = longest_edge[1][1] - longest_edge[0][1]
    angle = np.arctan2(dy, dx)

    def rotate_point(x, y, ang):
        return (x * np.cos(ang) + y * np.sin(ang), -x * np.sin(ang) + y * np.cos(ang))

    rotated_coords = [rotate_point(x, y, -angle) for x, y in polygon.exterior.coords]
    min_x = min(c[0] for c in rotated_coords)
    max_x = max(c[0] for c in rotated_coords)
    min_y = min(c[1] for c in rotated_coords)
    max_y = max(c[1] for c in rotated_coords)

    lines = []
    x = min_x + mower_width / 2
    while x < max_x:
        line_points = []
        y_vals = np.linspace(min_y, max_y, 500)
        for y in y_vals:
            rx = x * np.cos(angle) - y * np.sin(angle)
            ry = x * np.sin(angle) + y * np.cos(angle)
            line_points.append((rx, ry))

        line = LineString(line_points)
        clipped = line.intersection(polygon)

        if not clipped.is_empty:
            if clipped.geom_type == 'MultiLineString':
                clipped = max(clipped, key=lambda l: l.length)
            if clipped.geom_type == 'LineString':
                lines.append([(lat, lon) for lon, lat in clipped.coords])
        x += mower_width
    return lines

def main():
    st.title("Football Grass Field Waypoint Generator")

    default_coords = """43.555830, 27.826090
43.555775, 27.826100
43.555422, 27.826747
43.555425, 27.826786
43.556182, 27.827557
43.556217, 27.827538
43.556559, 27.826893
43.556547, 27.826833"""
    st.markdown("### Input grass field boundary coordinates (lat, lon):")
    coords_text = st.text_area("Coordinates", value=default_coords, height=150)
    field_coords = parse_coords(coords_text)

    if len(field_coords) < 3:
        st.error("Need at least 3 coordinates to form a polygon.")
        return

    mower_width = st.slider("Mower Operating Width (m)", 0.5, 5.0, 2.0, 0.1)

    if st.button("Generate Waypoints"):
        waypoints = generate_waypoints(field_coords, mower_width)

        m = folium.Map(location=field_coords[0], zoom_start=18)
        folium.Polygon(locations=field_coords, color="green", fill=True, fill_opacity=0.2).add_to(m)
        for line in waypoints:
            folium.PolyLine(line, color="blue", weight=3).add_to(m)

        st_folium(m, width=700, height=500)

        kml = simplekml.Kml()
        for idx, line in enumerate(waypoints):
            ls = kml.newlinestring(name=f"Line {idx+1}", coords=[(lon, lat) for lat, lon in line])
            ls.style.linestyle.color = simplekml.Color.blue
            ls.style.linestyle.width = 3

        kml_str = kml.kml()
        kml_bytes = kml_str.encode("utf-8")

        st.download_button(
            label="Download Waypoints KML",
            data=kml_bytes,
            file_name="waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

if __name__ == "__main__":
    main()
