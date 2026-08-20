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


def render_korean_security_search(prefix: str, title: str) -> dict | None:
    """Render search, results, and explicit confirmation controls."""
    st.markdown(f"**{title}**")
    query = st.text_input(
        "종목코드 또는 종목명",
        key=f"{prefix}_query",
        placeholder="예: 005930, 삼성전자, KODEX 200",
    )
    if st.button("검색", key=f"{prefix}_search"):
        st.session_state.pop(f"{prefix}_result_choice", None)
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
    st.dataframe(
        results[["Code", "Name", "Type", "Market"]],
        hide_index=True,
        use_container_width=True,
    )
    by_code = {record["Code"]: record for record in records}
    selected_code = st.selectbox(
        "검색 결과에서 선택",
        options=[""] + list(by_code),
        index=0,
        format_func=lambda code: (
            "선택하세요" if not code else security_label(by_code[code])
        ),
        key=f"{prefix}_result_choice",
    )
    if st.button("선택 확정", key=f"{prefix}_confirm"):
        if not selected_code:
            st.warning("검색 결과 중 하나를 먼저 선택하세요.")
            return None
        return by_code[selected_code]
    return None


def remove_korean_portfolio_asset(code: str) -> None:
    """Remove an asset and normalize the remaining percentage weights."""
    selected_assets = st.session_state.get("korean_selected_assets", [])
    remaining = [asset for asset in selected_assets if asset["Code"] != code]
    st.session_state["korean_selected_assets"] = remaining
    st.session_state.pop(f"korean_weight_{code}", None)

    if not remaining:
        return
    values = np.array(
        [
            float(st.session_state.get(f"korean_weight_{asset['Code']}", 0.0))
            for asset in remaining
        ]
    )
    if np.isclose(values.sum(), 0.0):
        values = np.full(len(remaining), 100.0 / len(remaining))
    else:
        values = values / values.sum() * 100.0
    for asset, value in zip(remaining, values):
        st.session_state[f"korean_weight_{asset['Code']}"] = float(value)


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


def optimization_result(optimizer: PortfolioOptimizer, strategy: str) -> dict:
    """Run one of the existing optimization strategies."""
    methods = {
        "Maximum Sharpe": optimizer.optimize_max_sharpe,
        "Minimum Volatility": optimizer.optimize_min_volatility,
        "Risk Parity": optimizer.optimize_risk_parity,
    }
    return methods[strategy]()


st.sidebar.title("📊 Portfolio Analyzer")
market = st.sidebar.selectbox(
    "Market data provider", ["Korea (FinanceDataReader)", "Yahoo Finance"]
)

