"""Tests for Korean market loading and provider-neutral benchmarking."""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from portfolio_analysis.data.korean import KoreanDataLoader
from portfolio_analysis.data.loader import DataLoader
from portfolio_analysis.exceptions import DataError, ValidationError
from portfolio_analysis.metrics.benchmark import BenchmarkComparison


def _reader_with_staggered_dates(ticker, start, end):
    dates = pd.date_range("2024-01-02", periods=4, freq="D")
    if ticker == "069500":
        return pd.DataFrame({"Close": [100, 101, 102, 103]}, index=dates)
    return pd.DataFrame({"Close": [200, 202, 204]}, index=dates[1:])


class TestKoreanDataLoader:
    def test_fetches_in_input_order_and_aligns_common_dates(self):
        loader = KoreanDataLoader(
            ["411060", "069500"],
            "2024-01-01",
            "2024-02-01",
            reader=_reader_with_staggered_dates,
        )

        data = loader.fetch_data()

        assert list(data.columns) == ["411060", "069500"]
        assert len(data) == 3
        assert data.index.min() == pd.Timestamp("2024-01-03")

    @pytest.mark.parametrize("ticker", ["69500", "ABCDEF", "069500.KS", ""])
    def test_rejects_non_six_digit_codes(self, ticker):
        with pytest.raises(ValidationError, match="six digits"):
            KoreanDataLoader([ticker], "2024-01-01", "2024-02-01")

    def test_rejects_invalid_date_range(self):
        with pytest.raises(ValidationError, match="earlier"):
            KoreanDataLoader(["069500"], "2024-02-01", "2024-01-01")

    def test_reports_ticker_and_provider_error(self):
        def failing_reader(ticker, start, end):
            raise RuntimeError("provider unavailable")

        loader = KoreanDataLoader(
            ["069500"],
            "2024-01-01",
            "2024-02-01",
            reader=failing_reader,
        )

        with pytest.raises(DataError, match="069500.*provider unavailable"):
            loader.fetch_data()

    def test_requires_close_prices(self):
        loader = KoreanDataLoader(
            ["069500"],
            "2024-01-01",
            "2024-02-01",
            reader=lambda ticker, start, end: pd.DataFrame(
                {"Open": [100]}, index=pd.to_datetime(["2024-01-02"])
            ),
        )

        with pytest.raises(DataError, match="Close column"):
            loader.fetch_data()


def test_yahoo_loader_preserves_requested_ticker_order():
    dates = pd.date_range("2024-01-02", periods=3, freq="D")
    columns = pd.MultiIndex.from_product([["Close"], ["BND", "SPY"]])
    raw = pd.DataFrame(
        np.array([[50, 100], [51, 101], [52, 102]]),
        index=dates,
        columns=columns,
    )

    with patch("portfolio_analysis.data.loader.yf.download", return_value=raw):
        data = DataLoader(["SPY", "BND"], "2024-01-01", "2024-02-01").fetch_data(
            progress=False
        )

    assert list(data.columns) == ["SPY", "BND"]


def test_benchmark_comparison_accepts_preloaded_korean_prices():
    dates = pd.date_range("2024-01-02", periods=6, freq="D")
    portfolio_data = pd.DataFrame(
        {
            "069500": [100, 101, 100, 103, 104, 105],
            "411060": [100, 100, 102, 102, 103, 104],
        },
        index=dates,
    )
    benchmark = pd.Series(
        [200, 201, 203, 202, 205],
        index=dates[1:],
        name="487240",
    )

    comparison = BenchmarkComparison(
        portfolio_data,
        [0.6, 0.4],
        benchmark_ticker="487240",
        benchmark_data=benchmark,
    )
    metrics = comparison.get_metrics()

    assert comparison.portfolio_returns.index.equals(comparison.benchmark_returns.index)
    assert len(comparison.portfolio_returns) == 4
    assert np.isfinite(metrics["beta"])
    assert np.isfinite(metrics["correlation"])


def test_benchmark_comparison_accepts_precomputed_benchmark_returns():
    dates = pd.date_range("2024-01-02", periods=6, freq="D")
    portfolio_data = pd.DataFrame(
        {
            "069500": [100, 101, 100, 103, 104, 105],
            "411060": [100, 100, 102, 102, 103, 104],
        },
        index=dates,
    )
    benchmark_returns = pd.Series(
        [0.01, -0.005, 0.012, 0.004, 0.006],
        index=dates[1:],
        name="benchmark_portfolio",
    )

    comparison = BenchmarkComparison(
        portfolio_data,
        [0.6, 0.4],
        benchmark_ticker="Benchmark portfolio",
        benchmark_returns=benchmark_returns,
    )
    metrics = comparison.get_metrics()

    assert comparison.portfolio_returns.index.equals(benchmark_returns.index)
    assert np.isfinite(metrics["beta"])
    assert np.isfinite(metrics["tracking_error"])
