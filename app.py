import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import Proj

st.title("Football Field Maintenance Waypoint Generator")

# Input fields
field_length = st.number_input("Field Length (m)", min_value=50.0, max_value=120.0, value=105.0, step=0.1)
field_width = st.number_input("Field Width (m)", min_value=30.0, max_value=90.0, value=68.0, step=0.1)
lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

st.subheader("Input Field Corner Coordinates")

coord_mode = st.radio("Input Coordinates Format", ["UTM Easting,Northing", "Latitude,Longitude"])

utm_pts = None

if coord_mode == "UTM Easting,Northing":
    utm_coords = [st.text_input(f"Point {i+1} (Easting,Northing)", "0,0") for i in range(8)]
    utm_pts_list = []
    valid = True
    for txt in utm_coords:
        try:
            e, n = map(float, txt.split(","))
            utm_pts_list.append((e, n))
        except:
            st.error("Invalid UTM input — use format: Easting,Northing")
            valid = False
            break
    if valid:
        utm_pts = np.array(utm_pts_list)

else:  # Latitude,Longitude input
    latlon_coords = [st.text_input(f"Point {i+1} (Latitude,Longitude)", "0,0") for i in range(8)]
    lat_pts = []
    lon_pts = []
    valid = True
    for txt in latlon_coords:
        try:
            lat, lon = map(float, txt.split(","))
            lat_pts.append(lat)
            lon_pts.append(lon)
        except:
            st.error("Invalid Lat/Lon input — use format: Latitude,Longitude")
            valid = False
            break
    if valid:
        lat_pts = np.array(lat_pts)
        lon_pts = np.array(lon_pts)

        # Determine UTM zone from first point
        zone_number = int((lon_pts[0] + 180) / 6) + 1
        hemisphere = 'north' if lat_pts[0] >= 0 else 'south'
        proj_utm = Proj(proj='utm', zone=zone_number, hemisphere=hemisphere)
        proj_latlon = Proj(proj='latlong', datum='WGS84')

        utm_pts_list = []
        for lat, lon in zip(lat_pts, lon_pts):
            easting, northing = proj_utm(lon, lat)
            utm_pts_list.append((easting, northing))
        utm_pts = np.array(utm_pts_list)

if utm_pts is not None and len(utm_pts) == 8:
    # Use first point as local origin
    E0, N0 = utm_pts[0]
    local_pts = utm_pts - np.array([E0, N0])

    # Helper functions
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
        center_circle_radius = 9.15

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
            waypoints.append(interp_line(arc, 25))
        waypoints.append(penalty_spot_left.reshape(1, 2))
        waypoints.append(penalty_spot_right.reshape(1, 2))

        return np.vstack(waypoints)

    # Convert local UTM coordinates back to lat/lon for KML (using first point origin)
    def convert_local_to_latlon(xy_points, utm_origin_e, utm_origin_n, zone_number, hemisphere):
        proj_utm = Proj(proj='utm', zone=zone_number, hemisphere=hemisphere)
        proj_latlon = Proj(proj='latlong', datum='WGS84')
        latlon_points = []
        for x, y in xy_points:
            easting = utm_origin_e + x
            northing = utm_origin_n + y
            lon, lat = proj_utm(easting, northing, inverse=True)
            latlon_points.append((lat, lon))
        return np.array(latlon_points)

    # Create KML file string from lat/lon points
    def create_kml(latlon_pts):
        kml = simplekml.Kml()
        for lat, lon in latlon_pts:
            kml.newpoint(coords=[(lon, lat)])
        return kml.kml()

    # Generate waypoints based on operation
    if st.button("Generate Waypoints and KML"):
        if operation == "Mowing Lanes":
            waypoints = generate_mowing_waypoints(field_length, field_width, lane_spacing)
        else:
            waypoints = generate_line_marking_waypoints(field_length, field_width)

        latlon_waypoints = convert_local_to_latlon(
            waypoints,
            E0,
            N0,
            zone_number,
            hemisphere
        )

        # Plot preview
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(waypoints[:,0], waypoints[:,1], '.-', markersize=2)
        ax.set_title(f"{operation} Waypoints Preview")
        ax.set_xlabel("Length (m)")
        ax.set_ylabel("Width (m)")
        ax.set_aspect('equal')
        ax.grid(True)
        st.pyplot(fig)

        # Prepare KML for download
        kml_str = create_kml(latlon_waypoints)
        kml_bytes = kml_str.encode('utf-8')
        st.download_button(
            label="Download KML File",
            data=kml_bytes,
            file_name="field_waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

else:
    st.info("Please input valid coordinates for all 8 points.")

