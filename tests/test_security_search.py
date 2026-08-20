"""Tests for Korean security metadata search."""

import pandas as pd
import pytest

from portfolio_analysis.data.korean_securities import KoreanSecurityDirectory
from portfolio_analysis.exceptions import DataError


def listing_reader(market):
    if market == "KRX-DESC":
        return pd.DataFrame(
            {
                "Code": ["005930", "035420", "000660"],
                "Name": ["삼성전자", "NAVER", "SK하이닉스"],
                "Market": ["KOSPI", "KOSPI", "KOSPI"],
            }
        )
    if market == "ETF/KR":
        return pd.DataFrame(
            {
                "Symbol": ["069500", "360750"],
                "Name": ["KODEX 200", "TIGER 미국S&P500"],
            }
        )
    raise AssertionError(f"unexpected market: {market}")


def test_fetch_catalog_combines_stocks_and_etfs():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    assert set(catalog.columns) == {"Code", "Name", "Type", "Market"}
    assert catalog.loc[catalog["Code"] == "005930", "Type"].iloc[0] == "주식"
    assert catalog.loc[catalog["Code"] == "069500", "Type"].iloc[0] == "ETF"


def test_search_supports_exact_code_without_selecting_it():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    results = KoreanSecurityDirectory.search_catalog(catalog, "005930")

    assert results["Code"].tolist() == ["005930"]
    assert results.iloc[0]["Name"] == "삼성전자"


@pytest.mark.parametrize(
    ("query", "expected_codes"),
    [
        ("삼성", ["005930"]),
        ("tiger", ["360750"]),
        ("500", ["069500", "360750"]),
    ],
)
def test_search_uses_literal_case_insensitive_partial_matching(query, expected_codes):
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    results = KoreanSecurityDirectory.search_catalog(catalog, query)

    assert results["Code"].tolist() == expected_codes


def test_search_does_not_apply_fuzzy_inference():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    results = KoreanSecurityDirectory.search_catalog(catalog, "삼숭전자")

    assert results.empty


def test_catalog_remains_available_when_one_listing_source_fails():
    def partial_reader(market):
        if market == "KRX-DESC":
            raise RuntimeError("stock listing unavailable")
        return listing_reader(market)

    catalog = KoreanSecurityDirectory(partial_reader).fetch_catalog()

    assert set(catalog["Type"]) == {"ETF"}
    assert "KRX-DESC" in catalog.attrs["warnings"][0]


def test_catalog_reports_failure_when_all_sources_fail():
    def failing_reader(market):
        raise RuntimeError(f"{market} unavailable")

    with pytest.raises(DataError, match="KRX-DESC.*ETF/KR"):
        KoreanSecurityDirectory(failing_reader).fetch_catalog()


def test_catalog_rejects_listing_rows_without_usable_codes():
    def invalid_reader(market):
        code_column = "Symbol" if market == "ETF/KR" else "Code"
        return pd.DataFrame({code_column: ["invalid"], "Name": ["Unknown"]})

    with pytest.raises(DataError, match="usable rows"):
        KoreanSecurityDirectory(invalid_reader).fetch_catalog()


def test_search_limit_and_empty_query():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    assert KoreanSecurityDirectory.search_catalog(catalog, "").empty
    assert len(KoreanSecurityDirectory.search_catalog(catalog, "0", limit=2)) == 2
