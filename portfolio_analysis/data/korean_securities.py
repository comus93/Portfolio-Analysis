"""Searchable Korean stock, ETF, and ETN metadata, separate from prices."""

import json
from collections.abc import Callable
from urllib.request import urlopen

import pandas as pd

from portfolio_analysis.data.korean import is_valid_korean_ticker
from portfolio_analysis.exceptions import DataError


class KoreanSecurityDirectory:
    """Load and search Korean-listed stock, ETF, and ETN metadata.

    The directory performs literal code/name substring matching only. It never
    infers or selects a security on behalf of a caller.

    Parameters
    ----------
    listing_reader : callable, optional
        FinanceDataReader ``StockListing`` compatible callable. Primarily useful
        for tests.
    """

    COLUMNS = ["Code", "Name", "Type", "Market"]
    ETN_LISTING_URL = "https://finance.naver.com/api/sise/etnItemList.nhn"

    def __init__(self, listing_reader: Callable | None = None):
        self._listing_reader = listing_reader

    def _get_listing_reader(self) -> Callable:
        if self._listing_reader is not None:
            return self._listing_reader

        try:
            import FinanceDataReader as fdr
        except ImportError as exc:  # pragma: no cover - installation failure
            raise DataError(
                "FinanceDataReader is required for Korean security search."
            ) from exc
        return fdr.StockListing

    @staticmethod
    def _normalize_listing(listing: pd.DataFrame, security_type: str) -> pd.DataFrame:
        code_column = "Symbol" if "Symbol" in listing.columns else "Code"
        required = {code_column, "Name"}
        if not required.issubset(listing.columns):
            missing = sorted(required.difference(listing.columns))
            raise DataError(
                "Listing response is missing columns: " + ", ".join(missing)
            )

        codes = listing[code_column].astype(str).str.strip().str.upper()
        numeric_codes = codes.str.fullmatch(r"\d{1,6}")
        codes = codes.where(~numeric_codes, codes.str.zfill(6))
        normalized = pd.DataFrame(
            {
                "Code": codes,
                "Name": listing["Name"].astype(str).str.strip(),
                "Type": security_type,
                "Market": (
                    listing["Market"].astype(str).str.strip()
                    if "Market" in listing.columns
                    else "KRX"
                ),
            }
        )
        valid = normalized["Code"].map(is_valid_korean_ticker) & normalized[
            "Name"
        ].ne("")
        return normalized.loc[valid, KoreanSecurityDirectory.COLUMNS]

    @classmethod
    def _fetch_etn_listing(cls) -> pd.DataFrame:
        """Load ETNs from the Naver listing family used by FDR for Korean ETFs."""
        try:
            with urlopen(cls.ETN_LISTING_URL, timeout=15) as response:
                payload = json.loads(response.read().decode("euc-kr"))
            items = payload["result"]["etnItemList"]
        except Exception as exc:
            raise DataError(f"ETN listing unavailable: {exc}") from exc
        return pd.DataFrame(
            {
                "Symbol": [item.get("itemcode", "") for item in items],
                "Name": [item.get("itemname", "") for item in items],
                "Market": "KRX",
            }
        )

    def _read_listing(self, market: str) -> pd.DataFrame:
        if market == "ETN/KR" and self._listing_reader is None:
            return self._fetch_etn_listing()
        return self._get_listing_reader()(market)

    def fetch_catalog(self) -> pd.DataFrame:
        """Fetch and normalize listed-company, ETF, and ETN metadata."""
        frames: list[pd.DataFrame] = []
        failures: list[str] = []

        sources = (("KRX-DESC", "주식"), ("ETF/KR", "ETF"), ("ETN/KR", "ETN"))
        for market, security_type in sources:
            try:
                listing = self._read_listing(market)
                if listing is None or listing.empty:
                    raise DataError("no rows returned")
                frames.append(self._normalize_listing(listing, security_type))
            except Exception as exc:
                failures.append(f"{market} ({exc})")

        if not frames:
            raise DataError(
                "Failed to load Korean security metadata: " + "; ".join(failures)
            )

        catalog = pd.concat(frames, ignore_index=True)
        if catalog.empty:
            raise DataError("Korean security metadata did not contain usable rows.")
        # Specialized product listings are authoritative when a provider also
        # happens to include the same code in a general stock listing.
        catalog = catalog.drop_duplicates(subset="Code", keep="last")
        catalog = catalog.sort_values(["Name", "Code"], kind="stable").reset_index(
            drop=True
        )
        catalog.attrs["warnings"] = failures
        return catalog

    @staticmethod
    def search_catalog(
        catalog: pd.DataFrame, query: str, limit: int = 50
    ) -> pd.DataFrame:
        """Return literal code/name matches without choosing a result."""
        query = query.strip()
        if not query or limit < 1:
            return pd.DataFrame(columns=KoreanSecurityDirectory.COLUMNS)
        if not set(KoreanSecurityDirectory.COLUMNS).issubset(catalog.columns):
            raise DataError("Korean security catalog has an invalid schema.")

        code = catalog["Code"].astype(str).str.upper()
        name = catalog["Name"].astype(str)
        normalized_query = query.upper()
        folded_query = query.casefold()
        folded_name = name.str.casefold()

        matches = code.str.contains(
            normalized_query, regex=False
        ) | folded_name.str.contains(folded_query, regex=False)
        results = catalog.loc[matches, KoreanSecurityDirectory.COLUMNS].copy()
        if results.empty:
            return results

        result_code = results["Code"].astype(str)
        result_name = results["Name"].astype(str).str.casefold()
        results["_priority"] = 4
        results.loc[result_name.str.startswith(folded_query), "_priority"] = 3
        results.loc[result_code.str.startswith(normalized_query), "_priority"] = 2
        results.loc[result_name.eq(folded_query), "_priority"] = 1
        results.loc[result_code.eq(normalized_query), "_priority"] = 0

        return (
            results.sort_values(["_priority", "Name", "Code"], kind="stable")
            .drop(columns="_priority")
            .head(limit)
            .reset_index(drop=True)
        )
