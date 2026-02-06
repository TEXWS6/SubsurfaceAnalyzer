"""Tests for petrophysics engine."""

import numpy as np
import pytest
from services.petrophysics import PetrophysicsEngine


class TestVshale:
    def test_linear_vshale(self, sample_arrays):
        _, gr, _, _, _ = sample_arrays
        vsh = PetrophysicsEngine.vshale_linear(gr, gr_clean=20, gr_shale=120)
        assert vsh.shape == gr.shape
        assert np.all(vsh >= 0)
        assert np.all(vsh <= 1)
        # Clean (GR=20) → Vsh=0, Shale (GR=120) → Vsh=1
        np.testing.assert_almost_equal(vsh[-1], 0.0, decimal=1)  # GR=18 < clean

    def test_larionov_tertiary(self, sample_arrays):
        _, gr, _, _, _ = sample_arrays
        vsh = PetrophysicsEngine.vshale_larionov_tertiary(gr, 20, 120)
        assert np.all(vsh >= 0)
        assert np.all(vsh <= 1)

    def test_larionov_old(self, sample_arrays):
        _, gr, _, _, _ = sample_arrays
        vsh = PetrophysicsEngine.vshale_larionov_old(gr, 20, 120)
        assert np.all(vsh >= 0)
        assert np.all(vsh <= 1)

    def test_clavier(self, sample_arrays):
        _, gr, _, _, _ = sample_arrays
        vsh = PetrophysicsEngine.vshale_clavier(gr, 20, 120)
        assert np.all(vsh >= 0)
        assert np.all(vsh <= 1)

    def test_nonlinear_less_than_linear(self, sample_arrays):
        _, gr, _, _, _ = sample_arrays
        vsh_lin = PetrophysicsEngine.vshale_linear(gr, 20, 120)
        vsh_lari = PetrophysicsEngine.vshale_larionov_tertiary(gr, 20, 120)
        # Non-linear methods generally give lower Vshale for mid-range GR
        mid = (gr > 40) & (gr < 100)
        if mid.any():
            assert np.mean(vsh_lari[mid]) <= np.mean(vsh_lin[mid])


class TestPorosity:
    def test_density_porosity(self, sample_arrays):
        _, _, rhob, _, _ = sample_arrays
        phi = PetrophysicsEngine.porosity_density(rhob, rho_matrix=2.65, rho_fluid=1.0)
        assert np.all(phi >= 0)
        assert np.all(phi <= 0.5)
        # Higher density → lower porosity
        assert phi[0] < phi[6]  # 2.55 vs 2.35

    def test_neutron_porosity(self, sample_arrays):
        _, _, _, nphi, _ = sample_arrays
        phi = PetrophysicsEngine.porosity_neutron(nphi, nphi_matrix=0.0)
        np.testing.assert_array_almost_equal(phi, nphi)

    def test_density_neutron_crossplot(self, sample_arrays):
        _, _, rhob, nphi, _ = sample_arrays
        phi = PetrophysicsEngine.porosity_density_neutron(rhob, nphi)
        assert np.all(phi >= 0)
        assert np.all(phi <= 0.5)


class TestArchie:
    def test_archie_sw(self):
        # Use controlled values to get a range of Sw
        phi = np.array([0.20, 0.20, 0.10, 0.10])
        rt = np.array([5.0, 50.0, 5.0, 50.0])
        sw = PetrophysicsEngine.archie_sw(phi, rt, rw=0.02, a=1.0, m=2.0, n=2.0)
        # Range checks
        valid = ~np.isnan(sw)
        assert np.all(sw[valid] >= 0)
        assert np.all(sw[valid] <= 1)
        # Higher Rt with same phi → lower Sw
        assert sw[1] < sw[0]
        # Lower phi with same Rt → higher Sw
        assert sw[2] > sw[0]


class TestNetPay:
    def test_net_pay_flag(self):
        vsh = np.array([0.1, 0.6, 0.1, 0.1, 0.8])
        phi = np.array([0.15, 0.10, 0.05, 0.15, 0.12])
        sw = np.array([0.3, 0.2, 0.3, 0.7, 0.3])
        pay = PetrophysicsEngine.net_pay_flag(vsh, phi, sw)
        # Only index 0 passes all cutoffs: vsh<0.5, phi>0.08, sw<0.5
        assert pay[0] == 1.0
        assert pay[1] == 0.0  # vsh too high
        assert pay[2] == 0.0  # phi too low
        assert pay[3] == 0.0  # sw too high
        assert pay[4] == 0.0  # vsh too high

    def test_net_pay_summary(self, sample_arrays):
        depth, gr, rhob, nphi, rt = sample_arrays
        phi = PetrophysicsEngine.porosity_density(rhob)
        vsh = PetrophysicsEngine.vshale_linear(gr, 20, 120)
        sw = PetrophysicsEngine.archie_sw(phi, rt)
        pay = PetrophysicsEngine.net_pay_flag(vsh, phi, sw)
        summary = PetrophysicsEngine.net_pay_summary(depth, pay, phi, sw)

        assert "gross" in summary
        assert "net" in summary
        assert "ng_ratio" in summary
        assert "avg_phi" in summary
        assert "avg_sw" in summary
        assert summary["gross"] > 0


class TestFullAnalysis:
    def test_full_analysis(self, sample_arrays):
        depth, gr, rhob, nphi, rt = sample_arrays
        results = PetrophysicsEngine.run_full_analysis(
            depth, gr, rhob, nphi, rt,
            {"gr_clean": 20, "gr_shale": 120, "vshale_method": "linear",
             "rho_matrix": 2.65, "rho_fluid": 1.0, "rw": 0.05}
        )

        assert "VSHALE" in results
        assert "PHIE" in results
        assert "SW" in results
        assert "PAY_FLAG" in results
        assert "summary" in results
        assert len(results["VSHALE"]) == len(depth)
