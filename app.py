import streamlit as st
import folium
from streamlit_folium import st_folium
import simplekml
import io
from shapely.geometry import Polygon, LineString

# Default field boundary coords
DEFAULT_FIELD = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
]

def generate_lines(boundary, mower_width):
    poly = Polygon([(lon, lat) for lat, lon in boundary])
    minx, miny, maxx, maxy = poly.bounds
    lines = []
    y = miny
    while y <= maxy:
        line = LineString([(minx, y), (maxx, y)])
        inter = line.intersection(poly)
        if inter.is_empty:
            y += mower_width
            continue
        if inter.geom_type == "MultiLineString":
            lines.extend(inter.geoms)
        elif inter.geom_type == "LineString":
            lines.append(inter)
        y += mower_width
    return lines

def create_map(boundary, lines):
    avg_lat = sum([pt[0] for pt in boundary]) / len(boundary)
    avg_lon = sum([pt[1] for pt in boundary]) / len(boundary)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=18)
    folium.Polygon(locations=boundary, color="green", fill=True, fill_opacity=0.1).add_to(m)
    for line in lines:
        folium.PolyLine(locations=[(pt[1], pt[0]) for pt in line.coords], color="blue").add_to(m)
    return m

def create_kml(lines):
    kml = simplekml.Kml()
    for line in lines:
        coords = [(pt[0], pt[1]) for pt in line.coords]
        kml.newlinestring(coords=coords)
    kml_str = kml.kml()
    bio = io.BytesIO(kml_str.encode("utf-8"))
    bio.seek(0)
    return bio

st.title("Football Field Waypoint Generator")

coords_text = st.text_area(
    "Field Boundary Coordinates (lat, lon)", 
    "\n".join(f"{lat}, {lon}" for lat, lon in DEFAULT_FIELD), 
    height=100,
)

mower_width = st.number_input("Mower Width (meters)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)

if st.button("Generate"):
    # Parse coords safely
    try:
        boundary = []
        for line in coords_text.strip().split("\n"):
            lat, lon = map(float, line.split(","))
            boundary.append((lat, lon))
        if len(boundary) < 3:
            st.error("Please enter at least 3 points.")
            st.stop()
    except Exception as e:
        st.error(f"Invalid coordinate format: {e}")
        st.stop()

    lines = generate_lines(boundary, mower_width)

    # Save results in session state to persist after reruns
    st.session_state['boundary'] = boundary
    st.session_state['lines'] = lines

if "boundary" in st.session_state and "lines" in st.session_state:
    m = create_map(st.session_state['boundary'], st.session_state['lines'])
    st_folium(m, width=700, height=500)

    kml_bytes = create_kml(st.session_state['lines'])
    st.download_button("Download KML", kml_bytes, "waypoints.kml", "application/vnd.google-earth.kml+xml")
