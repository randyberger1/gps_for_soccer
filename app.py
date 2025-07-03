import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString, Point
import simplekml
import io
import math

# --- Utils for converting between lat/lon and UTM-ish meters (approx) ---
# For simplicity, we do minimal conversion here (assuming small areas)

def latlon_to_xy(latlon, origin):
    """Convert lat/lon to local xy meters relative to origin (approx)."""
    lat0, lon0 = origin
    R = 6371000  # Earth radius in meters
    x = (latlon[1] - lon0) * math.cos(math.radians(lat0)) * R
    y = (latlon[0] - lat0) * R
    return (x, y)

def xy_to_latlon(xy, origin):
    """Convert local xy meters relative to origin to lat/lon (approx)."""
    lat0, lon0 = origin
    R = 6371000
    lat = xy[1]/R + lat0
    lon = xy[0]/(R * math.cos(math.radians(lat0))) + lon0
    return (lat, lon)

# --- Waypoint generation functions ---

def generate_grass_cutting_waypoints(boundary_latlon, mower_width):
    """
    Generate simple parallel tracks covering the polygon.
    We'll:
    - convert latlon to xy
    - create parallel lines spaced by mower_width inside the polygon bounding box
    - clip each line to the polygon
    """
    origin = boundary_latlon[0]
    poly_xy = [latlon_to_xy(pt, origin) for pt in boundary_latlon]
    polygon = Polygon(poly_xy)

    minx, miny, maxx, maxy = polygon.bounds
    lines = []
    y = miny
    while y <= maxy:
        line = LineString([(minx, y), (maxx, y)])
        clipped = line.intersection(polygon)
        if clipped.is_empty:
            y += mower_width
            continue
        # clipped can be MultiLineString or LineString
        if clipped.geom_type == 'LineString':
            lines.append(clipped)
        elif clipped.geom_type == 'MultiLineString':
            lines.extend(list(clipped))
        y += mower_width

    # convert lines back to latlon
    waypoints = []
    for line in lines:
        coords = [xy_to_latlon(pt, origin) for pt in line.coords]
        waypoints.append(coords)
    return waypoints

def generate_striping_waypoints(boundary_latlon, mower_width, pattern):
    """
    Generate stripe patterns.
    For simplicity:
    - BSP (basic): same as grass cutting
    - CSP (checkerboard): grass cutting lines + perpendicular lines
    - DSP (diagonal): diagonal lines at 45 degrees across bounding box
    """
    origin = boundary_latlon[0]
    poly_xy = [latlon_to_xy(pt, origin) for pt in boundary_latlon]
    polygon = Polygon(poly_xy)
    minx, miny, maxx, maxy = polygon.bounds

    waypoints = []

    if pattern == "Basic Stripe Pattern":
        return generate_grass_cutting_waypoints(boundary_latlon, mower_width)

    if pattern == "Checkerboard Stripe Pattern":
        # horizontal lines
        horizontal_lines = []
        y = miny
        while y <= maxy:
            line = LineString([(minx, y), (maxx, y)])
            clipped = line.intersection(polygon)
            if clipped.is_empty:
                y += mower_width
                continue
            if clipped.geom_type == 'LineString':
                horizontal_lines.append(clipped)
            elif clipped.geom_type == 'MultiLineString':
                horizontal_lines.extend(list(clipped))
            y += mower_width

        # vertical lines
        vertical_lines = []
        x = minx
        while x <= maxx:
            line = LineString([(x, miny), (x, maxy)])
            clipped = line.intersection(polygon)
            if clipped.is_empty:
                x += mower_width
                continue
            if clipped.geom_type == 'LineString':
                vertical_lines.append(clipped)
            elif clipped.geom_type == 'MultiLineString':
                vertical_lines.extend(list(clipped))
            x += mower_width

        for line in horizontal_lines + vertical_lines:
            coords = [xy_to_latlon(pt, origin) for pt in line.coords]
            waypoints.append(coords)
        return waypoints

    if pattern == "Diagonal Stripe Pattern":
        # lines at 45 degrees spaced by mower_width
        # calculate length of diagonal bounding box
        diag_length = math.hypot(maxx - minx, maxy - miny)
        spacing = mower_width / math.sqrt(2)
        offsets = []
        offset = -diag_length
        while offset <= diag_length:
            offsets.append(offset)
            offset += spacing

        diagonal_lines = []
        for offset in offsets:
            # line from (minx, miny+offset) to (minx+offset, miny)
            p1 = (minx, miny + offset)
            p2 = (minx + offset, miny)
            line = LineString([p1, p2])
            # extend line to bounding box rectangle for intersection
            extended_line = line.parallel_offset(diag_length*2, 'right')
            clipped = extended_line.intersection(polygon)
            if clipped.is_empty:
                continue
            if clipped.geom_type == 'LineString':
                diagonal_lines.append(clipped)
            elif clipped.geom_type == 'MultiLineString':
                diagonal_lines.extend(list(clipped))
        for line in diagonal_lines:
            coords = [xy_to_latlon(pt, origin) for pt in line.coords]
            waypoints.append(coords)
        return waypoints

    # fallback to basic grass cutting
    return generate_grass_cutting_waypoints(boundary_latlon, mower_width)

