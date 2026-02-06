"""Arps decline curve analysis engine.

Supports exponential, hyperbolic, and harmonic decline models.
Pure computation — no Dash dependencies.
"""

import numpy as np
from scipy.optimize import curve_fit
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeclineFitResult:
    """Result of a decline curve fit."""
    model: str = ""           # "exponential", "hyperbolic"
    qi: float = 0.0           # initial rate
    di: float = 0.0           # initial decline rate (1/month)
    b: float = 0.0            # Arps b-factor (0=exponential, 0<b<1=hyperbolic)
    r_squared: float = 0.0
    eur: float = 0.0
    forecast_months: list = field(default_factory=list)
    forecast_rates: list = field(default_factory=list)
    cum_forecast: list = field(default_factory=list)


class DeclineCurveEngine:
    """Arps decline curve fitting and forecasting."""

    @staticmethod
    def exponential_rate(t: np.ndarray, qi: float, di: float) -> np.ndarray:
        """q(t) = qi * exp(-di * t)"""
        return qi * np.exp(-di * t)

    @staticmethod
    def hyperbolic_rate(t: np.ndarray, qi: float, di: float,
                        b: float) -> np.ndarray:
        """q(t) = qi / (1 + b * di * t)^(1/b)"""
        return qi / (1.0 + b * di * t) ** (1.0 / b)

    @staticmethod
    def exponential_cumulative(t: np.ndarray, qi: float,
                               di: float) -> np.ndarray:
        """Np(t) = (qi / di) * (1 - exp(-di * t))"""
        if di == 0:
            return qi * t
        return (qi / di) * (1.0 - np.exp(-di * t))

    @staticmethod
    def hyperbolic_cumulative(t: np.ndarray, qi: float, di: float,
                              b: float) -> np.ndarray:
        """Np(t) for hyperbolic decline."""
        if b == 0 or di == 0:
            return DeclineCurveEngine.exponential_cumulative(t, qi, di)
        if abs(b - 1.0) < 1e-10:
            # Harmonic: Np = (qi / di) * ln(1 + di * t)
            return (qi / di) * np.log(1.0 + di * t)
        q_t = DeclineCurveEngine.hyperbolic_rate(t, qi, di, b)
        return (qi ** b / ((1.0 - b) * di)) * (qi ** (1.0 - b) - q_t ** (1.0 - b))

    @classmethod
    def _r_squared(cls, actual: np.ndarray, predicted: np.ndarray) -> float:
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        if ss_tot == 0:
            return 0.0
        return 1.0 - ss_res / ss_tot

    @classmethod
    def fit_exponential(cls, time: np.ndarray,
                        rates: np.ndarray) -> DeclineFitResult:
        """Fit exponential decline to rate-time data.

        time: months from first production (0-indexed).
        rates: monthly volumes.
        """
        # Filter out zeros and negatives
        mask = rates > 0
        t_fit = time[mask].astype(float)
        r_fit = rates[mask].astype(float)

        if len(t_fit) < 2:
            return DeclineFitResult(model="exponential")

        # Initial guesses
        qi_guess = float(r_fit[0]) if r_fit[0] > 0 else 100.0
        ratio = r_fit[-1] / r_fit[0] if r_fit[0] > 0 else 0.5
        t_span = t_fit[-1] - t_fit[0]
        di_guess = -np.log(max(ratio, 0.01)) / max(t_span, 1.0)
        di_guess = max(di_guess, 0.001)

        try:
            popt, _ = curve_fit(
                cls.exponential_rate, t_fit, r_fit,
                p0=[qi_guess, di_guess],
                bounds=([0, 0], [qi_guess * 10, 1.0]),
                maxfev=5000,
            )
            qi, di = popt
            predicted = cls.exponential_rate(t_fit, qi, di)
            r2 = cls._r_squared(r_fit, predicted)

            result = DeclineFitResult(
                model="exponential", qi=qi, di=di, b=0.0, r_squared=r2)
            result.eur = cls.calculate_eur(result)
            return result
        except (RuntimeError, ValueError):
            return DeclineFitResult(model="exponential")

    @classmethod
    def fit_hyperbolic(cls, time: np.ndarray, rates: np.ndarray,
                       b_bounds: tuple = (0.01, 2.0)) -> DeclineFitResult:
        """Fit hyperbolic decline to rate-time data."""
        mask = rates > 0
        t_fit = time[mask].astype(float)
        r_fit = rates[mask].astype(float)

        if len(t_fit) < 3:
            return DeclineFitResult(model="hyperbolic")

        qi_guess = float(r_fit[0]) if r_fit[0] > 0 else 100.0
        ratio = r_fit[-1] / r_fit[0] if r_fit[0] > 0 else 0.5
        t_span = t_fit[-1] - t_fit[0]
        di_guess = -np.log(max(ratio, 0.01)) / max(t_span, 1.0)
        di_guess = max(di_guess, 0.001)

        try:
            popt, _ = curve_fit(
                cls.hyperbolic_rate, t_fit, r_fit,
                p0=[qi_guess, di_guess, 0.5],
                bounds=([0, 0, b_bounds[0]], [qi_guess * 10, 1.0, b_bounds[1]]),
                maxfev=10000,
            )
            qi, di, b = popt
            predicted = cls.hyperbolic_rate(t_fit, qi, di, b)
            r2 = cls._r_squared(r_fit, predicted)

            result = DeclineFitResult(
                model="hyperbolic", qi=qi, di=di, b=b, r_squared=r2)
            result.eur = cls.calculate_eur(result)
            return result
        except (RuntimeError, ValueError):
            return DeclineFitResult(model="hyperbolic")

    @classmethod
    def fit_best(cls, time: np.ndarray,
                 rates: np.ndarray) -> DeclineFitResult:
        """Try exponential and hyperbolic fits, return the one with better R²."""
        exp_fit = cls.fit_exponential(time, rates)
        hyp_fit = cls.fit_hyperbolic(time, rates)

        if hyp_fit.r_squared >= exp_fit.r_squared and hyp_fit.qi > 0:
            return hyp_fit
        if exp_fit.qi > 0:
            return exp_fit
        return hyp_fit

    @staticmethod
    def calculate_eur(fit: DeclineFitResult, economic_limit: float = 1.0,
                      max_months: int = 600) -> float:
        """Project EUR from fitted decline curve to economic limit."""
        if fit.qi <= 0 or fit.di <= 0:
            return 0.0

        t = np.arange(0, max_months + 1, dtype=float)

        if fit.model == "hyperbolic" and fit.b > 0:
            rates = DeclineCurveEngine.hyperbolic_rate(t, fit.qi, fit.di, fit.b)
            cum = DeclineCurveEngine.hyperbolic_cumulative(t, fit.qi, fit.di, fit.b)
        else:
            rates = DeclineCurveEngine.exponential_rate(t, fit.qi, fit.di)
            cum = DeclineCurveEngine.exponential_cumulative(t, fit.qi, fit.di)

        # Find where rate drops below economic limit
        below = np.where(rates < economic_limit)[0]
        if len(below) > 0:
            return float(cum[below[0]])
        return float(cum[-1])

    @staticmethod
    def generate_forecast(fit: DeclineFitResult, forecast_months: int = 360,
                          economic_limit: float = 1.0) -> tuple:
        """Generate forecast arrays from a fit result.

        Returns (time_array, rate_array, cumulative_array).
        """
        if fit.qi <= 0 or fit.di <= 0:
            return np.array([]), np.array([]), np.array([])

        t = np.arange(0, forecast_months + 1, dtype=float)

        if fit.model == "hyperbolic" and fit.b > 0:
            rates = DeclineCurveEngine.hyperbolic_rate(t, fit.qi, fit.di, fit.b)
            cum = DeclineCurveEngine.hyperbolic_cumulative(t, fit.qi, fit.di, fit.b)
        else:
            rates = DeclineCurveEngine.exponential_rate(t, fit.qi, fit.di)
            cum = DeclineCurveEngine.exponential_cumulative(t, fit.qi, fit.di)

        # Truncate at economic limit
        above = rates >= economic_limit
        if not np.all(above):
            cutoff = np.argmax(~above)
            if cutoff > 0:
                t = t[:cutoff + 1]
                rates = rates[:cutoff + 1]
                cum = cum[:cutoff + 1]

        return t, rates, cum
