import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString
import simplekml
import io
import math

# Default grass field boundary coords (lat, lon)
DEFAULT_FIELD = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
]

def parse_coords(text):
    coords = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) != 2:
            continue
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            coords.append((lat, lon))
        except:
            pass
    return coords

def generate_parallel_passes(polygon, width, angle=0):
    """
    Generate simple parallel lines (LineStrings) inside polygon at given angle and spacing (width).
    Simplified: just generate lines bounding polygon bbox, then clip with polygon.
    """
    minx, miny, maxx, maxy = polygon.bounds
    # Create lines along the longer dimension depending on angle
    # We will generate lines spaced by width along the bbox width/height

    lines = []
    # Angle in degrees, convert to radians
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Compute bounding box diagonal length to cover polygon fully
    diag = math.hypot(maxx - minx, maxy - miny)

    # We'll generate lines perpendicular to angle direction, spaced by width
    # Start from a point outside bounding box and move across

    # Project bounding box corners onto axis perpendicular to angle
    def proj(x, y):
        return -sin_a * x + cos_a * y

    min_p = min(proj(x, y) for x, y in [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)])
    max_p = max(proj(x, y) for x, y in [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)])

    current_p = min_p - width * 2
    while current_p <= max_p + width * 2:
        # For each line, we solve for two points far along the line in the rotated space
        # Line formula param: x(t), y(t) = base + t * (cos_a, sin_a)
        # Here, base point is on the line at offset current_p along perpendicular axis

        # Base point at (x0,y0)
        x0 = cos_a * current_p
        y0 = sin_a * current_p

        # Generate long segment along direction
        line_pts = []
        # t ranges large enough to cover bbox
        for t in [-diag * 2, diag * 2]:
            # Solve x,y from perpendicular projection
            # We want points along line perpendicular axis = current_p
            # Actually, here line is parameterized as:
            # x = t * cos_a + x0
            # y = t * sin_a + y0
            x = t * cos_a + x0
            y = t * sin_a + y0
            line_pts.append((x, y))

        line = LineString(line_pts)
        # Clip line with polygon
        clipped = line.intersection(polygon)
        if clipped.is_empty:
            current_p += width
            continue
        if clipped.geom_type == "MultiLineString":
            lines.extend(clipped.geoms)
        elif clipped.geom_type == "LineString":
            lines.append(clipped)
        current_p += width

    return lines

def generate_pitch_marking(polygon):
    """
    Very simplified: just draw outer rectangle polygon as pitch marking.
    """
    # Just return the polygon exterior as one line for demonstration
    return [LineString(polygon.exterior.coords)]

def create_kml_bytes(lines):
    kml = simplekml.Kml()
    for line in lines:
        coords = [(pt[0], pt[1]) for pt in list(line.coords)]  # (lon, lat)
        # simplekml expects (lon, lat)
        kml.newlinestring(name="WaypointPath", coords=coords)
    kml_bytes = io.BytesIO()
    kml.save(kml_bytes)
    kml_bytes.seek(0)
    return kml_bytes

def main():
    st.title("Football Field Waypoints Generator")

    coords_text = st.text_area(
        "Enter grass field boundary coordinates (lat, lon), one per line:",
        value="\n".join([f"{lat}, {lon}" for lat, lon in DEFAULT_FIELD]),
        height=150,
    )
    coords = parse_coords(coords_text)

    if len(coords) < 3:
        st.warning("Please input at least 3 valid coordinates for the polygon.")
        return

    polygon = Polygon([(lon, lat) for lat, lon in coords])  # Note shapely x=lon, y=lat

    mower_width = st.number_input("Mower Operating Width (meters)", min_value=0.5, max_value=10.0, value=1.0, step=0.1)

    task = st.selectbox("Select Task", ["Grass Cutting", "Striping", "Pitch Marking"])

    striping_pattern = None
    if task == "Striping":
        striping_pattern = st.selectbox("Select Striping Pattern", ["Basic Stripes", "Checkerboard", "Diagonal"])

    if st.button("Generate Waypoints"):
        # Generate waypoints lines based on task
        lines = []
        if task == "Grass Cutting":
            lines = generate_parallel_passes(polygon, mower_width, angle=0)
        elif task == "Striping":
            if striping_pattern == "Basic Stripes":
                lines = generate_parallel_passes(polygon, mower_width, angle=0)
            elif striping_pattern == "Checkerboard":
                lines = generate_parallel_passes(polygon, mower_width, angle=0) + generate_parallel_passes(polygon, mower_width, angle=90)
            elif striping_pattern == "Diagonal":
                lines = generate_parallel_passes(polygon, mower_width, angle=45)
        elif task == "Pitch Marking":
            lines = generate_pitch_marking(polygon)

        # Show map
        m = folium.Map(location=[coords[0][0], coords[0][1]], zoom_start=18)
        folium.Polygon(locations=coords, color="green", fill=False, weight=3).add_to(m)

        for line in lines:
            # line.coords are (x=lon, y=lat)
            line_latlon = [(pt[1], pt[0]) for pt in list(line.coords)]
            color = "blue" if task != "Pitch Marking" else "white"
            folium.PolyLine(line_latlon, color=color, weight=3).add_to(m)

        st_folium(m, width=700, height=500)

        # Create KML for download
        kml_bytes = create_kml_bytes(lines)
        st.download_button("Download KML", kml_bytes, file_name="waypoints.kml", mime="application/vnd.google-earth.kml+xml")

if __name__ == "__main__":
    main()
