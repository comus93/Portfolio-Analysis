"""Streamlit portfolio analyzer with Yahoo and Korean market data support."""

import hashlib
from datetime import datetime, timedelta
from functools import partial

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from portfolio_analysis import (
    BenchmarkComparison,
    DataLoader,
    KoreanDataLoader,
    KoreanSecurityDirectory,
    MonteCarloSimulation,
    PortfolioAnalysis,
    PortfolioAnalysisError,
    PortfolioOptimizer,
)
from portfolio_analysis.data.korean import is_valid_korean_ticker
from portfolio_analysis.local_portfolios import (
    LocalPortfolioStore,
    LocalPortfolioStoreError,
    export_preset_json,
    import_preset_json,
    make_asset_records,
    preset_export_filename,
    split_asset_records,
)

st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=3600)
def fetch_market_data(
    market: str, tickers: tuple[str, ...], start_date: str, end_date: str
) -> pd.DataFrame:
    """Fetch aligned price data through the selected market provider."""
    if market == "Korea (FinanceDataReader)":
        return KoreanDataLoader(list(tickers), start_date, end_date).fetch_data()
    return DataLoader(list(tickers), start_date, end_date).fetch_data(progress=False)


@st.cache_data(ttl=86400)
def fetch_korean_security_catalog() -> pd.DataFrame:
    """Fetch Korean stock/ETF/ETN metadata independently of price data."""
    return KoreanSecurityDirectory().fetch_catalog()


def reset_korean_security_search(prefix: str) -> None:
    """Clear search widgets and results after an explicit add action."""
    st.session_state.pop(f"{prefix}_results", None)
    st.session_state.pop(f"{prefix}_selected_row", None)
    st.session_state[f"{prefix}_query_version"] = (
        st.session_state.get(f"{prefix}_query_version", 0) + 1
    )


def capture_korean_security_selection(prefix: str) -> None:
    """Preserve a selected result across the separate form-submit rerun."""
    selection_state = st.session_state.get(f"{prefix}_results_table", {})
    rows = selection_state.get("selection", {}).get("rows", [])
    if rows:
        st.session_state[f"{prefix}_selected_row"] = rows[0]
    else:
        st.session_state.pop(f"{prefix}_selected_row", None)


def parse_direct_code_query(query: str) -> list[str] | None:
    """Return normalized unique codes only when every comma token is valid."""
    tokens = [token.strip().upper() for token in query.split(",")]
    if not tokens or any(not token for token in tokens):
        return None
    if not all(is_valid_korean_ticker(token) for token in tokens):
        return None
    return list(dict.fromkeys(tokens))


def resolve_direct_code_assets(codes: list[str]) -> list[dict]:
    """Enrich direct codes from the catalog while retaining an offline fallback."""
    try:
        catalog = fetch_korean_security_catalog()
        records_by_code = {
            record["Code"]: record
            for record in catalog.to_dict("records")
            if record["Code"] in codes
        }
    except Exception:
        records_by_code = {}
    return [
        records_by_code.get(
            code,
            {
                "Code": code,
                "Name": code,
                "Type": "직접 입력",
                "Market": "KRX",
            },
        )
        for code in codes
    ]


def render_korean_security_search(prefix: str, title: str) -> list[dict]:
    """Render unified name search and direct code add controls."""
    st.markdown(f"**{title}**")
    st.session_state.setdefault(f"{prefix}_query_version", 0)
    query_key = f"{prefix}_query_{st.session_state[f'{prefix}_query_version']}"

    query = st.text_input(
        "종목코드 또는 종목명",
        key=query_key,
        placeholder="예: 005930, 삼성전자, KODEX 200",
    )
    with st.container(horizontal=True):
        search_submitted = st.button(
            "검색", key=f"{prefix}_search", icon=":material/search:"
        )
        add_submitted = st.button(
            "추가", key=f"{prefix}_add", icon=":material/add:"
        )
    st.space("small")

    if search_submitted or add_submitted:
        direct_codes = parse_direct_code_query(query)
        if direct_codes is not None:
            return resolve_direct_code_assets(direct_codes)
    if search_submitted:
        st.session_state.pop(f"{prefix}_selected_row", None)
        try:
            catalog = fetch_korean_security_catalog()
            results = KoreanSecurityDirectory.search_catalog(catalog, query)
            st.session_state[f"{prefix}_results"] = results.to_dict("records")
            warnings = catalog.attrs.get("warnings", [])
            if warnings:
                st.warning(
                    "일부 종목 목록을 불러오지 못했습니다: " + "; ".join(warnings)
                )
        except Exception as exc:
            st.session_state[f"{prefix}_results"] = []
            st.error(f"종목 검색을 사용할 수 없습니다: {exc}")

    records = st.session_state.get(f"{prefix}_results", [])
    if not records:
        if add_submitted:
            st.warning("검색 결과 표에서 한 행을 먼저 선택하세요.")
        if query and f"{prefix}_results" in st.session_state:
            st.info("검색 결과가 없습니다.")
        return []

    results = pd.DataFrame(records)
    event = st.dataframe(
        results[["Code", "Name", "Type"]],
        hide_index=True,
        key=f"{prefix}_results_table",
        on_select=partial(capture_korean_security_selection, prefix),
        selection_mode="single-row",
        column_config={
            "Code": st.column_config.TextColumn(width=50),
            "Name": st.column_config.TextColumn(width=90),
            "Type": st.column_config.TextColumn(width=50),
        },
    )

    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        st.session_state[f"{prefix}_selected_row"] = selected_rows[0]
    if add_submitted:
        selected_row = st.session_state.get(f"{prefix}_selected_row")
        if not isinstance(selected_row, int) or not 0 <= selected_row < len(records):
            st.warning("검색 결과 표에서 한 행을 먼저 선택하세요.")
            return []
        return [records[selected_row]]
    return []


