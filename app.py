import streamlit as st
import numpy as np
import simplekml
import matplotlib.pyplot as plt

st.title("Football Field Maintenance Waypoint Generator")

# 1️⃣ UTM corners input
st.subheader("UTM Corner Coordinates (Easting, Northing) – 8 points")
utm_coords = [st.text_input(f"Point {i+1} (E,N)", "0,0") for i in range(8)]
utm_pts = []; invalid = False
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

    # Field size default from UTM extents
    x_extent = float(np.ptp(local_pts[:,0]))
    y_extent = float(np.ptp(local_pts[:,1]))
    field_length = st.number_input("Field Length (m)", 50.0, 120.0, x_extent, 0.1)
    field_width  = st.number_input("Field Width  (m)", 30.0,  90.0, y_extent, 0.1)
    lane_spacing = st.number_input("Lane Spacing (m)", 0.1, 5.0, 1.0, 0.1)

    # Lat/Lon ref for KML conversion
    ref_lat = st.number_input("Reference Latitude (°)", value=40.0, format="%.6f")
    ref_lon = st.number_input("Reference Longitude (°)", value=-74.0, format="%.6f")

    operation = st.radio("Operation Mode", ("Mowing Lanes", "Line Marking"))

    # --- Geometry functions unchanged ---
    def interp_line(pts, n=100):
        d = np.insert(np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1)), 0, 0)
        t = np.linspace(0, d[-1], n)
        x = np.interp(t, d, pts[:,0]); y = np.interp(t, d, pts[:,1])
        return np.column_stack((x, y))

    def center_circle(center, radius, n_points=100):
        a = np.linspace(0, 2*np.pi, n_points)
        return np.column_stack((center[0] + radius*np.cos(a), center[1] + radius*np.sin(a)))

    # ... generate_mowing_waypoints and generate_line_marking_waypoints as before ...

    def convert_to_latlon(xy, ref_lat, ref_lon):
        m2d_lat = 111320
        m2d_lon = 111320 * np.cos(np.radians(ref_lat))
        return ref_lat + xy[:,1]/m2d_lat, ref_lon + xy[:,0]/m2d_lon

    def create_kml(lat, lon, field_outline=None):
        kml = simplekml.Kml()
        for la, lo in zip(lat, lon):
            kml.newpoint(coords=[(lo, la)])
        if field_outline is not None:
            fl_lat, fl_lon = convert_to_latlon(field_outline, ref_lat, ref_lon)
            ls = kml.newlinestring(name="Field Boundary", coords=list(zip(fl_lon, fl_lat)) + [(fl_lon[0], fl_lat[0])])
            ls.style.linestyle.width = 2; ls.style.linestyle.color = simplekml.Color.red
        return kml.kml()

    if st.button("Generate Waypoints and KML"):
        if operation == "Mowing Lanes":
            waypoints = generate_mowing_waypoints(field_length, field_width, lane_spacing)
        else:
            waypoints = generate_line_marking_waypoints(field_length, field_width)

        lat, lon = convert_to_latlon(waypoints, ref_lat, ref_lon)

        # Preview
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(local_pts[:,0], local_pts[:,1], 'k--', linewidth=1.5, label='Field Outline (UTM)')
        ax.plot(waypoints[:,0], waypoints[:,1], '.-', markersize=2, label=f"{operation} Path")
        ax.set_title(f"{operation} Preview")
        ax.set_xlabel("Local X (m)"); ax.set_ylabel("Local Y (m)")
        ax.set_aspect('equal'); ax.grid(True); ax.legend()
        st.pyplot(fig)

        kml_str = create_kml(lat, lon, field_outline=local_pts)
        st.download_button("Download KML", kml_str.encode(), "field_waypoints.kml", "application/vnd.google-earth.kml+xml")
