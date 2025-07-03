import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Streamlit UI
st.title('Football Field Robotics: Guidance Line Generation')

# Instructions for the user
st.write("""
    This app allows you to define coordinates of key points on a football field 
    (e.g., corners, goal areas) and generate guidance lines automatically based on these points.
""")

# Define the table of coordinates
columns = ['Point', 'X Coordinate', 'Y Coordinate']
data = {
    'Point': ['Top-Left Corner', 'Top-Right Corner', 'Bottom-Left Corner', 'Bottom-Right Corner', 'Center'],
    'X Coordinate': [0, 100, 0, 100, 50],
    'Y Coordinate': [0, 0, 50, 50, 25]
}
df = pd.DataFrame(data)

# Allow the user to modify the table
st.subheader('Define Coordinates of Key Points on the Field')
user_input_df = st.dataframe(df)

# Optionally, let users modify the coordinates
# In practice, Streamlit currently does not support editing the dataframe directly.
# You can create input boxes for each field.

# For simplicity, we will assume they are updated manually
# If needed, create an input form instead for custom points

# After user input, convert to numpy array
coordinates = user_input_df[['X Coordinate', 'Y Coordinate']].to_numpy()

# Create the plot
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_xlim(0, 100)  # Assuming 100x50 football field
ax.set_ylim(0, 50)

# Plot the coordinates
for idx, (x, y) in enumerate(coordinates):
    ax.scatter(x, y, label=f"Point {df.iloc[idx]['Point']} ({x},{y})", s=100)

# Optionally, connect the points with lines (e.g., connecting the corners)
for i in range(len(coordinates) - 1):
    x1, y1 = coordinates[i]
    x2, y2 = coordinates[i + 1]
    ax.plot([x1, x2], [y1, y2], color='blue', linestyle='--', linewidth=2)

# Customize the plot to simulate a field
ax.set_title('Football Field with Generated Guidance Lines')
ax.set_xlabel('X Coordinate')
ax.set_ylabel('Y Coordinate')
ax.grid(True)

# Show the plot in Streamlit
st.pyplot(fig)

# Add further instructions for generating more complex guidance lines
