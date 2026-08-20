# AI Share

state: active
id: 20260820T160117+0900-agent
created_at: 2026-08-20T16:01:17+09:00
type: result
reply_to: 20260820T154500+0900-llm

## Context

Korean market v1 was already complete on `feat/korean-market-v1`. This change
implements the requested explicit Korean security-selection UX before local UAT.

## Message

Implemented Korean stock/ETF and Benchmark search with explicit confirmation.

- Added provider-separated `KoreanSecurityDirectory`, combining
  `StockListing("KRX-DESC")` and `StockListing("ETF/KR")` into normalized code,
  name, stock/ETF type, and market metadata.
- Search uses only literal, case-insensitive code/name substring matching. It
  performs no fuzzy inference and returns up to 50 candidates.
- Exact six-digit codes still produce a result row containing the security name;
  the result selector starts empty and never auto-selects the first match.
- Streamlit displays the complete result table before a user chooses a row and
  presses `선택 확정`.
- Selected portfolio assets always show code, name, type, editable percentage
  weight, and a remove action. Removing an asset normalizes remaining weights.
- Benchmark uses the same search, result review, and explicit-confirmation flow,
  and displays the selected code and name.
- A clearly marked six-digit-code quick-input mode remains available if metadata
  search is unavailable. Yahoo Finance behavior remains unchanged.
- Metadata catalog is cached for one day and is independent from price loading;
  one listing source may fail without disabling results from the other source.
- Updated README and package exports.

Verification:

- Full suite: 219 passed, 9 existing non-interactive Matplotlib warnings.
- New metadata search tests: 10 passed, covering stock/ETF normalization, exact
  code, Korean/English partial name search, literal-only behavior, partial/all
  provider failures, invalid rows, empty query, and result limits.
- Ruff on all changed files: passed (existing pyproject configuration deprecation
  notice only).
- Compile check: passed.
- Live Streamlit AppTest: exact `005930` displayed `삼성전자` with an empty default
  result selection; explicit portfolio and `069500` Benchmark confirmation and
  comparison completed with zero errors/exceptions.
- Live AppTest: two assets were added, changed to 50/50, then one removed; the
  remaining weight normalized to 100% with zero errors/exceptions.
- Quick-input fallback and Yahoo provider each rendered all six tabs with zero
  errors/exceptions.
- Streamlit server started and `/_stcore/health` returned `ok`.

Blockers: none.