def remove_korean_asset(list_key: str, weight_prefix: str, code: str) -> None:
    """Remove an asset and normalize the remaining percentage weights."""
    selected_assets = st.session_state.get(list_key, [])
    remaining = [asset for asset in selected_assets if asset["Code"] != code]
    st.session_state[list_key] = remaining
    st.session_state.pop(f"{weight_prefix}_{code}", None)

    if not remaining:
        return
    values = np.array(
        [
            float(st.session_state.get(f"{weight_prefix}_{asset['Code']}", 0.0))
            for asset in remaining
        ]
    )
    if np.isclose(values.sum(), 0.0):
        values = np.full(len(remaining), 100.0 / len(remaining))
    else:
        values = values / values.sum() * 100.0
    for asset, value in zip(remaining, values):
        st.session_state[f"{weight_prefix}_{asset['Code']}"] = float(value)


def add_korean_asset(list_key: str, asset: dict) -> bool:
    """Add an asset only when it is not already present."""
    selected_assets = st.session_state.setdefault(list_key, [])
    if any(selected["Code"] == asset["Code"] for selected in selected_assets):
        return False
    selected_assets.append(asset)
    return True


def add_korean_assets(list_key: str, assets: list[dict]) -> int:
    """Add unique securities in input order and return the number added."""
    return sum(add_korean_asset(list_key, asset) for asset in assets)


def render_selected_assets(
    title: str,
    list_key: str,
    weight_prefix: str,
    empty_message: str,
) -> tuple[list[dict], np.ndarray]:
    """Render selected Korean securities with editable percentage weights."""
    selected_assets = st.session_state.setdefault(list_key, [])
    st.sidebar.subheader(title)
    st.sidebar.caption("각 종목 오른쪽에 비중(%)을 입력하고 ✕로 삭제합니다.")
    weight_percentages: list[float] = []
    if not selected_assets:
        st.sidebar.info(empty_message)

    for asset in selected_assets:
        label_column, weight_column, remove_column = st.sidebar.columns([5, 3, 1])
        label_column.markdown(
            f"**{asset['Code']}**  \n{asset['Name']} · {asset['Type']}"
        )
        weight_key = f"{weight_prefix}_{asset['Code']}"
        weight_default = (
            {"value": 100.0 if len(selected_assets) == 1 else 0.0}
            if weight_key not in st.session_state
            else {}
        )
        weight_percentages.append(
            weight_column.number_input(
                "비중 %",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key=weight_key,
                label_visibility="collapsed",
                **weight_default,
            )
        )
        remove_column.button(
            "✕",
            key=f"remove_{list_key}_{asset['Code']}",
            on_click=remove_korean_asset,
            args=(list_key, weight_prefix, asset["Code"]),
        )

    return selected_assets, np.array(weight_percentages, dtype=float) / 100.0


