import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import Transformer

st.title("Football Field Maintenance Waypoint Generator")

# Coordinate input mode choice
coord_mode = st.radio("Coordinate Input Mode", ("UTM Coordinates", "Latitude/Longitude"))

# Default coordinates from Table 1 (UTM zone 32N)
default_utm = [
    "576076.96,6251342.10",
    "576078.19,6251339.95",
    "576006.56,6251242.74",
    "576003.54,6251241.13",
    "575939.33,6251270.06",
    "575937.44,6251269.14",
    "576068.52,6251407.65",
    "576070.59,6251410.03"
]

# Default lat/lon points from Table 1 (decimal degrees)
default_latlon = [
    "56.456359,9.402698",
    "56.456339,9.40272",
    "56.455373,9.402473",
    "56.455357,9.402434",
    "56.455438,9.401313",
    "56.455455,9.401286",
    "56.456427,9.40154",
    "56.456447,9.401577"
]

# Input 8 corner points depending on mode
utm_points = []
latlon_points = []

st.subheader("Field Corner Coordinates (8 points)")

if coord_mode == "UTM Coordinates":
    coords_input = [
        st.text_input(f"Point {i+1} (Easting, Northing)", default_utm[i]) for i in range(8)
    ]
    # Parse UTM inputs
    for txt in coords_input:
        try:
            e, n = map(float, txt.strip().split(","))
            utm_points.append((e, n))
        except Exception:
            st.error("Invalid UTM input. Use format: Easting,Northing")
            st.stop()
else:
    coords_input = [
        st.text_input(f"Point {i+1} (Latitude, Longitude)", default_latlon[i]) for i in range(8)
    ]
    # Convert Lat/Lon to UTM zone 32N
    transformer = Transformer.from_crs("epsg:4326", "epsg:32632", always_xy=True)
    for txt in coords_input:
        try:
            lat, lon = map(float, txt.strip().split(","))
            e, n = transformer.transform(lon, lat)
            utm_points.append((e, n))
            latlon_points.append((lat, lon))
        except Exception:
            st.error("Invalid Lat/Lon input. Use format: Latitude,Longitude")
            st.stop()

utm_pts = np.array(utm_points)  # shape (8,2)

# Normalize points relative to first corner
E0, N0 = utm_pts[0]
local_pts = utm_pts - np.array([E0, N0])

# Now input other field parameters with FIFA standard defaults
field_length = st.number_input("Field Length (m)", min_value=90.0, max_value=120.0, value=105.0, step=0.1)
field_width = st.number_input("Field Width (m)", min_value=45.0, max_value=90.0, value=68.0, step=0.1)
lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

# Reference Lat/Lon for waypoint output conversion (use first point if Lat/Lon input)
if coord_mode == "Latitude/Longitude":
    ref_lat, ref_lon = latlon_points[0]
else:
    # Convert first UTM point back to lat/lon for reference
    transformer_to_latlon = Transformer.from_crs("epsg:32632", "epsg:4326", always_xy=True)
    ref_lon, ref_lat = transformer_to_latlon.transform(*utm_pts[0])

st.write(f"Reference Latitude: {ref_lat:.6f}, Reference Longitude: {ref_lon:.6f}")

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

# Helper function to interpolate lines smoothly
def interp_line(pts, n=100):
    distances = np.insert(np.cumsum(np.sqrt(np.sum(np.diff(pts, axis=0)**2, axis=1))), 0, 0)
    query = np.linspace(0, distances[-1], n)
    x = np.interp(query, distances, pts[:,0])
    y = np.interp(query, distances, pts[:,1])
    return np.column_stack((x,y))

# Center circle points
def center_circle(center, radius, n_points=100):
    angles = np.linspace(0, 2*np.pi, n_points)
    x = center[0] + radius * np.cos(angles)
    y = center[1] + radius * np.sin(angles)
    return np.column_stack((x,y))

# Generate mowing lanes waypoints
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

# Generate line marking waypoints
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
        waypoints.append(interp_line(arc, 50))

    return np.vstack(waypoints)

# Generate waypoints according to operation mode
if operation == "Mowing Lanes":
    waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
else:
    waypoints_local = generate_line_marking_waypoints(field_length, field_width)

# Convert local waypoints back to UTM absolute
waypoints_utm = waypoints_local + np.array([E0, N0])

# Convert waypoints UTM back to Lat/Lon for output
transformer_to_latlon = Transformer.from_crs("epsg:32632", "epsg:4326", always_xy=True)
waypoints_latlon = np.array([transformer_to_latlon.transform(x, y) for x, y in waypoints_utm])

# Plot
fig, ax = plt.subplots()
ax.plot(waypoints_local[:,0], waypoints_local[:,1], 'b-', label='Waypoints')
ax.scatter(local_pts[:,0], local_pts[:,1], c='r', label='Input Corners')
ax.set_aspect('equal', adjustable='datalim')
ax.set_title(f"{operation} Waypoints Preview")
ax.set_xlabel("Local Easting (m)")
ax.set_ylabel("Local Northing (m)")
ax.legend()
st.pyplot(fig)

# Export KML
def export_kml(waypoints_latlon):
    kml = simplekml.Kml()
    for i, (lon, lat) in enumerate(waypoints_latlon):
        kml.newpoint(name=f"WP{i+1}", coords=[(lon, lat)])
    return kml.kml()

kml_data = export_kml(waypoints_latlon)

st.download_button(
    label="Download Waypoints KML",
    data=kml_data,
    file_name="waypoints.kml",
    mime="application/vnd.google-earth.kml+xml"
)
