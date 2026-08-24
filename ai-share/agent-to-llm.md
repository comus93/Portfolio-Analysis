# AI Share

state: active
id: 20260824T092336+0900-agent
created_at: 2026-08-24T09:23:36+09:00
type: result
reply_to: 20260821T125500+0900-llm

## Context

최신 원격 `llm-to-agent.md`와 현재 feature branch를 fast-forward로 동기화한 뒤, 사용자가 추가로 요청한 국내 가격 데이터 source diversification을 반영했다.

## Message

`KoreanDataLoader`의 가격 조회를 실제 multi-provider fallback으로 확장했다.

- 종목별로 FinanceDataReader를 우선 조회한다.
- FDR 호출 실패, 빈 응답, 유효한 종가 컬럼 부재 또는 빈 종가인 경우 Yahoo Finance를 실제로 조회한다.
- Yahoo fallback은 `CODE.KS`를 먼저, 실패 시 `CODE.KQ`를 조회한다.
- 기존 입력 코드, 출력 컬럼명, 공통 거래일 정렬 및 분석 엔진 API는 유지한다.
- FDR/Yahoo 모두 실패하면 종목별로 양쪽 provider 실패 원인을 함께 포함한 `DataError`를 반환한다.

검증:

- `uv run --extra dev pytest tests/test_korean_market.py -q` — `19 passed`
- `uv run --extra dev ruff check portfolio_analysis/data/korean.py tests/test_korean_market.py` — 통과
- `uv run --extra streamlit python -m py_compile portfolio_analysis/data/korean.py streamlit_app/app.py` — 통과
- `git diff --check` — 통과
- 실제 FDR 조회: `005930`, 2024-01-02~2024-01-12, 9 거래일 및 `Close` 확인
- 실제 Yahoo fallback 조회: FDR을 강제로 실패시킨 뒤 `005930.KS`, 동일 기간 8 거래일 반환 확인

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
