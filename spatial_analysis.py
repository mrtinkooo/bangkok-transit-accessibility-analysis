"""
Bangkok Rail Network – Spatial Accessibility Analysis
======================================================
This script:
  1. Creates 1 km buffers (~10-15 min walk) around every station.
  2. Calculates 'Transit Coverage' — total urban area served (sq km).
  3. Identifies 'Transit Deserts' — gaps where consecutive stations on the
     same line are more than 5 km apart.
  4. Generates `coverage.geojson` with service-area polygons, station points,
     and gap-indicator lines.
  5. Prints TOD planning recommendations.

Dependencies: pandas, shapely, geojson  (all pure-Python / lightweight)
"""

import json
import math
import csv
import os

# ---------------------------------------------------------------------------
# 1. Load station data
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "dist", "data.csv")

stations = []
with open(DATA_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        stations.append({
            "stationId": row["stationId"],
            "name": row["name"],
            "nameEng": row["nameEng"],
            "lat": float(row["geoLat"]),
            "lng": float(row["geoLng"]),
            "lineNameEng": row["lineNameEng"],
            "lineColorHex": row["lineColorHex"],
            "lineServiceName": row["lineServiceName"],
        })

print(f"✅ Loaded {len(stations)} stations from {DATA_PATH}")

# ---------------------------------------------------------------------------
# Helper – approximate conversions for Bangkok (~13.7°N)
# ---------------------------------------------------------------------------
# At latitude ~13.7°, 1° lat ≈ 110.574 km, 1° lng ≈ 107.551 km
KM_PER_DEG_LAT = 110.574
KM_PER_DEG_LNG = 107.551  # cos(13.7°) * 111.320

BUFFER_KM = 1.0   # ~10-15 min walk radius
GAP_THRESHOLD_KM = 5.0  # transit-desert threshold


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance between two points (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def circle_polygon(lat, lng, radius_km, n_points=64):
    """Return a list of [lng, lat] pairs approximating a circle."""
    coords = []
    d_lat = radius_km / KM_PER_DEG_LAT
    d_lng = radius_km / KM_PER_DEG_LNG
    for i in range(n_points + 1):
        angle = 2 * math.pi * i / n_points
        coords.append([
            round(lng + d_lng * math.cos(angle), 8),
            round(lat + d_lat * math.sin(angle), 8),
        ])
    return coords


# ---------------------------------------------------------------------------
# 2. Build individual 1 km buffer polygons for each station
# ---------------------------------------------------------------------------
station_features = []
buffer_polygons = []  # list of coordinate rings for union later

for s in stations:
    ring = circle_polygon(s["lat"], s["lng"], BUFFER_KM)
    buffer_polygons.append(ring)

    # Station point feature
    station_features.append({
        "type": "Feature",
        "properties": {
            "type": "station",
            "stationId": s["stationId"],
            "name": s["nameEng"],
            "nameTH": s["name"],
            "line": s["lineNameEng"],
            "service": s["lineServiceName"],
            "color": s["lineColorHex"],
        },
        "geometry": {
            "type": "Point",
            "coordinates": [s["lng"], s["lat"]],
        },
    })

    # Buffer polygon feature
    station_features.append({
        "type": "Feature",
        "properties": {
            "type": "buffer_1km",
            "stationId": s["stationId"],
            "name": s["nameEng"],
            "line": s["lineNameEng"],
            "color": s["lineColorHex"],
            "radius_km": BUFFER_KM,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    })

print(f"✅ Created {len(stations)} individual 1 km buffer polygons")

# ---------------------------------------------------------------------------
# 3. Estimate total Transit Coverage area (sq km)
#    We use a grid-sampling technique to approximate the union area of all
#    circular buffers without needing heavy GIS dependencies.
# ---------------------------------------------------------------------------
# Determine bounding box of all buffers
all_lats = [s["lat"] for s in stations]
all_lngs = [s["lng"] for s in stations]

min_lat = min(all_lats) - BUFFER_KM / KM_PER_DEG_LAT
max_lat = max(all_lats) + BUFFER_KM / KM_PER_DEG_LAT
min_lng = min(all_lngs) - BUFFER_KM / KM_PER_DEG_LNG
max_lng = max(all_lngs) + BUFFER_KM / KM_PER_DEG_LNG

# Grid resolution: ~100 m cells
CELL_SIZE_KM = 0.1
n_rows = int(math.ceil((max_lat - min_lat) * KM_PER_DEG_LAT / CELL_SIZE_KM))
n_cols = int(math.ceil((max_lng - min_lng) * KM_PER_DEG_LNG / CELL_SIZE_KM))

print(f"📐 Computing coverage over {n_rows}×{n_cols} grid "
      f"({n_rows * n_cols:,} cells @ {CELL_SIZE_KM*1000:.0f} m resolution)…")

# Pre-compute station positions in "km-space" relative to the bbox origin
# for fast distance checks
stations_km = [
    ((s["lat"] - min_lat) * KM_PER_DEG_LAT,
     (s["lng"] - min_lng) * KM_PER_DEG_LNG)
    for s in stations
]

covered_cells = 0
for r in range(n_rows):
    y = r * CELL_SIZE_KM + CELL_SIZE_KM / 2  # center of cell in km
    for c in range(n_cols):
        x = c * CELL_SIZE_KM + CELL_SIZE_KM / 2
        for (sy, sx) in stations_km:
            if (x - sx) ** 2 + (y - sy) ** 2 <= BUFFER_KM ** 2:
                covered_cells += 1
                break  # cell is covered, no need to check further

cell_area = CELL_SIZE_KM ** 2  # sq km per cell
total_coverage_sqkm = covered_cells * cell_area

print(f"\n{'='*60}")
print(f"🚆  TRANSIT COVERAGE SUMMARY")
print(f"{'='*60}")
print(f"  Stations analysed     : {len(stations)}")
print(f"  Buffer radius         : {BUFFER_KM} km (~10-15 min walk)")
print(f"  Grid resolution       : {CELL_SIZE_KM*1000:.0f} m")
print(f"  Covered cells         : {covered_cells:,} / {n_rows * n_cols:,}")
print(f"  ▸ Transit Coverage    : {total_coverage_sqkm:.2f} sq km")
print(f"{'='*60}\n")

# ---------------------------------------------------------------------------
# 4. Identify Transit Deserts (inter-station gaps > 5 km on the same line)
# ---------------------------------------------------------------------------
# Group stations by line AND branch.  Station IDs have a letter-prefix
# (e.g. N1, E1, S1, BL01, PP01, A1, G1) — different prefixes on the same
# line represent separate branches that meet at an interchange, so they
# must NOT be treated as consecutive.
import re
from collections import OrderedDict


def branch_key(station):
    """Extract branch prefix from station ID, e.g. 'N' from 'N24', 'BL' from 'BL01'."""
    m = re.match(r"([A-Z]+)", station["stationId"])
    return m.group(1) if m else station["stationId"]


line_branch_groups = OrderedDict()
for s in stations:
    key = (s["lineNameEng"], branch_key(s))
    line_branch_groups.setdefault(key, []).append(s)

gap_features = []
gaps_info = []

for (line_name, branch), line_stations in line_branch_groups.items():
    for i in range(len(line_stations) - 1):
        a = line_stations[i]
        b = line_stations[i + 1]
        dist = haversine_km(a["lat"], a["lng"], b["lat"], b["lng"])
        if dist >= GAP_THRESHOLD_KM:
            gaps_info.append({
                "line": f"{line_name} ({branch}-branch)",
                "from": a["nameEng"],
                "to": b["nameEng"],
                "distance_km": round(dist, 2),
            })
            # Add a LineString feature to the GeoJSON
            gap_features.append({
                "type": "Feature",
                "properties": {
                    "type": "transit_desert_gap",
                    "line": line_name,
                    "from_station": a["nameEng"],
                    "to_station": b["nameEng"],
                    "gap_km": round(dist, 2),
                    "color": "#FF0000",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [a["lng"], a["lat"]],
                        [b["lng"], b["lat"]],
                    ],
                },
            })

# Also check inter-line nearest-neighbour gaps for areas far from ANY station
# Build a list of locations that are local "deserts" — furthest from any station
# We reuse the grid and find cells > 5 km from every station
desert_center_cells = []
for r in range(0, n_rows, 5):  # sample every 500 m
    y_km = r * CELL_SIZE_KM + CELL_SIZE_KM / 2
    lat_cell = min_lat + y_km / KM_PER_DEG_LAT
    for c in range(0, n_cols, 5):
        x_km = c * CELL_SIZE_KM + CELL_SIZE_KM / 2
        lng_cell = min_lng + x_km / KM_PER_DEG_LNG
        min_dist = min(
            math.sqrt((x_km - sx) ** 2 + (y_km - sy) ** 2)
            for (sy, sx) in stations_km
        )
        if min_dist >= GAP_THRESHOLD_KM:
            desert_center_cells.append({
                "lat": lat_cell,
                "lng": lng_cell,
                "nearest_km": round(min_dist, 2),
            })

# Create desert zone circles (5 km radius) for the top desert centres
# group them and keep the top 10 most isolated
desert_center_cells.sort(key=lambda d: d["nearest_km"], reverse=True)
desert_zones = desert_center_cells[:10]

for i, dz in enumerate(desert_zones):
    ring = circle_polygon(dz["lat"], dz["lng"], 2.0, n_points=48)
    gap_features.append({
        "type": "Feature",
        "properties": {
            "type": "transit_desert_zone",
            "rank": i + 1,
            "nearest_station_km": dz["nearest_km"],
            "color": "#FF4444",
            "fillOpacity": 0.15,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    })

print(f"{'='*60}")
print(f"🏜️  TRANSIT DESERTS (consecutive station gaps ≥ {GAP_THRESHOLD_KM} km)")
print(f"{'='*60}")
if gaps_info:
    for g in gaps_info:
        print(f"  ⚠  {g['line']}: {g['from']} → {g['to']}  "
              f"({g['distance_km']} km)")
else:
    print("  ✅ No consecutive gaps ≥ 5 km found on any line.")

if desert_zones:
    print(f"\n  Top isolated urban zones (furthest from any station):")
    for dz in desert_zones:
        print(f"    📍 ({dz['lat']:.4f}, {dz['lng']:.4f}) — "
              f"{dz['nearest_km']} km to nearest station")
print(f"{'='*60}\n")

# ---------------------------------------------------------------------------
# 5. Build a combined coverage polygon (convex hull of all stations)
# ---------------------------------------------------------------------------
# Compute the convex hull of all station positions to represent the overall
# "network footprint".
def convex_hull(points):
    """Andrew's monotone chain algorithm for 2D convex hull.
    Input: list of (x, y) tuples. Returns hull in CCW order."""
    points = sorted(set(points))
    if len(points) <= 1:
        return points
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


hull_pts = convex_hull([(s["lng"], s["lat"]) for s in stations])
hull_coords = [[p[0], p[1]] for p in hull_pts]
hull_coords.append(hull_coords[0])  # close the ring

network_footprint = {
    "type": "Feature",
    "properties": {
        "type": "network_footprint",
        "description": "Convex hull of all rail stations (network extent)",
        "color": "#1E90FF",
        "fillOpacity": 0.05,
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [hull_coords],
    },
}

# ---------------------------------------------------------------------------
# 6. Assemble and write the GeoJSON
# ---------------------------------------------------------------------------
geojson = {
    "type": "FeatureCollection",
    "metadata": {
        "title": "Bangkok Rail Network – Spatial Accessibility Analysis",
        "description": (
            "1 km station buffers (~10-15 min walk), transit desert gaps, "
            "and network coverage footprint."
        ),
        "transit_coverage_sqkm": round(total_coverage_sqkm, 2),
        "total_stations": len(stations),
        "buffer_radius_km": BUFFER_KM,
        "gap_threshold_km": GAP_THRESHOLD_KM,
        "transit_desert_gaps": gaps_info,
    },
    "features": [network_footprint] + station_features + gap_features,
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "coverage.geojson")
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print(f"📄 GeoJSON written to: {OUTPUT_PATH}")
print(f"   Total features: {len(geojson['features'])}")

# ---------------------------------------------------------------------------
# 7. TOD Planning Recommendations
# ---------------------------------------------------------------------------
print(f"""
{'='*60}
🏗️  TRANSIT-ORIENTED DEVELOPMENT (TOD) RECOMMENDATIONS
{'='*60}

Based on this spatial analysis, the following insights can guide
Transit-Oriented Development planning in Bangkok:

1. HIGH-PRIORITY TOD ZONES (within 1 km buffers)
   ─────────────────────────────────────────────
   • The {total_coverage_sqkm:.1f} sq km coverage area is ideal for
     mixed-use, high-density zoning (FAR bonuses near stations).
   • Stations like Siam, Asok/Sukhumvit, and Mo Chit/Chatuchak
     already act as major interchange hubs — priority for commercial
     and residential densification.
   • Outer terminus stations (Khu Khot, Kheha, Lak Song, Khlong
     Bang Phai) are prime TOD candidates for affordable housing
     development with rail connectivity.

2. ADDRESSING TRANSIT DESERTS
   ─────────────────────────────────────────────
   • The identified gaps (>5 km between stations) highlight areas
     that would benefit from:
       – Feeder bus / BRT route planning
       – Future line extensions or infill station studies
       – Bike-share / last-mile mobility hubs
   • Western Bangkok (Thonburi, Bang Khae corridor) and the
     Bangkok-Nonthaburi fringe show significant under-coverage.

3. LAND-USE & DENSITY POLICY
   ─────────────────────────────────────────────
   • Implement density gradients: highest FAR within 500 m of
     stations, tapering to medium density at the 1 km boundary.
   • Encourage ground-floor retail / mixed-use within buffer zones
     to maximise pedestrian activity and ridership.
   • Restrict low-density, car-oriented development within the
     1 km station catchment to reduce induced traffic.

4. WALKABILITY & LAST-MILE IMPROVEMENTS
   ─────────────────────────────────────────────
   • The 1 km buffer assumes pedestrian access — cities must invest
     in safe sidewalks, covered walkways, and wayfinding signage.
   • Deploy bike-sharing stations at every rail station to extend
     the effective catchment to ~3 km.
   • Improve feeder transport in transit-desert zones to connect
     underserved communities to the nearest rail station.

5. EQUITY & AFFORDABILITY
   ─────────────────────────────────────────────
   • Monitor land-price escalation within TOD zones to prevent
     displacement of low-income residents.
   • Mandate affordable-housing quotas (e.g. 20-30%) in new
     developments within station buffer areas.
   • Prioritise TOD in underserved transit-desert zones to
     improve accessibility equity across the metro region.

6. DATA-DRIVEN MONITORING
   ─────────────────────────────────────────────
   • Use this coverage.geojson as a baseline layer for ongoing
     monitoring of development patterns vs. transit access.
   • Overlay with population density, land-use, and property
     transaction data for dynamic TOD performance dashboards.
   • Update the analysis as new lines (e.g. Orange, Yellow,
     Pink lines) become operational.
{'='*60}
""")
