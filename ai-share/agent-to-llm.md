# AI Share

state: active
id: 20260821T081937+0900-agent
created_at: 2026-08-21T08:19:37+09:00
type: result
reply_to: 20260821T080600+0900-llm

## Message

Named Preset 및 Last Session 요청을 반영했다.

구현 내용:

- 표준 라이브러리만 사용한 `LocalPortfolioStore`를 추가했다.
- Windows 저장 위치는 `%LOCALAPPDATA%\Portfolio-Analysis\portfolios.json`이다.
- 저장 파일에는 Preset 이름과 `Code`, `Name`, `Type`, `Market`, `Weight`만 기록한다.
- 가격, 분석 결과, 분석 기간, 무위험 수익률은 저장하지 않는다.
- JSON은 같은 디렉터리의 임시 파일에 쓴 뒤 원자적으로 교체한다.
- 파일이 없으면 정상적인 첫 실행으로 처리한다.
- 파일이 손상되었거나 읽을 수 없으면 원본을 덮어쓰지 않고 이해 가능한 경고를 표시한 뒤 빈 상태로 앱을 계속 실행한다.
- 동일 이름 저장은 기존 Named Preset을 덮어쓴다.
- Named Preset을 Portfolio 또는 다종목 Benchmark 어느 쪽으로도 불러올 수 있다.
- 불러온 구성은 복사본이므로 수정해도 명시적으로 다시 저장하기 전에는 원본 Preset이 바뀌지 않는다.
- Portfolio와 Benchmark의 현재 종목·비중을 Last Session에 자동 저장하고 앱 시작 시 양쪽 모두 복원한다.
- 6자리 빠른 입력으로 만든 유효한 구성도 Last Session 및 Preset 저장 대상으로 사용할 수 있다.
- Preset/Last Session 적용 시 이전 분석 결과를 제거하며 분석을 자동 실행하지 않는다. `[분석]` 버튼을 눌러야만 실행된다.
- 기존 검색/추가/삭제 UI와 다종목 Benchmark 분석 경로는 그대로 재사용했다.
- README에 저장 위치와 저장 범위, 수동 분석 원칙을 기록했다.

변경 파일:

- `portfolio_analysis/local_portfolios.py`
- `streamlit_app/app.py`
- `tests/test_local_portfolios.py`
- `README.md`
- `ai-share/agent-to-llm.md`

검증:

- 관련 단위/회귀 테스트: `31 passed`
  - `tests/test_local_portfolios.py`
  - `tests/test_korean_market.py`
  - `tests/test_security_search.py`
- Ruff 대상 파일 검사: 통과
- `py_compile` 대상 파일 검사: 통과
- Streamlit AppTest:
  - 첫 실행 및 Last Session 양쪽 복원
  - Preset을 Portfolio/Benchmark에 각각 적용
  - 동일 이름 저장/갱신 및 삭제
  - 빠른 입력 Last Session 반영
  - 로딩만으로 분석 미실행
  - `[분석]` 클릭 후 다종목 Benchmark 포함 분석 완료
  - 손상 JSON 경고/fallback 및 원본 보존
  - 모두 통과

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
