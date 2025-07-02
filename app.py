import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import Proj, Transformer

st.title("Football Field Maintenance Waypoint Generator")

# --- UTM coordinates input from Table 1 (Denmark example) ---
st.subheader("UTM Corner Coordinates (Easting, Northing)")
utm_defaults = [
    "573739.87,6250717.02",  # approx conversion from lat/lon Table 1 (example values)
    "573741.23,6250719.23",
    "573741.12,6250708.81",
    "573740.04,6250708.31",
    "573736.29,6250699.98",
    "573736.10,6250699.55",
    "573738.56,6250703.84",
    "573739.87,6250705.25"
]

utm_coords = [
    st.text_input(f"Point {i+1} (Easting, Northing)", utm_defaults[i])
    for i in range(8)
]

utm_pts = []
valid_utm = True
for txt in utm_coords:
    try:
        e, n = map(float, txt.split(","))
        utm_pts.append((e, n))
    except:
        st.error("Invalid UTM input—use format: Easting,Northing")
        valid_utm = False
        break

if not valid_utm:
    st.stop()

utm_pts = np.array(utm_pts)  # shape (8,2)

# Origin at first point
E0, N0 = utm_pts[0]
local_pts = utm_pts - np.array([E0, N0])

# --- Field size inputs ---
# Use FIFA recommended sizes as default
field_length = st.number_input("Field Length (m)", min_value=50.0, max_value=120.0, value=105.0, step=0.1)
field_width = st.number_input("Field Width (m)", min_value=30.0, max_value=90.0, value=68.0, step=0.1)
lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

# For converting XY to lat/lon, user needs ref lat/lon:
# We'll get lat/lon of first UTM point automatically using pyproj
proj_utm = Proj(proj='utm', zone=32, ellps='WGS84', preserve_units=False)  # Zone 32 for Denmark example
transformer_to_latlon = Transformer.from_proj(proj_utm, 'epsg:4326')

ref_lon, ref_lat = transformer_to_latlon.transform(E0, N0)

st.markdown(f"**Reference Latitude:** {ref_lat:.6f}°  **Reference Longitude:** {ref_lon:.6f}°")

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

# --- Helper functions ---

def interp_line(pts, n=100):
    distances = np.insert(np.cumsum(np.sqrt(np.sum(np.diff(pts, axis=0)**2, axis=1))), 0, 0)
    query = np.linspace(0, distances[-1], n)
    x = np.interp(query, distances, pts[:,0])
    y = np.interp(query, distances, pts[:,1])
    return np.column_stack((x,y))