def validate_analysis_inputs(
    tickers: list[str],
    weights: np.ndarray,
    benchmark_tickers: list[str],
    benchmark_weights: np.ndarray,
    start_date,
    end_date,
) -> None:
    """Validate user inputs only when the analysis button is pressed."""
    if start_date >= end_date:
        raise ValueError("Start date must be earlier than end date.")
    if not tickers:
        raise ValueError("포트폴리오 종목을 하나 이상 추가하세요.")
    if not np.isclose(weights.sum(), 1.0):
        raise ValueError(
            f"포트폴리오 비중 합계가 100%여야 합니다 (현재 {weights.sum():.1%})."
        )
    invalid = [ticker for ticker in tickers if not is_valid_korean_ticker(ticker)]
    if invalid:
        raise ValueError("올바르지 않은 국내 종목코드입니다: " + ", ".join(invalid))
    if benchmark_tickers and not np.isclose(benchmark_weights.sum(), 1.0):
        raise ValueError(
            f"Benchmark 비중 합계가 100%여야 합니다 (현재 {benchmark_weights.sum():.1%})."
        )
    invalid_benchmarks = [
        ticker
        for ticker in benchmark_tickers
        if not is_valid_korean_ticker(ticker)
    ]
    if invalid_benchmarks:
        raise ValueError(
            "올바르지 않은 국내 Benchmark 종목코드입니다: "
            + ", ".join(invalid_benchmarks)
        )


def build_display_labels(tickers: list[str], display_names: dict[str, str]) -> dict:
    """Create code plus name labels with code-only fallback."""
    return {
        ticker: (
            f"{ticker} · {display_names[ticker]}" if ticker in display_names else ticker
        )
        for ticker in tickers
    }


def optimization_result(optimizer: PortfolioOptimizer, strategy: str) -> dict:
    """Run one of the existing optimization strategies."""
    methods = {
        "Maximum Sharpe": optimizer.optimize_max_sharpe,
        "Minimum Volatility": optimizer.optimize_min_volatility,
        "Risk Parity": optimizer.optimize_risk_parity,
    }
    return methods[strategy]()


def apply_saved_composition(
    records: list[dict], list_key: str, weight_prefix: str
) -> None:
    """Copy a stored composition into editable Streamlit session state."""
    assets, weights = split_asset_records(records)
    for key in list(st.session_state):
        if key.startswith(f"{weight_prefix}_"):
            del st.session_state[key]
    st.session_state[list_key] = assets
    for asset, weight in zip(assets, weights):
        st.session_state[f"{weight_prefix}_{asset['Code']}"] = weight * 100.0
    # A load changes inputs only. It must never reuse or run an old analysis.
    st.session_state.pop("analysis_result", None)


def current_composition(list_key: str, weight_prefix: str) -> list[dict]:
    """Build persistable records from the current editable selection."""
    assets = st.session_state.get(list_key, [])
    default_weight = 100.0 if len(assets) == 1 else 0.0
    weights = [
        float(
            st.session_state.get(
                f"{weight_prefix}_{asset['Code']}", default_weight
            )
        )
        / 100.0
        for asset in assets
    ]
    return make_asset_records(assets, weights)


NO_PRESET = "Preset 선택 안 함"


def workspace_weight_total(list_key: str, weight_prefix: str) -> float:
    """Return the current percentage total before rendering the asset list."""
    assets = st.session_state.get(list_key, [])
    values = [
        float(
            st.session_state.get(
                f"{weight_prefix}_{asset['Code']}",
                100.0 if len(assets) == 1 else 0.0,
            )
        )
        for asset in assets
    ]
    return round(sum(values), 2)


def select_workspace_preset(
    presets: dict,
    selector_key: str,
    active_key: str,
    list_key: str,
    weight_prefix: str,
    target: str,
) -> None:
    """Load a preset only when a workspace selector actually changes."""
    selected_name = st.session_state[selector_key]
    if selected_name == NO_PRESET:
        st.session_state[active_key] = None
        return
    records = presets.get(selected_name)
    if records is None:
        st.session_state[active_key] = None
        st.session_state[selector_key] = NO_PRESET
        st.session_state["korean_last_error"] = (
            f"'{selected_name}' Preset을 찾을 수 없습니다."
        )
        return
    apply_saved_composition(records, list_key, weight_prefix)
    st.session_state[active_key] = selected_name
    st.session_state["korean_last_message"] = (
        f"'{selected_name}' Preset을 {target}에 불러왔습니다."
    )


def clear_workspace(
    list_key: str,
    weight_prefix: str,
    search_prefix: str,
    active_key: str,
    selector_key: str,
) -> None:
    """Clear one editable workspace without deleting any named preset."""
    apply_saved_composition([], list_key, weight_prefix)
    for key in list(st.session_state):
        if search_prefix in key:
            del st.session_state[key]
    st.session_state[active_key] = None
    st.session_state[selector_key] = NO_PRESET


def request_preset_name(mode_key: str, mode: str) -> None:
    """Reveal the compact name input for a new preset or Save As."""
    st.session_state[mode_key] = mode


