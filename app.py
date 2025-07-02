import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt

st.title("Football Field Maintenance Waypoint Generator")

# --- 1. Input 8 UTM Corner Coordinates ---
st.subheader("UTM Corner Coordinates (Easting, Northing) – 8 Points")
utm_coords = [st.text_input(f"Point {i+1} (E,N)", "0,0") for i in range(8)]

utm_pts = []
invalid = False
for i, txt in enumerate(utm_coords):
    try:
        e, n = map(float, txt.strip().split(","))
        utm_pts.append((e, n))
    except:
        st.error(f"Invalid format at Point {i+1}. Use 'Easting,Northing'")
        invalid = True
        break

if not invalid:
    utm_pts = np.array(utm_pts)
    E0, N0 = utm_pts[0]
    local_pts = utm_pts - [E0, N0]

    # Estimate field extents from input
    x_extent = float(np.ptp(local_pts[:, 0]))
    y_extent = float(np.ptp(local_pts[:, 1]))

    # Clamp defaults to legal values for Streamlit widgets
    default_length = max(50.0, min(120.0, x_extent))
    default_width = max(30.0, min(90.0, y_extent))

    field_length = st.number_input("Field Length (m)", 50.0, 120.0, default_length, 0.1)
    field_width = st.number_input("Field Width (m)", 30.0, 90.0, default_width, 0.1)
    lane_spacing = st.number_input("Lane Spacing (m)", 0.1, 5.0, 1.0, 0.1)

    ref_lat = st.number_input("Reference Latitude (°)", value=40.0, format="%.6f")
    ref_lon = st.number_input("Reference Longitude (°)", value=-74.0, format="%.6f")
    operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

    # --- Helper functions ---
    def interp_line(pts, n=100):
        d = np.insert(np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1)), 0, 0)
        t = np.linspace(0, d[-1], n)
        x = np.interp(t, d, pts[:, 0])
        y = np.interp(t, d, pts[:, 1])
        return np.column_stack((x, y))

    def center_circle(center, radius, n_points=100):
        a = np.linspace(0, 2 * np.pi, n_points)
        return np.column_stack((center[0] + radius * np.cos(a), center[1] + radius * np.sin(a)))

    def generate_mowing_waypoints(length, width, spacing):
        waypoints = []
        y_vals = np.arange(0, width + spacing, spacing)
        for i, y in enumerate(y_vals):
            x = np.linspace(0, length, 100) if i % 2 == 0 else np.linspace(length, 0, 100)
            y_arr = np.full_like(x, y)
            waypoints.append(np.column_stack((x, y_arr)))
        return np.vstack(waypoints)

    def generate_line_marking_waypoints(length, width):
        waypoints = []

        # Boundary
        boundary = np.array([[0, 0], [length, 0], [length, width], [0, width], [0, 0]])
        halfway_line = np.array([[length / 2, 0], [length / 2, width]])
        center = np.array([length / 2, width / 2])
        circle = center_circle(center, 9.15)

        penalty_area = np.array([
            [0, (width - 40.3) / 2], [16.5, (width - 40.3) / 2],
            [16.5, (width + 40.3) / 2], [0, (width + 40.3) / 2]
        ])
        penalty_area_right = penalty_area + [length - 16.5, 0]

        goal_area = np.array([
            [0, (width - 18.32) / 2], [5.5, (width - 18.32) / 2],
            [5.5, (width + 18.32) / 2], [0, (width + 18.32) / 2]
        ])
        goal_area_right = goal_area + [length - 5.5, 0]

        penalty_spot_left = np.array([11, width / 2])
        penalty_spot_right = np.array([length - 11, width / 2])

        arc_left_center = penalty_spot_left
        arc_right_center = penalty_spot_right
        angle_left = np.linspace(-np.pi / 2, np.pi / 2, 50)
        angle_right = np.linspace(np.pi / 2, 3 * np.pi / 2, 50)

        arc_left = np.column_stack((
            arc_left_center[0] + 9.15 * np.cos(angle_left),
            arc_left_center[1] + 9.15 * np.sin(angle_left)
        ))
        arc_right = np.column_stack((
            arc_right_center[0] + 9.15 * np.cos(angle_right),
            arc_right_center[1] + 9.15 * np.sin(angle_right)
        ))

        waypoints.append(interp_line(boundary, 200))
        waypoints.append(interp_line(halfway_line, 100))
        waypoints.append(interp_line(circle, 100))
        waypoints.append(interp_line(penalty_area[[0, 1, 2, 3, 0]], 100))
        waypoints.append(interp_line(penalty_area_right[[0, 1, 2, 3, 0]], 100))
        waypoints.append(interp_line(goal_area[[0, 1, 2, 3, 0]], 100))
        waypoints.append(interp_line(goal_area_right[[0, 1, 2, 3, 0]], 100))
        waypoints.append(interp_line(arc_left, 50))
        waypoints.append(interp_line(arc_right, 50))
        waypoints.append(penalty_spot_left.reshape(1, 2))
        waypoints.append(penalty_spot_right.reshape(1, 2))

        return np.vstack(waypoints)

    def convert_to_latlon(xy_points, ref_lat, ref_lon):
        meters_per_deg_lat = 111320
        meters_per_deg_lon = 111320 * np.cos(np.radians(ref_lat))
        lat = ref_lat + xy_points[:, 1] / meters_per_deg_lat
        lon = ref_lon + xy_points[:, 0] / meters_per_deg_lon
        return lat, lon

    def create_kml(lat, lon, field_outline=None):
        kml = simplekml.Kml()
        for la, lo in zip(lat, lon):
            kml.newpoint(coords=[(lo, la)])
        if field_outline is not None:
            fl_lat, fl_lon = convert_to_latlon(field_outline, ref_lat, ref_lon)
            kml.newlinestring(
                name="Field Boundary",
                coords=list(zip(fl_lon, fl_lat)) + [(fl_lon[0], fl_lat[0])]
            ).style.linestyle.color = simplekml.Color.red
        return kml.kml()

    # --- Generate on click ---
    if st.button("Generate Waypoints and KML"):
        if operation == "Mowing Lanes":
            waypoints = generate_mowing_waypoints(field_length, field_width, lane_spacing)
        else:
            waypoints = generate_line_marking_waypoints(field_length, field_width)

        lat, lon = convert_to_latlon(waypoints, ref_lat, ref_lon)

        # Plot preview
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(local_pts[:, 0], local_pts[:, 1], 'k--', linewidth=1.5, label='Field Boundary')
        ax.plot(waypoints[:, 0], waypoints[:, 1], '.-', markersize=2, label=f"{operation}")
        ax.set_title("Waypoint Preview")
        ax.set_xlabel("Local X (m)")
        ax.set_ylabel("Local Y (m)")
        ax.set_aspect('equal')
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

        # KML download
        kml_str = create_kml(lat, lon, field_outline=local_pts)
        st.download_button(
            label="Download KML File",
            data=kml_str.encode('utf-8'),
            file_name="field_waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )
