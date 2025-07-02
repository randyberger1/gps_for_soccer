import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import CRS, Transformer

st.title("Football Field Maintenance Waypoint Generator")

# --- UTM corner coordinates input (default from paper's Table 1) ---
st.subheader("UTM Corner Coordinates (Easting, Northing)")

default_utm_coords = [
    "561083.21,6251241.04",
    "561106.42,6251242.99",
    "561080.36,6250132.75",
    "561081.83,6250129.57",
    "561010.65,6250155.16",
    "561012.17,6250152.85",
    "561035.23,6251253.40",
    "561036.85,6251250.76"
]

utm_coords = [
    st.text_input(f"Point {i+1} (Easting, Northing)", default_utm_coords[i])
    for i in range(8)
]

# Parse UTM points
utm_pts = []
parse_error = False
for txt in utm_coords:
    try:
        e, n = map(float, txt.split(","))
        utm_pts.append((e, n))
    except:
        st.error("Invalid UTM input. Use format: Easting,Northing")
        parse_error = True
        break

if parse_error:
    st.stop()

utm_pts = np.array(utm_pts)

# Use first point as origin
E0, N0 = utm_pts[0]
local_pts_orig = utm_pts - np.array([E0, N0])

# --- Detect UTM zone and setup CRS ---
# Assuming all points in same zone; calculate from first point
zone_number = int((E0 // 1000000) % 100)  # Rough hack; better from lat/lon but let's do lat/lon for UTM zone

# Instead, convert first UTM point back to lat/lon (approximate):
# For that we must guess UTM zone from lat/lon - better to prompt user for zone or lat/lon directly

# Let's request user input for UTM zone and hemisphere for precise transform:
st.subheader("UTM Zone and Hemisphere")
utm_zone = st.number_input("UTM Zone Number", min_value=1, max_value=60, value=32)
hemisphere = st.selectbox("Hemisphere", options=["N", "S"], index=0)

# Setup CRS strings
if hemisphere == "N":
    utm_crs = CRS.from_dict({"proj": "utm", "zone": utm_zone, "south": False})
else:
    utm_crs = CRS.from_dict({"proj": "utm", "zone": utm_zone, "south": True})

wgs84_crs = CRS.from_epsg(4326)
transformer_utm2wgs = Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
transformer_wgs2utm = Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)

# --- Input fields with FIFA default sizes ---
field_length = st.number_input("Field Length (m)", min_value=90.0, max_value=120.0, value=105.0, step=0.1)
field_width = st.number_input("Field Width (m)", min_value=45.0, max_value=90.0, value=68.0, step=0.1)
lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

# --- Geometry functions ---
def interp_line(pts, n=100):
    distances = np.insert(np.cumsum(np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))), 0, 0)
    query = np.linspace(0, distances[-1], n)
    x = np.interp(query, distances, pts[:, 0])
    y = np.interp(query, distances, pts[:, 1])
    return np.column_stack((x, y))


def center_circle(center, radius, n_points=100):
    angles = np.linspace(0, 2 * np.pi, n_points)
    x = center[0] + radius * np.cos(angles)
    y = center[1] + radius * np.sin(angles)
    return np.column_stack((x, y))


def generate_mowing_waypoints(length, width, spacing):
    waypoints = []
    y_vals = np.arange(0, width + spacing, spacing)
    for i, y in enumerate(y_vals):
        if i % 2 == 0:
            x_points = np.linspace(0, length, 100)
        else:
            x_points = np.linspace(length, 0, 100)
        y_points = np.full_like(x_points, y)
        waypoints.append(np.column_stack((x_points, y_points)))
    return np.vstack(waypoints)


