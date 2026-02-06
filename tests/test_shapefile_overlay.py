"""Tests for shapefile overlay methods in MappingService."""

import json
import pytest
import plotly.graph_objects as go

from services.mapping import MappingService


def _make_layer(name, geom_type, features, **style):
    """Helper to create a layer data dict for overlay testing."""
    defaults = {
        "name": name,
        "geometry_type": geom_type,
        "line_color": "#FF0000",
        "line_width": 2.0,
        "fill_color": "#0000FF",
        "fill_opacity": 0.3,
    }
    defaults.update(style)
    defaults["features"] = features
    return defaults


class TestGeojsonToXY:
    def test_point(self):
        geom = {"type": "Point", "coordinates": [5.0, 10.0]}
        x, y = MappingService._geojson_to_xy(geom)
        assert x == [5.0]
        assert y == [10.0]

    def test_multipoint(self):
        geom = {"type": "MultiPoint", "coordinates": [[1, 2], [3, 4]]}
        x, y = MappingService._geojson_to_xy(geom)
        assert x == [1, 3]
        assert y == [2, 4]

    def test_linestring(self):
        geom = {"type": "LineString", "coordinates": [[0, 0], [1, 1], [2, 0]]}
        x, y = MappingService._geojson_to_xy(geom)
        assert x == [0, 1, 2]
        assert y == [0, 1, 0]

    def test_multilinestring(self):
        geom = {"type": "MultiLineString",
                 "coordinates": [[[0, 0], [1, 1]], [[2, 2], [3, 3]]]}
        x, y = MappingService._geojson_to_xy(geom)
        # Should have None separators between lines
        assert None in x
        assert len(x) == 6  # 2 + None + 2 + None

    def test_polygon(self):
        geom = {"type": "Polygon",
                 "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        x, y = MappingService._geojson_to_xy(geom)
        assert x[:4] == [0, 1, 1, 0]
        assert x[-1] is None  # separator after ring

    def test_multipolygon(self):
        geom = {"type": "MultiPolygon",
                 "coordinates": [
                     [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                     [[[5, 5], [6, 5], [6, 6], [5, 5]]],
                 ]}
        x, y = MappingService._geojson_to_xy(geom)
        non_none = [v for v in x if v is not None]
        assert len(non_none) == 8  # 4 pts per polygon

    def test_empty_geometry(self):
        geom = {"type": "Unknown", "coordinates": []}
        x, y = MappingService._geojson_to_xy(geom)
        assert x == []
        assert y == []


class TestColorWithOpacity:
    def test_hex_to_rgba(self):
        result = MappingService._color_with_opacity("#FF0000", 0.5)
        assert result == "rgba(255,0,0,0.5)"

    def test_already_rgba(self):
        result = MappingService._color_with_opacity("rgba(1,2,3,0.4)", 0.8)
        assert result == "rgba(1,2,3,0.4)"

    def test_fallback(self):
        result = MappingService._color_with_opacity("red", 0.5)
        assert result == "rgba(0,0,0,0.5)"


class TestAddShapefileOverlay:
    def test_polygon_overlay(self):
        fig = go.Figure()
        geom = json.dumps({"type": "Polygon",
                           "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]})
        layer = _make_layer("Lease", "Polygon", [
            {"geometry_json": geom, "label": "Smith", "attributes_json": "{}"},
        ])
        fig = MappingService.add_shapefile_overlay(fig, [layer])
        assert len(fig.data) == 1
        assert fig.data[0].fill == "toself"
        assert fig.data[0].name == "Lease"

    def test_line_overlay(self):
        fig = go.Figure()
        geom = json.dumps({"type": "LineString",
                           "coordinates": [[0, 0], [1, 1], [2, 0]]})
        layer = _make_layer("Faults", "LineString", [
            {"geometry_json": geom, "label": "F1", "attributes_json": "{}"},
        ])
        fig = MappingService.add_shapefile_overlay(fig, [layer])
        assert len(fig.data) == 1
        assert fig.data[0].mode == "lines"

    def test_point_overlay(self):
        fig = go.Figure()
        geom = json.dumps({"type": "Point", "coordinates": [5, 10]})
        layer = _make_layer("Wells", "Point", [
            {"geometry_json": geom, "label": "W-1", "attributes_json": "{}"},
        ])
        fig = MappingService.add_shapefile_overlay(fig, [layer])
        assert len(fig.data) == 1
        assert "markers" in fig.data[0].mode

    def test_multi_layer_overlay(self):
        fig = go.Figure()
        poly_geom = json.dumps({"type": "Polygon",
                                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]})
        line_geom = json.dumps({"type": "LineString",
                                "coordinates": [[0, 0], [5, 5]]})
        layers = [
            _make_layer("Leases", "Polygon", [
                {"geometry_json": poly_geom, "label": "L1", "attributes_json": "{}"},
            ]),
            _make_layer("Faults", "LineString", [
                {"geometry_json": line_geom, "label": "F1", "attributes_json": "{}"},
            ]),
        ]
        fig = MappingService.add_shapefile_overlay(fig, layers)
        assert len(fig.data) == 2

    def test_empty_layer(self):
        fig = go.Figure()
        layer = _make_layer("Empty", "Polygon", [])
        fig = MappingService.add_shapefile_overlay(fig, [layer])
        assert len(fig.data) == 0

    def test_legend_grouping(self):
        fig = go.Figure()
        geom1 = json.dumps({"type": "Polygon",
                            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]})
        geom2 = json.dumps({"type": "Polygon",
                            "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 2]]]})
        layer = _make_layer("Leases", "Polygon", [
            {"geometry_json": geom1, "label": "A", "attributes_json": "{}"},
            {"geometry_json": geom2, "label": "B", "attributes_json": "{}"},
        ])
        fig = MappingService.add_shapefile_overlay(fig, [layer])
        assert len(fig.data) == 2
        # First shows legend, second doesn't
        assert fig.data[0].showlegend is True
        assert fig.data[1].showlegend is False
        assert fig.data[0].legendgroup == "Leases"

    def test_hover_with_attributes(self):
        fig = go.Figure()
        geom = json.dumps({"type": "Point", "coordinates": [1, 2]})
        attrs = json.dumps({"OPERATOR": "Acme", "ACRES": 640})
        layer = _make_layer("Wells", "Point", [
            {"geometry_json": geom, "label": "Smith", "attributes_json": attrs},
        ])
        fig = MappingService.add_shapefile_overlay(fig, [layer])
        ht = fig.data[0].hovertemplate
        assert "Smith" in ht
        assert "OPERATOR" in ht
