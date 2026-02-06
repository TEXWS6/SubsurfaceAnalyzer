"""Petrophysical calculation engine.

Vshale (4 methods), porosity (3 methods), Archie Sw, net pay flagging.
"""

import numpy as np


class PetrophysicsEngine:
    # --- Vshale methods ---

    @staticmethod
    def igi(gr: np.ndarray, gr_clean: float, gr_shale: float) -> np.ndarray:
        """Gamma-ray index (linear Vshale)."""
        denom = gr_shale - gr_clean
        if abs(denom) < 1e-10:
            return np.full_like(gr, np.nan)
        igi = (gr - gr_clean) / denom
        return np.clip(igi, 0, 1)

    @staticmethod
    def vshale_linear(gr: np.ndarray, gr_clean: float, gr_shale: float) -> np.ndarray:
        return PetrophysicsEngine.igi(gr, gr_clean, gr_shale)

    @staticmethod
    def vshale_larionov_tertiary(gr: np.ndarray, gr_clean: float, gr_shale: float) -> np.ndarray:
        igi = PetrophysicsEngine.igi(gr, gr_clean, gr_shale)
        return np.clip(0.083 * (2 ** (3.7 * igi) - 1), 0, 1)

    @staticmethod
    def vshale_larionov_old(gr: np.ndarray, gr_clean: float, gr_shale: float) -> np.ndarray:
        igi = PetrophysicsEngine.igi(gr, gr_clean, gr_shale)
        return np.clip(0.33 * (2 ** (2.0 * igi) - 1), 0, 1)

    @staticmethod
    def vshale_clavier(gr: np.ndarray, gr_clean: float, gr_shale: float) -> np.ndarray:
        igi = PetrophysicsEngine.igi(gr, gr_clean, gr_shale)
        return np.clip(1.7 - np.sqrt(3.38 - (igi + 0.7) ** 2), 0, 1)

    VSHALE_METHODS = {
        "linear": vshale_linear.__func__,
        "larionov_tertiary": vshale_larionov_tertiary.__func__,
        "larionov_old": vshale_larionov_old.__func__,
        "clavier": vshale_clavier.__func__,
    }

    @classmethod
    def calculate_vshale(cls, gr: np.ndarray, gr_clean: float, gr_shale: float,
                         method: str = "linear") -> np.ndarray:
        func = cls.VSHALE_METHODS.get(method, cls.vshale_linear)
        return func(gr, gr_clean, gr_shale)

    # --- Porosity methods ---

    @staticmethod
    def porosity_density(rhob: np.ndarray, rho_matrix: float = 2.65,
                         rho_fluid: float = 1.0) -> np.ndarray:
        denom = rho_matrix - rho_fluid
        if abs(denom) < 1e-10:
            return np.full_like(rhob, np.nan)
        phi = (rho_matrix - rhob) / denom
        return np.clip(phi, 0, 0.5)

    @staticmethod
    def porosity_neutron(nphi: np.ndarray, nphi_matrix: float = 0.0) -> np.ndarray:
        phi = nphi - nphi_matrix
        return np.clip(phi, 0, 0.5)

    @staticmethod
    def porosity_density_neutron(rhob: np.ndarray, nphi: np.ndarray,
                                 rho_matrix: float = 2.65,
                                 rho_fluid: float = 1.0,
                                 nphi_matrix: float = 0.0) -> np.ndarray:
        phi_d = PetrophysicsEngine.porosity_density(rhob, rho_matrix, rho_fluid)
        phi_n = PetrophysicsEngine.porosity_neutron(nphi, nphi_matrix)
        phi = np.sqrt((phi_d ** 2 + phi_n ** 2) / 2)
        return np.clip(phi, 0, 0.5)

    # --- Water saturation ---

    @staticmethod
    def archie_sw(phi: np.ndarray, rt: np.ndarray,
                  rw: float = 0.05, a: float = 1.0,
                  m: float = 2.0, n: float = 2.0) -> np.ndarray:
        """Archie water saturation equation: Sw = (a * Rw / (phi^m * Rt))^(1/n)"""
        with np.errstate(divide="ignore", invalid="ignore"):
            phi_safe = np.where(phi > 0.001, phi, np.nan)
            rt_safe = np.where(rt > 0.001, rt, np.nan)
            sw = (a * rw / (phi_safe ** m * rt_safe)) ** (1.0 / n)
        return np.clip(np.nan_to_num(sw, nan=np.nan), 0, 1)

    # --- Net pay ---

    @staticmethod
    def net_pay_flag(vshale: np.ndarray, phi: np.ndarray, sw: np.ndarray,
                     vshale_cutoff: float = 0.5, phi_cutoff: float = 0.08,
                     sw_cutoff: float = 0.5) -> np.ndarray:
        """Returns 1 where all cutoffs are met (pay), 0 otherwise."""
        pay = ((vshale <= vshale_cutoff) &
               (phi >= phi_cutoff) &
               (sw <= sw_cutoff)).astype(float)
        # Preserve NaN where any input is NaN
        nan_mask = np.isnan(vshale) | np.isnan(phi) | np.isnan(sw)
        pay[nan_mask] = np.nan
        return pay

    @staticmethod
    def net_pay_summary(depth: np.ndarray, pay_flag: np.ndarray,
                        phi: np.ndarray, sw: np.ndarray) -> dict:
        """Calculate net pay summary statistics."""
        valid = ~np.isnan(pay_flag) & ~np.isnan(depth)
        if not valid.any():
            return {"gross": 0, "net": 0, "ng_ratio": 0, "avg_phi": 0, "avg_sw": 0}

        d = depth[valid]
        step = np.median(np.diff(d)) if len(d) > 1 else 0.5
        gross = float(d[-1] - d[0] + step)

        pay = pay_flag[valid] == 1
        net = float(np.sum(pay) * step)
        ng = net / gross if gross > 0 else 0

        pay_phi = phi[valid][pay]
        pay_sw = sw[valid][pay]
        avg_phi = float(np.nanmean(pay_phi)) if len(pay_phi) > 0 else 0
        avg_sw = float(np.nanmean(pay_sw)) if len(pay_sw) > 0 else 0

        return {
            "gross": round(gross, 2),
            "net": round(net, 2),
            "ng_ratio": round(ng, 3),
            "avg_phi": round(avg_phi, 4),
            "avg_sw": round(avg_sw, 4),
        }

    # --- Full workflow ---

    @classmethod
    def run_full_analysis(cls, depth: np.ndarray, gr: np.ndarray,
                          rhob: np.ndarray = None, nphi: np.ndarray = None,
                          rt: np.ndarray = None, params: dict = None) -> dict:
        """Run complete petrophysical analysis.

        Returns dict of computed arrays: VSHALE, PHIE, SW, PAY_FLAG, and summary.
        """
        if params is None:
            params = {}

        results = {"depth": depth}

        # Vshale
        if gr is not None:
            vsh = cls.calculate_vshale(
                gr,
                params.get("gr_clean", 20.0),
                params.get("gr_shale", 120.0),
                params.get("vshale_method", "linear"),
            )
            results["VSHALE"] = vsh
        else:
            vsh = np.full_like(depth, np.nan)
            results["VSHALE"] = vsh

        # Porosity
        if rhob is not None and nphi is not None:
            phi = cls.porosity_density_neutron(
                rhob, nphi,
                params.get("rho_matrix", 2.65),
                params.get("rho_fluid", 1.0),
                params.get("nphi_matrix", 0.0),
            )
        elif rhob is not None:
            phi = cls.porosity_density(
                rhob,
                params.get("rho_matrix", 2.65),
                params.get("rho_fluid", 1.0),
            )
        elif nphi is not None:
            phi = cls.porosity_neutron(nphi, params.get("nphi_matrix", 0.0))
        else:
            phi = np.full_like(depth, np.nan)
        results["PHIE"] = phi

        # Water saturation
        if rt is not None and not np.all(np.isnan(phi)):
            sw = cls.archie_sw(
                phi, rt,
                params.get("rw", 0.05),
                params.get("archie_a", 1.0),
                params.get("archie_m", 2.0),
                params.get("archie_n", 2.0),
            )
        else:
            sw = np.full_like(depth, np.nan)
        results["SW"] = sw

        # Net pay
        pay = cls.net_pay_flag(
            vsh, phi, sw,
            params.get("vshale_cutoff", 0.5),
            params.get("phi_cutoff", 0.08),
            params.get("sw_cutoff", 0.5),
        )
        results["PAY_FLAG"] = pay
        results["summary"] = cls.net_pay_summary(depth, pay, phi, sw)

        return results
