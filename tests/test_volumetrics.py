"""Tests for VolumetricsEngine — OOIP/OGIP calculations."""

import numpy as np
import pytest
from services.volumetrics import (
    VolumetricsEngine, VolumetricsInput, MonteCarloParam,
)


class TestOOIPCalculation:
    def test_basic_ooip(self):
        # OOIP = 7758 * A * h * Phi * (1-Sw) / Bo * RF
        ooip = VolumetricsEngine.calculate_ooip(
            area=40, h=20, phi=0.15, sw=0.3, bo=1.2, rf=1.0)
        expected = 7758 * 40 * 20 * 0.15 * 0.7 / 1.2
        assert abs(ooip - expected) < 1.0

    def test_ooip_with_recovery_factor(self):
        ooip_full = VolumetricsEngine.calculate_ooip(
            area=40, h=20, phi=0.15, sw=0.3, bo=1.2, rf=1.0)
        ooip_half = VolumetricsEngine.calculate_ooip(
            area=40, h=20, phi=0.15, sw=0.3, bo=1.2, rf=0.5)
        assert abs(ooip_half - ooip_full * 0.5) < 1.0

    def test_ooip_zero_bo(self):
        assert VolumetricsEngine.calculate_ooip(40, 20, 0.15, 0.3, 0, 1.0) == 0.0

    def test_ogip_basic(self):
        ogip = VolumetricsEngine.calculate_ogip(
            area=80, h=30, phi=0.10, sw=0.4, bg=0.005, rf=1.0)
        expected = 43560 * 80 * 30 * 0.10 * 0.6 / 0.005
        assert abs(ogip - expected) < 1.0

    def test_ogip_zero_bg(self):
        assert VolumetricsEngine.calculate_ogip(80, 30, 0.10, 0.4, 0, 1.0) == 0.0


class TestDeterministic:
    def test_oil_deterministic(self):
        inputs = VolumetricsInput(
            area=40, h=20, phi=0.15, sw=0.3, bo=1.2, rf=0.3, fluid_type="oil")
        result = VolumetricsEngine.deterministic(inputs)
        assert result["fluid_type"] == "oil"
        assert "ooip" in result
        assert result["ooip"] > 0
        assert "ooip_mstb" in result

    def test_gas_deterministic(self):
        inputs = VolumetricsInput(
            area=80, h=30, phi=0.10, sw=0.4, bg=0.005, rf=0.7, fluid_type="gas")
        result = VolumetricsEngine.deterministic(inputs)
        assert result["fluid_type"] == "gas"
        assert "ogip" in result
        assert result["ogip"] > 0
        assert "ogip_bcf" in result


class TestMonteCarlo:
    def test_mc_oil(self):
        params = {
            "area": MonteCarloParam("area", "triangular", 20, 40, 80),
            "h": MonteCarloParam("h", "triangular", 10, 25, 50),
            "phi": MonteCarloParam("phi", "triangular", 0.05, 0.12, 0.25),
            "sw": MonteCarloParam("sw", "triangular", 0.2, 0.35, 0.6),
            "bo": MonteCarloParam("bo", "triangular", 1.1, 1.2, 1.4),
        }
        result = VolumetricsEngine.monte_carlo(params, n_iterations=1000, fluid_type="oil")
        assert result["label"] == "OOIP"
        assert result["p10"] > 0
        assert result["p50"] > result["p10"]
        assert result["p90"] > result["p50"]
        assert len(result["values"]) == 1000

    def test_mc_gas(self):
        params = {
            "area": MonteCarloParam("area", "uniform", 20, 0, 80),
            "h": MonteCarloParam("h", "triangular", 10, 30, 60),
            "phi": MonteCarloParam("phi", "triangular", 0.05, 0.1, 0.2),
            "sw": MonteCarloParam("sw", "triangular", 0.2, 0.3, 0.5),
            "bg": MonteCarloParam("bg", "triangular", 0.003, 0.005, 0.008),
        }
        result = VolumetricsEngine.monte_carlo(params, n_iterations=500, fluid_type="gas")
        assert result["label"] == "OGIP"
        assert result["p10"] > 0
        assert result["n_iterations"] == 500

    def test_mc_with_rf(self):
        params = {
            "area": MonteCarloParam("area", "triangular", 20, 40, 60),
            "h": MonteCarloParam("h", "triangular", 10, 20, 30),
            "phi": MonteCarloParam("phi", "triangular", 0.08, 0.12, 0.18),
            "sw": MonteCarloParam("sw", "triangular", 0.2, 0.3, 0.5),
            "bo": MonteCarloParam("bo", "triangular", 1.1, 1.2, 1.3),
            "rf": MonteCarloParam("rf", "triangular", 0.1, 0.3, 0.5),
        }
        result = VolumetricsEngine.monte_carlo(params, n_iterations=500, fluid_type="oil")
        assert result["p50"] > 0


