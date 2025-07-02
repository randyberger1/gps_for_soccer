import streamlit as st
import numpy as np
import pandas as pd
import simplekml
import io
import matplotlib.pyplot as plt

st.title("Field Maintenance Waypoint Generator")

# Input fields
field_length = st.number_input("Field Length (m)", min_value=1.0, value=105.0)
field_width = st.number_input("Field Width (m)", min_value=1.0, value=68.0)
lane_spacing = st.number_input("Lane Spacing (m)", min_value=0.1, value=1.0)
ref_lat = st.number_input("Reference Latitude", value=40.0, format="%.6f")
ref_lon = st.number_input("Reference Longitude", value=-74.0, format="%.6f")

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

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

def interpolate_line(points, n_points=100):
    distances = np.insert(np.cumsum(np.sqrt(np.sum(np.diff(points, axis=0)**2, axis=1))), 0, 0)
    query_dist = np.linspace(0, distances[-1], n_points)
    interp_x = np.interp(query_dist, distances, points[:,0])
    interp_y = np.interp(query_dist, distances, points[:,1])
    return np.column_stack((interp_x, interp_y))

def generate_line_marking_waypoints(length, width):
    boundary = np.array([
        [0, 0],
        [length, 0],
        [length, width],
        [0, width],
        [0, 0]
    ])
    center_line = np.array([
        [length/2, 0],
        [length/2, width]
    ])
    boundary_interp = interpolate_line(boundary, 200)
    center_interp = interpolate_line(center_line, 100)
    return np.vstack((boundary_interp, center_interp))

def convert_to_latlon(xy_points, ref_lat, ref_lon):
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * np.cos(np.radians(ref_lat))
    lat = ref_lat + xy_points[:,1] / meters_per_deg_lat
    lon = ref_lon + xy_points[:,0] / meters_per_deg_lon
    return lat, lon

def create_kml(lat, lon):
    kml = simplekml.Kml()
    for la, lo in zip(lat, lon):
        kml.newpoint(coords=[(lo, la)])
    return kml.kml()

if st.button("Generate Waypoints and KML"):
    if operation == "Mowing Lanes":
        waypoints = generate_mowing_waypoints(field_length, field_width, lane_spacing)
    else:
        waypoints = generate_line_marking_waypoints(field_length, field_width)

    lat, lon = convert_to_latlon(waypoints, ref_lat, ref_lon)

    # Plot preview
    fig, ax = plt.subplots()
    ax.plot(waypoints[:,0], waypoints[:,1], '.-')
    ax.set_title(f"{operation} Waypoints Preview")
    ax.set_xlabel("Length (m)")
    ax.set_ylabel("Width (m)")
    ax.set_aspect('equal')
    ax.grid(True)
    st.pyplot(fig)

    # Create KML bytes for download
    kml_str = create_kml(lat, lon)
    kml_bytes = kml_str.encode('utf-8')
    st.download_button(
        label="Download KML File",
        data=kml_bytes,
        file_name="field_waypoints.kml",
        mime="application/vnd.google-earth.kml+xml"
    )
