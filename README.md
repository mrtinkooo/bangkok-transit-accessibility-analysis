# Bangkok Rail Network – Transit Accessibility Analysis

This repository provides a spatial accessibility analysis of Bangkok's rail network, including an interactive web map visualization.

## Files

- **`coverage.geojson`** - GeoJSON file containing:
  - 125 rail stations with metadata
  - 1 km buffer zones around each station (~10-15 min walk)
  - Network coverage footprint (233.21 km²)
  - Transit desert gaps (>5 km between consecutive stations)
  - Transit desert zones (areas far from any station)

- **`index.html`** - Interactive web map visualization
- **`spatial_analysis.py`** - Python script that generates the coverage.geojson file

## Using the Web Map

### Option 1: Open Directly (Simple)

Simply open `index.html` in your web browser:

```bash
open index.html  # macOS
xdg-open index.html  # Linux
start index.html  # Windows
```

Or double-click the `index.html` file in your file explorer.

### Option 2: Local Web Server (Recommended)

For best results, serve the files via a local web server:

```bash
# Python 3
python3 -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000

# Node.js (if you have http-server installed)
npx http-server
```

Then open http://localhost:8000 in your browser.

## Web Map Features

- **Interactive Visualization**: Pan and zoom to explore the map
- **Station Details**: Hover over stations to see names, lines, and services
- **Transit Coverage**: Visual representation of 1 km walking buffers
- **Transit Deserts**: Identification of underserved areas
- **Statistics**: Real-time display of network metrics
- **Legend**: Clear explanation of all map elements

### Controls

- **Zoom In**: Click the `+` button or use mouse wheel
- **Zoom Out**: Click the `-` button or use mouse wheel
- **Pan**: Click and drag the map
- **Reset View**: Click the home `⌂` button
- **Tooltips**: Hover over any feature to see details

## Generating the Data

To regenerate `coverage.geojson` from scratch:

```bash
python3 spatial_analysis.py
```

This requires the station data to be available in `dist/data.csv`.

## Analysis Highlights

- **Total Stations**: 125 rail stations across multiple lines
- **Transit Coverage**: 233.21 km² of urban area within walking distance
- **Buffer Radius**: 1 km (~10-15 minute walk)
- **Transit Deserts**: 2 gaps identified where consecutive stations are >5 km apart

## Technology

The web map is built with:
- Pure JavaScript (no external dependencies)
- SVG for vector graphics rendering
- HTML5 and CSS3 for responsive design
- Secure HTML escaping to prevent XSS vulnerabilities

No external libraries or internet connection required - everything runs locally in your browser.

## License

See repository license for details.
