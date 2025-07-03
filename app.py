import streamlit as st
import folium
from folium import Map, PolyLine, Polygon as FoliumPolygon
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString
from shapely.affinity import rotate
import numpy as np
from io import BytesIO
import simplekml

st.set_page_config(layout="wide")

def find_longest_edge(polygon: Polygon):
    coords = list(polygon.exterior.coords)
    max_len = 0
    longest_segment = None
    for i in range(len(coords)-1):
        p1 = np.array(coords[i])
        p2 = np.array(coords[i+1])
        dist = np.linalg.norm(p2 - p1)
        if dist > max_len:
            max_len = dist
            longest_segment = (p1, p2)
    return longest_segment

def angle_of_segment(p1, p2):
    delta = p2 - p1
    angle_rad = np.arctan2(delta[1], delta[0])
    return np.degrees(angle_rad)

def generate_parallel_lines(polygon: Polygon, line_width_m: float, angle_deg: float):
    # Approximate meters to degrees latitude (~0.000009 deg per meter)
    spacing_deg = line_width_m * 0.000009

    # Rotate polygon so lines are horizontal (0 deg)
    rotated = rotate(polygon, -angle_deg, origin='centroid', use_radians=False)
    minx, miny, maxx, maxy = rotated.bounds

    lines = []
    y = miny
    while y <= maxy:
        base_line = LineString([(minx, y), (maxx, y)])
        # Rotate line back to original orientation
        rotated_line = rotate(base_line, angle_deg, origin='centroid', use_radians=False)
        clipped = rotated_line.intersection(polygon)
        if clipped.is_empty:
            y += spacing_deg
            continue
        if clipped.geom_type == "MultiLineString":
            for segment in clipped.geoms:
                lines.append(list(segment.coords))
        elif clipped.geom_type == "LineString":
            lines.append(list(clipped.coords))
        y += spacing_deg
    return lines

def lines_to_kml(lines, kml_filename="waypoints.kml"):
    kml = simplekml.Kml()
    for idx, line in enumerate(lines):
        ls = kml.newlinestring(name=f"Line {idx+1}", coords=line)
        ls.style.linestyle.color = simplekml.Color.red
        ls.style.linestyle.width = 3
    kml_bytes = kml.kml()
    return kml_bytes

def create_map(boundary, lines, show=True):
    if not show:
        return None
    center_lat = np.mean([pt[0] for pt in boundary])
    center_lon = np.mean([pt[1] for pt in boundary])
    m = Map(location=[center_lat, center_lon], zoom_start=17)

    # Draw polygon
    FoliumPolygon(locations=boundary, color="green", fill=True, fill_opacity=0.3, weight=3).add_to(m)

    # Draw lines
    for line in lines:
        FoliumPolyline = PolyLine(locations=line, color="blue", weight=2)
        FoliumPolyline.add_to(m)

    return m

def main():
    st.title("Football Grass Field Waypoint Generator")

    st.markdown("""
    Input the grass field boundary as a list of latitude,longitude points (non-rectangular allowed).
    Select mower operating width and driving course pattern.
    Generate waypoints and optionally show them on the map.
    Export waypoints as a KML file for robot navigation.
    """)

    default_boundary = [
        (43.699047, 27.840622),
        (43.699011, 27.841512),
        (43.699956, 27.841568),
        (43.699999, 27.840693),
        (43.699800, 27.840500),  # added extra points to simulate a polygon with >4 points
        (43.699500, 27.840400),
        (43.699200, 27.840450),
        (43.699000, 27.840500)
    ]

    boundary_input = st.text_area(
        "Enter polygon vertices as lat,lon per line",
        value="\n".join([f"{lat},{lon}" for lat, lon in default_boundary]),
        height=150
    )

    try:
        boundary = []
        for line in boundary_input.strip().split("\n"):
            lat_str, lon_str = line.strip().split(",")
            boundary.append((float(lat_str), float(lon_str)))
        if len(boundary) < 3:
            st.error("Please enter at least 3 vertices.")
            return
    except Exception as e:
        st.error(f"Error parsing coordinates: {e}")
        return

    mower_width = st.number_input("Mower operating width (meters)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)

    course_type = st.selectbox(
        "Driving Course Pattern",
        options=["parallel to longest side", "perpendicular to longest side", "checkerboard", "diagonal"]
    )

    show_map = st.checkbox("Show map visualization", value=True)

    if st.button("Generate Waypoints"):
        polygon = Polygon(boundary)
        longest_seg = find_longest_edge(polygon)
        p1, p2 = longest_seg
        longest_angle = angle_of_segment(p1, p2)

        st.write(f"Longest side angle: {longest_angle:.2f} degrees")

        if course_type == "parallel to longest side":
            lines = generate_parallel_lines(polygon, mower_width, longest_angle)
        elif course_type == "perpendicular to longest side":
            perp_angle = (longest_angle + 90) % 360
            lines = generate_parallel_lines(polygon, mower_width, perp_angle)
        elif course_type == "checkerboard":
            lines1 = generate_parallel_lines(polygon, mower_width, longest_angle)
            perp_angle = (longest_angle + 90) % 360
            lines2 = generate_parallel_lines(polygon, mower_width, perp_angle)
            lines = lines1 + lines2
        elif course_type == "diagonal":
            if len(boundary) >= 3:
                diag_angle = angle_of_segment(np.array(boundary[0]), np.array(boundary[2]))
                lines = generate_parallel_lines(polygon, mower_width, diag_angle)
            else:
                lines = []
        else:
            lines = []

        st.success(f"Generated {len(lines)} waypoint lines.")

        kml_bytes = lines_to_kml(lines)

        st.download_button(
            label="Download KML file",
            data=kml_bytes,
            file_name="waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

        if show_map:
            m = create_map(boundary, lines, show=True)
            st_data = st_folium(m, width=700, height=500)
        else:
            st.info("Map visualization is disabled.")

if __name__ == "__main__":
    main()
