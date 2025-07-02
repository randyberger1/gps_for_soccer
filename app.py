import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import Transformer

st.title("Football Field Maintenance Waypoint Generator with UTM Corner Input")

# Input mode selector
coord_mode = st.radio("Input Coordinate Type", ["UTM Coordinates", "Latitude/Longitude"])

if coord_mode == "UTM Coordinates":
    st.subheader("UTM Corner Coordinates (Easting, Northing)")
    default_utm = [
        "500000,0",
        "500105,0",
        "500105,68000",
        "500000,68000",
        "500000,0",
        "500105,0",
        "500105,68000",
        "500000,68000"
    ]  # Replace with your actual default UTM corners if desired

    utm_coords = [
        st.text_input(f"Point {i+1} (E,N)", default_utm[i] if i < len(default_utm) else "0,0")
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
    if parse_error:
        st.stop()
    utm_pts = np.array(utm_pts)

    # Determine rotation angle to align first edge with X axis
    edge_vector = utm_pts[1] - utm_pts[0]
    angle = -np.arctan2(edge_vector[1], edge_vector[0])
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle),  np.cos(angle)]])

    # Translate and rotate points to local aligned system
    translated_pts = utm_pts - utm_pts[0]
    local_pts = (R @ translated_pts.T).T

    # Use FIFA standard dimensions as defaults
    field_length = st.number_input("Field Length (m)", min_value=90.0, max_value=120.0, value=105.0, step=0.1)
    field_width = st.number_input("Field Width (m)", min_value=45.0, max_value=90.0, value=68.0, step=0.1)
    lane_spacing = st.number_input("Lane Spacing for Mowing (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

    operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

    # Waypoint generation functions (you already have these in your script)
    # def generate_mowing_waypoints(...)
    # def generate_line_marking_waypoints(...)

    if st.button("Generate Waypoints and KML"):
        if operation == "Mowing Lanes":
            waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
        else:
            waypoints_local = generate_line_marking_waypoints(field_length, field_width)

        # Rotate waypoints back to UTM
        waypoints_rotated_back = (R.T @ waypoints_local.T).T
        waypoints_utm = waypoints_rotated_back + utm_pts[0]

        # Convert UTM to Lat/Lon for KML export (adjust EPSG if your UTM zone differs)
        transformer_to_latlon = Transformer.from_crs("epsg:32632", "epsg:4326", always_xy=True)
        waypoints_latlon = np.array([transformer_to_latlon.transform(x, y) for x, y in waypoints_utm])

        # Plot local waypoints for preview
        fig, ax = plt.subplots()
        ax.plot(waypoints_local[:,0], waypoints_local[:,1], 'b-', label='Waypoints')
        ax.scatter(local_pts[:,0], local_pts[:,1], c='r', label='Input Corners')
        ax.set_aspect('equal', adjustable='datalim')
        ax.set_title(f"{operation} Waypoints Preview (Local aligned coordinates)")
        ax.set_xlabel("Local Easting (m)")
        ax.set_ylabel("Local Northing (m)")
        ax.legend()
        st.pyplot(fig)

        # Create KML
        kml = simplekml.Kml()
        for i, (lon, lat) in enumerate(waypoints_latlon):
            kml.newpoint(name=f"WP{i+1}", coords=[(lon, lat)])
        kml_str = kml.kml()

        st.download_button(
            label="Download Waypoints KML",
            data=kml_str,
            file_name="waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

else:
    # Latitude/Longitude input mode — add if you want, with conversion to UTM inside
    st.info("Lat/Lon input mode is coming soon.")
