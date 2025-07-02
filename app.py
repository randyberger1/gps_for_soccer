import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import Transformer

st.title("Football Field Maintenance Waypoint Generator with UTM Corner Input")

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

# --- Main UI and logic ---

coord_mode = st.radio("Input Coordinate Type", ["UTM Coordinates", "Latitude/Longitude"])

if coord_mode == "UTM Coordinates":
    st.subheader("UTM Corner Coordinates (Easting, Northing)")
    # Default corners from paper (converted to approximate UTM zone 32N, you might need to adjust EPSG)
    default_utm = [
        "500000,6264000",
        "500105,6264000",
        "500105,6264680",
        "500000,6264680",
        "500000,6264000",
        "500105,6264000",
        "500105,6264680",
        "500000,6264680"
    ]

    utm_coords = [
        st.text_input(f"Point {i+1} (E,N)", default_utm[i] if i < len(default_utm) else "0,0")
        for i in range(8)
    ]

    utm_pts = []
    parse_error = False
    for txt in utm_coords:
        try:
            e, n = map(float, txt.split(","))
            utm_pts.append((e, n))
        except:
            st.error("Invalid UTM input. Use format: Easting,Northing")
            parse_error = True
    if parse_error:
        st.stop()
    utm_pts = np.array(utm_pts)

    # Rotation to align first edge with X axis
    edge_vector = utm_pts[1] - utm_pts[0]
    angle = -np.arctan2(edge_vector[1], edge_vector[0])
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle),  np.cos(angle)]])

    translated_pts = utm_pts - utm_pts[0]
    local_pts = (R @ translated_pts.T).T

    # Set default FIFA standard field dimensions
    field_length = st.number_input("Field Length (m)", min_value=90.0, max_value=120.0, value=105.0, step=0.1)
    field_width = st.number_input("Field Width (m)", min_value=45.0, max_value=90.0, value=68.0, step=0.1)
    lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

    operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

    if st.button("Generate Waypoints and KML"):
        if operation == "Mowing Lanes":
            waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
        else:
            waypoints_local = generate_line_marking_waypoints(field_length, field_width)

        # Rotate waypoints back to UTM coordinate system
        waypoints_global = (R.T @ waypoints_local.T).T + utm_pts[0]

        # Plot waypoints
        fig, ax = plt.subplots()
        ax.plot(waypoints_local[:,0], waypoints_local[:,1], "-o", markersize=2)
        ax.set_aspect('equal')
        ax.set_title("Local Waypoints (rotated)")
        st.pyplot(fig)

        # Generate KML
        kml = simplekml.Kml()
        for i, pt in enumerate(waypoints_global):
            kml.newpoint(name=str(i+1), coords=[(pt[0], pt[1])])
        kml_str = kml.kml()
        st.download_button("Download KML", data=kml_str, file_name="waypoints.kml", mime="application/vnd.google-earth.kml+xml")

elif coord_mode == "Latitude/Longitude":
    st.subheader("Enter Lat/Lon for 4 corners (decimal degrees)")
    default_latlon = [
        "56.456359,9.402698",
        "56.456339,9.402720",
        "56.455373,9.402473",
        "56.455357,9.402434",
        "56.455438,9.401313",
        "56.455455,9.401286",
        "56.456427,9.401540",
        "56.456447,9.401577"
    ]
    latlon_coords = [
        st.text_input(f"Point {i+1} (Lat,Lon)", default_latlon[i] if i < len(default_latlon) else "0,0")
        for i in range(8)
    ]

    latlon_pts = []
    parse_error = False
    for txt in latlon_coords:
        try:
            lat, lon = map(float, txt.split(","))
            latlon_pts.append((lat, lon))
        except:
            st.error("Invalid Lat/Lon input. Use format: Latitude,Longitude")
            parse_error = True
    if parse_error:
        st.stop()
    latlon_pts = np.array(latlon_pts)

    # Convert lat/lon to UTM
    # We'll automatically detect UTM zone from first point longitude
    lon0 = latlon_pts[0,1]
    zone_number = int((lon0 + 180) / 6) + 1
    epsg_code = 32600 + zone_number  # northern hemisphere assumption
    transformer = Transformer.from_crs("epsg:4326", f"epsg:{epsg_code}", always_xy=True)

    utm_pts = np.array([transformer.transform(lon, lat) for lat, lon in latlon_pts])

    # Same rotation and local coordinate computation as above
    edge_vector = utm_pts[1] - utm_pts[0]
    angle = -np.arctan2(edge_vector[1], edge_vector[0])
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle),  np.cos(angle)]])

    translated_pts = utm_pts - utm_pts[0]
    local_pts = (R @ translated_pts.T).T

    # FIFA defaults
    field_length = st.number_input("Field Length (m)", min_value=90.0, max_value=120.0, value=105.0, step=0.1)
    field_width = st.number_input("Field Width (m)", min_value=45.0, max_value=90.0, value=68.0, step=0.1)
    lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

    operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

    if st.button("Generate Waypoints and KML"):
        if operation == "Mowing Lanes":
            waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
        else:
            waypoints_local = generate_line_marking_waypoints(field_length, field_width)

        waypoints_global = (R.T @ waypoints_local.T).T + utm_pts[0]

        fig, ax = plt.subplots()
        ax.plot(waypoints_local[:,0], waypoints_local[:,1], "-o", markersize=2)
        ax.set_aspect('equal')
        ax.set_title("Local Waypoints (rotated)")
        st.pyplot(fig)

        kml = simplekml.Kml()
        for i, pt in enumerate(waypoints_global):
            kml.newpoint(name=str(i+1), coords=[(pt[0], pt[1])])
        kml_str = kml.kml()
        st.download_button("Download KML", data=kml_str, file_name="waypoints.kml", mime="application/vnd.google-earth.kml+xml")
