"""Tests for ShapefileParser service."""

import json
import os
import tempfile
import zipfile
import pytest

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, LineString, Polygon, MultiPolygon

from services.shapefile_parser import ShapefileParser
from database.repositories import ProjectRepository, ShapefileRepository


def _make_shapefile_zip(gdf, name="test_layer"):
    """Helper: write a GeoDataFrame to a zipped shapefile and return zip bytes."""
    tmp_dir = tempfile.mkdtemp()
    shp_path = os.path.join(tmp_dir, f"{name}.shp")
    gdf.to_file(shp_path)

    zip_path = os.path.join(tmp_dir, f"{name}.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            fpath = os.path.join(tmp_dir, f"{name}{ext}")
            if os.path.exists(fpath):
                zf.write(fpath, f"{name}{ext}")

    with open(zip_path, "rb") as f:
        return f.read()


@pytest.fixture
def polygon_gdf():
    polys = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
    ]
    return gpd.GeoDataFrame({
        "LEASE_NAME": ["Smith Ranch", "Jones Lease"],
        "OPERATOR": ["Acme", "Beta"],
        "ACRES": [640.0, 320.0],
    }, geometry=polys, crs="EPSG:4326")


@pytest.fixture
def line_gdf():
    lines = [
        LineString([(0, 0), (1, 1), (2, 0)]),
        LineString([(3, 3), (4, 4)]),
    ]
    return gpd.GeoDataFrame({
        "FAULT_NAME": ["F1", "F2"],
        "LENGTH": [2.83, 1.41],
    }, geometry=lines, crs="EPSG:4326")


@pytest.fixture
def point_gdf():
    points = [Point(100, 200), Point(105, 210), Point(110, 205)]
    return gpd.GeoDataFrame({
        "WELL_NAME": ["Well-A", "Well-B", "Well-C"],
        "TD": [5000, 6000, 4500],
    }, geometry=points, crs="EPSG:4326")


def test_parse_polygon_shapefile(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "lease_bounds")
    result = ShapefileParser.parse_from_zip(zip_bytes, "lease_bounds.zip")

    meta = result["metadata"]
    assert meta["geometry_type"] == "Polygon"
    assert meta["feature_count"] == 2
    assert "LEASE_NAME" in meta["attribute_columns"]
    assert len(result["features"]) == 2


def test_parse_line_shapefile(line_gdf):
    zip_bytes = _make_shapefile_zip(line_gdf, "faults")
    result = ShapefileParser.parse_from_zip(zip_bytes, "faults.zip")

    meta = result["metadata"]
    assert meta["geometry_type"] == "LineString"
    assert meta["feature_count"] == 2


def test_parse_point_shapefile(point_gdf):
    zip_bytes = _make_shapefile_zip(point_gdf, "well_spots")
    result = ShapefileParser.parse_from_zip(zip_bytes, "well_spots.zip")

    meta = result["metadata"]
    assert meta["geometry_type"] == "Point"
    assert meta["feature_count"] == 3
    assert "WELL_NAME" in meta["attribute_columns"]


def test_attribute_extraction(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "lease")
    result = ShapefileParser.parse_from_zip(zip_bytes, "lease.zip")
    feat = result["features"][0]
    assert feat["attributes"]["OPERATOR"] in ("Acme", "Beta")
    assert isinstance(feat["attributes"]["ACRES"], float)


def test_label_detection_name_column(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "lease")
    result = ShapefileParser.parse_from_zip(zip_bytes, "lease.zip")
    # LEASE_NAME should be auto-detected as label
    labels = [f["label"] for f in result["features"]]
    assert "Smith Ranch" in labels or "Jones Lease" in labels


def test_label_detection_well_column(point_gdf):
    zip_bytes = _make_shapefile_zip(point_gdf, "wells")
    result = ShapefileParser.parse_from_zip(zip_bytes, "wells.zip")
    labels = [f["label"] for f in result["features"]]
    assert "Well-A" in labels


def test_crs_extraction(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "crs_test")
    result = ShapefileParser.parse_from_zip(zip_bytes, "crs_test.zip")
    assert result["metadata"]["crs_wkt"] != ""


def test_bounds_extraction(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "bounds_test")
    result = ShapefileParser.parse_from_zip(zip_bytes, "bounds_test.zip")
    bounds = result["metadata"]["bounds"]
    assert len(bounds) == 4
    assert bounds[0] <= bounds[2]  # xmin <= xmax


def test_geometry_json_valid(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "geom_test")
    result = ShapefileParser.parse_from_zip(zip_bytes, "geom_test.zip")
    for feat in result["features"]:
        geom = json.loads(feat["geometry_json"])
        assert "type" in geom
        assert "coordinates" in geom


def test_import_to_project(polygon_gdf):
    zip_bytes = _make_shapefile_zip(polygon_gdf, "import_test")
    parsed = ShapefileParser.parse_from_zip(zip_bytes, "import_test.zip")

    project_repo = ProjectRepository()
    pid = project_repo.create("SHP Import Test", "")
    shapefile_repo = ShapefileRepository()

    result = ShapefileParser.import_to_project(parsed, pid, shapefile_repo)
    assert result["layer_id"] > 0
    assert result["feature_count"] == 2

    # Verify DB
    layers = shapefile_repo.get_layers_by_project(pid)
    assert len(layers) == 1
    features = shapefile_repo.get_features_by_layer(result["layer_id"])
    assert len(features) == 2


def test_import_with_custom_label_field(point_gdf):
    zip_bytes = _make_shapefile_zip(point_gdf, "label_test")
    parsed = ShapefileParser.parse_from_zip(zip_bytes, "label_test.zip")

    project_repo = ProjectRepository()
    pid = project_repo.create("Label Test", "")
    shapefile_repo = ShapefileRepository()

    result = ShapefileParser.import_to_project(
        parsed, pid, shapefile_repo, label_field="WELL_NAME")
    features = shapefile_repo.get_features_by_layer(result["layer_id"])
    labels = {f["label"] for f in features}
    assert "Well-A" in labels


def test_empty_zip_raises():
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, "empty.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "no shapefile here")
    with open(zip_path, "rb") as f:
        content = f.read()

    with pytest.raises(ValueError, match="No .shp file"):
        ShapefileParser.parse_from_zip(content, "empty.zip")


def test_multipolygon_geometry():
    mp = MultiPolygon([
        Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]),
        Polygon([(5, 5), (6, 5), (6, 6), (5, 5)]),
    ])
    gdf = gpd.GeoDataFrame({"NAME": ["Multi"]}, geometry=[mp], crs="EPSG:4326")
    zip_bytes = _make_shapefile_zip(gdf, "multi")
    result = ShapefileParser.parse_from_zip(zip_bytes, "multi.zip")
    assert result["metadata"]["geometry_type"] == "MultiPolygon"
    assert len(result["features"]) == 1