if market == "Korea (FinanceDataReader)":
    quick_input_mode = st.sidebar.checkbox(
        "검색 장애 시 6자리 코드 빠른 입력 사용", key="korean_quick_input"
    )

    if quick_input_mode:
        st.sidebar.warning(
            "빠른 입력은 종목명을 확인하지 않습니다. 검색 기능을 사용할 수 없을 때만 권장합니다."
        )
        ticker_text = st.sidebar.text_input(
            "6자리 종목코드 (쉼표로 구분)",
            "069500, 411060, 487240",
            key="korean_tickers",
        )
        weight_text = st.sidebar.text_input(
            "비중 (합계 1.0 또는 100)", "40, 30, 30", key="korean_weights"
        )
        benchmark_ticker = st.sidebar.text_input(
            "Benchmark 6자리 코드", "069500", key="korean_quick_benchmark"
        ).strip()
        benchmark_name = ""
        display_names = {}
    else:
        st.session_state.setdefault("korean_selected_assets", [])
        with st.sidebar.expander("포트폴리오 종목 검색·추가", expanded=True):
            selected_security = render_korean_security_search(
                "portfolio_security", "국내 주식/ETF 검색"
            )
            if selected_security is not None:
                selected_assets = st.session_state["korean_selected_assets"]
                if any(
                    asset["Code"] == selected_security["Code"]
                    for asset in selected_assets
                ):
                    st.warning("이미 포트폴리오에 추가된 종목입니다.")
                else:
                    selected_assets.append(selected_security)
                    st.success(f"{security_label(selected_security)} 추가됨")

        selected_assets = st.session_state["korean_selected_assets"]
        st.sidebar.subheader("선택된 포트폴리오 종목")
        st.sidebar.caption("각 종목 오른쪽에 비중(%)을 입력하고 ✕로 삭제합니다.")
        weight_percentages: list[float] = []
        if not selected_assets:
            st.sidebar.info("검색 결과에서 종목을 선택하고 '선택 확정'을 누르세요.")
        for asset in selected_assets:
            label_column, weight_column, remove_column = st.sidebar.columns([5, 3, 1])
            label_column.markdown(
                f"**{asset['Code']}**  \n{asset['Name']} · {asset['Type']}"
            )
            weight_key = f"korean_weight_{asset['Code']}"
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
                key=f"remove_{asset['Code']}",
                on_click=remove_korean_portfolio_asset,
                args=(asset["Code"],),
            )

        st.session_state.setdefault("korean_selected_benchmark", None)
        with st.sidebar.expander("Benchmark 검색·선택", expanded=True):
            selected_benchmark = render_korean_security_search(
                "benchmark_security", "국내 Benchmark 검색"
            )
            if selected_benchmark is not None:
                st.session_state["korean_selected_benchmark"] = selected_benchmark
                st.success(f"{security_label(selected_benchmark)} 선택됨")

        benchmark_security = st.session_state["korean_selected_benchmark"]
        if benchmark_security is None:
            benchmark_ticker = ""
            benchmark_name = ""
            st.sidebar.info("Benchmark 검색 결과에서 종목을 명시적으로 선택하세요.")
        else:
            benchmark_ticker = benchmark_security["Code"]
            benchmark_name = benchmark_security["Name"]
            st.sidebar.markdown(
                "**선택된 Benchmark**  \n" + security_label(benchmark_security)
            )
            if st.sidebar.button("Benchmark 선택 해제"):
                st.session_state["korean_selected_benchmark"] = None
                st.rerun()

        tickers = [asset["Code"] for asset in selected_assets]
        weights = np.array(weight_percentages, dtype=float) / 100.0
        display_names = {asset["Code"]: asset["Name"] for asset in selected_assets}
else:
    quick_input_mode = True
    ticker_text = st.sidebar.text_input(
        "Tickers (comma-separated)", "VTI, VXUS, BND", key="yahoo_tickers"
    )
    weight_text = st.sidebar.text_input(
        "Weights (fractions or percentages)", "0.4, 0.2, 0.4", key="yahoo_weights"
    )
    benchmark_default = "SPY"

st.sidebar.header("Analysis period")
date_columns = st.sidebar.columns(2)
with date_columns[0]:
    start_date = st.date_input("Start", datetime.now() - timedelta(days=3 * 365))
with date_columns[1]:
    end_date = st.date_input("End", datetime.now())

if market == "Yahoo Finance":
    benchmark_ticker = (
        st.sidebar.text_input(
            "Benchmark ticker/code", benchmark_default, key=f"benchmark_{market}"
        )
        .strip()
        .upper()
    )
    benchmark_name = ""
    display_names = {}
risk_free_rate = st.sidebar.slider(
    "Risk-free rate", 0.0, 0.10, 0.03, 0.005, format="%.1f%%"
)
st.sidebar.caption("Weights may sum to 1.0 or 100. Not investment advice.")

if not quick_input_mode and not tickers:
    st.info("검색 결과에서 포트폴리오 종목을 하나 이상 선택하세요.")
    st.stop()

try:
    if start_date >= end_date:
        raise ValueError("Start date must be earlier than end date.")
    if quick_input_mode:
        tickers, weights = parse_portfolio(ticker_text, weight_text)
    elif not np.isclose(weights.sum(), 1.0):
        raise ValueError(
            f"선택 종목의 비중 합계가 100%여야 합니다 (현재 {weights.sum():.1%})."
        )
    if (
        market == "Korea (FinanceDataReader)"
        and benchmark_ticker
        and (not benchmark_ticker.isdigit() or len(benchmark_ticker) != 6)
    ):
        raise ValueError("국내 Benchmark는 6자리 코드여야 합니다.")