def generate_pitch_marking_waypoints(boundary_latlon):
    """
    Generate the standard FIFA pitch markings:
    - Outer boundary (the playing field)
    - Center line
    - Center circle
    - Penalty areas and arcs
    - Goal areas
    - Corner arcs

    Assume field is rectangular approx.
    """

    origin = boundary_latlon[0]
    poly_xy = [latlon_to_xy(pt, origin) for pt in boundary_latlon]
    polygon = Polygon(poly_xy)

    # Standard FIFA pitch dimensions (meters)
    lp = 105  # length
    wp = 68   # width

    # Let's assume the pitch is aligned with the boundary's bounding box
    # Get bounding box center:
    minx, miny, maxx, maxy = polygon.bounds
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2

    # Calculate offset to center the pitch inside the boundary
    field_minx = center_x - lp/2
    field_maxx = center_x + lp/2
    field_miny = center_y - wp/2
    field_maxy = center_y + wp/2

    # Create polygons/lines for pitch markings
    waypoints = []

    # Outer boundary (rectangle)
    outer = [
        (field_minx, field_miny),
        (field_maxx, field_miny),
        (field_maxx, field_maxy),
        (field_minx, field_maxy),
        (field_minx, field_miny),
    ]
    waypoints.append([xy_to_latlon(pt, origin) for pt in outer])

    # Center line
    center_line = [(center_x, field_miny), (center_x, field_maxy)]
    waypoints.append([xy_to_latlon(pt, origin) for pt in center_line])

    # Center circle (circle of radius 9.15m)
    center_circle = []
    radius = 9.15
    for angle_deg in range(0, 361, 5):
        angle_rad = math.radians(angle_deg)
        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)
        center_circle.append(xy_to_latlon((x, y), origin))
    waypoints.append(center_circle)

    # Penalty area dimensions
    penalty_length = 40.32
    penalty_width = 16.5

    # Left penalty area (near minx)
    left_penalty = [
        (field_minx, center_y - penalty_width/2),
        (field_minx + penalty_length, center_y - penalty_width/2),
        (field_minx + penalty_length, center_y + penalty_width/2),
        (field_minx, center_y + penalty_width/2),
        (field_minx, center_y - penalty_width/2),
    ]
    waypoints.append([xy_to_latlon(pt, origin) for pt in left_penalty])

    # Right penalty area (near maxx)
    right_penalty = [
        (field_maxx, center_y - penalty_width/2),
        (field_maxx - penalty_length, center_y - penalty_width/2),
        (field_maxx - penalty_length, center_y + penalty_width/2),
        (field_maxx, center_y + penalty_width/2),
        (field_maxx, center_y - penalty_width/2),
    ]
    waypoints.append([xy_to_latlon(pt, origin) for pt in right_penalty])

    # Penalty arcs - 9.15m radius arcs at penalty spots
    penalty_spot_dist = 11
    left_penalty_spot = (field_minx + penalty_spot_dist, center_y)
    right_penalty_spot = (field_maxx - penalty_spot_dist, center_y)

    def generate_arc(center, radius, start_angle, end_angle, steps=20):
        arc_pts = []
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            x = center[0] + radius * math.cos(math.radians(angle))
            y = center[1] + radius * math.sin(math.radians(angle))
            arc_pts.append(xy_to_latlon((x, y), origin))
        return arc_pts

    # Left penalty arc - from ~310° to 50° (clockwise)
    left_arc = generate_arc(left_penalty_spot, 9.15, 310, 50)
    waypoints.append(left_arc)

    # Right penalty arc - from ~130° to 230°
    right_arc = generate_arc(right_penalty_spot, 9.15, 130, 230)
    waypoints.append(right_arc)

    # Goal area dimensions
    goal_length = 18.32
    goal_width = 5.5

    # Left goal area
    left_goal = [
        (field_minx, center_y - goal_width/2),
        (field_minx + goal_length, center_y - goal_width/2),
        (field_minx + goal_length, center_y + goal_width/2),
        (field_minx, center_y + goal_width/2),
        (field_minx, center_y - goal_width/2),
    ]
    waypoints.append([xy_to_latlon(pt, origin) for pt in left_goal])

    # Right goal area
    right_goal = [
        (field_maxx, center_y - goal_width/2),
        (field_maxx - goal_length, center_y - goal_width/2),
        (field_maxx - goal_length, center_y + goal_width/2),
        (field_maxx, center_y + goal_width/2),
        (field_maxx, center_y - goal_width/2),
    ]
    waypoints.append([xy_to_latlon(pt, origin) for pt in right_goal])

    # Corner arcs - radius 1m at four corners (quarter circles)
    corner_radius = 1.0
    corners = [
        (field_minx, field_miny),
        (field_minx, field_maxy),
        (field_maxx, field_miny),
        (field_maxx, field_maxy),
    ]

    # Arcs: bottom-left (270 to 360), top-left (0 to 90), bottom-right (180 to 270), top-right (90 to 180)
    corner_angles = [
        (270, 360),
        (0, 90),
        (180, 270),
        (90, 180),
    ]

    for center_corner, (start_ang, end_ang) in zip(corners, corner_angles):
        arc = generate_arc(center_corner, corner_radius, start_ang, end_ang)
        waypoints.append(arc)

    return waypoints

