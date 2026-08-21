"""FinanceDataReader-backed loading for Korean-listed securities."""

import re
from collections.abc import Callable
from datetime import datetime
from typing import Union

import pandas as pd

from portfolio_analysis.exceptions import DataError, ValidationError

KOREAN_TICKER_PATTERN = re.compile(r"^\d{4}[0-9A-HJ-NP-TV-Z][0-9KLMN]$")


def normalize_korean_ticker(ticker: object) -> str:
    """Normalize a KRX short code without altering its six-character form."""
    return str(ticker).strip().upper()


def is_valid_korean_ticker(ticker: object) -> bool:
    """Return whether a value follows the current KRX short-code format."""
    return KOREAN_TICKER_PATTERN.fullmatch(normalize_korean_ticker(ticker)) is not None


class KoreanDataLoader:
    """Fetch aligned closing prices for Korean-listed stocks, ETFs, and ETNs.

    Parameters
    ----------
    tickers : list of str
        Six-character Korean security codes, including alphanumeric codes.
    start_date, end_date : str or datetime
        Requested analysis period.
    reader : callable, optional
        FinanceDataReader-compatible callable. Primarily useful for tests.
    """

    def __init__(
        self,
        tickers: list[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        reader: Callable | None = None,
    ):
        self.tickers = [normalize_korean_ticker(ticker) for ticker in tickers]
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self._reader = reader
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        if not self.tickers:
            raise ValidationError("At least one Korean ticker code is required.")
        invalid = [
            ticker
            for ticker in self.tickers
            if not is_valid_korean_ticker(ticker)
        ]
        if invalid:
            raise ValidationError(
                "Korean ticker codes must be valid six-character KRX codes: "
                + ", ".join(invalid)
            )
        if len(set(self.tickers)) != len(self.tickers):
            raise ValidationError("Duplicate Korean ticker codes are not allowed.")
        if self.start_date >= self.end_date:
            raise ValidationError("Start date must be earlier than end date.")

    def _get_reader(self) -> Callable:
        if self._reader is not None:
            return self._reader

        try:
            import FinanceDataReader as fdr
        except ImportError as exc:  # pragma: no cover - installation failure
            raise DataError(
                "FinanceDataReader is required for Korean market data."
            ) from exc
        return fdr.DataReader

    def fetch_data(self) -> pd.DataFrame:
        """Fetch close prices and align all securities to common trading dates."""
        reader = self._get_reader()
        prices: dict[str, pd.Series] = {}
        failures: list[str] = []

        for ticker in self.tickers:
            try:
                frame = reader(ticker, self.start_date, self.end_date)
                if frame is None or frame.empty:
                    raise DataError("no rows returned")
                if "Close" not in frame.columns:
                    raise DataError("response has no Close column")
                close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
                if close.empty:
                    raise DataError("Close prices are empty")
                close.index = pd.to_datetime(close.index).tz_localize(None)
                prices[ticker] = close.rename(ticker)
            except Exception as exc:
                failures.append(f"{ticker} ({exc})")

        if failures:
            raise DataError(
                "Failed to fetch Korean market data for: " + "; ".join(failures)
            )

        data = pd.concat(prices.values(), axis=1, join="inner").sort_index().dropna()
        data = data.loc[:, self.tickers]
        if data.empty:
            raise DataError(
                "The selected securities have no overlapping price dates in the "
                "requested period."
            )
        return data

    def fetch_returns(self) -> pd.DataFrame:
        """Fetch prices and calculate aligned daily returns."""
        return self.fetch_data().pct_change().dropna()
