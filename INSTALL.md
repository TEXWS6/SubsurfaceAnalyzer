# SubsurfaceAnalyzer — Installation Guide

## Prerequisites

- **Python 3.10 or newer** — Download from https://www.python.org/downloads/
  - During install, check **"Add Python to PATH"**
- **Git** — Download from https://git-scm.com/downloads (or use GitHub Desktop)

## Install Steps

1. **Open a terminal** (Command Prompt, PowerShell, or Terminal on Mac/Linux)

2. **Clone the repository**
   ```
   git clone https://github.com/TEXWS6/SubsurfaceAnalyzer.git
   cd SubsurfaceAnalyzer
   ```

3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```
   This installs Dash, Plotly, NumPy, SciPy, geopandas, pykrige, and other packages. May take a few minutes the first time.

4. **Run the app**
   ```
   python app.py
   ```

5. **Open your browser** to http://127.0.0.1:8050

That's it — the app runs entirely on your local machine with no external database or server required.

## Quick Start

1. **Create a project** on the Home page
2. **Import data** — drag and drop LAS files, IHS .297/.298 files, or shapefile .zip archives
3. **Explore** — use the navbar to access Log Viewer, Formation Tops, Petrophysics, Contour Maps, Cross Sections, and Production Data

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python` not found | Try `python3` instead, or reinstall Python with "Add to PATH" checked |
| `pip` not found | Try `python -m pip install -r requirements.txt` |
| Port 8050 already in use | Close other instances, or edit `config.py` to change `APP_PORT` |
| Import errors on startup | Make sure you ran `pip install -r requirements.txt` from inside the project folder |
| geopandas install fails | On Windows, try `pip install --upgrade pip` first. On Mac, you may need `brew install gdal` beforehand |

## Updating

To get the latest version:
```
cd SubsurfaceAnalyzer
git pull
pip install -r requirements.txt
python app.py
```
