# download_tiles.py
# -----------------
# Download OpenStreetMap tiles for a given area and zoom levels.
# Tiles are saved in tiles/{zoom}/{x}/{y}.png

import os
import math
import requests

def latlon_to_tile(lat, lon, zoom):
    """Convert latitude/longitude to tile x, y coordinates."""
    n = 2 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
    return xtile, ytile

def download_tile(x, y, z, folder="tiles"):
    """Download a single OSM tile."""
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    path = f"{folder}/{z}/{x}/{y}.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        print(f"Tile {z}/{x}/{y} already exists, skipping.")
        return
    r = requests.get(url)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"Downloaded tile {z}/{x}/{y}")
    else:
        print(f"Failed to download tile {z}/{x}/{y}: {r.status_code}")

def download_tiles_for_area(lat_min, lat_max, lon_min, lon_max, zoom_min, zoom_max, folder="tiles"):
    """Download all tiles for the given bounding box and zoom levels."""
    for z in range(zoom_min, zoom_max + 1):
        x_min, y_max = latlon_to_tile(lat_min, lon_min, z)
        x_max, y_min = latlon_to_tile(lat_max, lon_max, z)
        if x_min > x_max: x_min, x_max = x_max, x_min
        if y_min > y_max: y_min, y_max = y_max, y_min
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                download_tile(x, y, z, folder)

# ------------------- Example Usage -------------------
if __name__ == "__main__":
    # Replace with your area of interest
    lat_min, lat_max = 37.0, 38.0      # latitude bounds
    lon_min, lon_max = -123.0, -122.0  # longitude bounds
    zoom_min, zoom_max = 3, 5          # zoom levels to download
    download_tiles_for_area(lat_min, lat_max, lon_min, lon_max, zoom_min, zoom_max)
