"""Domain model dataclasses."""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class Project:
    id: int = 0
    name: str = ""
    description: str = ""


@dataclass
class Well:
    id: int = 0
    project_id: int = 0
    uwi: str = ""
    name: str = ""
    x_coord: Optional[float] = None
    y_coord: Optional[float] = None
    kb: Optional[float] = None
    td: Optional[float] = None
    las_path: Optional[str] = None


@dataclass
class Curve:
    id: int = 0
    well_id: int = 0
    mnemonic: str = ""
    original_mnemonic: str = ""
    unit: str = ""
    depth_min: Optional[float] = None
    depth_max: Optional[float] = None
    sample_count: int = 0
    is_computed: bool = False
    depth_data: Optional[np.ndarray] = field(default=None, repr=False)
    data: Optional[np.ndarray] = field(default=None, repr=False)


@dataclass
class FormationTop:
    id: int = 0
    well_id: int = 0
    formation: str = ""
    md_top: float = 0.0
    md_base: Optional[float] = None
    confidence: str = "medium"
    source: str = "manual"


@dataclass
class PetroParams:
    id: int = 0
    well_id: int = 0
    name: str = "default"
    vshale_method: str = "linear"
    gr_clean: float = 20.0
    gr_shale: float = 120.0
    rho_matrix: float = 2.65
    rho_fluid: float = 1.0
    nphi_matrix: float = 0.0
    archie_a: float = 1.0
    archie_m: float = 2.0
    archie_n: float = 2.0
    rw: float = 0.05
    phi_cutoff: float = 0.08
    sw_cutoff: float = 0.5
    vshale_cutoff: float = 0.5


@dataclass
class ProductionRecord:
    id: int = 0
    well_id: int = 0
    date: str = ""
    oil_vol: float = 0.0
    gas_vol: float = 0.0
    water_vol: float = 0.0
    days_produced: float = 0.0


@dataclass
class Completion:
    id: int = 0
    well_id: int = 0
    perf_top: Optional[float] = None
    perf_base: Optional[float] = None
    completion_date: Optional[str] = None
    treatment_type: str = ""


@dataclass
class OOIPResult:
    id: int = 0
    well_id: Optional[int] = None
    project_id: Optional[int] = None
    formation: str = ""
    method: str = "deterministic"
    ooip: Optional[float] = None
    ogip: Optional[float] = None
    parameters_json: str = "{}"


@dataclass
class ShapefileLayer:
    id: int = 0
    project_id: int = 0
    name: str = ""
    geometry_type: str = ""
    feature_count: int = 0
    bounds_json: str = ""
    crs_wkt: str = ""
    attribute_columns_json: str = "[]"
    line_color: str = "#000000"
    line_width: float = 1.5
    fill_color: str = "rgba(0,0,0,0.1)"
    fill_opacity: float = 0.3
    label_field: Optional[str] = None


@dataclass
class ShapefileFeature:
    id: int = 0
    layer_id: int = 0
    geometry_json: str = ""
    attributes_json: str = "{}"
    label: str = ""
