"""Tests for Korean security metadata search."""

import json

import pandas as pd
import pytest

from portfolio_analysis.data.korean_securities import KoreanSecurityDirectory
from portfolio_analysis.exceptions import DataError


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("euc-kr")


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
                "Symbol": ["069500", "360750", "0137V0", "0172V0"],
                "Name": [
                    "KODEX 200",
                    "TIGER 미국S&P500",
                    "KIWOOM 미국S&P500모멘텀",
                    "1Q 은액티브",
                ],
            }
        )
    if market == "ETN/KR":
        return pd.DataFrame(
            {
                "Symbol": ["530107", "0123A0"],
                "Name": ["삼성 인버스 2X 코스닥150 선물 ETN", "향후 영숫자 ETN"],
            }
        )
    raise AssertionError(f"unexpected market: {market}")


def test_fetch_catalog_combines_stocks_etfs_and_etns():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    assert set(catalog.columns) == {"Code", "Name", "Type", "Market"}
    assert catalog.loc[catalog["Code"] == "005930", "Type"].iloc[0] == "주식"
    assert catalog.loc[catalog["Code"] == "069500", "Type"].iloc[0] == "ETF"
    assert catalog.loc[catalog["Code"] == "530107", "Type"].iloc[0] == "ETN"


def test_default_etn_fallback_maps_naver_listing(monkeypatch):
    payload = {
        "result": {
            "etnItemList": [
                {"itemcode": "530107", "itemname": "삼성 인버스 ETN"}
            ]
        }
    }
    monkeypatch.setattr(
        "portfolio_analysis.data.korean_securities.urlopen",
        lambda url, timeout: FakeResponse(payload),
    )

    listing = KoreanSecurityDirectory._fetch_etn_listing()

    assert listing.to_dict("records") == [
        {"Symbol": "530107", "Name": "삼성 인버스 ETN", "Market": "KRX"}
    ]


@pytest.mark.parametrize(
    ("query", "expected_code"),
    [
        ("0137v0", "0137V0"),
        ("KIWOOM 미국S&P500모멘텀", "0137V0"),
        ("0172V0", "0172V0"),
        ("은액티브", "0172V0"),
        ("530107", "530107"),
    ],
)
def test_search_supports_new_etfs_case_insensitively_and_etn(query, expected_code):
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    assert KoreanSecurityDirectory.search_catalog(catalog, query).iloc[0]["Code"] == expected_code


def test_search_supports_exact_code_without_selecting_it():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    results = KoreanSecurityDirectory.search_catalog(catalog, "005930")

    assert results["Code"].tolist() == ["005930"]
    assert results.iloc[0]["Name"] == "삼성전자"


@pytest.mark.parametrize(
    ("query", "expected_codes"),
    [
        ("삼성", ["530107", "005930"]),
        ("tiger", ["360750"]),
        ("500", ["0137V0", "069500", "360750"]),
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

    assert set(catalog["Type"]) == {"ETF", "ETN"}
    assert "KRX-DESC" in catalog.attrs["warnings"][0]


def test_catalog_reports_failure_when_all_sources_fail():
    def failing_reader(market):
        raise RuntimeError(f"{market} unavailable")

    with pytest.raises(DataError, match="KRX-DESC.*ETF/KR.*ETN/KR"):
        KoreanSecurityDirectory(failing_reader).fetch_catalog()


def test_catalog_rejects_listing_rows_without_usable_codes():
    def invalid_reader(market):
        code_column = "Symbol" if market in {"ETF/KR", "ETN/KR"} else "Code"
        return pd.DataFrame({code_column: ["invalid"], "Name": ["Unknown"]})

    with pytest.raises(DataError, match="usable rows"):
        KoreanSecurityDirectory(invalid_reader).fetch_catalog()


def test_search_limit_and_empty_query():
    catalog = KoreanSecurityDirectory(listing_reader).fetch_catalog()

    assert KoreanSecurityDirectory.search_catalog(catalog, "").empty
    assert len(KoreanSecurityDirectory.search_catalog(catalog, "0", limit=2)) == 2