def cancel_preset_name(mode_key: str, name_key: str) -> None:
    """Close a pending naming flow."""
    st.session_state[mode_key] = None
    st.session_state[name_key] = ""


def save_named_workspace(
    store: LocalPortfolioStore,
    records: list[dict] | None,
    name_key: str,
    mode_key: str,
    active_key: str,
    selector_key: str,
) -> None:
    """Save a workspace under a requested name and make it active."""
    try:
        if records is None:
            raise ValueError(
                "종목코드와 비중을 올바르게 입력한 뒤 저장하세요."
            )
        name = st.session_state.get(name_key, "").strip()
        store.save_preset(name, records)
        st.session_state[active_key] = name
        st.session_state[selector_key] = name
        st.session_state[mode_key] = None
        st.session_state[name_key] = ""
        st.session_state["korean_last_message"] = f"'{name}' Preset을 저장했습니다."
    except (LocalPortfolioStoreError, ValueError) as exc:
        st.session_state["korean_last_error"] = str(exc)


def render_workspace_preset_controls(
    store: LocalPortfolioStore,
    document: dict,
    target: str,
    records: list[dict] | None,
    total_percentage: float,
    list_key: str,
    weight_prefix: str,
    search_prefix: str,
    state_prefix: str,
) -> None:
    """Render one workspace's shared-library preset controls above its assets."""
    active_key = f"{state_prefix}_active_preset"
    selector_key = f"{state_prefix}_preset_selector"
    mode_key = f"{state_prefix}_preset_name_mode"
    name_key = f"{state_prefix}_preset_name"
    preset_names = sorted(document["presets"])

    active_name = st.session_state.setdefault(active_key, None)
    if active_name not in preset_names:
        st.session_state[active_key] = None
        active_name = None
    options = [NO_PRESET, *preset_names]
    current_selector = st.session_state.get(selector_key)
    if current_selector not in options:
        st.session_state[selector_key] = active_name or NO_PRESET

    st.sidebar.selectbox(
        f"{target} Preset",
        options,
        key=selector_key,
        on_change=select_workspace_preset,
        args=(
            document["presets"],
            selector_key,
            active_key,
            list_key,
            weight_prefix,
            target,
        ),
    )

    with st.sidebar.container(horizontal=True):
        st.button(
            "새 구성",
            key=f"{state_prefix}_new_workspace",
            on_click=clear_workspace,
            args=(
                list_key,
                weight_prefix,
                search_prefix,
                active_key,
                selector_key,
            ),
        )
        if st.button("저장", key=f"{state_prefix}_save"):
            active_name = st.session_state.get(active_key)
            if active_name:
                try:
                    if records is None:
                        raise ValueError(
                            "종목코드와 비중을 올바르게 입력한 뒤 저장하세요."
                        )
                    store.save_preset(active_name, records)
                    st.session_state["korean_last_message"] = (
                        f"'{active_name}' Preset을 갱신했습니다."
                    )
                    st.rerun()
                except (LocalPortfolioStoreError, ValueError) as exc:
                    st.error(str(exc))
            else:
                request_preset_name(mode_key, "new")
    st.sidebar.button(
        "다른 이름으로 저장",
        key=f"{state_prefix}_save_as",
        width="stretch",
        on_click=request_preset_name,
        args=(mode_key, "save_as"),
    )

    if st.session_state.get(mode_key):
        prompt = (
            "새 Preset 이름"
            if st.session_state[mode_key] == "new"
            else "다른 이름으로 저장"
        )
        st.sidebar.text_input(prompt, key=name_key, placeholder="Preset 이름")
        with st.sidebar.container(horizontal=True):
            st.button(
                "확인",
                key=f"{state_prefix}_confirm_name",
                type="primary",
                on_click=save_named_workspace,
                args=(
                    store,
                    records,
                    name_key,
                    mode_key,
                    active_key,
                    selector_key,
                ),
            )
            st.button(
                "취소",
                key=f"{state_prefix}_cancel_name",
                on_click=cancel_preset_name,
                args=(mode_key, name_key),
            )

    st.sidebar.caption(f"현재 비중 합계: {total_percentage:g}%")


def delete_named_preset(
    store: LocalPortfolioStore, name: str, workspace_prefixes: tuple[str, ...]
) -> None:
    """Delete a preset and detach workspaces while preserving their contents."""
    try:
        if store.delete_preset(name):
            for prefix in workspace_prefixes:
                active_key = f"{prefix}_active_preset"
                if st.session_state.get(active_key) == name:
                    st.session_state[active_key] = None
                    st.session_state[f"{prefix}_preset_selector"] = NO_PRESET
            st.session_state["korean_last_message"] = (
                f"'{name}' Preset을 삭제했습니다. 현재 구성은 유지됩니다."
            )
    except LocalPortfolioStoreError as exc:
        st.session_state["korean_last_error"] = str(exc)


