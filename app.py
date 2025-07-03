import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import translate, rotate
import simplekml

import math

# Default field boundary coordinates (lat, lon)
DEFAULT_FIELD = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693)
]

def parse_coords(text):
    """Parse input coordinates from multiline text into list of (lat, lon)."""
    coords = []
    for line in text.strip().split("\n"):
        parts = line.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                coords.append((lat, lon))
            except:
                pass
    return coords

def generate_parallel_passes(polygon, width, angle=0):
    """
    Generate parallel lines inside polygon with spacing = width.
    angle in degrees defines driving direction.
    Returns list of LineString waypoints (paths).
    """
    # Rotate polygon to align with driving direction
    rotated_poly = rotate(polygon, -angle, origin='centroid', use_radians=False)
    minx, miny, maxx, maxy = rotated_poly.bounds

    lines = []
    y = miny + width/2
    while y < maxy:
        line = LineString([(minx, y), (maxx, y)])
        # intersect with polygon to cut line
        intersected = line.intersection(rotated_poly)
        if not intersected.is_empty:
            # Could be MultiLineString if multiple parts
            if intersected.geom_type == 'MultiLineString':
                for segment in intersected:
                    lines.append(segment)
            elif intersected.geom_type == 'LineString':
                lines.append(intersected)
        y += width

    # Rotate lines back
    final_lines = [rotate(line, angle, origin=polygon.centroid, use_radians=False) for line in lines]
    return final_lines

def generate_pitch_marking(polygon):
    """
    Generate fixed FIFA pitch marking waypoints based on polygon centroid.
    This is simplified and assumes rectangle approx.
    Returns list of LineStrings and Points (for arcs etc).
    """
    # Extract centroid and approximate pitch rectangle based on polygon bounds
    # Using FIFA standard: 105x68 meters (approx convert to degrees)
    # For demo, we just create rectangular lines inside polygon bounds
    minx, miny, maxx, maxy = polygon.bounds

    # You'd need real geodetic calculation or a projected system here
    # For simplicity, just use bounds

    pitch_lines = []

    # Outer rectangle (pitch boundary)
    pitch_lines.append(LineString([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)]))

    # Center line
    pitch_lines.append(LineString([(minx + (maxx - minx)/2, miny), (minx + (maxx - minx)/2, maxy)]))

    # Center circle (approximate with points)
    # For simplicity, we won’t draw arcs here, just points

    return pitch_lines

def create_kml(lines, filename="waypoints.kml"):
    kml = simplekml.Kml()
    for line in lines:
        coords = [(pt[0], pt[1]) for pt in list(line.coords)]
        kml.newlinestring(name="Path", coords=coords)
    kml.save(filename)

def main():
    st.title("Football Field Robotics Waypoints Generator")

    st.markdown("Input the grass field boundary coordinates (lat, lon), one per line:")

    input_coords_text = st.text_area("Field boundary coordinates", 
                                    value="\n".join([f"{lat}, {lon}" for lat, lon in DEFAULT_FIELD]), height=150)
    
    coords = parse_coords(input_coords_text)
    if len(coords) < 3:
        st.error("Please input at least 3 coordinates for the field boundary polygon.")
        return

    polygon = Polygon([(lon, lat) for lat, lon in coords])  # shapely uses (x,y) = (lon, lat)

    mower_width = st.number_input("Mower operating width (meters)", min_value=0.5, max_value=10.0, value=1.0, step=0.1)

    task = st.selectbox("Select task", ["Grass Cutting", "Striping", "Pitch Marking"])

    striping_pattern = None
    if task == "Striping":
        striping_pattern = st.selectbox("Select striping pattern", ["Basic Stripes", "Checkerboard", "Diagonal"])

    generate_button = st.button("Generate Waypoints")

    if generate_button:
        m = folium.Map(location=[coords[0][0], coords[0][1]], zoom_start=18)

        if task in ["Grass Cutting", "Striping"]:
            angle = 0
            if task == "Striping" and striping_pattern == "Checkerboard":
                # For checkerboard, generate two passes with 0 and 90 degrees and merge
                lines1 = generate_parallel_passes(polygon, mower_width, angle=0)
                lines2 = generate_parallel_passes(polygon, mower_width, angle=90)
                lines = lines1 + lines2
            elif task == "Striping" and striping_pattern == "Diagonal":
                lines = generate_parallel_passes(polygon, mower_width, angle=45)
            else:
                # Basic stripes or Grass Cutting same direction
                lines = generate_parallel_passes(polygon, mower_width, angle=0)

            # Add polygon boundary
            folium.Polygon(locations=coords, color="green", fill=False).add_to(m)

            # Plot lines
            for line in lines:
                line_coords = [(pt[1], pt[0]) for pt in list(line.coords)]  # folium uses (lat, lon)
                folium.PolyLine(line_coords, color="blue", weight=2).add_to(m)

            # Save KML file
            create_kml(lines, "waypoints.kml")
            st.success("Waypoints generated! You can download the KML file below.")

            with open("waypoints.kml", "rb") as f:
                st.download_button("Download KML", f, "waypoints.kml")

            st_folium(m, width=700, height=500)

        elif task == "Pitch Marking":
            lines = generate_pitch_marking(polygon)
            folium.Polygon(locations=coords, color="green", fill=False).add_to(m)

            for line in lines:
                line_coords = [(pt[1], pt[0]) for pt in list(line.coords)]
                folium.PolyLine(line_coords, color="white", weight=3).add_to(m)

            # Save KML
            create_kml(lines, "pitch_marking.kml")
            st.success("Pitch marking generated! Download KML below.")

            with open("pitch_marking.kml", "rb") as f:
                st.download_button("Download KML", f, "pitch_marking.kml")

            st_folium(m, width=700, height=500)

if __name__ == "__main__":
    main()
