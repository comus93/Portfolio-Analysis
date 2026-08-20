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
    ticker_text = st.sidebar.text_input(
        "6-digit ticker codes (comma-separated)",
        "069500, 411060, 487240",
        key="korean_tickers",
    )
    weight_text = st.sidebar.text_input(
        "Weights (fractions or percentages)", "40, 30, 30", key="korean_weights"
    )
    benchmark_default = "069500"
else:
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

benchmark_ticker = (
    st.sidebar.text_input(
        "Benchmark ticker/code", benchmark_default, key=f"benchmark_{market}"
    )
    .strip()
    .upper()
)
risk_free_rate = st.sidebar.slider(
    "Risk-free rate", 0.0, 0.10, 0.03, 0.005, format="%.1f%%"
)
st.sidebar.caption("Weights may sum to 1.0 or 100. Not investment advice.")

try:
    if start_date >= end_date:
        raise ValueError("Start date must be earlier than end date.")
    tickers, weights = parse_portfolio(ticker_text, weight_text)
    if market == "Korea (FinanceDataReader)" and (
        not benchmark_ticker.isdigit() or len(benchmark_ticker) != 6
    ):
        raise ValueError("The Korean benchmark must be a six-digit code.")
except ValueError as exc:
    st.error(str(exc))
    st.stop()

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
        allocation = px.pie(values=weights, names=tickers, hole=0.4)
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
    st.line_chart(data / data.iloc[0])

with correlation_tab:
    st.header("Daily Return Correlation Matrix")
    correlation = data.pct_change().dropna().corr()
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
    st.write(f"Benchmark: **{benchmark_ticker}**")
    if st.button("Compare to benchmark", type="primary"):
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
