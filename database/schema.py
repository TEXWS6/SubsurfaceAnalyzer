"""SQLite database schema definition and initialization."""

from database.connection import db

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    uwi TEXT DEFAULT '',
    name TEXT NOT NULL,
    x_coord REAL,
    y_coord REAL,
    kb REAL,
    td REAL,
    las_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS curves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    mnemonic TEXT NOT NULL,
    original_mnemonic TEXT NOT NULL,
    unit TEXT DEFAULT '',
    depth_min REAL,
    depth_max REAL,
    sample_count INTEGER,
    data BLOB NOT NULL,
    depth_data BLOB NOT NULL,
    is_computed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (well_id) REFERENCES wells(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS formation_tops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    formation TEXT NOT NULL,
    md_top REAL NOT NULL,
    md_base REAL,
    confidence TEXT DEFAULT 'medium',
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (well_id) REFERENCES wells(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS map_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    map_type TEXT NOT NULL DEFAULT 'structure',
    formation_top TEXT,
    formation_base TEXT,
    interpolation_method TEXT DEFAULT 'cubic',
    grid_resolution INTEGER DEFAULT 100,
    colorscale TEXT DEFAULT 'Viridis',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS petro_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT 'default',
    vshale_method TEXT DEFAULT 'linear',
    gr_clean REAL DEFAULT 20.0,
    gr_shale REAL DEFAULT 120.0,
    rho_matrix REAL DEFAULT 2.65,
    rho_fluid REAL DEFAULT 1.0,
    nphi_matrix REAL DEFAULT 0.0,
    archie_a REAL DEFAULT 1.0,
    archie_m REAL DEFAULT 2.0,
    archie_n REAL DEFAULT 2.0,
    rw REAL DEFAULT 0.05,
    phi_cutoff REAL DEFAULT 0.08,
    sw_cutoff REAL DEFAULT 0.5,
    vshale_cutoff REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (well_id) REFERENCES wells(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS production_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    oil_vol REAL DEFAULT 0,
    gas_vol REAL DEFAULT 0,
    water_vol REAL DEFAULT 0,
    days_produced REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (well_id) REFERENCES wells(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    perf_top REAL,
    perf_base REAL,
    completion_date TEXT,
    treatment_type TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (well_id) REFERENCES wells(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ooip_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER,
    project_id INTEGER,
    formation TEXT,
    method TEXT NOT NULL DEFAULT 'deterministic',
    ooip REAL,
    ogip REAL,
    parameters_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (well_id) REFERENCES wells(id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""


def init_db():
    """Create all tables if they don't exist."""
    conn = db.get_connection()
    conn.executescript(SCHEMA_SQL)

    # Migrate map_configs with new columns (idempotent)
    alter_cols = [
        ("kriging_model", "TEXT DEFAULT 'spherical'"),
        ("kriging_sill", "REAL"),
        ("kriging_range", "REAL"),
        ("kriging_nugget", "REAL"),
        ("idw_power", "REAL DEFAULT 2.0"),
        ("extra_config_json", "TEXT DEFAULT '{}'"),
    ]
    for col_name, col_def in alter_cols:
        try:
            conn.execute(f"ALTER TABLE map_configs ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass  # Column already exists

    conn.commit()
