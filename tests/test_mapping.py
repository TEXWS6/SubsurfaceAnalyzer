"""Tests for mapping service."""

import numpy as np
import pytest
from services.mapping import MappingService


class TestMappingService:
    def test_interpolate_grid(self):
        x = np.array([0, 1, 0, 1, 0.5])
        y = np.array([0, 0, 1, 1, 0.5])
        z = np.array([100, 200, 150, 250, 175])

        xi, yi, zi = MappingService.interpolate_grid(x, y, z, method="linear", resolution=50)
        assert xi.shape == (50,)
        assert yi.shape == (50,)
        assert zi.shape == (50, 50)
        # Center value should be close to 175
        center = zi[25, 25]
        assert 150 < center < 200

    def test_interpolate_nearest(self):
        x = np.array([0, 1, 0.5])
        y = np.array([0, 0, 1])
        z = np.array([100, 200, 150])

        xi, yi, zi = MappingService.interpolate_grid(x, y, z, method="nearest", resolution=20)
        assert not np.any(np.isnan(zi))

    def test_build_structure_map(self):
        wells_data = [
            {"x_coord": 0, "y_coord": 0, "kb": 200, "md_top": 1000, "well_name": "W1"},
            {"x_coord": 1000, "y_coord": 0, "kb": 210, "md_top": 1050, "well_name": "W2"},
            {"x_coord": 500, "y_coord": 1000, "kb": 190, "md_top": 980, "well_name": "W3"},
            {"x_coord": 500, "y_coord": 500, "kb": 200, "md_top": 1020, "well_name": "W4"},
        ]
        fig = MappingService.build_structure_map(wells_data, "Top Sand")
        assert fig is not None
        assert len(fig.data) >= 2  # contour + well spots

    def test_build_isopach_map(self):
        wells_data = [
            {"x_coord": 0, "y_coord": 0, "md_top": 1000, "md_base": 1100, "well_name": "W1"},
            {"x_coord": 1000, "y_coord": 0, "md_top": 1050, "md_base": 1200, "well_name": "W2"},
            {"x_coord": 500, "y_coord": 1000, "md_top": 980, "md_base": 1050, "well_name": "W3"},
            {"x_coord": 500, "y_coord": 500, "md_top": 1020, "md_base": 1150, "well_name": "W4"},
        ]
        fig = MappingService.build_isopach_map(wells_data, "Top", "Base")
        assert fig is not None

    def test_empty_data(self):
        fig = MappingService.build_structure_map([], "Formation")
        assert "No data" in fig.layout.title.text