except ValueError as exc:
    st.error(str(exc))
    st.stop()

display_labels = {
    ticker: (
        f"{ticker} · {display_names[ticker]}" if ticker in display_names else ticker
    )
    for ticker in tickers
}
benchmark_label = (
    f"{benchmark_ticker} · {benchmark_name}" if benchmark_name else benchmark_ticker
)

st.title("Portfolio Analyzer")
st.caption(f"Provider: {market} · {start_date} to {end_date}")

try:
    with st.spinner("Fetching and aligning market data..."):
        data = fetch_market_data(
            market,
            tuple(tickers),
            start_date.isoformat(),
            end_date.isoformat(),
        )
except (PortfolioAnalysisError, ValueError) as exc:
    st.error(f"Market data could not be loaded: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Unexpected market data error: {exc}")
    st.stop()

if len(data) < 2:
    st.error("At least two aligned price observations are required.")
    st.stop()

portfolio = PortfolioAnalysis(data, weights.tolist())
metrics = portfolio.get_summary(risk_free_rate)
optimizer = PortfolioOptimizer(data, risk_free_rate)

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
        st.plotly_chart(allocation, use_container_width=True)
    with return_column:
        cumulative = portfolio.calculate_cumulative_returns()
        figure = px.line(
            x=cumulative.index,
            y=cumulative.values,
            labels={"x": "Date", "y": "Growth of 1"},
        )
        figure.update_traces(name="Portfolio", showlegend=True)
        st.plotly_chart(figure, use_container_width=True)

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
    st.plotly_chart(heatmap, use_container_width=True)
    st.dataframe(correlation.style.format("{:.3f}"), use_container_width=True)

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
            st.dataframe(weight_frame.style.format("{:.2%}"), use_container_width=True)

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
            st.plotly_chart(frontier_figure, use_container_width=True)
        except Exception as exc:
            st.error(f"Optimization failed: {exc}")

with benchmark_tab:
    st.header("Benchmark Comparison")
    if benchmark_ticker:
        st.write(f"Benchmark: **{benchmark_label}**")
    else:
        st.info(
            "사이드바에서 Benchmark를 검색하고 결과를 확인한 뒤 '선택 확정'을 누르세요."
        )
    if st.button("Compare to benchmark", type="primary", disabled=not benchmark_ticker):
        try:
            benchmark_prices = fetch_market_data(
                market,
                (benchmark_ticker,),
                start_date.isoformat(),
                end_date.isoformat(),
            ).iloc[:, 0]
            comparison = BenchmarkComparison(
                data,
                weights.tolist(),
                benchmark_ticker=benchmark_ticker,
                risk_free_rate=risk_free_rate,
                benchmark_data=benchmark_prices,
            )
            comparison_metrics = comparison.get_metrics()
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

            portfolio_cumulative = (1 + comparison.portfolio_returns).cumprod()
            benchmark_cumulative = (1 + comparison.benchmark_returns).cumprod()
            figure = go.Figure()
            figure.add_scatter(
                x=portfolio_cumulative.index,
                y=portfolio_cumulative,
                name="Portfolio",
            )
            figure.add_scatter(
                x=benchmark_cumulative.index,
                y=benchmark_cumulative,
                name=benchmark_ticker,
            )
            figure.update_layout(xaxis_title="Date", yaxis_title="Growth of 1")
            st.plotly_chart(figure, use_container_width=True)
        except Exception as exc:
            st.error(f"Benchmark comparison failed: {exc}")

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
        st.plotly_chart(figure, use_container_width=True)

with about_tab:
    st.header("About")
    st.markdown(
        """
        This application reuses the project's portfolio analysis and optimization
        engines. Yahoo Finance remains available, while FinanceDataReader supplies
        Korean-listed stock and ETF prices using six-digit security codes.

        Past performance does not guarantee future results. This tool is for
        educational use and is not investment advice.
        """
    )
