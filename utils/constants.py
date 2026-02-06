"""Mnemonic aliases, default curve styles, and color constants."""

# Mnemonic aliasing: maps common LAS mnemonics to standardized names
MNEMONIC_ALIASES = {
    # Gamma Ray
    "GR": "GR", "SGR": "GR", "CGR": "GR", "GRD": "GR", "GRAM": "GR",
    # Caliper
    "CALI": "CALI", "CAL": "CALI", "HCAL": "CALI", "BS": "BS",
    # Spontaneous Potential
    "SP": "SP", "SSP": "SP",
    # Resistivity
    "ILD": "ILD", "RILD": "ILD",
    "ILM": "ILM", "RILM": "ILM",
    "LLD": "LLD", "RLLD": "LLD",
    "LLS": "LLS", "RLLS": "LLS",
    "MSFL": "MSFL", "RMSFL": "MSFL",
    "RT": "RT", "RD": "RT", "RESD": "RT", "AT90": "RT",
    "RXOZ": "RXOZ", "RS": "RXOZ", "RESS": "RXOZ",
    # Density
    "RHOB": "RHOB", "RHOZ": "RHOB", "DEN": "RHOB", "ZDEN": "RHOB",
    "DPHI": "DPHI", "PHID": "DPHI",
    # Neutron
    "NPHI": "NPHI", "TNPH": "NPHI", "NEU": "NPHI", "PHIN": "NPHI", "NPOR": "NPHI",
    # Sonic
    "DT": "DT", "DTC": "DT", "AC": "DT", "DTCO": "DT",
    "DTS": "DTS", "DTSM": "DTS",
    # Photoelectric
    "PE": "PE", "PEF": "PE", "PEFZ": "PE",
    # Depth
    "DEPT": "DEPT", "DEPTH": "DEPT", "MD": "DEPT",
}

# Default curve display styles: (color, linewidth, track, scale_type, min, max)
CURVE_STYLES = {
    "GR":    {"color": "green",   "width": 1.5, "track": 1, "scale": "linear", "min": 0,     "max": 150},
    "CALI":  {"color": "black",   "width": 1.0, "track": 1, "scale": "linear", "min": 6,     "max": 16},
    "SP":    {"color": "blue",    "width": 1.0, "track": 1, "scale": "linear", "min": -100,  "max": 50},
    "BS":    {"color": "gray",    "width": 1.0, "track": 1, "scale": "linear", "min": 6,     "max": 16},
    "ILD":   {"color": "red",     "width": 1.5, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "ILM":   {"color": "blue",    "width": 1.0, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "LLD":   {"color": "red",     "width": 1.5, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "LLS":   {"color": "blue",    "width": 1.0, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "MSFL":  {"color": "orange",  "width": 1.0, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "RT":    {"color": "red",     "width": 1.5, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "RXOZ":  {"color": "orange",  "width": 1.0, "track": 2, "scale": "log",    "min": 0.2,   "max": 200},
    "RHOB":  {"color": "red",     "width": 1.5, "track": 3, "scale": "linear", "min": 1.95,  "max": 2.95},
    "NPHI":  {"color": "blue",    "width": 1.5, "track": 3, "scale": "linear", "min": 0.45,  "max": -0.15},
    "DPHI":  {"color": "blue",    "width": 1.0, "track": 3, "scale": "linear", "min": 0.45,  "max": -0.15},
    "DT":    {"color": "purple",  "width": 1.5, "track": 3, "scale": "linear", "min": 140,   "max": 40},
    "PE":    {"color": "brown",   "width": 1.0, "track": 3, "scale": "linear", "min": 0,     "max": 10},
    # Computed curves
    "VSHALE":   {"color": "olive",    "width": 1.5, "track": 1, "scale": "linear", "min": 0, "max": 1},
    "PHIE":     {"color": "blue",     "width": 1.5, "track": 3, "scale": "linear", "min": 0.45, "max": -0.15},
    "SW":       {"color": "blue",     "width": 1.5, "track": 4, "scale": "linear", "min": 0, "max": 1},
    "PAY_FLAG": {"color": "gold",     "width": 2.0, "track": 5, "scale": "linear", "min": 0, "max": 1},
}

# Track header labels
DEFAULT_TRACK_LABELS = {
    1: "GR / Caliper",
    2: "Resistivity",
    3: "Porosity / Density",
    4: "Sw",
    5: "Pay Flag",
}

# Formation top colors for display
TOP_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
    "#469990", "#dcbeff", "#9A6324", "#800000", "#aaffc3",
]


def normalize_mnemonic(mnemonic: str) -> str:
    """Normalize a LAS mnemonic to its standard alias."""
    upper = mnemonic.strip().upper()
    return MNEMONIC_ALIASES.get(upper, upper)


def get_curve_style(mnemonic: str) -> dict:
    """Get display style for a curve mnemonic, with fallback defaults."""
    return CURVE_STYLES.get(mnemonic, {
        "color": "black", "width": 1.0, "track": 1,
        "scale": "linear", "min": None, "max": None,
    })
