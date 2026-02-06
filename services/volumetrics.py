"""Volumetrics engine — OOIP/OGIP deterministic + Monte Carlo calculations.

Zero UI dependencies. Pure computation using numpy.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import plotly.graph_objects as go


@dataclass
class MonteCarloParam:
    """Describes a parameter's statistical distribution for MC simulation."""
    name: str = ""
    distribution: str = "triangular"  # triangular, normal, lognormal, uniform
    min_val: float = 0.0
    mode_val: float = 0.0
    max_val: float = 0.0
    mean: float = 0.0
    std: float = 0.0


@dataclass
class VolumetricsInput:
    """Input parameters for deterministic OOIP/OGIP."""
    area: float = 0.0       # acres
    h: float = 0.0          # net pay thickness (ft)
    phi: float = 0.0        # porosity (fraction)
    sw: float = 0.0         # water saturation (fraction)
    bo: float = 1.2         # oil formation volume factor (rb/stb)
    bg: float = 0.005       # gas formation volume factor (rcf/scf)
    rf: float = 0.0         # recovery factor (fraction, 0-1)
    fluid_type: str = "oil" # "oil" or "gas"


class VolumetricsEngine:
    @staticmethod
    def calculate_ooip(area: float, h: float, phi: float,
                       sw: float, bo: float, rf: float = 1.0) -> float:
        """Original Oil In Place (STB).

        OOIP = 7758 * A * h * Phi * (1-Sw) / Bo * RF
        """
        if bo <= 0:
            return 0.0
        return 7758.0 * area * h * phi * (1.0 - sw) / bo * rf

    @staticmethod
    def calculate_ogip(area: float, h: float, phi: float,
                       sw: float, bg: float, rf: float = 1.0) -> float:
        """Original Gas In Place (SCF).

        OGIP = 43560 * A * h * Phi * (1-Sw) / Bg * RF
        """
        if bg <= 0:
            return 0.0
        return 43560.0 * area * h * phi * (1.0 - sw) / bg * rf

    @classmethod
    def deterministic(cls, inputs: VolumetricsInput) -> dict:
        """Run deterministic volumetrics calculation."""
        if inputs.fluid_type == "gas":
            ogip = cls.calculate_ogip(
                inputs.area, inputs.h, inputs.phi, inputs.sw,
                inputs.bg, inputs.rf,
            )
            return {
                "fluid_type": "gas",
                "ogip": ogip,
                "ogip_bcf": ogip / 1e9,
                "inputs": {
                    "area": inputs.area, "h": inputs.h, "phi": inputs.phi,
                    "sw": inputs.sw, "bg": inputs.bg, "rf": inputs.rf,
                },
            }
        else:
            ooip = cls.calculate_ooip(
                inputs.area, inputs.h, inputs.phi, inputs.sw,
                inputs.bo, inputs.rf,
            )
            return {
                "fluid_type": "oil",
                "ooip": ooip,
                "ooip_mstb": ooip / 1e3,
                "inputs": {
                    "area": inputs.area, "h": inputs.h, "phi": inputs.phi,
                    "sw": inputs.sw, "bo": inputs.bo, "rf": inputs.rf,
                },
            }

    @staticmethod
    def _sample_distribution(param: MonteCarloParam, n: int) -> np.ndarray:
        """Sample n values from the specified distribution."""
        dist = param.distribution.lower()
        if dist == "triangular":
            return np.random.triangular(
                param.min_val, param.mode_val, param.max_val, n
            )
        elif dist == "normal":
            return np.random.normal(param.mean, param.std, n)
        elif dist == "lognormal":
            # Convert mean/std to underlying normal params
            if param.mean <= 0:
                return np.full(n, param.mean)
            variance = param.std ** 2
            mu = np.log(param.mean ** 2 / np.sqrt(variance + param.mean ** 2))
            sigma = np.sqrt(np.log(1 + variance / param.mean ** 2))
            return np.random.lognormal(mu, sigma, n)
        elif dist == "uniform":
            return np.random.uniform(param.min_val, param.max_val, n)
        else:
            return np.full(n, param.mode_val)

    @classmethod
    def monte_carlo(cls, params: dict, n_iterations: int = 10000,
                    fluid_type: str = "oil") -> dict:
        """Run Monte Carlo volumetrics simulation.

        params: dict of parameter_name -> MonteCarloParam
            Required keys: area, h, phi, sw, and bo (oil) or bg (gas)
            Optional: rf (defaults to 1.0)

        Returns dict with P10, P50, P90, mean, std, raw values.
        """
        n = n_iterations

        area = cls._sample_distribution(params["area"], n)
        h = cls._sample_distribution(params["h"], n)
        phi = cls._sample_distribution(params["phi"], n)
        sw = cls._sample_distribution(params["sw"], n)

        if "rf" in params:
            rf = cls._sample_distribution(params["rf"], n)
        else:
            rf = np.ones(n)

        if fluid_type == "gas":
            bg = cls._sample_distribution(params["bg"], n)
            bg = np.where(bg <= 0, 0.001, bg)
            values = 43560.0 * area * h * phi * (1.0 - sw) / bg * rf
            label = "OGIP"
        else:
            bo = cls._sample_distribution(params["bo"], n)
            bo = np.where(bo <= 0, 0.1, bo)
            values = 7758.0 * area * h * phi * (1.0 - sw) / bo * rf
            label = "OOIP"

        # Clip negative values
        values = np.maximum(values, 0)

        p10 = float(np.percentile(values, 10))
        p50 = float(np.percentile(values, 50))
        p90 = float(np.percentile(values, 90))

        return {
            "fluid_type": fluid_type,
            "label": label,
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "n_iterations": n,
            "values": values,
        }

    @staticmethod
    def extract_zone_properties(depth: np.ndarray, phi: np.ndarray,
                                sw: np.ndarray, pay_flag: np.ndarray,
                                md_top: float, md_base: float) -> dict:
        """Extract average phi, sw, and net pay within a formation interval.

        Bridges petrophysics results to volumetrics inputs.
        """
        mask = (depth >= md_top) & (depth <= md_base)
        if not np.any(mask):
            return {"avg_phi": 0, "avg_sw": 0, "net_pay": 0, "gross": 0}

        zone_depth = depth[mask]
        zone_phi = phi[mask]
        zone_sw = sw[mask]
        zone_pay = pay_flag[mask]

        step = float(np.median(np.diff(zone_depth))) if len(zone_depth) > 1 else 0.5
        gross = float(zone_depth[-1] - zone_depth[0] + step)

        pay_mask = zone_pay == 1
        net_pay = float(np.sum(pay_mask) * step)

        avg_phi = float(np.nanmean(zone_phi[pay_mask])) if np.any(pay_mask) else 0
        avg_sw = float(np.nanmean(zone_sw[pay_mask])) if np.any(pay_mask) else 0

        return {
            "avg_phi": round(avg_phi, 4),
            "avg_sw": round(avg_sw, 4),
            "net_pay": round(net_pay, 2),
            "gross": round(gross, 2),
        }

    @staticmethod
    def polygon_area_acres(vertices: list) -> float:
        """Compute area of polygon using Shoelace formula, convert sq ft to acres.

        vertices: list of (x, y) tuples in consistent units (feet).
        Returns area in acres (1 acre = 43560 sq ft).
        """
        if len(vertices) < 3:
            return 0.0
        n = len(vertices)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        area_sqft = abs(area) / 2.0
        return area_sqft / 43560.0

    @staticmethod
    def build_histogram_figure(mc_results: dict) -> go.Figure:
        """Build a histogram with P10/P50/P90 vertical lines."""
        values = mc_results["values"]
        label = mc_results["label"]
        p10 = mc_results["p10"]
        p50 = mc_results["p50"]
        p90 = mc_results["p90"]

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=values,
            nbinsx=50,
            marker_color="steelblue",
            opacity=0.75,
            name=label,
        ))

        for val, name, color in [
            (p10, "P10", "green"),
            (p50, "P50", "orange"),
            (p90, "P90", "red"),
        ]:
            fig.add_vline(
                x=val, line_dash="dash", line_color=color, line_width=2,
                annotation_text=f"{name}: {val:,.0f}",
                annotation_position="top",
                annotation_font_color=color,
            )

        fig.update_layout(
            title=f"Monte Carlo {label} Distribution ({mc_results['n_iterations']} iterations)",
            xaxis_title=f"{label} ({'STB' if mc_results['fluid_type'] == 'oil' else 'SCF'})",
            yaxis_title="Frequency",
            height=400,
            margin=dict(l=60, r=20, t=50, b=50),
        )

        return fig
