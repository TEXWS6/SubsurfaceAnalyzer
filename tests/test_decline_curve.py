"""Tests for DeclineCurveEngine — Arps decline curve analysis."""

import numpy as np
import pytest

from services.decline_curve import DeclineCurveEngine, DeclineFitResult


class TestExponentialRate:
    def test_at_time_zero(self):
        t = np.array([0.0])
        q = DeclineCurveEngine.exponential_rate(t, qi=1000, di=0.05)
        assert q[0] == pytest.approx(1000)

    def test_monotonically_decreasing(self):
        t = np.arange(0, 25, dtype=float)
        q = DeclineCurveEngine.exponential_rate(t, qi=1000, di=0.05)
        assert all(q[i] >= q[i + 1] for i in range(len(q) - 1))

    def test_known_value(self):
        # q(12) = 1000 * exp(-0.05 * 12) ≈ 548.8
        t = np.array([12.0])
        q = DeclineCurveEngine.exponential_rate(t, qi=1000, di=0.05)
        assert q[0] == pytest.approx(548.8, rel=0.01)


class TestExponentialCumulative:
    def test_at_time_zero(self):
        t = np.array([0.0])
        cum = DeclineCurveEngine.exponential_cumulative(t, qi=1000, di=0.05)
        assert cum[0] == pytest.approx(0, abs=1)

    def test_monotonically_increasing(self):
        t = np.arange(0, 25, dtype=float)
        cum = DeclineCurveEngine.exponential_cumulative(t, qi=1000, di=0.05)
        assert all(cum[i] <= cum[i + 1] for i in range(len(cum) - 1))


class TestHyperbolicRate:
    def test_at_time_zero(self):
        t = np.array([0.0])
        q = DeclineCurveEngine.hyperbolic_rate(t, qi=1000, di=0.1, b=0.5)
        assert q[0] == pytest.approx(1000)

    def test_monotonically_decreasing(self):
        t = np.arange(0, 60, dtype=float)
        q = DeclineCurveEngine.hyperbolic_rate(t, qi=1000, di=0.1, b=0.5)
        assert all(q[i] >= q[i + 1] for i in range(len(q) - 1))

    def test_declines_slower_than_exponential(self):
        t = np.array([24.0])
        q_exp = DeclineCurveEngine.exponential_rate(t, qi=1000, di=0.1)
        q_hyp = DeclineCurveEngine.hyperbolic_rate(t, qi=1000, di=0.1, b=0.5)
        assert q_hyp[0] > q_exp[0]


class TestFitExponential:
    def test_fit_synthetic_data(self):
        np.random.seed(42)
        t = np.arange(0, 36, dtype=float)
        qi_true, di_true = 1000.0, 0.05
        rates = qi_true * np.exp(-di_true * t) + np.random.normal(0, 5, len(t))
        rates = np.maximum(rates, 1)
        result = DeclineCurveEngine.fit_exponential(t, rates)
        assert result.qi == pytest.approx(qi_true, rel=0.1)
        assert result.di == pytest.approx(di_true, rel=0.2)
        assert result.r_squared > 0.9

    def test_fit_too_few_points(self):
        t = np.array([0.0])
        rates = np.array([1000.0])
        result = DeclineCurveEngine.fit_exponential(t, rates)
        assert result.qi == 0.0  # default fallback


class TestFitHyperbolic:
    def test_fit_synthetic_data(self):
        np.random.seed(42)
        t = np.arange(0, 60, dtype=float)
        qi, di, b = 1000.0, 0.1, 0.5
        rates = qi / (1 + b * di * t) ** (1 / b) + np.random.normal(0, 5, len(t))
        rates = np.maximum(rates, 1)
        result = DeclineCurveEngine.fit_hyperbolic(t, rates)
        assert result.r_squared > 0.9
        assert result.b > 0


class TestFitBest:
    def test_selects_better_model(self):
        np.random.seed(42)
        t = np.arange(0, 48, dtype=float)
        rates = 1000 * np.exp(-0.03 * t)
        result = DeclineCurveEngine.fit_best(t, rates)
        assert result.model in ("exponential", "hyperbolic")
        assert result.r_squared > 0.95


class TestEUR:
    def test_eur_positive(self):
        np.random.seed(42)
        t = np.arange(0, 36, dtype=float)
        rates = 1000 * np.exp(-0.05 * t)
        fit = DeclineCurveEngine.fit_exponential(t, rates)
        eur = DeclineCurveEngine.calculate_eur(fit, economic_limit=10, max_months=600)
        assert eur > 0

    def test_eur_exceeds_historical(self):
        np.random.seed(42)
        t = np.arange(0, 24, dtype=float)
        rates = 1000 * np.exp(-0.05 * t)
        fit = DeclineCurveEngine.fit_exponential(t, rates)
        eur = DeclineCurveEngine.calculate_eur(fit, economic_limit=1, max_months=600)
        assert eur > sum(rates)

    def test_eur_zero_qi(self):
        fit = DeclineFitResult(model="exponential", qi=0, di=0.05)
        assert DeclineCurveEngine.calculate_eur(fit) == 0.0


class TestForecast:
    def test_forecast_length(self):
        np.random.seed(42)
        t = np.arange(0, 24, dtype=float)
        rates = 1000 * np.exp(-0.05 * t)
        fit = DeclineCurveEngine.fit_exponential(t, rates)
        t_arr, r_arr, c_arr = DeclineCurveEngine.generate_forecast(
            fit, forecast_months=120)
        assert len(t_arr) > 0
        assert len(r_arr) == len(t_arr)
        assert len(c_arr) == len(t_arr)

    def test_forecast_rates_decrease(self):
        np.random.seed(42)
        t = np.arange(0, 36, dtype=float)
        rates = 1000 * np.exp(-0.05 * t)
        fit = DeclineCurveEngine.fit_exponential(t, rates)
        t_arr, r_arr, c_arr = DeclineCurveEngine.generate_forecast(fit)
        assert all(r_arr[i] >= r_arr[i + 1] for i in range(len(r_arr) - 1))

    def test_forecast_empty_on_bad_fit(self):
        fit = DeclineFitResult(model="exponential", qi=0, di=0)
        t_arr, r_arr, c_arr = DeclineCurveEngine.generate_forecast(fit)
        assert len(t_arr) == 0


class TestHyperbolicCumulative:
    def test_cumulative_increases(self):
        t = np.arange(0, 60, dtype=float)
        cum = DeclineCurveEngine.hyperbolic_cumulative(t, qi=1000, di=0.1, b=0.5)
        assert all(cum[i] <= cum[i + 1] for i in range(len(cum) - 1))

    def test_harmonic_case(self):
        """b=1 should use harmonic formula without error."""
        t = np.arange(0, 12, dtype=float)
        cum = DeclineCurveEngine.hyperbolic_cumulative(t, qi=1000, di=0.1, b=1.0)
        assert cum[-1] > 0
