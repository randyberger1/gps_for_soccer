import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString, Point
from shapely import affinity
from shapely.ops import unary_union
from pyproj import Transformer
import simplekml
import io
import math

# ---- Coordinate conversion setup ----
# Use UTM zone 35N (adjust if your coords are elsewhere)
to_utm = Transformer.from_crs("epsg:4326", "epsg:32635", always_xy=True)
to_latlon = Transformer.from_crs("epsg:32635", "epsg:4326", always_xy=True)

# ---- Default boundary: 7 vertices polygon (stadium) ----
DEFAULT_BOUNDARY_LATLON = [
    (43.555830, 27.826090),
    (43.555775, 27.826100),
    (43.555422, 27.826747),
    (43.555425, 27.826786),
    (43.556182, 27.827557),
    (43.556217, 27.827538),
    (43.556559, 27.826893),
]

# ---- Utility functions ----

def latlon_to_utm(polygon_latlon):
    """Convert list of (lat, lon) to list of (x, y) UTM"""
    return [to_utm.transform(lon, lat) for lat, lon in polygon_latlon]

def utm_to_latlon(coords_utm):
    """Convert list of (x, y) UTM to (lat, lon)"""
    return [(to_latlon.transform(x, y)[1], to_latlon.transform(x, y)[0]) for x, y in coords_utm]

def generate_headland_passes(field_poly, mower_width, num_passes):
    """Generate list of inward offset polygons for headland passes"""
    passes = []
    for i in range(num_passes):
        offset_dist = -mower_width * (i + 1)
        offset_poly = field_poly.buffer(offset_dist)
        if offset_poly.is_empty or not offset_poly.is_valid:
            break
        # If MultiPolygon from buffering, unify it to one polygon
        if offset_poly.geom_type == 'MultiPolygon':
            offset_poly = unary_union(offset_poly)
        passes.append(offset_poly)
    return passes