class TestDistributions:
    def test_triangular(self):
        param = MonteCarloParam("test", "triangular", 1.0, 5.0, 10.0)
        samples = VolumetricsEngine._sample_distribution(param, 10000)
        assert samples.min() >= 1.0
        assert samples.max() <= 10.0

    def test_normal(self):
        param = MonteCarloParam("test", "normal", mean=100, std=10)
        samples = VolumetricsEngine._sample_distribution(param, 10000)
        assert abs(np.mean(samples) - 100) < 2.0

    def test_uniform(self):
        param = MonteCarloParam("test", "uniform", 0, 0, 100)
        samples = VolumetricsEngine._sample_distribution(param, 10000)
        assert samples.min() >= 0
        assert samples.max() <= 100

    def test_lognormal(self):
        param = MonteCarloParam("test", "lognormal", mean=10, std=3)
        samples = VolumetricsEngine._sample_distribution(param, 10000)
        assert np.all(samples > 0)


class TestExtractZoneProperties:
    def test_zone_extraction(self):
        depth = np.arange(1000, 1010, 0.5)
        phi = np.full_like(depth, 0.15)
        sw = np.full_like(depth, 0.3)
        pay = np.ones_like(depth)
        pay[0:4] = 0  # First 2 ft not pay

        zone = VolumetricsEngine.extract_zone_properties(
            depth, phi, sw, pay, 1000, 1010)
        assert zone["gross"] > 0
        assert zone["net_pay"] > 0
        assert zone["net_pay"] < zone["gross"]
        assert abs(zone["avg_phi"] - 0.15) < 0.01

    def test_zone_no_data(self):
        depth = np.arange(1000, 1010, 0.5)
        phi = np.full_like(depth, 0.15)
        sw = np.full_like(depth, 0.3)
        pay = np.ones_like(depth)
        zone = VolumetricsEngine.extract_zone_properties(
            depth, phi, sw, pay, 2000, 2010)  # Outside range
        assert zone["gross"] == 0
        assert zone["net_pay"] == 0


class TestPolygonArea:
    def test_square(self):
        # 208.71 ft side = 1 acre
        side = 208.71
        vertices = [(0, 0), (side, 0), (side, side), (0, side)]
        area = VolumetricsEngine.polygon_area_acres(vertices)
        assert abs(area - 1.0) < 0.01

    def test_too_few_vertices(self):
        assert VolumetricsEngine.polygon_area_acres([(0, 0), (1, 1)]) == 0.0

    def test_triangle(self):
        # Triangle with base 200, height 100
        vertices = [(0, 0), (200, 0), (100, 100)]
        area_sqft = 0.5 * 200 * 100
        expected_acres = area_sqft / 43560
        result = VolumetricsEngine.polygon_area_acres(vertices)
        assert abs(result - expected_acres) < 0.01


class TestHistogram:
    def test_build_histogram(self):
        params = {
            "area": MonteCarloParam("area", "triangular", 20, 40, 80),
            "h": MonteCarloParam("h", "triangular", 10, 25, 50),
            "phi": MonteCarloParam("phi", "triangular", 0.05, 0.12, 0.25),
            "sw": MonteCarloParam("sw", "triangular", 0.2, 0.35, 0.6),
            "bo": MonteCarloParam("bo", "triangular", 1.1, 1.2, 1.4),
        }
        result = VolumetricsEngine.monte_carlo(params, 500, "oil")
        fig = VolumetricsEngine.build_histogram_figure(result)
        assert fig is not None
        assert len(fig.data) > 0
