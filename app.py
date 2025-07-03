import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString
import numpy as np
import simplekml

# Helper to parse input coordinates from multiline text
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

# Simple function to generate parallel lines (waypoints) inside polygon for mowing
def generate_waypoints(field_coords, mower_width, direction='longest'):
    polygon = Polygon([(lon, lat) for lat, lon in field_coords])  # note order for shapely: (x, y) = (lon, lat)

    # Calculate longest side for direction
    coords = list(polygon.exterior.coords)
    edges = [(np.linalg.norm(np.array(coords[i]) - np.array(coords[i-1])), (coords[i-1], coords[i])) for i in range(1, len(coords))]
    longest_edge = max(edges, key=lambda x: x[0])[1]
    dx = longest_edge[1][0] - longest_edge[0][0]
    dy = longest_edge[1][1] - longest_edge[0][1]
    angle = np.arctan2(dy, dx)

    # If direction is 'perpendicular', rotate angle by 90 deg
    if direction == 'perpendicular':
        angle += np.pi/2

    # Rotate polygon to align with direction axis
    def rotate_point(x, y, angle):
        return (x*np.cos(angle) + y*np.sin(angle), -x*np.sin(angle) + y*np.cos(angle))

    rotated_coords = [rotate_point(x, y, -angle) for x, y in polygon.exterior.coords]
    min_x = min(c[0] for c in rotated_coords)
    max_x = max(c[0] for c in rotated_coords)

    # Generate parallel lines inside polygon bounds spaced by mower width
    lines = []
    x = min_x + mower_width / 2
    while x < max_x:
        line_coords = []
        for y in np.linspace(min(c[1] for c in rotated_coords), max(c[1] for c in rotated_coords), 100):
            # Rotate back
            rx = x*np.cos(angle) - y*np.sin(angle)
            ry = x*np.sin(angle) + y*np.cos(angle)
            line_coords.append((rx, ry))
        line = LineString(line_coords)
        line_clipped = line.intersection(polygon)
        if not line_clipped.is_empty:
            if line_clipped.geom_type == 'MultiLineString':
                # pick the longest part
                line_clipped = max(line_clipped, key=lambda l: l.length)
            lines.append(line_clipped)

        x += mower_width

    # Convert lines to lat-lon waypoint list
    waypoints = []
    for line in lines:
        if line.geom_type == 'LineString':
            waypoints.append([(lat, lon) for lon, lat in line.coords])
    return waypoints

# Check if polygon roughly matches FIFA field size (105x68m)
def check_fifa_size(field_coords):
    polygon = Polygon([(lon, lat) for lat, lon in field_coords])
    # Approximate polygon bounding box size in meters (using rough equirectangular projection)
    latitudes = [lat for lat, lon in field_coords]
    longitudes = [lon for lat, lon in field_coords]
    avg_lat = np.mean(latitudes)
    # Constants
    meter_per_deg_lat = 111320
    meter_per_deg_lon = 40075000 * np.cos(np.radians(avg_lat)) / 360

    width_m = (max(longitudes) - min(longitudes)) * meter_per_deg_lon
    height_m = (max(latitudes) - min(latitudes)) * meter_per_deg_lat

    # Check if close to FIFA dimensions (within 10%)
    fifa_width, fifa_height = 105, 68
    width_ok = abs(width_m - fifa_width) / fifa_width < 0.1
    height_ok = abs(height_m - fifa_height) / fifa_height < 0.1

    return width_ok and height_ok, width_m, height_m

def main():
    st.title("Football Grass Field Waypoint Generator")

    st.markdown("### Input grass field boundary coordinates (lat, lon) one per line:")
    default_coords = """43.555830, 27.826090
43.555775, 27.826100
43.555422, 27.826747
43.555425, 27.826786
43.556182, 27.827557
43.556217, 27.827538
43.556559, 27.826893
43.556547, 27.826833"""
    coords_text = st.text_area("Coordinates", value=default_coords, height=150)
    field_coords = parse_coords(coords_text)

    st.markdown(f"**Parsed {len(field_coords)} vertices**")

    if len(field_coords) < 3:
        st.error("Please input at least 3 valid coordinates to form a polygon.")
        return

    fifa_check, w_m, h_m = check_fifa_size(field_coords)
    if fifa_check:
        st.success(f"Field approx matches FIFA size: Width={w_m:.1f}m, Height={h_m:.1f}m")
    else:
        st.warning(f"Field size off FIFA standard: Width={w_m:.1f}m, Height={h_m:.1f}m")

    mower_width = st.slider("Mower Operating Width (meters)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
    direction = st.selectbox("Driving Direction", options=['longest', 'perpendicular'], help="Driving direction relative to the longest edge")

    generate = st.button("Generate Waypoints")

    if generate:
        waypoints_lines = generate_waypoints(field_coords, mower_width, direction)

        # Show on map
        m = folium.Map(location=field_coords[0], zoom_start=18)
        folium.Polygon(locations=field_coords, color='green', fill=True, fill_opacity=0.2).add_to(m)

        for line in waypoints_lines:
            folium.PolyLine(locations=line, color='blue', weight=3).add_to(m)

        st_data = st_folium(m, width=700, height=500)

        # Prepare KML for download
        kml = simplekml.Kml()
        for idx, line in enumerate(waypoints_lines):
            ls = kml.newlinestring(name=f'Waypoint Line {idx+1}', coords=[(lon, lat) for lat, lon in line])
            ls.style.linestyle.color = simplekml.Color.blue
            ls.style.linestyle.width = 3

        kml_str = kml.kml()
        kml_bytes = kml_str.encode('utf-8')

        st.download_button(
            label="Download Waypoints KML",
            data=kml_bytes,
            file_name="waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )


if __name__ == "__main__":
    main()