# --- KML export function ---

def export_kml(waypoints_list):
    kml = simplekml.Kml()
    for i, coords in enumerate(waypoints_list):
        ls = kml.newlinestring(name=f'Line {i+1}')
        ls.coords = [(lon, lat) for lat, lon in coords]  # Note order lon,lat in KML
        ls.style.linestyle.color = simplekml.Color.white
        ls.style.linestyle.width = 2
    return kml.kml()

# --- Default boundary (your coords) ---

DEFAULT_BOUNDARY = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
]

# --- Streamlit App ---

def main():
    st.title("Football Field Waypoint Generator")

    st.markdown("""
    Input grass field boundary coordinates as latitude and longitude points (one pair per line, comma separated).  
    Select a task and mower width / pattern as needed.  
    Generate waypoints and download as KML for robot navigation.
    """)

    boundary_input = st.text_area(
        "Field Boundary Coordinates (lat, lon per line):",
        value="\n".join([f"{lat},{lon}" for lat, lon in DEFAULT_BOUNDARY]),
        height=120,
    )

    task = st.selectbox("Select Task", ["Grass Cutting", "Striping", "Pitch Marking"])

    mower_width = None
    stripe_pattern = None

    if task in ["Grass Cutting", "Striping"]:
        mower_width = st.number_input(
            "Mower Operating Width (meters):", min_value=0.1, value=5.0, step=0.1
        )
    if task == "Striping":
        stripe_pattern = st.selectbox(
            "Select Striping Pattern",
            ["Basic Stripe Pattern", "Checkerboard Stripe Pattern", "Diagonal Stripe Pattern"],
        )

    # Parse input boundary
    try:
        boundary_latlon = []
        for line in boundary_input.strip().split("\n"):
            lat_str, lon_str = line.strip().split(",")
            lat = float(lat_str.strip())
            lon = float(lon_str.strip())
            boundary_latlon.append((lat, lon))
        polygon = Polygon([ (lon, lat) for lat, lon in boundary_latlon])
        if not polygon.is_valid or polygon.is_empty:
            st.error("Invalid polygon for boundary coordinates.")
            return
    except Exception as e:
        st.error(f"Error parsing boundary coordinates: {e}")
        return

    if st.button("Generate Waypoints"):
        with st.spinner("Generating waypoints..."):
            if task == "Grass Cutting":
                waypoints_list = generate_grass_cutting_waypoints(boundary_latlon, mower_width)
            elif task == "Striping":
                waypoints_list = generate_striping_waypoints(boundary_latlon, mower_width, stripe_pattern)
            else:  # Pitch Marking
                waypoints_list = generate_pitch_marking_waypoints(boundary_latlon)

            # Display on map
            m = folium.Map(location=boundary_latlon[0], zoom_start=18)

            # Draw boundary polygon
            folium.Polygon(locations=boundary_latlon, color="green", weight=3, fill=False).add_to(m)

            # Draw waypoints lines
            colors = ["red", "blue", "white", "yellow", "cyan"]
            for i, line in enumerate(waypoints_list):
                folium.PolyLine(locations=line, color=colors[i % len(colors)], weight=2).add_to(m)

            st_map = st_folium(m, width=700, height=500)

            # Prepare KML download
            kml_data = export_kml(waypoints_list)
            kml_bytes = kml_data.encode("utf-8")
            st.download_button(
                label="Download Waypoints as KML",
                data=kml_bytes,
                file_name="waypoints.kml",
                mime="application/vnd.google-earth.kml+xml",
            )

if __name__ == "__main__":
    main()
