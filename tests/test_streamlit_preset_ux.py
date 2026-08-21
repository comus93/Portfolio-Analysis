"""Focused AppTest coverage for the workspace-level preset UX."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from portfolio_analysis import KoreanDataLoader, KoreanSecurityDirectory
from portfolio_analysis.local_portfolios import (
    LocalPortfolioStore,
    export_preset_json,
    make_asset_records,
)

st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP_PATH = Path(__file__).parents[1] / "streamlit_app" / "app.py"


def sample_records():
    return make_asset_records(
        [
            {
                "Code": "005930",
                "Name": "삼성전자",
                "Type": "Stock",
                "Market": "KOSPI",
            },
            {
                "Code": "069500",
                "Name": "KODEX 200",
                "Type": "ETF",
                "Market": "KRX",
            },
        ],
        [0.7, 0.3],
    )


def sample_catalog():
    return pd.DataFrame(
        [
            {
                "Code": "005930",
                "Name": "삼성전자",
                "Type": "주식",
                "Market": "KOSPI",
            },
            {
                "Code": "069500",
                "Name": "KODEX 200",
                "Type": "ETF",
                "Market": "KRX",
            },
            {
                "Code": "0137V0",
                "Name": "KIWOOM 미국S&P500모멘텀",
                "Type": "ETF",
                "Market": "KRX",
            },
            {
                "Code": "035420",
                "Name": "NAVER",
                "Type": "주식",
                "Market": "KOSPI",
            },
        ]
    )


def start_app(
    monkeypatch,
    tmp_path,
    *,
    presets=None,
    portfolio=None,
    benchmark=None,
    catalog_error=False,
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    st.cache_data.clear()
    if catalog_error:
        def fail_catalog(self):
            raise RuntimeError("catalog unavailable")

        monkeypatch.setattr(KoreanSecurityDirectory, "fetch_catalog", fail_catalog)
    else:
        monkeypatch.setattr(
            KoreanSecurityDirectory,
            "fetch_catalog",
            lambda self: sample_catalog(),
        )
    store = LocalPortfolioStore()
    for name, records in (presets or {}).items():
        store.save_preset(name, records)
    store.save_last_session(portfolio or [], benchmark or [])
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert not app.exception
    return app, store


def test_each_workspace_loads_shared_preset_only_when_selector_changes(
    monkeypatch, tmp_path
):
    records = sample_records()
    app, _ = start_app(monkeypatch, tmp_path, presets={"혼합": records})

    assert app.sidebar.selectbox(key="portfolio_workspace_preset_selector").label == (
        "Portfolio Preset"
    )
    assert app.sidebar.selectbox(key="benchmark_workspace_preset_selector").label == (
        "Benchmark Preset"
    )

    app.session_state["analysis_result"] = {"sentinel": True}
    app.sidebar.selectbox(key="portfolio_workspace_preset_selector").select(
        "혼합"
    ).run()
    assert [asset["Code"] for asset in app.session_state["korean_selected_assets"]] == [
        "005930",
        "069500",
    ]
    assert app.session_state["korean_selected_benchmark_assets"] == []
    assert "analysis_result" not in app.session_state.filtered_state

    app.sidebar.number_input(key="korean_weight_005930").set_value(65.0).run()
    app.run()
    assert app.session_state["korean_weight_005930"] == 65.0

    app.sidebar.selectbox(key="benchmark_workspace_preset_selector").select(
        "혼합"
    ).run()
    assert [
        asset["Code"]
        for asset in app.session_state["korean_selected_benchmark_assets"]
    ] == ["005930", "069500"]
    assert app.session_state["korean_weight_005930"] == 65.0

    sidebar_nodes = list(app.sidebar)
    keyed_positions = {
        node.key: index
        for index, node in enumerate(sidebar_nodes)
        if node.key is not None
    }
    assert keyed_positions["portfolio_workspace_preset_selector"] < keyed_positions[
        "korean_weight_005930"
    ]
    assert keyed_positions["benchmark_workspace_preset_selector"] < keyed_positions[
        "korean_benchmark_weight_005930"
    ]
    caption_positions = {
        getattr(node, "value", None): index
        for index, node in enumerate(sidebar_nodes)
        if getattr(node, "type", None) == "caption"
    }
    assert caption_positions["현재 비중 합계: 95%"] < keyed_positions[
        "korean_weight_005930"
    ]
    assert caption_positions["현재 비중 합계: 100%"] < keyed_positions[
        "korean_benchmark_weight_005930"
    ]


def test_new_workspace_clears_one_side_and_last_session(monkeypatch, tmp_path):
    records = sample_records()
    app, store = start_app(
        monkeypatch,
        tmp_path,
        presets={"혼합": records},
        portfolio=records,
        benchmark=records,
    )

    app.sidebar.button(key="portfolio_workspace_new_workspace").click().run()

    assert app.session_state["korean_selected_assets"] == []
    assert app.session_state["portfolio_workspace_active_preset"] is None
    assert [
        asset["Code"]
        for asset in app.session_state["korean_selected_benchmark_assets"]
    ] == ["005930", "069500"]
    document = store.load()
    assert document["presets"]["혼합"] == records
    assert document["last_session"]["portfolio"] == []
    assert document["last_session"]["benchmark"] == records

    app.sidebar.button(key="benchmark_workspace_new_workspace").click().run()
    assert app.session_state["korean_selected_benchmark_assets"] == []
    assert store.load()["presets"]["혼합"] == records


def test_save_save_as_and_delete_preserve_expected_workspace_state(
    monkeypatch, tmp_path
):
    records = sample_records()
    app, store = start_app(monkeypatch, tmp_path, portfolio=records)

    assert "portfolio_workspace_preset_name" not in {
        widget.key for widget in app.sidebar.text_input
    }
    app.sidebar.button(key="portfolio_workspace_save").click().run()
    app.sidebar.text_input(key="portfolio_workspace_preset_name").input("원본").run()
    app.sidebar.button(key="portfolio_workspace_confirm_name").click().run()
    assert store.load()["presets"]["원본"] == records

    app.sidebar.number_input(key="korean_weight_005930").set_value(60.0).run()
    app.sidebar.number_input(key="korean_weight_069500").set_value(40.0).run()
    app.sidebar.button(key="portfolio_workspace_save").click().run()
    assert [
        record["Weight"] for record in store.load()["presets"]["원본"]
    ] == [60.0, 40.0]

    app.sidebar.number_input(key="korean_weight_005930").set_value(55.0).run()
    app.sidebar.number_input(key="korean_weight_069500").set_value(45.0).run()
    app.sidebar.button(key="portfolio_workspace_save_as").click().run()
    app.sidebar.text_input(key="portfolio_workspace_preset_name").input("복제").run()
    app.sidebar.button(key="portfolio_workspace_confirm_name").click().run()

    document = store.load()
    assert [record["Weight"] for record in document["presets"]["원본"]] == [60.0, 40.0]
    assert [record["Weight"] for record in document["presets"]["복제"]] == (
        pytest.approx([55.0, 45.0])
    )
    assert app.session_state["portfolio_workspace_active_preset"] == "복제"

    app.sidebar.selectbox(key="preset_delete_selector").select("복제").run()
    app.sidebar.button(key="delete_named_preset").click().run()
    assert "복제" not in store.load()["presets"]
    assert app.session_state["portfolio_workspace_active_preset"] is None
    assert [asset["Code"] for asset in app.session_state["korean_selected_assets"]] == [
        "005930",
        "069500",
    ]
    assert app.session_state["korean_weight_005930"] == 55.0
    assert app.session_state["korean_weight_069500"] == 45.0


def test_unified_search_direct_adds_codes_and_keeps_name_selection_flow(
    monkeypatch, tmp_path
):
    app, _ = start_app(monkeypatch, tmp_path)

    assert all(
        checkbox.label != "검색 장애 시 국내 종목코드 빠른 입력 사용"
        for checkbox in app.sidebar.checkbox
    )
    analyze_buttons = [button for button in app.sidebar.button if button.label == "분석"]
    assert len(analyze_buttons) == 1
    sidebar_nodes = list(app.sidebar)
    title_position = next(
        index
        for index, node in enumerate(sidebar_nodes)
        if node.type == "title" and node.value == "Portfolio Analyzer"
    )
    analyze_position = sidebar_nodes.index(analyze_buttons[0])
    portfolio_header_position = next(
        index
        for index, node in enumerate(sidebar_nodes)
        if node.type == "header" and node.value == "Portfolio"
    )
    assert title_position < analyze_position < portfolio_header_position

    app.sidebar.text_input(key="portfolio_security_query_0").input("005930").run()
    app.sidebar.button(key="portfolio_security_search").click().run()
    assert [asset["Code"] for asset in app.session_state["korean_selected_assets"]] == [
        "005930"
    ]

    app.sidebar.text_input(key="portfolio_security_query_1").input(
        "005930,069500,0137v0,005930"
    ).run()
    app.sidebar.button(key="portfolio_security_search").click().run()
    assert [asset["Code"] for asset in app.session_state["korean_selected_assets"]] == [
        "005930",
        "069500",
        "0137V0",
    ]

    app.sidebar.text_input(key="benchmark_security_query_0").input(
        "069500,0137v0"
    ).run()
    app.sidebar.button(key="benchmark_security_search").click().run()
    assert [
        asset["Code"]
        for asset in app.session_state["korean_selected_benchmark_assets"]
    ] == ["069500", "0137V0"]

    app.sidebar.text_input(key="portfolio_security_query_2").input("NAVER").run()
    search_button = app.sidebar.button(key="portfolio_security_search")
    add_button = app.sidebar.button(key="portfolio_security_add")
    sidebar_keys = [node.key for node in app.sidebar if node.key is not None]
    assert sidebar_keys.index(search_button.key) < sidebar_keys.index(add_button.key)
    search_button.click().run()
    results = next(
        frame
        for frame in app.sidebar.dataframe
        if frame.key == "portfolio_security_results_table"
    )
    assert results.value.columns.tolist() == ["Code", "Name", "Type"]
    column_config = json.loads(results.proto.columns)
    assert column_config["Code"]["width"] == 50
    assert column_config["Name"]["width"] == 90
    assert column_config["Type"]["width"] == 50
    assert app.session_state["korean_selected_assets"][0]["Market"] == "KOSPI"
    app.sidebar.button(key="portfolio_security_add").click().run()
    assert any(
        "검색 결과 표에서 한 행을 먼저 선택하세요" in warning.value
        for warning in app.sidebar.warning
    )


def test_preset_import_round_trip_overwrite_and_malformed_error(monkeypatch, tmp_path):
    records = sample_records()
    app, store = start_app(monkeypatch, tmp_path, presets={"원본": records})

    assert app.sidebar.button(key="delete_named_preset").label == "Delete"
    assert app.sidebar.download_button(key="export_named_preset").label == "Export"
    assert app.sidebar.file_uploader(key="preset_import_file").label == "Import"

    imported = export_preset_json("가져옴", records)
    app.sidebar.file_uploader(key="preset_import_file").set_value(
        ("가져옴.portfolio.json", imported, "application/json")
    ).run()
    assert store.load()["presets"]["가져옴"] == records
    assert app.session_state["korean_selected_assets"] == []
    assert "analysis_result" not in app.session_state.filtered_state

    replacement = sample_records()
    replacement[0]["Weight"] = 60.0
    replacement[1]["Weight"] = 40.0
    app.sidebar.file_uploader(key="preset_import_file").set_value(
        (
            "가져옴.portfolio.json",
            export_preset_json("가져옴", replacement),
            "application/json",
        )
    ).run()
    assert store.load()["presets"]["가져옴"] == replacement

    app.sidebar.file_uploader(key="preset_import_file").set_value(
        ("broken.json", b"{broken", "application/json")
    ).run()
    assert not app.exception
    assert any("손상" in error.value for error in app.sidebar.error)


def test_direct_code_falls_back_without_catalog_or_extra_guidance(
    monkeypatch, tmp_path
):
    app, _ = start_app(monkeypatch, tmp_path, catalog_error=True)

    app.sidebar.text_input(key="portfolio_security_query_0").input("0172v0").run()
    app.sidebar.button(key="portfolio_security_search").click().run()

    assert app.session_state["korean_selected_assets"] == [
        {
            "Code": "0172V0",
            "Name": "0172V0",
            "Type": "직접 입력",
            "Market": "KRX",
        }
    ]
    assert not app.sidebar.error
    assert all(
        "직접 입력" not in caption.value and "빠른 입력" not in caption.value
        for caption in app.sidebar.caption
    )


def test_top_analysis_button_runs_existing_analysis_flow(monkeypatch, tmp_path):
    records = sample_records()

    def fake_prices(loader):
        index = pd.date_range("2025-01-02", periods=40, freq="B")
        return pd.DataFrame(
            {
                ticker: np.linspace(100.0 + offset, 120.0 + offset, len(index))
                for offset, ticker in enumerate(loader.tickers)
            },
            index=index,
        )

    monkeypatch.setattr(KoreanDataLoader, "fetch_data", fake_prices)
    app, _ = start_app(monkeypatch, tmp_path, portfolio=records)

    app.sidebar.button(key="analyze_portfolio").click().run(timeout=20)

    assert not app.exception
    assert app.session_state["analysis_result"]["tickers"] == ["005930", "069500"]
