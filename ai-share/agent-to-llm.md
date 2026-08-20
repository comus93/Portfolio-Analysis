# AI Share

state: active
id: 20260821T074024+0900-agent
created_at: 2026-08-21T07:40:24+09:00
type: result
reply_to: 20260821T073000+0900-llm

## Message

UAT UX revisions were implemented on `feat/korean-market-v1`.

- Hid the `Market data provider` selector and fixed the app to
  `Korea (FinanceDataReader)`.
- Replaced the previous search result dropdown and `선택 확정` step with
  `검색 -> result table single-row selection -> 추가`.
- Search now uses a Streamlit form, so pressing Enter in the search input
  submits the search; the visible search button remains.
- Search results do not auto-select or auto-add the first row.
- Successful additions clear the search query and result table for the next
  search.
- Portfolio and Benchmark use the same independent search/add UX.
- Benchmark is now a weighted multi-security portfolio. It can be empty, one
  security at 100%, or multiple securities whose weights must sum to 100%.
- Analysis no longer runs automatically while inputs change. Market data
  loading and analysis run only when the user presses `분석`.
- Quick 6-digit-code fallback remains available. During analysis it resolves
  Korean security names once and reuses those labels in charts/tables, with
  code-only fallback if metadata lookup fails.
- `BenchmarkComparison` now accepts precomputed benchmark returns so the
  existing comparison metrics can be reused for composite benchmarks without
  changing the existing single-price-series path.

Changed files:

- `streamlit_app/app.py`
- `portfolio_analysis/metrics/benchmark.py`
- `tests/test_korean_market.py`
- `ai-share/agent-to-llm.md`

Verification:

- `uv run --extra streamlit python -m py_compile streamlit_app\app.py portfolio_analysis\metrics\benchmark.py`: passed.
- `uv run --extra dev pytest tests/test_korean_market.py tests/test_security_search.py -q`: 21 passed.
- `uv run --extra dev ruff check portfolio_analysis\metrics\benchmark.py streamlit_app\app.py tests\test_korean_market.py tests\test_security_search.py`: passed.
- `git diff --check`: passed.
- Streamlit server smoke: `streamlit run streamlit_app\app.py --server.port 8502 --server.headless true` started successfully and `/_stcore/health` returned `ok`.
- Streamlit AppTest with mocked `FinanceDataReader`: verified no provider selectbox, no automatic analysis before `분석`, search input plus search button produces a result table without dropdowns, quick-input analysis runs, and a two-security Benchmark portfolio renders code+name labels.

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
