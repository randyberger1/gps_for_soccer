import streamlit as st
import simplekml
import numpy as np
from shapely.geometry import Polygon
import pyproj  # Coordinate transformation for UTM

# Function to convert lat/lon to UTM
def latlon_to_utm(lat, lon):
    wgs84 = pyproj.CRS("EPSG:4326")  # WGS84 (Lat/Lon)
    utm = pyproj.CRS("EPSG:32633")  # UTM zone 33N
    transformer = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True)
    return transformer.transform(lon, lat)

# Function to generate parallel lines for mowing
def generate_parallel_lines(polygon, mower_width, direction_angle=0, headland_passes=2):
    """Generate parallel mowing lines inside polygon"""
    minx, miny, maxx, maxy = polygon.bounds
    lines = []
    
    # Convert direction angle to radians
    angle_rad = np.radians(direction_angle)
    
    # Generate headland passes (parallel to the field boundary)
    for i in range(headland_passes):
        offset = i * mower_width
        line = [(minx + offset, miny), (minx + offset, maxy)]
        lines.append(line)
    
    # Generate mowing lines in the field area after headland passes
    x = minx + mower_width / 2  # Start position for mowing
    while x <= maxx:
        line = [(x, miny), (x, maxy)]
        lines.append(line)
        x += mower_width

    return lines

# Function to create KML from generated lines
def create_kml(lines, task_name):
    kml = simplekml.Kml()
    for idx, line in enumerate(lines):
        ls = kml.newlinestring(name=f"{task_name} Line {idx + 1}", coords=[(lon, lat) for lat, lon in line])
        ls.style.linestyle.color = simplekml.Color.blue if task_name == "Grass Cutting" else simplekml.Color.green
        ls.style.linestyle.width = 3
    return kml.kml().encode('utf-8')

# Main app
def main():
    st.title("Football Field Grass Cutting and Striping Generator")

    st.markdown("### Input Grass Field Boundary (lat, lon) Coordinates")
    default_coords = """43.555830, 27.826090
43.555775, 27.826100
43.555422, 27.826747
43.555425, 27.826786
43.556182, 27.827557
43.556217, 27.827538
43.556559, 27.826893
43.556547, 27.826833"""
    
    coords_text = st.text_area("Enter coordinates (lat, lon), one per line:", value=default_coords, height=150)
    field_coords = []
    
    # Parse the input coordinates
    for line in coords_text.split("\n"):
        try:
            lat, lon = map(float, line.strip().split(","))
            field_coords.append((lat, lon))
        except ValueError:
            continue
    
    # Validate coordinates
    if len(field_coords) < 3:
        st.warning("Please enter at least 3 coordinates to form a polygon.")
        return
    
    # Convert lat/lon to UTM and create Polygon
    polygon_coords = [latlon_to_utm(lat, lon) for lat, lon in field_coords]
    polygon = Polygon(polygon_coords)

    st.markdown("### Operational Parameters")
    mower_width = st.number_input("Grass Mower Operating Width (meters)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)
    headland_passes = st.number_input("Number of Headland Passes", min_value=1, max_value=5, value=2, step=1)
    mowing_direction = st.number_input("Mowing Direction Angle (degrees)", min_value=0, max_value=360, value=0, step=5)

    if st.button("Generate Waypoints"):
        # Generate waypoints for grass cutting task
        grass_lines = generate_parallel_lines(polygon, mower_width, direction_angle=mowing_direction, headland_passes=headland_passes)
        
        # Create KML for grass cutting
        grass_kml = create_kml(grass_lines, "Grass Cutting")
        
        # Provide KML download button
        st.download_button("Download Grass Cutting KML", grass_kml, "grass_cutting.kml", "application/vnd.google-earth.kml+xml")

if __name__ == "__main__":
    main()