def render_preset_library_management(
    store: LocalPortfolioStore, document: dict
) -> None:
    """Render lower-priority delete, export, and import preset actions."""
    with st.sidebar.expander("Preset 관리", expanded=False):
        preset_names = sorted(document["presets"])
        selected_name = (
            st.selectbox("Preset", preset_names, key="preset_delete_selector")
            if preset_names
            else None
        )
        if selected_name is None:
            st.caption("저장된 Preset이 없습니다.")

        export_data = (
            export_preset_json(selected_name, document["presets"][selected_name])
            if selected_name is not None
            else b""
        )
        with st.container(horizontal=True):
            st.button(
                "Delete",
                key="delete_named_preset",
                disabled=selected_name is None,
                on_click=delete_named_preset,
                args=(
                    store,
                    selected_name or "",
                    ("portfolio_workspace", "benchmark_workspace"),
                ),
            )
            st.download_button(
                "Export",
                export_data,
                file_name=(
                    preset_export_filename(selected_name)
                    if selected_name is not None
                    else "portfolio.portfolio.json"
                ),
                mime="application/json",
                key="export_named_preset",
                disabled=selected_name is None,
                on_click="ignore",
            )

        uploaded = st.file_uploader(
            "Import", type="json", key="preset_import_file", max_upload_size=1
        )
        if uploaded is None:
            st.session_state.pop("preset_import_digest", None)
            st.session_state.pop("preset_import_error", None)
        else:
            uploaded_data = uploaded.getvalue()
            digest = hashlib.sha256(uploaded_data).hexdigest()
            if st.session_state.get("preset_import_digest") != digest:
                st.session_state["preset_import_digest"] = digest
                try:
                    name, records = import_preset_json(uploaded_data)
                    store.save_preset(name, records)
                    st.session_state.pop("preset_import_error", None)
                    st.session_state["korean_last_message"] = (
                        f"'{name}' Preset을 Import했습니다."
                    )
                    st.rerun()
                except (LocalPortfolioStoreError, ValueError) as exc:
                    st.session_state["preset_import_error"] = str(exc)
            import_error = st.session_state.get("preset_import_error")
            if import_error:
                st.error(import_error)


st.sidebar.title("Portfolio Analyzer")
analyze_requested = st.sidebar.button(
    "분석",
    key="analyze_portfolio",
    type="primary",
    icon=":material/analytics:",
    width="stretch",
)
market = "Korea (FinanceDataReader)"
portfolio_store = LocalPortfolioStore()
store_available = True
try:
    store_document = portfolio_store.load()
except LocalPortfolioStoreError as exc:
    store_available = False
    store_document = {
        "version": 1,
        "presets": {},
        "last_session": {"portfolio": [], "benchmark": []},
    }
    st.sidebar.warning(str(exc))

st.session_state.setdefault("korean_selected_assets", [])
st.session_state.setdefault("korean_selected_benchmark_assets", [])
if "local_workspace_restored" not in st.session_state:
    apply_saved_composition(
        store_document["last_session"]["portfolio"],
        "korean_selected_assets",
        "korean_weight",
    )
    apply_saved_composition(
        store_document["last_session"]["benchmark"],
        "korean_selected_benchmark_assets",
        "korean_benchmark_weight",
    )
    st.session_state["local_workspace_restored"] = True

last_message = st.session_state.pop("korean_last_message", None)
if last_message:
    st.sidebar.success(last_message)
last_error = st.session_state.pop("korean_last_error", None)
if last_error:
    st.sidebar.error(last_error)

st.sidebar.header("Portfolio")
persistable_portfolio = current_composition(
    "korean_selected_assets", "korean_weight"
)
if store_available:
    render_workspace_preset_controls(
        portfolio_store,
        store_document,
        "Portfolio",
        persistable_portfolio,
        workspace_weight_total("korean_selected_assets", "korean_weight"),
        "korean_selected_assets",
        "korean_weight",
        "portfolio_security",
        "portfolio_workspace",
    )
else:
    st.sidebar.caption(
        "현재 비중 합계: "
        f"{workspace_weight_total('korean_selected_assets', 'korean_weight'):g}%"
    )
