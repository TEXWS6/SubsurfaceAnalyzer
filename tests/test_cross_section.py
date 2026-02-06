"""Tests for CrossSectionBuilder."""

import numpy as np
import pytest
from components.cross_section import CrossSectionBuilder


@pytest.fixture
def sample_wells():
    """Create sample well data for cross section tests."""
    depth = np.arange(1000, 1050, 0.5)
    gr = np.random.uniform(20, 120, len(depth))

    wells = [
        {
            "name": "Well A",
            "kb": 3200,
            "x_coord": 0,
            "y_coord": 0,
            "curves": {
                "GR": {"depth": depth, "data": gr},
            },
            "tops": [
                {"formation": "WOLFCAMP", "md_top": 1010},
                {"formation": "BONE_SPRING", "md_top": 1025},
            ],
        },
        {
            "name": "Well B",
            "kb": 3250,
            "x_coord": 1000,
            "y_coord": 0,
            "curves": {
                "GR": {"depth": depth, "data": gr + 5},
            },
            "tops": [
                {"formation": "WOLFCAMP", "md_top": 1015},
                {"formation": "BONE_SPRING", "md_top": 1030},
            ],
        },
        {
            "name": "Well C",
            "kb": 3180,
            "x_coord": 2000,
            "y_coord": 500,
            "curves": {
                "GR": {"depth": depth, "data": gr - 3},
            },
            "tops": [
                {"formation": "WOLFCAMP", "md_top": 1008},
                {"formation": "BONE_SPRING", "md_top": 1020},
            ],
        },
    ]
    return wells


class TestCrossSectionBuilder:
    def test_empty_wells(self):
        fig = CrossSectionBuilder.build([])
        assert fig is not None
        assert "No wells" in fig.layout.title.text

    def test_structural_mode(self, sample_wells):
        fig = CrossSectionBuilder.build(
            sample_wells,
            mode="structural",
            curves_to_display=["GR"],
        )
        assert fig is not None
        assert len(fig.data) > 0
        assert "Structural" in fig.layout.title.text

    def test_stratigraphic_mode(self, sample_wells):
        fig = CrossSectionBuilder.build(
            sample_wells,
            mode="stratigraphic",
            datum_formation="WOLFCAMP",
            curves_to_display=["GR"],
        )
        assert fig is not None
        assert len(fig.data) > 0
        assert "Stratigraphic" in fig.layout.title.text

    def test_correlation_lines(self, sample_wells):
        fig = CrossSectionBuilder.build(
            sample_wells,
            mode="structural",
            curves_to_display=["GR"],
            formations_to_correlate=["WOLFCAMP"],
        )
        assert fig is not None
        # Should have shapes for correlation lines
        assert len(fig.layout.shapes) > 0

    def test_multiple_curves(self, sample_wells):
        # Add resistivity curve to wells
        for w in sample_wells:
            depth = np.arange(1000, 1050, 0.5)
            w["curves"]["ILD"] = {
                "depth": depth,
                "data": np.random.uniform(0.5, 50, len(depth)),
            }

        fig = CrossSectionBuilder.build(
            sample_wells,
            mode="structural",
            curves_to_display=["GR", "ILD"],
        )
        assert fig is not None
        # Should have traces for both curves across 3 wells
        assert len(fig.data) >= 6

    def test_two_wells_minimum(self, sample_wells):
        fig = CrossSectionBuilder.build(
            sample_wells[:2],
            mode="structural",
            curves_to_display=["GR"],
        )
        assert fig is not None
        assert len(fig.data) > 0