def angle_between_points(p1, p2):
    """Calculate angle in degrees between horizontal axis and line p1->p2"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle_rad = math.atan2(dy, dx)
    return math.degrees(angle_rad)

def generate_parallel_tracks(polygon, mower_width, driving_angle_deg):
    """
    Generate parallel mowing lines inside polygon
    spaced by mower_width, oriented by driving_angle_deg
    """
    bounds = polygon.bounds  # minx, miny, maxx, maxy
    minx, miny, maxx, maxy = bounds
    # Rotate polygon so mowing lines are vertical (parallel to Y axis)
    rotated = affinity.rotate(polygon, -driving_angle_deg, origin='centroid', use_radians=False)
    rotated_bounds = rotated.bounds
    r_minx, r_miny, r_maxx, r_maxy = rotated_bounds

    tracks = []
    x = r_minx
    while x <= r_maxx:
        # create vertical line at x spanning polygon height
        line = LineString([(x, r_miny), (x, r_maxy)])
        # intersect with polygon
        clipped = line.intersection(rotated)
        if clipped.is_empty:
            x += mower_width
            continue
        # clipped can be LineString or MultiLineString
        if clipped.geom_type == 'MultiLineString':
            for segment in clipped.geoms:
                tracks.append(segment)
        elif clipped.geom_type == 'LineString':
            tracks.append(clipped)
        x += mower_width

    # Rotate tracks back to original orientation
    tracks_rotated_back = [affinity.rotate(track, driving_angle_deg, origin='centroid', use_radians=False) for track in tracks]

    return tracks_rotated_back

def tracks_to_latlon(tracks):
    """Convert list of shapely linestrings in UTM to latlon coords"""
    all_tracks_latlon = []
    for line in tracks:
        coords_utm = list(line.coords)
        coords_latlon = utm_to_latlon(coords_utm)
        all_tracks_latlon.append(coords_latlon)
    return all_tracks_latlon

def export_kml(tracks_latlon):
    kml = simplekml.Kml()
    for idx, track in enumerate(tracks_latlon):
        ls = kml.newlinestring(name=f"Track {idx+1}", coords=[(lon, lat) for lat, lon in track])
        ls.style.linestyle.color = simplekml.Color.red
        ls.style.linestyle.width = 2
    kml_bytes = io.BytesIO()
    kml.save(kml_bytes)
    kml_bytes.seek(0)
    return kml_bytes

def plot_map(field_latlon, headlands, tracks_latlon):
    # Center map roughly on field centroid
    lats = [pt[0] for pt in field_latlon]
    lons = [pt[1] for pt in field_latlon]
    center = (sum(lats) / len(lats), sum(lons) / len(lons))

    m = folium.Map(location=center, zoom_start=18)

    # Draw field polygon
    folium.Polygon(field_latlon, color='green', fill=True, fill_opacity=0.3, popup="Field Boundary").add_to(m)

    # Draw headland passes
    for idx, poly in enumerate(headlands):
        latlon = utm_to_latlon(list(poly.exterior.coords))
        folium.Polygon(latlon, color='orange', fill=False, weight=2, popup=f"Headland Pass {idx+1}").add_to(m)

    # Draw mowing tracks
    for idx, track in enumerate(tracks_latlon):
        folium.PolyLine(track, color='blue', weight=2, popup=f"Track {idx+1}").add_to(m)

    return m

# ---- Streamlit app ----

def main():
    st.title("Autonomous Grass Cutting Path Generator")

    st.markdown("""
    This tool generates mowing paths based on stadium boundaries, mower width, headland passes, and driving direction.
    Coordinates are processed in UTM (meters) for accuracy.
    """)

    # Input polygon coords
    input_coords_str = st.text_area("Field boundary coordinates (lat, lon per line, comma-separated):",
                                   value="\n".join([f"{lat}, {lon}" for lat, lon in DEFAULT_BOUNDARY_LATLON]),
                                   height=140)
    coords_lines = input_coords_str.strip().split("\n")
    try:
        boundary_latlon = [tuple(map(float, line.strip().split(","))) for line in coords_lines]
    except Exception:
        st.error("Invalid coordinates format!")
        return

    mower_width = st.number_input("Mower operating width (meters):", min_value=0.5, max_value=10.0, value=2.0, step=0.1)
    num_headland = st.number_input("Number of headland passes:", min_value=0, max_value=10, value=2, step=1)

    # Select driving direction by picking two boundary points
    st.markdown("Select driving direction (line between two boundary vertices):")
    idx1 = st.number_input("First vertex index (0-based):", min_value=0, max_value=len(boundary_latlon)-1, value=0)
    idx2 = st.number_input("Second vertex index (0-based):", min_value=0, max_value=len(boundary_latlon)-1, value=1)
    if idx1 == idx2:
        st.error("Select two different vertices for driving direction.")
        return

    show_map = st.checkbox("Show generated map", value=True)

    if st.button("Generate Paths"):
        # Convert boundary to UTM polygon
        boundary_utm = latlon_to_utm(boundary_latlon)
        field_poly = Polygon(boundary_utm)
        if not field_poly.is_valid:
            st.warning("Warning: Field polygon is invalid. Please check coordinates.")

        # Generate headland passes
        headland_polys = generate_headland_passes(field_poly, mower_width, num_headland)

        # Inner polygon for mowing tracks
        inner_poly = headland_polys[-1] if headland_polys else field_poly

        # Calculate driving direction angle in UTM
        p1 = boundary_utm[idx1]
        p2 = boundary_utm[idx2]
        driving_angle = angle_between_points(p1, p2)

        # Generate mowing tracks inside inner polygon
        tracks = generate_parallel_tracks(inner_poly, mower_width, driving_angle)
        tracks_latlon = tracks_to_latlon(tracks)

        # Map visualization
        if show_map:
            m = plot_map(boundary_latlon, headland_polys, tracks_latlon)
            st_folium(m, width=700, height=500)

        # Export KML
        kml_bytes = export_kml(tracks_latlon)
        st.download_button("Download KML file", kml_bytes, file_name="mowing_tracks.kml", mime="application/vnd.google-earth.kml+xml")

if __name__ == "__main__":
    main()
