"""Focused AppTest coverage for the workspace-level preset UX."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from portfolio_analysis.local_portfolios import LocalPortfolioStore, make_asset_records

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


def start_app(monkeypatch, tmp_path, *, presets=None, portfolio=None, benchmark=None):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
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


def test_quick_input_hides_redundant_warning_and_shows_invalid_live_total(
    monkeypatch, tmp_path
):
    app, store = start_app(monkeypatch, tmp_path)

    app.sidebar.checkbox(key="korean_quick_input").check().run()
    app.sidebar.text_input(key="korean_weights").input("40, 40").run()

    assert "현재 비중 합계: 80%" in {
        caption.value for caption in app.sidebar.caption
    }
    assert all(
        "빠른 입력은 검색 결과 확인을 생략합니다" not in warning.value
        for warning in app.sidebar.warning
    )

    app.sidebar.button(key="portfolio_workspace_new_workspace").click().run()
    assert store.load()["last_session"]["portfolio"] == []
    assert store.load()["last_session"]["benchmark"]
