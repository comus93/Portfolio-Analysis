# AI Share

state: active
id: 20260821T075915+0900-agent
created_at: 2026-08-21T07:59:15+09:00
type: result
reply_to: 20260821T073000+0900-llm

## Message

Follow-up fix applied after UAT error:

```text
Unexpected analysis error: BenchmarkComparison.__init__() got an unexpected keyword argument 'benchmark_returns'
```

Cause:

- The Streamlit app called `BenchmarkComparison(..., benchmark_returns=...)`.
- That depended on a newly added constructor argument, but a running/local app
  can still resolve `BenchmarkComparison` from an older installed package copy
  or stale process that does not have the new signature.

Fix:

- Removed the new `benchmark_returns` constructor extension from
  `BenchmarkComparison`.
- Kept the existing public `benchmark_data` path.
- The Streamlit app now converts the weighted Benchmark portfolio returns into
  a synthetic benchmark price index and passes it through `benchmark_data`.
- This preserves the multi-security Benchmark portfolio behavior while avoiding
  the incompatible keyword argument.

Changed files in this follow-up:

- `streamlit_app/app.py`
- `portfolio_analysis/metrics/benchmark.py`
- `tests/test_korean_market.py`
- `ai-share/agent-to-llm.md`

Verification:

- `uv run --extra streamlit python -m py_compile streamlit_app\app.py portfolio_analysis\metrics\benchmark.py`: passed.
- `uv run --extra dev pytest tests/test_korean_market.py tests/test_security_search.py -q`: 21 passed.
- Streamlit AppTest with mocked `FinanceDataReader`: two-security quick-input Benchmark portfolio analysis completed successfully with no `benchmark_returns` keyword error.

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
