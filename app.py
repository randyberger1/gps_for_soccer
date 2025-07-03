import streamlit as st
import folium
from streamlit_folium import st_folium
import simplekml

# Default boundary coordinates (lat, lon)
default_boundary = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693)
]

def main():
    st.title("Football Field Waypoints Generator")

    # Input boundary coords
    st.write("**Grass Field Boundary Coordinates (lat, lon):**")
    coords_text = st.text_area(
        "Enter lat,lon per line (default example shown):",
        value="\n".join([f"{lat},{lon}" for lat, lon in default_boundary]),
        height=100
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
        st.error("Invalid input format. Please enter coordinates as lat,lon per line.")
        return

    mower_width = st.number_input("Mower Operating Width (meters)", min_value=0.1, value=3.0, step=0.1)

    task = st.selectbox("Select Task", ["Grass Cutting", "Lawn Striping", "Pitch Marking"])

    if st.button("Generate Waypoints"):
        # Generate waypoints based on task
        if task == "Pitch Marking":
            waypoints = generate_pitch_marking(boundary_coords)
        elif task == "Grass Cutting":
            waypoints = generate_grass_cutting(boundary_coords, mower_width)
        else:  # Lawn Striping
            waypoints = generate_lawn_striping(boundary_coords, mower_width)

        # Display map with waypoints
        m = create_map(boundary_coords, waypoints)
        st_folium(m, width=700, height=500)

        # Export KML
        kml_file = export_kml(waypoints)
        st.download_button(label="Download Waypoints KML", data=kml_file, file_name="waypoints.kml", mime="application/vnd.google-earth.kml+xml")

# Placeholder functions — will implement next
def generate_pitch_marking(boundary_coords):
    # For now, just return the boundary polygon as waypoints
    return boundary_coords

def generate_grass_cutting(boundary_coords, width):
    # Simple example: generate parallel lines within the polygon
    # Implement later
    return boundary_coords

def generate_lawn_striping(boundary_coords, width):
    # Simple example: generate stripes
    # Implement later
    return boundary_coords

def create_map(boundary_coords, waypoints):
    # Center map on field centroid
    lat_center = sum(lat for lat, lon in boundary_coords) / len(boundary_coords)
    lon_center = sum(lon for lat, lon in boundary_coords) / len(boundary_coords)

    m = folium.Map(location=[lat_center, lon_center], zoom_start=18)

    # Draw boundary polygon
    folium.Polygon(locations=boundary_coords, color="green", weight=3, fill=True, fill_opacity=0.1).add_to(m)

    # Draw waypoints as polyline
    folium.PolyLine(locations=waypoints, color="blue", weight=2).add_to(m)

    return m

def export_kml(waypoints):
    kml = simplekml.Kml()
    ls = kml.newlinestring(name="Waypoints")
    ls.coords = [(lon, lat) for lat, lon in waypoints]
    ls.style.linestyle.width = 3
    ls.style.linestyle.color = simplekml.Color.blue
    return kml.kml()

if __name__ == "__main__":
    main()