def center_circle(center, radius, n_points=100):
    angles = np.linspace(0, 2*np.pi, n_points)
    x = center[0] + radius * np.cos(angles)
    y = center[1] + radius * np.sin(angles)
    return np.column_stack((x,y))

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

    # Boundary rectangle
    boundary = np.array([
        [0, 0],
        [field_length, 0],
        [field_length, field_width],
        [0, field_width],
        [0, 0]
    ])

    # Halfway line
    halfway_line = np.array([
        [field_length / 2, 0],
        [field_length / 2, field_width]
    ])

    # Center circle
    center_circle_center = np.array([field_length / 2, field_width / 2])
    center_circle_radius = 9.15  # meters

    # Penalty area (length x width)
    penalty_area_length = 16.5
    penalty_area_width = 40.3
    penalty_area_left = np.array([
        [0, (field_width - penalty_area_width) / 2],
        [penalty_area_length, (field_width - penalty_area_width) / 2],
        [penalty_area_length, (field_width + penalty_area_width) / 2],
        [0, (field_width + penalty_area_width) / 2]
    ])

    penalty_area_right = penalty_area_left + np.array([field_length - penalty_area_length, 0])

    # Goal area (length x width)
    goal_area_length = 5.5
    goal_area_width = 18.32
    goal_area_left = np.array([
        [0, (field_width - goal_area_width) / 2],
        [goal_area_length, (field_width - goal_area_width) / 2],
        [goal_area_length, (field_width + goal_area_width) / 2],
        [0, (field_width + goal_area_width) / 2]
    ])

    goal_area_right = goal_area_left + np.array([field_length - goal_area_length, 0])

    # Penalty spots
    penalty_spot_distance = 11
    penalty_spot_left = np.array([penalty_spot_distance, field_width / 2])
    penalty_spot_right = np.array([field_length - penalty_spot_distance, field_width / 2])

    # Penalty arcs parameters
    penalty_arc_radius = 9.15
    arc_angles_left = np.linspace(-np.pi/2, np.pi/2, 50)
    arc_angles_right = np.linspace(np.pi/2, 3*np.pi/2, 50)

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

    # Corner arcs radius and positions
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
            angles = np.linspace(0, np.pi/2, 25)
        elif np.array_equal(corner, [0, field_width]):
            angles = np.linspace(-np.pi/2, 0, 25)
        elif np.array_equal(corner, [field_length, 0]):
            angles = np.linspace(np.pi/2, np.pi, 25)
        else:
            angles = np.linspace(np.pi, 3*np.pi/2, 25)
        arc = np.vstack([
            corner[0] + corner_arc_radius * np.cos(angles),
            corner[1] + corner_arc_radius * np.sin(angles)
        ]).T
        corner_arcs.append(arc)

    # Add all elements to waypoints (interpolated for smoothness)
    waypoints.append(interp_line(boundary, 200))
    waypoints.append(interp_line(halfway_line, 100))
    waypoints.append(interp_line(center_circle(center_circle_center, center_circle_radius, 100)))
    waypoints.append(interp_line(penalty_area_left[[0,1,2,3,0]], 100))
    waypoints.append(interp_line(penalty_area_right[[0,1,2,3,0]], 100))
    waypoints.append(interp_line(goal_area_left[[0,1,2,3,0]], 100))
    waypoints.append(interp_line(goal_area_right[[0,1,2,3,0]], 100))
    waypoints.append(interp_line(penalty_arc_left, 50))
    waypoints.append(interp_line(penalty_arc_right, 50))
    for arc in corner_arcs:
        waypoints.append(interp_line(arc, 25))
    # Add penalty spots as single points
    waypoints.append(penalty_spot_left.reshape(1, 2))
    waypoints.append(penalty_spot_right.reshape(1, 2))

    return np.vstack(waypoints)

# Convert local XY (meters) to lat/lon using ref lat/lon & simple flat earth approx
def convert_to_latlon(xy_points, ref_lat, ref_lon):
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * np.cos(np.radians(ref_lat))
    lat = ref_lat + xy_points[:,1] / meters_per_deg_lat
    lon = ref_lon + xy_points[:,0] / meters_per_deg_lon
    return lat, lon

# Create KML file string from lat/lon waypoints
def create_kml(lat, lon):
    kml = simplekml.Kml()
    for la, lo in zip(lat, lon):
        kml.newpoint(coords=[(lo, la)])
    return kml.kml()

# --- Main ---
if st.button("Generate Waypoints and KML"):
    if operation == "Mowing Lanes":
        waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
    else:
        waypoints_local = generate_line_marking_waypoints(field_length, field_width)

    # Shift waypoints relative to origin corner
    # You can choose to align your field with local_pts or just origin
    # For now, assume origin is (0,0)
    lat, lon = convert_to_latlon(waypoints_local, ref_lat, ref_lon)

    st.subheader("Waypoint Preview Plot")
    fig, ax = plt.subplots(figsize=(8,5))
    ax.plot(waypoints_local[:,0], waypoints_local[:,1], 'b.-', label='Waypoints')
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"{operation} Waypoints")
    ax.set_aspect('equal', adjustable='box')
    st.pyplot(fig)

    kml_str = create_kml(lat, lon)
    st.download_button("Download KML file", data=kml_str, file_name="waypoints.kml", mime="application/vnd.google-earth.kml+xml")

st.markdown("---")
st.markdown("**Note:** UTM zone is hardcoded to 32 for Denmark (WGS84). Adjust `Proj` zone in the code if needed for your location.")
