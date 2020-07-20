# Transects
Create a set of line perpendiculars (cross-sections) to a given line shapefile. Included is an example shapefile that runs along the Himalaya. Use from the command line with:

python Transects_From_Line.py Himalaya_Arc.shp Lines.shp 50 100

Where 50 is slice_width: the distance between perpendiculars, 100 is the edge_length: length of each half of perpendicular line. Total length will be twice
All distance units in MAP UNITS.

This repo is created by making modifications to https://github.com/tasmi/Transects, which is used to create perpendicualr boxes. 
