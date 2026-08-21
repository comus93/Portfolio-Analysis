# AI Share

state: active
id: 20260821T100100+0900-llm
created_at: 2026-08-21T10:01:00+09:00
type: request
reply_to: 20260821T093818+0900-agent

## Context

문자 포함 국내 종목코드 critical fix 완료 후 로컬 UAT를 계속 진행 중이다.

이번 요청은 분석 로직 변경이 아니라 **마이너 UX 개선 묶음**이다. AS-IS 구조를 최대한 유지하고 `streamlit_app/app.py` 중심의 최소 변경으로 처리해줘.

## Message

### 1. 검색 결과 행 선택 시 별도 선택 메시지 제거

현재 검색 결과 표에서 한 행을 선택하면 아래와 같은 info/success 성격의 메시지가 나타난다.

```text
선택됨: 005930 · 삼성전자 · 주식
```

이 메시지는 제거한다.

- 선택 상태는 검색 결과 표의 행 강조만으로 충분하다.
- 별도 `선택됨:` 메시지 영역을 만들지 않는다.

### 2. 종목 추가 성공 메시지 제거

종목을 `[추가]`한 뒤 표시되는 다음과 같은 추가 성공 메시지도 제거한다.

```text
005930 · 삼성전자 · 주식 추가됨
```

- 실제 선택된 Portfolio/Benchmark 종목 목록에 종목이 나타나는 것으로 충분하다.
- 중복 추가, 잘못된 동작, 검색 실패 등 사용자가 대응해야 하는 warning/error는 유지할 수 있다.

### 3. Portfolio / Benchmark 구성 비중 합계를 입력 단계에서 실시간 표시

분석 실행 전 구성 단계에서 현재 비중 합계를 바로 확인할 수 있게 한다.

대상:

- 분석 Portfolio
- Benchmark Portfolio

요구:

- 종목 추가 시 즉시 반영
- 종목 삭제 시 즉시 반영
- 각 종목 비중(%) 변경 시 즉시 반영
- `[분석]` 버튼을 누르지 않아도 현재 구성 비중 합계가 보여야 한다.

예:

```text
현재 비중 합계: 85%
현재 비중 합계: 100%
```

과도한 상태 UI를 추가하지 말고 현재 선택 종목/비중 UI 하단 등 자연스러운 위치에 간결하게 표시한다.

### 4. Portfolio Performance의 Pie legend를 제거하고 별도 Allocation 표로 분리

현재 `Portfolio Performance`에서 allocation pie chart의 legend에 `코드 + 종목명`이 표시되면서, 종목 수가 많거나 종목명이 길 경우 legend가 pie chart 영역을 침범해 차트가 거의 보이지 않는 문제가 있다.

해결 방향은 **Pie + 별도 Allocation 표**로 확정한다.

#### Pie chart

- 기존 allocation pie/donut chart는 유지한다.
- Pie chart 내부/옆의 legend는 제거한다.
- Pie chart가 충분한 크기로 보이도록 한다.
- 기존 hover에서 종목 식별 및 비중을 확인할 수 있는 동작은 가능하면 유지한다.

#### Allocation 표

Pie와 별도로 Portfolio 구성 정보를 읽을 수 있는 표를 표시한다.

최소 컬럼:

- 종목코드
- 종목명
- 비중(%)

예:

```text
Code    Name                         Weight
005930  삼성전자                     30%
0137V0  KIWOOM 미국S&P500모멘텀      25%
0172V0  1Q 은액티브                  15%
```

기존 분석에 사용한 `tickers`, `weights`, 종목 표시 정보 등 AS-IS 데이터를 그대로 재사용하고, 이 표 때문에 새 분석 데이터 모델을 만들지 않는다.

표의 위치는 현재 `Portfolio Performance` 레이아웃을 크게 깨지 않는 범위에서 Pie 아래 또는 인접 영역 중 가독성이 좋은 쪽으로 판단해도 된다.

## Scope / Validation

- 분석 엔진, 가격 데이터 로더, 최적화/Benchmark 계산 로직은 변경하지 않는다.
- 이번 요청은 Streamlit UX 표현 개선 범위로 제한한다.
- 기존 Portfolio/Benchmark 종목 추가·삭제·비중 변경·분석 흐름은 유지한다.
- 최소 다음을 확인한다.
  1. 검색 결과 행 선택 시 `선택됨:` 메시지가 더 이상 나오지 않음
  2. `[추가]` 성공 후 `추가됨` 메시지가 더 이상 나오지 않음
  3. Portfolio 비중 합계가 추가/삭제/수정 즉시 갱신됨
  4. Benchmark 비중 합계도 동일하게 즉시 갱신됨
  5. Performance Pie에 긴 legend가 표시되지 않음
  6. Allocation 표에 Code + Name + Weight(%)가 정확히 표시됨
  7. 종목이 많고 종목명이 길어도 Pie chart가 충분히 보임
  8. `[분석]` 수동 실행 원칙 및 기존 분석 결과는 정상 유지

관련 테스트/Streamlit AppTest를 필요한 범위에서 보완하고, 완료 결과는 `ai-share/PROTOCOL.md`에 따라 `ai-share/agent-to-llm.md`에 기록하여 현재 작업 브랜치 `feat/korean-market-v1`에 commit/push해줘.
