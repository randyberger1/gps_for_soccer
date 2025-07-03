import streamlit as st
import folium
from streamlit_folium import st_folium
import simplekml
from io import BytesIO

def create_kml(lines_latlon):
    kml = simplekml.Kml()
    for points in lines_latlon:
        # simplekml expects (lon, lat)
        kml.newlinestring(coords=[(lon, lat) for lat, lon in points], altitudemode='clampToGround')
    return kml.kml()

def main():
    st.title("Grass Cutting Driving Course Generator")

    # Your 8 vertices of the field boundary
    field_boundary = [
        (43.555830, 27.826090),
        (43.555775, 27.826100),
        (43.555422, 27.826747),
        (43.555425, 27.826786),
        (43.556182, 27.827557),
        (43.556217, 27.827538),
        (43.556559, 27.826893),
        (43.556547, 27.826833),
        (43.555830, 27.826090)  # Close polygon
    ]

    mower_width = st.number_input("Mower Operating Width (m)", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
    headland_passes = st.number_input("Number of Headland Passes", min_value=0, max_value=5, value=2, step=1)
    driving_direction = st.selectbox("Driving Direction", ["Along longest side", "Perpendicular to longest side"])

    if st.button("Generate Driving Course"):
        # Dummy driving course: generate vertical lines inside polygon for demo
        # Real logic should generate lines based on driving_direction & mower_width
        num_passes = 5
        driving_lines = []
        lats = [pt[0] for pt in field_boundary]
        lons = [pt[1] for pt in field_boundary]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        lon_step = (max_lon - min_lon) / (num_passes - 1)

        for i in range(num_passes):
            lon = min_lon + i * lon_step
            line = [(min_lat, lon), (max_lat, lon)]
            driving_lines.append(line)

        # Display map with polygon and driving lines
        m = folium.Map(location=field_boundary[0], zoom_start=18)
        folium.Polygon(locations=field_boundary, color="green", fill=True, fill_opacity=0.3).add_to(m)
        for line in driving_lines:
            folium.PolyLine(locations=line, color="blue", weight=3).add_to(m)

        st_folium(m, width=700, height=500)

        # Create KML for download
        kml_content = create_kml(driving_lines)
        kml_bytes = BytesIO(kml_content.encode("utf-8"))

        st.download_button(
            label="Download Driving Course KML",
            data=kml_bytes,
            file_name="driving_course.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

if __name__ == "__main__":
    main()
