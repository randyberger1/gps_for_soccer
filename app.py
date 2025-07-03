import streamlit as st
import folium
from streamlit_folium import st_folium
from io import BytesIO

st.set_page_config(page_title="Football Field Waypoints Generator", layout="wide")

st.title("Football Grass Field Waypoints Generator")

# Default boundary coordinates (lat, lon)
DEFAULT_BOUNDARY = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
]

# Utility: generate waypoints by simple parallel lines for demo
def generate_waypoints(boundary, mower_width, task):
    # For simplicity: generate parallel lines between min/max lat with spacing = mower_width meters approx in lat degrees
    # 1 meter ~ 0.000009 degrees latitude (approx)
    spacing_deg = mower_width * 0.000009
    lats = [p[0] for p in boundary]
    lons = [p[1] for p in boundary]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    lines = []
    current_lat = min_lat

    while current_lat <= max_lat:
        # Create line at this latitude between min_lon and max_lon
        line = [(current_lat, min_lon), (current_lat, max_lon)]
        lines.append(line)
        current_lat += spacing_deg

    # For pitch marking task, add rectangle outline as a single polygon line (for demo)
    if task == "pitch marking":
        lines = [boundary]  # Just the boundary polygon line

    return lines

# Export KML file content from waypoint lines
def export_kml(waypoint_lines):
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>'''
    kml_footer = "</Document></kml>"

    placemarks = ""
    for i, line in enumerate(waypoint_lines):
        coords_str = " ".join([f"{lon},{lat},0" for lat, lon in line])
        placemark = f"""
    <Placemark>
      <name>Line {i+1}</name>
      <LineString>
        <coordinates>{coords_str}</coordinates>
      </LineString>
    </Placemark>"""
        placemarks += placemark

    return kml_header + placemarks + kml_footer


# --- Streamlit UI ---

with st.sidebar:
    st.header("Input Parameters")

    # Boundary input as multiline text box
    boundary_text = st.text_area(
        "Grass Field Boundary Coordinates (lat, lon per line, comma-separated):",
        value="\n".join([f"{lat},{lon}" for lat, lon in DEFAULT_BOUNDARY]),
        height=150,
    )

    # Parse boundary input
    boundary = []
    for line in boundary_text.strip().split("\n"):
        parts = line.strip().split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                boundary.append((lat, lon))
            except ValueError:
                pass

    mower_width = st.number_input(
        "Mower Operating Width (meters)", min_value=0.1, max_value=10.0, value=1.0, step=0.1
    )

    task = st.selectbox(
        "Select Task",
        options=["grass cutting", "striping", "pitch marking"],
        index=0,
    )

    generate = st.button("Generate Waypoints")

if generate:
    if len(boundary) < 3:
        st.error("Please provide at least 3 valid boundary coordinates.")
    else:
        waypoints_list = generate_waypoints(boundary, mower_width, task)
        st.session_state["waypoints_list"] = waypoints_list
        st.session_state["boundary_latlon"] = boundary

if "waypoints_list" in st.session_state and "boundary_latlon" in st.session_state:
    waypoints_list = st.session_state["waypoints_list"]
    boundary_latlon = st.session_state["boundary_latlon"]

    show_map = st.checkbox("Show Map Visualization", value=True)

    if show_map:
        st.markdown("### Select which waypoint lines to display:")
        show_lines = []
        for i in range(len(waypoints_list)):
            show = st.checkbox(f"Line {i+1}", value=True, key=f"line_{i}")
            show_lines.append(show)

        m = folium.Map(location=boundary_latlon[0], zoom_start=18)
        folium.Polygon(locations=boundary_latlon, color="green", weight=3, fill=False).add_to(m)

        colors = ["red", "blue", "white", "yellow", "cyan"]
        for i, line in enumerate(waypoints_list):
            if show_lines[i]:
                folium.PolyLine(locations=line, color=colors[i % len(colors)], weight=2).add_to(m)

        st_folium(m, width=700, height=500)
    else:
        st.info("Map visualization is hidden. You can enable it by checking 'Show Map Visualization'.")

    # KML Download button
    kml_data = export_kml(waypoints_list)
    kml_bytes = kml_data.encode("utf-8")
    st.download_button(
        label="Download Waypoints as KML (all lines)",
        data=kml_bytes,
        file_name="waypoints.kml",
        mime="application/vnd.google-earth.kml+xml",
    )
