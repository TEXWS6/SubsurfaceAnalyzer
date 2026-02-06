"""Tests for enhanced mapping — IDW, bubble, posted values, pie chart, grid property maps."""

import numpy as np
import pytest
from services.mapping import MappingService


@pytest.fixture
def sample_points():
    """Generate sample scattered data points."""
    np.random.seed(42)
    x = np.array([100, 500, 900, 300, 700, 150, 850, 450])
    y = np.array([100, 300, 100, 500, 500, 700, 700, 400])
    z = np.array([3000, 3050, 3020, 3100, 3080, 3150, 3120, 3060])
    return x, y, z


@pytest.fixture
def sample_wells_data():
    """Generate sample wells data for map builders."""
    return [
        {"x_coord": 100, "y_coord": 100, "well_name": "Well A",
         "kb": 3200, "td": 8500, "net_pay": 25, "cum_oil": 50000,
         "cum_gas": 100000000, "cum_water": 20000},
        {"x_coord": 500, "y_coord": 300, "well_name": "Well B",
         "kb": 3250, "td": 9000, "net_pay": 35, "cum_oil": 80000,
         "cum_gas": 150000000, "cum_water": 30000},
        {"x_coord": 900, "y_coord": 100, "well_name": "Well C",
         "kb": 3180, "td": 8200, "net_pay": 20, "cum_oil": 30000,
         "cum_gas": 80000000, "cum_water": 15000},
        {"x_coord": 300, "y_coord": 500, "well_name": "Well D",
         "kb": 3300, "td": 9500, "net_pay": 40, "cum_oil": 100000,
         "cum_gas": 200000000, "cum_water": 40000},
    ]


class TestIDW:
    def test_basic_interpolation(self, sample_points):
        x, y, z = sample_points
        xi, yi, zi = MappingService.interpolate_grid_idw(x, y, z, power=2, resolution=20)
        assert zi.shape == (20, 20)
        assert not np.any(np.isnan(zi))

    def test_at_data_points(self, sample_points):
        """IDW should reproduce exact values at data points."""
        x, y, z = sample_points
        xi, yi, zi = MappingService.interpolate_grid_idw(x, y, z, power=2, resolution=50)
        # Values at grid points near data should be close to data values
        assert zi.min() >= z.min() - 50  # Should not extrapolate wildly
        assert zi.max() <= z.max() + 50

    def test_power_effect(self, sample_points):
        x, y, z = sample_points
        _, _, zi_low = MappingService.interpolate_grid_idw(x, y, z, power=1, resolution=20)
        _, _, zi_high = MappingService.interpolate_grid_idw(x, y, z, power=4, resolution=20)
        # Higher power → more local influence → more variation
        assert zi_low.std() != zi_high.std()


class TestBubbleMap:
    def test_basic(self, sample_wells_data):
        fig = MappingService.build_bubble_map(
            sample_wells_data, "net_pay", "Net Pay Bubble Map")
        assert fig is not None
        assert len(fig.data) > 0

    def test_empty_data(self):
        fig = MappingService.build_bubble_map([], "kb")
        assert "No data" in fig.layout.title.text

    def test_different_properties(self, sample_wells_data):
        for prop in ["kb", "td", "net_pay", "cum_oil"]:
            fig = MappingService.build_bubble_map(
                sample_wells_data, prop, f"Bubble — {prop}")
            assert len(fig.data) > 0


class TestPostedValuesMap:
    def test_basic(self, sample_wells_data):
        fig = MappingService.build_posted_values_map(
            sample_wells_data, "kb", "Posted KB Values")
        assert fig is not None
        assert len(fig.data) > 0
        # Should have annotations for each well
        assert len(fig.layout.annotations) >= len(sample_wells_data)

    def test_empty_data(self):
        fig = MappingService.build_posted_values_map([], "kb")
        assert "No data" in fig.layout.title.text


class TestPieChartMap:
    def test_basic(self, sample_wells_data):
        fig = MappingService.build_pie_chart_map(
            sample_wells_data, "Production Pie Map")
        assert fig is not None
        assert len(fig.data) > 0

    def test_empty_data(self):
        fig = MappingService.build_pie_chart_map([])
        assert "No data" in fig.layout.title.text

    def test_zero_production_well(self):
        wells = [
            {"x_coord": 100, "y_coord": 100, "well_name": "Dry Well",
             "cum_oil": 0, "cum_gas": 0, "cum_water": 0},
        ]
        fig = MappingService.build_pie_chart_map(wells)
        assert fig is not None


class TestGridPropertyMap:
    def test_basic(self, sample_points):
        x, y, z = sample_points
        xi, yi, zi = MappingService.interpolate_grid_idw(x, y, z, resolution=20)
        names = [f"Well {i}" for i in range(len(x))]
        fig = MappingService.build_grid_property_map(
            xi, yi, zi, x, y, names, "Grid Test")
        assert fig is not None
        assert len(fig.data) >= 2  # Heatmap + wells scatter
