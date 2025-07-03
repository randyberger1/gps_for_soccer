import streamlit as st
import folium
from streamlit_folium import st_folium
import simplekml

# Default grass field boundary coordinates (lat, lon)
default_boundary = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693)
]

def main():
    st.title("Minimal Football Field Waypoints Demo")

    # Input coordinates text area
    coords_text = st.text_area(
        "Enter grass field boundary coordinates (lat,lon) one per line:",
        value="\n".join([f"{lat},{lon}" for lat, lon in default_boundary]),
        height=120
    )

    # Parse input coords
    try:
        boundary_coords = [
            tuple(map(float, line.strip().split(',')))
            for line in coords_text.strip().split('\n') if line.strip()
        ]
        if len(boundary_coords) < 3:
            st.error("Please enter at least 3 coordinates to form a polygon.")
            return
    except Exception:
        st.error("Invalid coordinate format. Use 'lat,lon' per line.")
        return

    # For demo, let's just use the boundary itself as waypoints
    waypoints = boundary_coords + [boundary_coords[0]]  # close polygon as path

    # Create Folium map
    m = create_map(boundary_coords, waypoints)

    # Display map in Streamlit
    st_data = st_folium(m, width=700, height=500)

    # Export KML
    kml_bytes = export_kml(waypoints)

    st.download_button(
        label="Download Waypoints KML",
        data=kml_bytes,
        file_name="waypoints.kml",
        mime="application/vnd.google-earth.kml+xml"
    )

def create_map(boundary_coords, waypoints):
    # Center map on centroid of boundary
    lat_center = sum(lat for lat, lon in boundary_coords) / len(boundary_coords)
    lon_center = sum(lon for lat, lon in boundary_coords) / len(boundary_coords)

    m = folium.Map(location=[lat_center, lon_center], zoom_start=18)

    # Add polygon for the boundary
    folium.Polygon(
        locations=boundary_coords,
        color="green",
        weight=3,
        fill=True,
        fill_opacity=0.2,
        popup="Field Boundary"
    ).add_to(m)

    # Add polyline for waypoints (closed loop)
    folium.PolyLine(
        locations=waypoints,
        color="blue",
        weight=3,
        popup="Waypoints"
    ).add_to(m)

    # Add markers for waypoints
    for i, point in enumerate(waypoints):
        folium.Marker(
            location=point,
            popup=f"WP {i+1}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

    return m

def export_kml(waypoints):
    kml = simplekml.Kml()
    linestring = kml.newlinestring(name="Waypoints Path")
    # Note KML uses (lon, lat)
    linestring.coords = [(lon, lat) for lat, lon in waypoints]
    linestring.style.linestyle.color = simplekml.Color.blue
    linestring.style.linestyle.width = 3
    # Return bytes (string encoded as utf-8)
    return kml.kml().encode('utf-8')

if __name__ == "__main__":
    main()
