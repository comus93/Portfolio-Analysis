"""Streamlit portfolio analyzer with Yahoo and Korean market data support."""

from datetime import datetime, timedelta

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
    """Fetch Korean stock/ETF metadata independently of price data."""
    return KoreanSecurityDirectory().fetch_catalog()


def security_label(security: dict) -> str:
    """Format a security so code and name are always visible together."""
    return f"{security['Code']} · {security['Name']} · {security['Type']}"


def reset_korean_security_search(prefix: str) -> None:
    """Clear search widgets and results after an explicit add action."""
    st.session_state.pop(f"{prefix}_results", None)
    st.session_state[f"{prefix}_query_version"] = (
        st.session_state.get(f"{prefix}_query_version", 0) + 1
    )


def render_korean_security_search(prefix: str, title: str) -> dict | None:
    """Render search results with direct single-row selection and add button."""
    st.markdown(f"**{title}**")
    st.session_state.setdefault(f"{prefix}_query_version", 0)
    query_key = f"{prefix}_query_{st.session_state[f'{prefix}_query_version']}"

    with st.form(f"{prefix}_search_form", border=False):
        query = st.text_input(
            "종목코드 또는 종목명",
            key=query_key,
            placeholder="예: 005930, 삼성전자, KODEX 200",
        )
        submitted = st.form_submit_button("검색", icon=":material/search:")

    if submitted:
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
            st.caption("사이드바의 6자리 코드 빠른 입력을 사용할 수 있습니다.")

    records = st.session_state.get(f"{prefix}_results", [])
    if not records:
        if query and f"{prefix}_results" in st.session_state:
            st.info("검색 결과가 없습니다.")
        return None

    results = pd.DataFrame(records)
    event = st.dataframe(
        results[["Code", "Name", "Type", "Market"]],
        hide_index=True,
        key=f"{prefix}_results_table",
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows if event.selection else []
    selected_security = records[selected_rows[0]] if selected_rows else None
    if selected_security:
        st.success(f"선택됨: {security_label(selected_security)}")

    if st.button("추가", key=f"{prefix}_add", icon=":material/add:"):
        if selected_security is None:
            st.warning("검색 결과 표에서 한 행을 먼저 선택하세요.")
            return None
        return selected_security
    return None


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


def parse_portfolio(ticker_text: str, weight_text: str) -> tuple[list[str], np.ndarray]:
    """Parse ticker and weight inputs, accepting fractions or percentages."""
    tickers = [
        ticker.strip().upper() for ticker in ticker_text.split(",") if ticker.strip()
    ]
    weights = np.array(
        [float(weight.strip()) for weight in weight_text.split(",") if weight.strip()],
        dtype=float,
    )
    if not tickers:
        raise ValueError("Enter at least one ticker.")
    if len(tickers) != len(weights):
        raise ValueError("The number of tickers must match the number of weights.")
    if np.any(weights < 0):
        raise ValueError("Weights cannot be negative.")
    if np.isclose(weights.sum(), 100.0):
        weights = weights / 100.0
    if not np.isclose(weights.sum(), 1.0):
        raise ValueError(
            f"Weights must sum to 1.0 or 100 (currently {weights.sum():.4g})."
        )
    return tickers, weights


def resolve_korean_display_names(tickers: list[str]) -> dict[str, str]:
    """Resolve Korean security names once for the analysis run."""
    if not tickers:
        return {}
    try:
        catalog = fetch_korean_security_catalog()
    except Exception:
        return {}
    codes = set(tickers)
    matches = catalog[catalog["Code"].isin(codes)]
    return dict(zip(matches["Code"], matches["Name"]))


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
    invalid = [ticker for ticker in tickers if not ticker.isdigit() or len(ticker) != 6]
    if invalid:
        raise ValueError("국내 종목코드는 6자리 코드여야 합니다: " + ", ".join(invalid))
    if benchmark_tickers and not np.isclose(benchmark_weights.sum(), 1.0):
        raise ValueError(
            f"Benchmark 비중 합계가 100%여야 합니다 (현재 {benchmark_weights.sum():.1%})."
        )
    invalid_benchmarks = [
        ticker
        for ticker in benchmark_tickers
        if not ticker.isdigit() or len(ticker) != 6
    ]
    if invalid_benchmarks:
        raise ValueError(
            "국내 Benchmark 종목코드는 6자리 코드여야 합니다: "
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


st.sidebar.title("Portfolio Analyzer")
market = "Korea (FinanceDataReader)"
quick_input_mode = st.sidebar.checkbox(
    "검색 장애 시 6자리 코드 빠른 입력 사용", key="korean_quick_input"
)
last_message = st.session_state.pop("korean_last_message", None)
if last_message:
    st.sidebar.success(last_message)

if quick_input_mode:
    st.sidebar.warning(
        "빠른 입력은 검색 결과 확인을 생략합니다. 검색 기능을 사용할 수 없을 때만 권장합니다."
    )
    ticker_text = st.sidebar.text_input(
        "6자리 종목코드 (쉼표로 구분)",
        "069500, 411060, 487240",
        key="korean_tickers",
    )
    weight_text = st.sidebar.text_input(
        "비중 (합계 1.0 또는 100)", "40, 30, 30", key="korean_weights"
    )
    benchmark_text = st.sidebar.text_input(
        "Benchmark 6자리 코드 (쉼표로 구분)",
        "069500",
        key="korean_quick_benchmark",
    )
    benchmark_weight_text = st.sidebar.text_input(
        "Benchmark 비중 (합계 1.0 또는 100)",
        "100",
        key="korean_quick_benchmark_weights",
    )
else:
    st.session_state.setdefault("korean_selected_assets", [])
    st.session_state.setdefault("korean_selected_benchmark_assets", [])
    with st.sidebar.expander("포트폴리오 종목 검색·추가", expanded=True):
        selected_security = render_korean_security_search(
            "portfolio_security", "국내 주식/ETF 검색"
        )
        if selected_security is not None:
            if add_korean_asset("korean_selected_assets", selected_security):
                st.session_state["korean_last_message"] = (
                    f"{security_label(selected_security)} 추가됨"
                )
                reset_korean_security_search("portfolio_security")
                st.rerun()
            else:
                st.warning("이미 포트폴리오에 추가된 종목입니다.")

    selected_assets, weights = render_selected_assets(
        "선택된 포트폴리오 종목",
        "korean_selected_assets",
        "korean_weight",
        "검색 결과에서 종목을 선택하고 '추가'를 누르세요.",
    )

    with st.sidebar.expander("Benchmark 검색·추가", expanded=True):
        selected_benchmark = render_korean_security_search(
            "benchmark_security", "국내 Benchmark 검색"
        )
        if selected_benchmark is not None:
            if add_korean_asset("korean_selected_benchmark_assets", selected_benchmark):
                st.session_state["korean_last_message"] = (
                    f"{security_label(selected_benchmark)} 추가됨"
                )
                reset_korean_security_search("benchmark_security")
                st.rerun()
            else:
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

if st.sidebar.button("분석", type="primary", icon=":material/analytics:"):
    try:
        if quick_input_mode:
            tickers, weights = parse_portfolio(ticker_text, weight_text)
            if benchmark_text.strip():
                benchmark_tickers, benchmark_weights = parse_portfolio(
                    benchmark_text, benchmark_weight_text
                )
            else:
                benchmark_tickers = []
                benchmark_weights = np.array([], dtype=float)
            all_names = resolve_korean_display_names(tickers + benchmark_tickers)
            display_names = {
                ticker: all_names[ticker] for ticker in tickers if ticker in all_names
            }
            benchmark_display_names = {
                ticker: all_names[ticker]
                for ticker in benchmark_tickers
                if ticker in all_names
            }

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
            "weights": weights,
            "portfolio": portfolio,
            "metrics": metrics,
            "optimizer": optimizer,
            "display_labels": build_display_labels(tickers, display_names),
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
weights = analysis_result["weights"]
portfolio = analysis_result["portfolio"]
metrics = analysis_result["metrics"]
optimizer = analysis_result["optimizer"]
display_labels = analysis_result["display_labels"]
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
        allocation = px.pie(
            values=weights,
            names=[display_labels[ticker] for ticker in tickers],
            hole=0.4,
        )
        allocation.update_layout(margin=dict(t=20, b=20, l=0, r=0))
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
        engines. FinanceDataReader supplies Korean-listed stock and ETF prices
        using six-digit security codes.

        Past performance does not guarantee future results. This tool is for
        educational use and is not investment advice.
        """
    )
