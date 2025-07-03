import streamlit as st
import folium
from streamlit_folium import st_folium
import simplekml
import io
from shapely.geometry import Polygon, LineString, Point
import math

# Default grass field boundary coords (lat, lon)
DEFAULT_FIELD = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
]

def generate_grass_cutting_waypoints(boundary, mower_width):
    # Simplified: generate parallel lines inside polygon boundary spaced by mower width
    poly = Polygon([(lon, lat) for lat, lon in boundary])  # note lon, lat for shapely
    minx, miny, maxx, maxy = poly.bounds
    lines = []
    y = miny
    while y <= maxy:
        line = LineString([(minx, y), (maxx, y)])
        intersect = line.intersection(poly)
        if intersect.is_empty:
            y += mower_width
            continue
        if intersect.geom_type == 'MultiLineString':
            for segment in intersect.geoms:
                lines.append(segment)
        elif intersect.geom_type == 'LineString':
            lines.append(intersect)
        y += mower_width
    return lines

def generate_lawn_striping_waypoints(boundary, mower_width, pattern):
    # For demo, basic stripe pattern same as grass cutting
    # Could extend to checkerboard or diagonal by rotating field / lines
    return generate_grass_cutting_waypoints(boundary, mower_width)

def generate_pitch_marking_waypoints(boundary):
    # Very simplified: just the outer field rectangle for now
    # Replace with full FIFA pitch drawing logic if needed
    return [LineString([(lon, lat) for lat, lon in boundary])]

def create_kml_bytes(lines):
    kml = simplekml.Kml()
    for line in lines:
        coords = [(pt[0], pt[1]) for pt in list(line.coords)]  # (lon, lat)
        kml.newlinestring(name="WaypointPath", coords=coords)
    kml_str = kml.kml()  # get KML as string
    kml_bytes = io.BytesIO(kml_str.encode('utf-8'))  # encode string to bytes
    kml_bytes.seek(0)
    return kml_bytes

def main():
    st.title("Football Field Robot Guidance Line Generator")

    st.markdown("Input field boundary coordinates (lat, lon) one per line, comma-separated:")
    coords_text = st.text_area(
        "Field Boundary Coordinates",
        value="\n".join([f"{lat}, {lon}" for lat, lon in DEFAULT_FIELD]),
        height=100,
    )
    
    mower_width = st.number_input("Mower / Roller Operating Width (meters)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
    task = st.selectbox("Select Task", ["Grass Cutting", "Lawn Striping", "Pitch Marking"])

    if st.button("Generate Waypoints"):
        # Parse coordinates
        try:
            boundary = []
            for line in coords_text.strip().split("\n"):
                lat_str, lon_str = line.strip().split(",")
                lat = float(lat_str)
                lon = float(lon_str)
                boundary.append((lat, lon))
            if len(boundary) < 3:
                st.error("Please enter at least 3 boundary points.")
                return
        except Exception as e:
            st.error(f"Invalid coordinate format: {e}")
            return

        # Generate waypoints based on task
        if task == "Grass Cutting":
            lines = generate_grass_cutting_waypoints(boundary, mower_width)
        elif task == "Lawn Striping":
            lines = generate_lawn_striping_waypoints(boundary, mower_width, pattern="basic")
        else:
            lines = generate_pitch_marking_waypoints(boundary)

        # Create folium map centered on average point
        avg_lat = sum([pt[0] for pt in boundary]) / len(boundary)
        avg_lon = sum([pt[1] for pt in boundary]) / len(boundary)
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=18)

        # Draw field boundary polygon
        folium.Polygon(locations=boundary, color="green", weight=3, fill=True, fill_opacity=0.1).add_to(m)

        # Draw waypoint lines
        for line in lines:
            locs = [(pt[1], pt[0]) for pt in line.coords]  # folium expects (lat, lon)
            folium.PolyLine(locations=locs, color="blue", weight=2).add_to(m)

        st_folium(m, width=700, height=500)

        # Export KML
        kml_bytes = create_kml_bytes(lines)
        st.download_button("Download KML file", kml_bytes, file_name="waypoints.kml", mime="application/vnd.google-earth.kml+xml")

if __name__ == "__main__":
    main()
