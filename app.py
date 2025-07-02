import streamlit as st
import numpy as np
from pyproj import Proj
import simplekml
import matplotlib.pyplot as plt

st.title("Football Field Maintenance Waypoint Generator with UTM Inputs")

# Lat/lon points from Table 1 in the paper
lat_lon_points = [
    (56.456359, 9.402698),
    (56.456339, 9.40272),
    (56.455373, 9.402473),
    (56.455357, 9.402434),
    (56.455438, 9.401313),
    (56.455455, 9.401286),
    (56.456427, 9.40154),
    (56.456447, 9.401577),
]

# Projections setup
wgs84 = Proj(proj='latlong', datum='WGS84')
utm_proj = Proj(proj='utm', zone=32, datum='WGS84')  # Zone 32 for Denmark area

# Convert lat/lon to UTM for defaults
default_utm_coords = []
for lat, lon in lat_lon_points:
    easting, northing = utm_proj(lon, lat)
    default_utm_coords.append(f"{easting:.2f},{northing:.2f}")

st.subheader("UTM Corner Coordinates (Easting, Northing)")
utm_coords = [
    st.text_input(f"Point {i+1} (E,N)", default_utm_coords[i])
    for i in range(8)
]

utm_pts = []
valid_inputs = True
for txt in utm_coords:
    try:
        e, n = map(float, txt.split(","))
        utm_pts.append((e, n))
    except:
        st.error("Invalid UTM input—use format: Easting,Northing")
        valid_inputs = False
        break

if not valid_inputs:
    st.stop()

utm_pts = np.array(utm_pts)

# Set local coordinates relative to first corner
E0, N0 = utm_pts[0]
local_pts = utm_pts - np.array([E0, N0])

# Inputs for operation
field_length = st.number_input("Field Length (m)", min_value=50.0, max_value=120.0, value=float(np.max(local_pts[:,0])), step=0.1)
field_width = st.number_input("Field Width (m)", min_value=30.0, max_value=90.0, value=float(np.max(local_pts[:,1])), step=0.1)
lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

# Helper functions (as in your original script)
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

# Convert local field XY coords back to lat/lon (simple flat approx)
def convert_to_latlon(xy_points, ref_easting, ref_northing, ref_lat, ref_lon):
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 40075000 * np.cos(np.deg2rad(ref_lat)) / 360
    lats = ref_lat + (xy_points[:,1] + ref_northing - N0) / meters_per_deg_lat
    lons = ref_lon + (xy_points[:,0] + ref_easting - E0) / meters_per_deg_lon
    return lats, lons

# Main generation and display
if st.button("Generate Waypoints"):
    if operation == "Mowing Lanes":
        waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
    else:
        waypoints_local = generate_line_marking_waypoints(field_length, field_width)

    # Convert local XY back to UTM absolute
    waypoints_utm = waypoints_local + np.array([E0, N0])

    # Plot preview
    fig, ax = plt.subplots()
    ax.plot(waypoints_local[:,0], waypoints_local[:,1], 'b-', linewidth=1, label=operation)
    ax.plot(local_pts[:,0], local_pts[:,1], 'ro', label="Field Corners")
    ax.set_title(f"{operation} Waypoints Preview (Local Coordinates)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend()
    ax.axis('equal')
    ax.grid(True)
    st.pyplot(fig)

    # Generate KML for the waypoints
    kml = simplekml.Kml()

    for i, (easting, northing) in enumerate(waypoints_utm):
        # Convert UTM back to lat/lon for KML (approximate, better with pyproj if needed)
        lon, lat = utm_proj(easting, northing, inverse=True)
        kml.newpoint(name=f"WP{i+1}", coords=[(lon, lat)])

    # Add a linestring connecting the waypoints
    kml.newlinestring(name=operation + " Path", coords=[(utm_proj(e, n, inverse=True)) for e, n in waypoints_utm])

    kml_str = kml.kml()
    kml_bytes = kml_str.encode('utf-8')

    st.download_button(
        label="Download Waypoints KML",
        data=kml_bytes,
        file_name=f"{operation.lower().replace(' ','_')}_waypoints.kml",
        mime="application/vnd.google-earth.kml+xml"
    )