with st.sidebar.expander("포트폴리오 종목 검색·추가", expanded=True):
    selected_securities = render_korean_security_search(
        "portfolio_security", "국내 주식/ETF/ETN 검색"
    )
    if selected_securities:
        if add_korean_assets("korean_selected_assets", selected_securities):
            reset_korean_security_search("portfolio_security")
            st.rerun()
        st.warning("이미 포트폴리오에 추가된 종목입니다.")

selected_assets, weights = render_selected_assets(
    "선택된 포트폴리오 종목",
    "korean_selected_assets",
    "korean_weight",
    "검색 결과에서 종목을 선택하고 '추가'를 누르세요.",
)

st.sidebar.header("Benchmark")
persistable_benchmark = current_composition(
    "korean_selected_benchmark_assets", "korean_benchmark_weight"
)
if store_available:
    render_workspace_preset_controls(
        portfolio_store,
        store_document,
        "Benchmark",
        persistable_benchmark,
        workspace_weight_total(
            "korean_selected_benchmark_assets", "korean_benchmark_weight"
        ),
        "korean_selected_benchmark_assets",
        "korean_benchmark_weight",
        "benchmark_security",
        "benchmark_workspace",
    )
else:
    st.sidebar.caption(
        "현재 비중 합계: "
        f"{workspace_weight_total('korean_selected_benchmark_assets', 'korean_benchmark_weight'):g}%"
    )
with st.sidebar.expander("Benchmark 검색·추가", expanded=True):
    selected_benchmarks = render_korean_security_search(
        "benchmark_security", "국내 Benchmark 검색"
    )
    if selected_benchmarks:
        if add_korean_assets(
            "korean_selected_benchmark_assets", selected_benchmarks
        ):
            reset_korean_security_search("benchmark_security")
            st.rerun()
        st.warning("이미 Benchmark에 추가된 종목입니다.")

benchmark_assets, benchmark_weights = render_selected_assets(
    "선택된 Benchmark 종목",
    "korean_selected_benchmark_assets",
    "korean_benchmark_weight",
    "Benchmark가 없으면 비교 없이 분석합니다.",
)

tickers = [asset["Code"] for asset in selected_assets]
benchmark_tickers = [asset["Code"] for asset in benchmark_assets]
display_names = {asset["Code"]: asset["Name"] for asset in selected_assets}
benchmark_display_names = {
    asset["Code"]: asset["Name"] for asset in benchmark_assets
}
persistable_portfolio = current_composition(
    "korean_selected_assets", "korean_weight"
)
persistable_benchmark = current_composition(
    "korean_selected_benchmark_assets", "korean_benchmark_weight"
)

if store_available:
    render_preset_library_management(portfolio_store, store_document)
    try:
        current_session = {
            "portfolio": persistable_portfolio,
            "benchmark": persistable_benchmark,
        }
        if None not in current_session.values() and (
            store_document["last_session"] != current_session
        ):
            portfolio_store.save_last_session(
                persistable_portfolio, persistable_benchmark
            )
    except (LocalPortfolioStoreError, ValueError) as exc:
        st.sidebar.warning(str(exc))

st.sidebar.header("Analysis period")
date_columns = st.sidebar.columns(2)
with date_columns[0]:
    start_date = st.date_input("Start", datetime.now() - timedelta(days=3 * 365))
with date_columns[1]:
    end_date = st.date_input("End", datetime.now())

risk_free_rate = st.sidebar.slider(
    "Risk-free rate", 0.0, 0.10, 0.03, 0.005, format="%.1f%%"
)
st.sidebar.caption("Weights may sum to 1.0 or 100. Not investment advice.")

st.title("Portfolio Analyzer")
st.caption(f"Provider: {market} · {start_date} to {end_date}")