def generate_line_marking_waypoints(field_length, field_width):
    waypoints = []

    boundary = np.array([
        [0, 0],
        [field_length, 0],
        [field_length, field_width],
        [0, field_width],
        [0, 0]
    ])

    halfway_line = np.array([
        [field_length / 2, 0],
        [field_length / 2, field_width]
    ])

    center_circle_center = np.array([field_length / 2, field_width / 2])
    center_circle_radius = 9.15  # meters

    penalty_area_length = 16.5
    penalty_area_width = 40.3
    penalty_area_left = np.array([
        [0, (field_width - penalty_area_width) / 2],
        [penalty_area_length, (field_width - penalty_area_width) / 2],
        [penalty_area_length, (field_width + penalty_area_width) / 2],
        [0, (field_width + penalty_area_width) / 2]
    ])

    penalty_area_right = penalty_area_left + np.array([field_length - penalty_area_length, 0])

    goal_area_length = 5.5
    goal_area_width = 18.32
    goal_area_left = np.array([
        [0, (field_width - goal_area_width) / 2],
        [goal_area_length, (field_width - goal_area_width) / 2],
        [goal_area_length, (field_width + goal_area_width) / 2],
        [0, (field_width + goal_area_width) / 2]
    ])

    goal_area_right = goal_area_left + np.array([field_length - goal_area_length, 0])

    penalty_spot_distance = 11
    penalty_spot_left = np.array([penalty_spot_distance, field_width / 2])
    penalty_spot_right = np.array([field_length - penalty_spot_distance, field_width / 2])

    penalty_arc_radius = 9.15
    arc_angles_left = np.linspace(-np.pi / 2, np.pi / 2, 50)
    arc_angles_right = np.linspace(np.pi / 2, 3 * np.pi / 2, 50)

    penalty_arc_left_center = penalty_spot_left
    penalty_arc_right_center = penalty_spot_right

    penalty_arc_left = np.vstack([
        penalty_arc_left_center[0] + penalty_arc_radius * np.cos(arc_angles_left),
        penalty_arc_left_center[1] + penalty_arc_radius * np.sin(arc_angles_left)
    ]).T

    penalty_arc_right = np.vstack([
        penalty_arc_right_center[0] + penalty_arc_radius * np.cos(arc_angles_right),
        penalty_arc_right_center[1] + penalty_arc_radius * np.sin(arc_angles_right)
    ]).T

    corner_arc_radius = 1.0
    corners = [
        np.array([0, 0]),
        np.array([0, field_width]),
        np.array([field_length, 0]),
        np.array([field_length, field_width])
    ]

    corner_arcs = []
    for corner in corners:
        if np.array_equal(corner, [0, 0]):
            angles = np.linspace(0, np.pi / 2, 25)
        elif np.array_equal(corner, [0, field_width]):
            angles = np.linspace(-np.pi / 2, 0, 25)
        elif np.array_equal(corner, [field_length, 0]):
            angles = np.linspace(np.pi / 2, np.pi, 25)
        else:
            angles = np.linspace(np.pi, 3 * np.pi / 2, 25)
        arc = np.vstack([
            corner[0] + corner_arc_radius * np.cos(angles),
            corner[1] + corner_arc_radius * np.sin(angles)
        ]).T
        corner_arcs.append(arc)

    waypoints.append(interp_line(boundary, 200))
    waypoints.append(interp_line(halfway_line, 100))
    waypoints.append(interp_line(center_circle(center_circle_center, center_circle_radius, 100)))
    waypoints.append(interp_line(penalty_area_left[[0, 1, 2, 3, 0]], 100))
    waypoints.append(interp_line(penalty_area_right[[0, 1, 2, 3, 0]], 100))
    waypoints.append(interp_line(goal_area_left[[0, 1, 2, 3, 0]], 100))
    waypoints.append(interp_line(goal_area_right[[0, 1, 2, 3, 0]], 100))
    waypoints.append(interp_line(penalty_arc_left, 50))
    waypoints.append(interp_line(penalty_arc_right, 50))
    for arc in corner_arcs:
        waypoints.append(interp_line(arc, 25))
    waypoints.append(penalty_spot_left.reshape(1, 2))
    waypoints.append(penalty_spot_right.reshape(1, 2))

    return np.vstack(waypoints)

# --- Rotation correction ---

def rotate_points(pts, angle_deg):
    theta = np.radians(angle_deg)
    R = np.array([[np.cos(theta), -np.sin(theta)],
                  [np.sin(theta),  np.cos(theta)]])
    return (R @ pts.T).T

# --- Main logic ---

if st.button("Generate Waypoints and KML"):

    # Generate local waypoints in meters relative to origin
    if operation == "Mowing Lanes":
        waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
    else:
        waypoints_local = generate_line_marking_waypoints(field_length, field_width)

    # Correct orientation: rotate local waypoints by 90 degrees CCW if needed (adjust as per your field orientation)
    # You can let user input rotation if necessary; default 0 here
    rotation_angle = st.number_input("Field Rotation Angle (degrees, CCW)", value=0.0, step=1.0)
    waypoints_local_rot = rotate_points(waypoints_local, rotation_angle)

    # Translate local points back to global UTM coordinates
    waypoints_global_utm = waypoints_local_rot + np.array([E0, N0])

    # Convert UTM to lat/lon for KML export
    waypoints_latlon = np.array([transformer_utm2wgs.transform(pt[0], pt[1]) for pt in waypoints_global_utm])

    # Plot local waypoints for preview
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(waypoints_local_rot[:, 0], waypoints_local_rot[:, 1], ".-", markersize=2)
    ax.set_aspect('equal')
    ax.set_title(f"{operation} Waypoints (Local, rotated)")
    ax.set_xlabel("Meters")
    ax.set_ylabel("Meters")
    ax.grid(True)
    st.pyplot(fig)

    # Create KML file
    kml = simplekml.Kml()
    for i, (lon, lat) in enumerate(waypoints_latlon):
        kml.newpoint(name=str(i + 1), coords=[(lon, lat)])

    kml_str = kml.kml()
    st.download_button(
        label="Download KML File",
        data=kml_str.encode("utf-8"),
        file_name="field_waypoints.kml",
        mime="application/vnd.google-earth.kml+xml"
    )
