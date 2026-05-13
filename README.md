# OSM Road Quality Analyzer

A Python-based geospatial pipeline that evaluates the **attribute completeness** of OpenStreetMap road networks for any city and visualizes the results as an interactive quality map.

---

## Motivation

OpenStreetMap data quality varies significantly across urban areas. Missing attributes like `maxspeed`, `surface`, or `lit` can hinder routing, urban planning, and infrastructure management decisions. This tool automates the **attribute completeness** assessment of road network data — directly applicable to smart city, mobility, and humanitarian GIS workflows.

---

## Features

- **Automated OSM data retrieval** via `osmnx` for any city worldwide
- **Attribute completeness scoring** per road segment (0–100 %)
- **Color-coded interactive map** with click-to-highlight and tooltips
- **Summary statistics** on completeness per attribute and quality class
- **Reproducible environment** via conda

---

## Quality Classification

| Color | Class | Score |
|---|---|---|
| 🟢 Green | Good | ≥ 80 % |
| 🟡 Yellow | Medium | 60–79 % |
| 🟠 Orange | Weak | 40–59 % |
| 🔴 Red | Critical | < 40 % |

### Scoring Formula

For each road segment, 5 attributes are checked for presence:

```
score = (attributes present / total attributes) × 100
```

**Example — Zeil, Frankfurt:**

| Attribute | Value | Present |
|---|---|---|
| name | Zeil | ✅ |
| maxspeed | — | ❌ |
| surface | asphalt | ✅ |
| lit | yes | ✅ |
| lanes | — | ❌ |

```
score = 3/5 × 100 = 60 %  →  Medium (yellow)
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| `osmnx` | OSM graph download & processing |
| `geopandas` | Geospatial data handling |
| `folium` | Interactive Leaflet.js map |
| `pandas` | Tabular analysis |
| `Python 3.11` | Core language |

---

## Installation

### With conda (recommended)

```bash
conda create -n osm-quality python=3.11
conda activate osm-quality
conda install -c conda-forge osmnx geopandas folium pandas shapely
pip install sqlalchemy
```

### Export environment

```bash
conda env export > environment.yml
```

### Reproduce environment

```bash
conda env create -f environment.yml
conda activate osm-quality
```

---

## Usage

```bash
# Small town — fast loading
python osm_road_quality_analyzer.py --city "Bensheim, Germany"

# Custom output path
python osm_road_quality_analyzer.py --city "Weinheim, Germany" --output weinheim.html

# Also export summary as JSON
python osm_road_quality_analyzer.py --city "Darmstadt-Bessungen, Darmstadt, Germany" --export-json
```

The script outputs an interactive `road_quality.html` — open it in any browser.

---

## Project Structure

```
osm-road-quality-analyzer/
├── osm_road_quality_analyzer.py   # Main analysis pipeline
├── environment.yml                # Conda environment
└── README.md
```

---

## Author

**Tahira Ullah** — Geoinformatikerin  
MSc Geography (Geoinformatics), Ruprecht-Karls-Universität Heidelberg  
📧 tahira.ullah@hotmail.de  
🌍 Frankfurt am Main, Germany

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

*Data © OpenStreetMap contributors — [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright)*