if analyze_requested:
    try:
        validate_analysis_inputs(
            tickers,
            weights,
            benchmark_tickers,
            benchmark_weights,
            start_date,
            end_date,
        )

        with st.spinner("Fetching and aligning market data..."):
            data = fetch_market_data(
                market,
                tuple(tickers),
                start_date.isoformat(),
                end_date.isoformat(),
            )
            if len(data) < 2:
                raise ValueError("At least two aligned price observations are required.")

            portfolio = PortfolioAnalysis(data, weights.tolist())
            metrics = portfolio.get_summary(risk_free_rate)
            optimizer = PortfolioOptimizer(data, risk_free_rate)
            benchmark_comparison = None
            benchmark_labels = build_display_labels(
                benchmark_tickers, benchmark_display_names
            )
            if benchmark_tickers:
                benchmark_data = fetch_market_data(
                    market,
                    tuple(benchmark_tickers),
                    start_date.isoformat(),
                    end_date.isoformat(),
                )
                benchmark_portfolio = PortfolioAnalysis(
                    benchmark_data, benchmark_weights.tolist()
                )
                benchmark_returns = benchmark_portfolio.calculate_portfolio_returns()
                benchmark_index = pd.concat(
                    [
                        pd.Series([1.0], index=[benchmark_data.index.min()]),
                        (1 + benchmark_returns).cumprod(),
                    ]
                )
                benchmark_comparison = BenchmarkComparison(
                    data,
                    weights.tolist(),
                    benchmark_ticker="Benchmark portfolio",
                    risk_free_rate=risk_free_rate,
                    benchmark_data=benchmark_index,
                )

        st.session_state["analysis_result"] = {
            "data": data,
            "tickers": tickers,
            "weights": weights,
            "portfolio": portfolio,
            "metrics": metrics,
            "optimizer": optimizer,
            "display_labels": build_display_labels(tickers, display_names),
            "display_names": display_names,
            "benchmark_tickers": benchmark_tickers,
            "benchmark_weights": benchmark_weights,
            "benchmark_labels": benchmark_labels,
            "benchmark_comparison": benchmark_comparison,
            "market": market,
            "start_date": start_date,
            "end_date": end_date,
            "risk_free_rate": risk_free_rate,
        }
        st.success("분석이 완료되었습니다.")
    except (PortfolioAnalysisError, ValueError) as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unexpected analysis error: {exc}")

analysis_result = st.session_state.get("analysis_result")
if analysis_result is None:
    st.info("포트폴리오 구성을 마친 뒤 사이드바의 '분석' 버튼을 누르세요.")
    st.stop()

data = analysis_result["data"]
tickers = analysis_result.get("tickers", list(data.columns))
weights = analysis_result["weights"]
portfolio = analysis_result["portfolio"]
metrics = analysis_result["metrics"]
optimizer = analysis_result["optimizer"]
display_labels = analysis_result["display_labels"]
display_names = analysis_result.get("display_names", {})
if not display_names:
    display_names = {
        ticker: (
            display_labels[ticker].removeprefix(f"{ticker} · ")
            if display_labels[ticker] != ticker
            else "-"
        )
        for ticker in tickers
    }
benchmark_tickers = analysis_result["benchmark_tickers"]
benchmark_weights = analysis_result["benchmark_weights"]
benchmark_labels = analysis_result["benchmark_labels"]
benchmark_comparison = analysis_result["benchmark_comparison"]
risk_free_rate = analysis_result["risk_free_rate"]

(
    performance_tab,
    correlation_tab,
    optimization_tab,
    benchmark_tab,
    monte_carlo_tab,
    about_tab,
) = st.tabs(
    [
        "📈 Performance",
        "🔗 Correlation",
        "⚖️ Optimization",
        "📊 Benchmark",
        "🎲 Monte Carlo",
        "ℹ️ About",
    ]
)

