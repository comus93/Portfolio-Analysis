"""Tests for user-local portfolio preset and session persistence."""

import json
from copy import deepcopy

import pytest

from portfolio_analysis.local_portfolios import (
    LocalPortfolioStore,
    LocalPortfolioStoreError,
    default_store_path,
    export_preset_json,
    import_preset_json,
    make_asset_records,
    preset_export_filename,
    split_asset_records,
)


@pytest.fixture
def records():
    assets = [
        {"Code": "005930", "Name": "삼성전자", "Type": "Stock", "Market": "KOSPI"},
        {"Code": "069500", "Name": "KODEX 200", "Type": "ETF", "Market": "KRX"},
    ]
    return make_asset_records(assets, [0.7, 0.3])


def test_default_path_uses_windows_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert default_store_path() == tmp_path / "Portfolio-Analysis" / "portfolios.json"


def test_missing_file_is_a_normal_empty_first_run(tmp_path):
    store = LocalPortfolioStore(tmp_path / "missing" / "portfolios.json")

    document = store.load()

    assert document["presets"] == {}
    assert document["last_session"] == {"portfolio": [], "benchmark": []}


def test_save_load_and_overwrite_named_preset(tmp_path, records):
    store = LocalPortfolioStore(tmp_path / "portfolios.json")
    store.save_preset("혼합", records)

    replacement = deepcopy(records)
    replacement[0]["Weight"] = 20.0
    replacement[1]["Weight"] = 80.0
    store.save_preset("혼합", replacement)

    assert store.load()["presets"] == {"혼합": replacement}


def test_loaded_preset_is_independent_until_explicit_save(tmp_path, records):
    store = LocalPortfolioStore(tmp_path / "portfolios.json")
    store.save_preset("원본", records)

    editable = store.load()["presets"]["원본"]
    editable[0]["Weight"] = 10.0

    assert store.load()["presets"]["원본"] == records


def test_same_preset_can_supply_portfolio_or_benchmark(records):
    portfolio_assets, portfolio_weights = split_asset_records(records)
    benchmark_assets, benchmark_weights = split_asset_records(records)

    portfolio_assets[0]["Name"] = "작업 중 수정"

    assert benchmark_assets[0]["Name"] == "삼성전자"
    assert portfolio_weights == benchmark_weights == [0.7, 0.3]


def test_delete_named_preset(tmp_path, records):
    store = LocalPortfolioStore(tmp_path / "portfolios.json")
    store.save_preset("삭제할 항목", records)

    assert store.delete_preset("삭제할 항목") is True
    assert store.delete_preset("없는 항목") is False
    assert store.load()["presets"] == {}


def test_last_session_restores_both_sides_without_mutating_preset(tmp_path, records):
    store = LocalPortfolioStore(tmp_path / "portfolios.json")
    store.save_preset("원본", records)
    edited = deepcopy(records)
    edited[0]["Weight"] = 60.0
    edited[1]["Weight"] = 40.0

    store.save_last_session(edited, records)
    document = store.load()

    assert document["last_session"] == {
        "portfolio": edited,
        "benchmark": records,
    }
    assert document["presets"]["원본"] == records
    assert set(document) == {"version", "presets", "last_session"}


def test_preset_rejects_invalid_total_but_last_session_preserves_edit(tmp_path, records):
    store = LocalPortfolioStore(tmp_path / "portfolios.json")
    editing = deepcopy(records)
    editing[0]["Weight"] = 55.0

    with pytest.raises(ValueError, match="100%"):
        store.save_preset("미완성", editing)

    store.save_last_session(editing, [])
    assert store.load()["last_session"]["portfolio"] == editing


def test_corrupt_file_reports_understandable_error_and_is_not_overwritten(tmp_path):
    path = tmp_path / "portfolios.json"
    path.write_text("{broken json", encoding="utf-8")
    store = LocalPortfolioStore(path)

    with pytest.raises(LocalPortfolioStoreError, match="빈 상태로 계속 실행"):
        store.load()

    assert path.read_text(encoding="utf-8") == "{broken json"


def test_file_contains_only_allowed_configuration_fields(tmp_path, records):
    path = tmp_path / "portfolios.json"
    store = LocalPortfolioStore(path)
    store.save_preset("구성", records)
    store.save_last_session(records, records)

    serialized = json.loads(path.read_text(encoding="utf-8"))
    asset = serialized["presets"]["구성"][0]

    assert set(asset) == {"Code", "Name", "Type", "Market", "Weight"}
    forbidden = {"price", "result", "start_date", "end_date", "risk_free_rate"}
    assert not forbidden & set(asset)


def test_alphanumeric_code_is_normalized_and_preserved_in_preset(tmp_path):
    store = LocalPortfolioStore(tmp_path / "portfolios.json")
    records = make_asset_records(
        [
            {
                "Code": "0137v0",
                "Name": "KIWOOM 미국S&P500모멘텀",
                "Type": "ETF",
                "Market": "KRX",
            }
        ],
        [1.0],
    )

    store.save_preset("문자 코드", records)
    assets, weights = split_asset_records(store.load()["presets"]["문자 코드"])

    assert assets[0]["Code"] == "0137V0"
    assert weights == [1.0]


def test_preset_export_import_round_trip_contains_only_portable_fields(records):
    exported = export_preset_json("혼합 구성", records)
    payload = json.loads(exported)

    assert set(payload) == {"version", "name", "assets"}
    assert payload["name"] == "혼합 구성"
    assert payload["assets"] == records
    assert not {
        "last_session",
        "analysis_result",
        "start_date",
        "end_date",
        "risk_free_rate",
    } & set(payload)
    assert import_preset_json(exported) == ("혼합 구성", records)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"{broken", "손상"),
        (json.dumps({"version": 2, "name": "x", "assets": []}), "version"),
        (json.dumps({"version": 1, "name": "", "assets": []}), "이름"),
        (
            json.dumps(
                {
                    "version": 1,
                    "name": "잘못된 코드",
                    "assets": [
                        {
                            "Code": "INVALID",
                            "Name": "invalid",
                            "Type": "ETF",
                            "Market": "KRX",
                            "Weight": 100.0,
                        }
                    ],
                }
            ),
            "종목코드",
        ),
    ],
)
def test_preset_import_rejects_malformed_or_unsupported_payload(payload, message):
    with pytest.raises(ValueError, match=message):
        import_preset_json(payload)


def test_preset_export_filename_replaces_unsafe_characters():
    assert preset_export_filename('주식/금:*?') == "주식_금___.portfolio.json"


def test_preset_import_normalizes_alphanumeric_code_case():
    payload = {
        "version": 1,
        "name": "문자 코드",
        "assets": [
            {
                "Code": "0137v0",
                "Name": "KIWOOM 미국S&P500모멘텀",
                "Type": "ETF",
                "Market": "KRX",
                "Weight": 100.0,
            }
        ],
    }

    _, records = import_preset_json(json.dumps(payload))

    assert records[0]["Code"] == "0137V0"
