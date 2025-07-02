import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt
from pyproj import Proj

st.title("Football Field Maintenance Waypoint Generator")

# --- Input UTM corners (prefilled with example from Table 1) ---
st.subheader("UTM Corner Coordinates (Easting, Northing)")
utm_coords_defaults = [
    "574990.0,6263245.0",
    "574990.5,6263246.5",
    "574980.0,6263235.0",
    "574979.5,6263234.5",
    "574970.0,6263220.0",
    "574970.5,6263219.5",
    "574985.0,6263230.0",
    "574985.5,6263230.5"
]

utm_coords = [
    st.text_input(f"Point {i+1} (E,N)", utm_coords_defaults[i]) for i in range(8)
]

# Parse UTM inputs
utm_pts = []
for txt in utm_coords:
    try:
        e, n = map(float, txt.split(","))
        utm_pts.append((e, n))
    except:
        st.error("Invalid UTM input — please use format: Easting,Northing (e.g. 574990,6263245)")
        st.stop()
utm_pts = np.array(utm_pts)  # shape (8,2)

# Local coordinates relative to first corner
E0, N0 = utm_pts[0]
local_pts = utm_pts - np.array([E0, N0])

# FIFA recommended sizes for international matches
FIFA_LENGTH_MIN, FIFA_LENGTH_MAX = 100.0, 110.0
FIFA_WIDTH_MIN, FIFA_WIDTH_MAX = 64.0, 75.0
FIFA_LENGTH_DEFAULT = 105.0
FIFA_WIDTH_DEFAULT = 68.0

# Adjust default length/width to UTM extents or FIFA defaults, whichever is larger
default_length = max(FIFA_LENGTH_DEFAULT, float(np.max(local_pts[:,0])))
default_width = max(FIFA_WIDTH_DEFAULT, float(np.max(local_pts[:,1])))

field_length = st.number_input("Field Length (m)", FIFA_LENGTH_MIN, FIFA_LENGTH_MAX, default_length, 0.1)
field_width = st.number_input("Field Width (m)", FIFA_WIDTH_MIN, FIFA_WIDTH_MAX, default_width, 0.1)
lane_spacing = st.number_input("Lane Spacing for Mowing (m)", 0.1, 5.0, 1.0, 0.1)

operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

utm_proj = Proj(proj='utm', zone=32, ellps='WGS84', south=False)  # Adjust zone as needed

def interp_line(pts, n=100):
    distances = np.insert(np.cumsum(np.sqrt(np.sum(np.diff(pts, axis=0)**2, axis=1))), 0, 0)
    query = np.linspace(0, distances[-1], n)
    x = np.interp(query, distances, pts[:,0])
    y = np.interp(query, distances, pts[:,1])
    return np.column_stack((x,y))

# Add your generate_mowing_waypoints and generate_line_marking_waypoints functions here
# (reuse from your previous code)

# Convert local XY to absolute UTM
def local_to_utm(xy_points):
    return xy_points + np.array([E0, N0])

# Convert UTM to lat/lon for KML
def utm_to_latlon(easting, northing):
    lon, lat = utm_proj(easting, northing, inverse=True)
    return lat, lon

if st.button("Generate Waypoints"):
    if operation == "Mowing Lanes":
        waypoints_local = generate_mowing_waypoints(field_length, field_width, lane_spacing)
    else:
        waypoints_local = generate_line_marking_waypoints(field_length, field_width)

    waypoints_utm = local_to_utm(waypoints_local)

    # Plot preview in local coordinates
    fig, ax = plt.subplots(figsize=(10,6))
    ax.plot(waypoints_local[:,0], waypoints_local[:,1], 'b-', linewidth=1, label=operation)
    ax.plot(local_pts[:,0], local_pts[:,1], 'ro', label="Field Corners")
    ax.set_title(f"{operation} Waypoints Preview (Local Coordinates)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend()
    ax.axis('equal')
    ax.grid(True)
    st.pyplot(fig)

    # Create KML with lat/lon converted from UTM
    kml = simplekml.Kml()
    for i, (e, n) in enumerate(waypoints_utm):
        lat, lon = utm_to_latlon(e, n)
        kml.newpoint(name=f"WP{i+1}", coords=[(lon, lat)])
    kml.newlinestring(name=operation + " Path", coords=[utm_proj(e, n, inverse=True) for e, n in waypoints_utm])

    kml_bytes = kml.kml().encode('utf-8')
    st.download_button(
        label="Download Waypoints KML",
        data=kml_bytes,
        file_name=f"{operation.lower().replace(' ','_')}_waypoints.kml",
        mime="application/vnd.google-earth.kml+xml"
    )
