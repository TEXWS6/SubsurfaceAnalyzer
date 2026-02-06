"""Tests for ShapefileRepository CRUD operations."""

import json
import pytest
from database.repositories import ShapefileRepository, ProjectRepository


@pytest.fixture
def repos():
    project_repo = ProjectRepository()
    pid = project_repo.create("Shapefile Test Project", "")
    shapefile_repo = ShapefileRepository()
    return shapefile_repo, pid


def test_create_layer(repos):
    repo, pid = repos
    lid = repo.create_layer(pid, "lease_bounds", "Polygon", 5,
                            json.dumps([0, 0, 10, 10]), "EPSG:4326")
    assert lid > 0
    layer = repo.get_layer_by_id(lid)
    assert layer["name"] == "lease_bounds"
    assert layer["geometry_type"] == "Polygon"
    assert layer["feature_count"] == 5


def test_get_layers_by_project(repos):
    repo, pid = repos
    repo.create_layer(pid, "faults", "LineString", 3)
    repo.create_layer(pid, "wells", "Point", 10)
    layers = repo.get_layers_by_project(pid)
    assert len(layers) == 2
    names = {l["name"] for l in layers}
    assert names == {"faults", "wells"}


def test_bulk_create_features(repos):
    repo, pid = repos
    lid = repo.create_layer(pid, "polys", "Polygon", 2)
    geom1 = json.dumps({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]})
    geom2 = json.dumps({"type": "Polygon", "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 2]]]})
    records = [
        (lid, geom1, json.dumps({"name": "A"}), "A"),
        (lid, geom2, json.dumps({"name": "B"}), "B"),
    ]
    repo.bulk_create_features(records)
    features = repo.get_features_by_layer(lid)
    assert len(features) == 2
    labels = {f["label"] for f in features}
    assert labels == {"A", "B"}


def test_get_features_by_layer(repos):
    repo, pid = repos
    lid = repo.create_layer(pid, "pts", "Point", 1)
    geom = json.dumps({"type": "Point", "coordinates": [5.5, 3.2]})
    repo.bulk_create_features([(lid, geom, "{}", "P1")])
    features = repo.get_features_by_layer(lid)
    assert len(features) == 1
    parsed = json.loads(features[0]["geometry_json"])
    assert parsed["type"] == "Point"
    assert parsed["coordinates"] == [5.5, 3.2]


def test_update_layer_style(repos):
    repo, pid = repos
    lid = repo.create_layer(pid, "styled", "Polygon", 0)
    repo.update_layer_style(lid, line_color="#FF0000", line_width=3.0,
                            fill_color="#00FF00", fill_opacity=0.5,
                            label_field="NAME")
    layer = repo.get_layer_by_id(lid)
    assert layer["line_color"] == "#FF0000"
    assert layer["line_width"] == 3.0
    assert layer["fill_color"] == "#00FF00"
    assert layer["fill_opacity"] == 0.5
    assert layer["label_field"] == "NAME"


def test_delete_layer_cascades(repos):
    repo, pid = repos
    lid = repo.create_layer(pid, "to_delete", "Point", 1)
    geom = json.dumps({"type": "Point", "coordinates": [1, 1]})
    repo.bulk_create_features([(lid, geom, "{}", "X")])
    assert len(repo.get_features_by_layer(lid)) == 1

    repo.delete_layer(lid)
    assert repo.get_layer_by_id(lid) is None
    assert len(repo.get_features_by_layer(lid)) == 0


def test_json_roundtrip(repos):
    repo, pid = repos
    lid = repo.create_layer(pid, "json_test", "MultiPolygon", 1,
                            json.dumps([1.1, 2.2, 3.3, 4.4]),
                            attribute_columns_json=json.dumps(["col_a", "col_b"]))
    layer = repo.get_layer_by_id(lid)
    bounds = json.loads(layer["bounds_json"])
    assert bounds == [1.1, 2.2, 3.3, 4.4]
    cols = json.loads(layer["attribute_columns_json"])
    assert cols == ["col_a", "col_b"]


def test_get_nonexistent_layer(repos):
    repo, pid = repos
    assert repo.get_layer_by_id(99999) is None
