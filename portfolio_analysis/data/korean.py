"""Multi-provider price loading for Korean-listed securities."""

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
    yahoo_downloader : callable, optional
        ``yfinance.download``-compatible callable used when FinanceDataReader
        cannot return usable prices. Primarily useful for tests.
    """

    def __init__(
        self,
        tickers: list[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        reader: Callable | None = None,
        yahoo_downloader: Callable | None = None,
    ):
        self.tickers = [normalize_korean_ticker(ticker) for ticker in tickers]
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self._reader = reader
        self._yahoo_downloader = yahoo_downloader
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

    def _get_yahoo_downloader(self) -> Callable:
        if self._yahoo_downloader is not None:
            return self._yahoo_downloader

        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - installation failure
            raise DataError("yfinance is required for the Yahoo fallback.") from exc
        return yf.download

    @staticmethod
    def _close_series(frame: pd.DataFrame) -> pd.Series:
        """Extract one usable closing-price series from a provider response."""
        if frame is None or frame.empty:
            raise DataError("no rows returned")

        if isinstance(frame.columns, pd.MultiIndex):
            price_types = frame.columns.get_level_values(0).unique()
            if "Adj Close" in price_types:
                close = frame["Adj Close"]
            elif "Close" in price_types:
                close = frame["Close"]
            else:
                raise DataError("response has no Close or Adj Close column")
            if isinstance(close, pd.DataFrame):
                if close.shape[1] != 1:
                    raise DataError("response has multiple closing-price columns")
                close = close.iloc[:, 0]
        elif "Close" in frame.columns:
            close = frame["Close"]
        elif "Adj Close" in frame.columns:
            close = frame["Adj Close"]
        else:
            raise DataError("response has no Close or Adj Close column")

        close = pd.to_numeric(close, errors="coerce").dropna()
        if close.empty:
            raise DataError("Close prices are empty")

        index = pd.DatetimeIndex(pd.to_datetime(close.index))
        if index.tz is not None:
            index = index.tz_convert(None)
        close.index = index
        return close

    def _fetch_fdr_close(self, reader: Callable, ticker: str) -> pd.Series:
        return self._close_series(reader(ticker, self.start_date, self.end_date))

    def _fetch_yahoo_close(self, downloader: Callable, ticker: str) -> pd.Series:
        """Try Yahoo's KRX then KOSDAQ symbol suffixes for one short code."""
        failures: list[str] = []
        for suffix in (".KS", ".KQ"):
            yahoo_ticker = f"{ticker}{suffix}"
            try:
                frame = downloader(
                    yahoo_ticker,
                    start=self.start_date,
                    end=self.end_date,
                    progress=False,
                    auto_adjust=True,
                )
                return self._close_series(frame)
            except Exception as exc:
                failures.append(f"{yahoo_ticker} ({exc})")
        raise DataError("Yahoo Finance failed: " + "; ".join(failures))

    def fetch_data(self) -> pd.DataFrame:
        """Fetch prices from FDR first, then Yahoo, and align common dates."""
        try:
            reader = self._get_reader()
            fdr_setup_error: Exception | None = None
        except Exception as exc:
            reader = None
            fdr_setup_error = exc

        try:
            yahoo_downloader = self._get_yahoo_downloader()
            yahoo_setup_error: Exception | None = None
        except Exception as exc:
            yahoo_downloader = None
            yahoo_setup_error = exc

        prices: dict[str, pd.Series] = {}
        failures: list[str] = []

        for ticker in self.tickers:
            fdr_error: Exception | None = fdr_setup_error
            if reader is not None:
                try:
                    prices[ticker] = self._fetch_fdr_close(reader, ticker).rename(ticker)
                    continue
                except Exception as exc:
                    fdr_error = exc

            yahoo_error: Exception | None = yahoo_setup_error
            if yahoo_downloader is not None:
                try:
                    prices[ticker] = self._fetch_yahoo_close(
                        yahoo_downloader, ticker
                    ).rename(ticker)
                    continue
                except Exception as exc:
                    yahoo_error = exc

            failures.append(
                f"{ticker} (FDR ({fdr_error}); Yahoo Finance ({yahoo_error}))"
            )

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