with performance_tab:
    st.header("Portfolio Performance")
    metric_columns = st.columns(5)
    metric_columns[0].metric("Annual Return", f"{metrics['annual_return']:.2%}")
    metric_columns[1].metric("Annual Volatility", f"{metrics['annual_volatility']:.2%}")
    metric_columns[2].metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    metric_columns[3].metric("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}")
    metric_columns[4].metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")

    allocation_column, return_column = st.columns([1, 2])
    with allocation_column:
        st.subheader("Allocation")
        allocation = px.pie(
            values=weights,
            names=[display_labels[ticker] for ticker in tickers],
            hole=0.4,
        )
        allocation.update_traces(
            showlegend=False,
            textinfo="percent",
            hovertemplate="%{label}<br>비중: %{percent}<extra></extra>",
        )
        allocation.update_layout(
            showlegend=False,
            height=380,
            margin=dict(t=20, b=20, l=0, r=0),
        )
        st.plotly_chart(allocation)
    with return_column:
        cumulative = portfolio.calculate_cumulative_returns()
        figure = px.line(
            x=cumulative.index,
            y=cumulative.values,
            labels={"x": "Date", "y": "Growth of 1"},
        )
        figure.update_traces(name="Portfolio", showlegend=True)
        st.plotly_chart(figure)

    allocation_frame = pd.DataFrame(
        {
            "Code": tickers,
            "Name": [display_names.get(ticker, "-") for ticker in tickers],
            "Weight (%)": weights * 100.0,
        }
    )
    st.subheader("Allocation details")
    st.dataframe(
        allocation_frame,
        hide_index=True,
        column_config={
            "Weight (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    st.subheader("Aligned Price Data")
    st.line_chart((data / data.iloc[0]).rename(columns=display_labels))

with correlation_tab:
    st.header("Daily Return Correlation Matrix")
    correlation = (
        data.pct_change()
        .dropna()
        .corr()
        .rename(index=display_labels, columns=display_labels)
    )
    heatmap = px.imshow(
        correlation,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu_r",
        aspect="auto",
    )
    st.plotly_chart(heatmap)
    st.dataframe(correlation.style.format("{:.3f}"))

with optimization_tab:
    st.header("Portfolio Optimization")
    strategy = st.selectbox(
        "Strategy", ["Maximum Sharpe", "Minimum Volatility", "Risk Parity"]
    )
    if st.button("Run optimization", type="primary"):
        try:
            result = optimization_result(optimizer, strategy)
            st.subheader(f"{strategy} Result")
            result_columns = st.columns(3)
            result_columns[0].metric("Expected Return", f"{result['return']:.2%}")
            result_columns[1].metric("Volatility", f"{result['volatility']:.2%}")
            result_columns[2].metric("Sharpe Ratio", f"{result['sharpe_ratio']:.2f}")
            weight_frame = pd.DataFrame.from_dict(
                result["weights"], orient="index", columns=["Weight"]
            )
            weight_frame = weight_frame.rename(index=display_labels)
            st.dataframe(weight_frame.style.format("{:.2%}"))

            st.subheader("Efficient Frontier")
            frontier = optimizer.generate_efficient_frontier(n_points=40)
            frontier_figure = px.line(
                frontier,
                x="volatility",
                y="return",
                labels={"volatility": "Annual Volatility", "return": "Annual Return"},
                markers=True,
            )
            frontier_figure.update_xaxes(tickformat=".1%")
            frontier_figure.update_yaxes(tickformat=".1%")
            st.plotly_chart(frontier_figure)
        except Exception as exc:
            st.error(f"Optimization failed: {exc}")

with benchmark_tab:
    st.header("Benchmark Comparison")
    if benchmark_comparison is None:
        st.info("Benchmark를 구성하지 않아 비교 없이 분석했습니다.")
    else:
        benchmark_frame = pd.DataFrame(
            {
                "Weight": benchmark_weights,
            },
            index=[benchmark_labels[ticker] for ticker in benchmark_tickers],
        )
        st.dataframe(benchmark_frame.style.format("{:.2%}"))
        comparison_metrics = benchmark_comparison.get_metrics()
        columns = st.columns(4)
        columns[0].metric("Beta", f"{comparison_metrics['beta']:.3f}")
        columns[1].metric("Alpha", f"{comparison_metrics['alpha']:.2%}")
        columns[2].metric(
            "Tracking Error", f"{comparison_metrics['tracking_error']:.2%}"
        )
        columns[3].metric(
            "Information Ratio",
            f"{comparison_metrics['information_ratio']:.3f}",
        )

        portfolio_cumulative = (1 + benchmark_comparison.portfolio_returns).cumprod()
        benchmark_cumulative = (1 + benchmark_comparison.benchmark_returns).cumprod()
        figure = go.Figure()
        figure.add_scatter(
            x=portfolio_cumulative.index,
            y=portfolio_cumulative,
            name="Portfolio",
        )
        figure.add_scatter(
            x=benchmark_cumulative.index,
            y=benchmark_cumulative,
            name="Benchmark portfolio",
        )
        figure.update_layout(xaxis_title="Date", yaxis_title="Growth of 1")
        st.plotly_chart(figure)

with monte_carlo_tab:
    st.header("Monte Carlo Simulation")
    simulations = st.slider("Simulations", 100, 5000, 1000, 100)
    horizon = st.slider("Trading-day horizon", 21, 1260, 252, 21)
    if st.button("Run simulation"):
        simulation = MonteCarloSimulation(
            data,
            weights.tolist(),
            num_simulations=simulations,
            time_horizon=horizon,
        )
        results = simulation.simulate()
        percentiles = np.percentile(results, [5, 50, 95], axis=0)
        figure = go.Figure()
        for values, name in zip(percentiles, ["5th", "Median", "95th"]):
            figure.add_scatter(y=values, mode="lines", name=name)
        figure.update_layout(xaxis_title="Trading Days", yaxis_title="Portfolio Value")
        st.plotly_chart(figure)

with about_tab:
    st.header("About")
    st.markdown(
        """
        This application reuses the project's portfolio analysis and optimization
        engines. FinanceDataReader supplies Korean-listed stock, ETF, and ETN prices
        using numeric or alphanumeric KRX security codes.

        Past performance does not guarantee future results. This tool is for
        educational use and is not investment advice.
        """
    )
