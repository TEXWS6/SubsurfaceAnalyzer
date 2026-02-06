# SubsurfaceAnalyzer

A web-based subsurface geological analysis tool built with Dash and Plotly. Import well data, view logs, pick formation tops, run petrophysical analyses, generate contour maps, build cross sections, and calculate volumetrics — all from your browser.

## Features

### Data Import
- **LAS 2.0/3.0** — drag-and-drop upload with automatic mnemonic normalization and metadata extraction
- **IHS .297/.298** — fixed-width format import for well headers, completions, and monthly production data
- **Shapefiles** — .zip upload of .shp/.shx/.dbf/.prj; supports Polygon, LineString, Point, and Multi* geometry types via geopandas
- UWI-based deduplication on import

### Well Log Viewer
- Configurable multi-track display (GR, resistivity, porosity/density)
- Linear and logarithmic scales
- Formation top overlays
- Curve fill shading

### Formation Tops
- Interactive click-to-pick on log plots
- Manual depth entry with confidence levels (high/medium/low)
- Editable DataTable with inline editing and row deletion
- CSV export of all project tops

### Petrophysics
- **Vshale**: Linear, Larionov (Tertiary), Larionov (Older Rocks), Clavier
- **Porosity**: Density, Neutron, Density-Neutron crossplot
- **Water Saturation**: Archie equation
- **Net Pay**: Configurable cutoffs (porosity, Sw, Vshale)
- Save/load parameter sets and computed curves to database

### OOIP/OGIP Volumetrics
- **Deterministic**: Standard volumetric equations (7758 for oil, 43560 for gas)
- **Monte Carlo**: Triangular, normal, lognormal, and uniform distributions with configurable P10/P50/P90 output
- Histogram visualization with percentile markers
- Formation zone extraction bridges petrophysics results directly into volumetric inputs
- Polygon area calculator (Shoelace formula) for acreage from map drawings

### Contour Mapping
- **Map types**: Structure, Isopach, Bubble, Posted Values, Pie Chart, Grid Property
- **Interpolation**: Cubic, Linear, Nearest (scipy), Ordinary Kriging (pykrige), IDW
- **Shapefile overlays**: Toggle imported layers on/off, per-layer styling (line color/width, fill color/opacity, label field)
- Kriging variogram control (spherical/exponential/gaussian, manual or auto-fit sill/range/nugget)
- Polygon drawing mode for on-map area measurement
- Well coordinate editor with inline editing
- Save/load map configurations

### Cross Sections
- **Structural mode**: Wells at true TVDSS with shared depth axis
- **Stratigraphic mode**: Wells flattened on a datum formation
- Multi-curve display per well
- Formation correlation lines drawn across wells
- Uniform or proportional well spacing

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Dash 2.x, Dash Bootstrap Components, Plotly |
| Backend | Python 3.10+, NumPy, SciPy, pandas |
| Database | SQLite (thread-safe, WAL mode) |
| Kriging | PyKrige |
| Shapefiles | GeoPandas, Shapely |
| LAS Parsing | lasio |
| Server | Waitress (production) / Flask (dev) |

## Installation

```bash
git clone https://github.com/TEXWS6/SubsurfaceAnalyzer.git
cd SubsurfaceAnalyzer
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8050 in your browser.

## Project Structure

```
SubsurfaceAnalyzer/
├── app.py                  # Dash entry point
├── config.py               # App configuration
├── requirements.txt
├── components/
│   ├── log_plot.py         # Multi-track log figure builder
│   ├── cross_section.py    # Cross section figure builder
│   └── navbar.py           # Navigation bar
├── database/
│   ├── connection.py       # Thread-safe SQLite connection manager
│   ├── schema.py           # Schema definition + migrations
│   └── repositories/       # CRUD repositories (project, well, curve, tops,
│                           #   map, petro, production, completions, ooip, shapefile)
├── models/
│   └── domain.py           # Dataclasses (Well, Curve, FormationTop, ShapefileLayer, etc.)
├── pages/
│   ├── home.py             # Project management + LAS/IHS/Shapefile import
│   ├── well_log_viewer.py  # Multi-track log display
│   ├── formation_tops.py   # Top picking + editing
│   ├── petrophysics_page.py # Analysis + volumetrics
│   ├── contour_mapping.py  # All map types + interpolation + shapefile overlays
│   └── cross_section.py    # Cross section builder
├── services/
│   ├── las_parser.py       # LAS file parser
│   ├── ihs_parser.py       # IHS .297/.298 parser
│   ├── petrophysics.py     # Vshale, porosity, Sw, net pay
│   ├── volumetrics.py      # OOIP/OGIP + Monte Carlo
│   ├── mapping.py          # Interpolation + map builders + shapefile overlay
│   ├── shapefile_parser.py # Shapefile parser (geopandas)
│   └── export_service.py   # CSV export
├── utils/
│   ├── constants.py        # Mnemonic aliases, curve styles
│   └── validators.py       # Input validation
└── tests/                  # 166 tests (pytest)
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
