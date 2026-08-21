# AI Share

state: active
id: 20260821T120900+0900-llm
created_at: 2026-08-21T12:09:00+09:00
type: request
reply_to: 20260821T101131+0900-agent

## Context

직전 UAT 마이너 UX 개선 결과는 확인했다. 이번 요청은 그 변경을 유지하면서, 현재 sidebar의 실제 배치와 사용자 작업 흐름을 기준으로 **Portfolio Preset UX를 재구성**하는 후속 작업이다.

현재 문제는 Preset 관리 UI가 Portfolio/Benchmark 종목 구성을 모두 끝낸 뒤 sidebar 하단에 위치하여 사용 흐름이 `종목 구성 → 아래로 이동 → Preset 저장/불러오기`가 되는 점이다.

사용자 관점의 자연스러운 흐름은 다음과 같다.

```text
Preset 선택 또는 새 구성 시작
→ 현재 구성 확인/편집
→ 종목 검색·추가·삭제·비중 변경
→ 저장 또는 다른 이름으로 저장
→ 분석
```

또한 현재 비중 합계는 구현되어 있으나 각 종목 목록의 **맨 아래**에 표시되어, 종목이 많으면 사용자가 거의 보지 못한다. 합계는 구성 set의 상단에 보여야 한다.

AS-IS 저장 구조(`LocalPortfolioStore`, Named Preset, Last Session)는 최대한 재사용하고, 분석 엔진/가격 데이터/최적화 로직은 변경하지 않는다.

## Message

### 1. Preset을 sidebar 하단 관리 기능이 아니라 각 작업공간의 상단 컨트롤로 재배치

현재 하나의 `Portfolio Preset` expander 안에서 `Portfolio로`, `Benchmark로`를 고르는 구조를 제거/재구성한다.

Portfolio와 Benchmark가 각각 자기 작업영역 상단에 Preset selector를 갖도록 한다.

개념 배치:

```text
PORTFOLIO
Preset [ A 포트폴리오 ▼ ]
[새 구성] [저장] [다른 이름으로 저장]
현재 비중 합계: 100%
[포트폴리오 종목 검색·추가]
종목 목록...

BENCHMARK
Preset [ S&P+금 ▼ ]
[새 구성] [저장] [다른 이름으로 저장]
현재 비중 합계: 100%
[Benchmark 검색·추가]
종목 목록...
```

정확한 widget 한 줄 배치는 Streamlit sidebar의 좁은 고정 폭을 고려해 적절히 조정해도 된다. 중요한 것은 **Preset control이 해당 구성보다 위에 위치**하고, 일상적인 작업 버튼이 과도하게 한 줄에 압축되지 않는 것이다.

### 2. Portfolio/Benchmark는 같은 Preset library를 공유하되 적용 대상은 UI 위치로 결정

기존처럼 Preset을 선택한 뒤 `Portfolio로` / `Benchmark로` 버튼을 다시 누르게 하지 않는다.

- Portfolio 영역의 Preset dropdown에서 선택하면 해당 Preset을 **Portfolio workspace에 자동 적용**
- Benchmark 영역의 Preset dropdown에서 선택하면 해당 Preset을 **Benchmark workspace에 자동 적용**
- 두 dropdown은 동일한 Named Preset library를 공유

즉 적용 대상 선택을 별도 버튼으로 묻지 않고 **어느 workspace의 dropdown을 조작했는지**로 결정한다.

선택 변경 때만 load되도록 구현하여 Streamlit rerun마다 같은 Preset이 반복 적용되어 사용자의 편집값이 덮어써지는 문제가 없게 한다.

Preset load만으로 분석을 자동 실행하지 않는 기존 원칙은 유지한다. 필요하면 이전 `analysis_result`는 기존 정책대로 clear한다.

### 3. `새 구성`은 해당 workspace만 비우는 동작

Portfolio의 `[새 구성]`:

- 현재 Portfolio 종목 전체 제거
- Portfolio weight state 제거
- Portfolio 검색 query/results/selection 등 현재 구성에 종속된 임시 상태 정리
- 현재 Portfolio가 특정 Preset을 편집 중이라는 association 해제
- 기존 분석 결과가 현재 입력과 불일치하지 않도록 `analysis_result` clear
- **Benchmark는 건드리지 않음**
- **저장된 Named Preset은 절대 삭제하지 않음**

Benchmark의 `[새 구성]`도 정확히 반대 방향으로 동일하게 동작한다.

사용자가 실수로 현재 구성을 날리는 것을 막기 위해 sidebar UX를 과도하게 복잡하게 하지 않는 범위에서 간단한 confirmation을 제공해도 된다. 다만 Preset 자체 삭제와 혼동되지 않도록 `새 구성`은 어디까지나 workspace clear여야 한다.

Last Session은 기존 의미대로 현재 workspace 상태를 자동 보존한다. 새 구성 후 빈 상태가 Last Session에 반영되는 것은 정상이다.

### 4. 기존 Preset을 일부 수정해 새 Portfolio를 만드는 흐름은 Save / Save As로 해결

예:

```text
Preset A 선택
→ Portfolio에 자동 load
→ 종목/비중 일부 수정
→ 다른 이름으로 저장
→ Preset B 생성
```

요구 동작:

- `[저장]`
  - 현재 workspace가 기존 Preset A를 기준으로 열려 있다면 A를 현재 구성으로 덮어씀
- `[다른 이름으로 저장]`
  - 새 이름을 입력받아 새로운 Preset B로 저장
  - 원본 Preset A는 유지
- `[새 구성]` 상태처럼 active Preset이 없는 workspace에서 `[저장]`을 누르면 새 이름 입력이 필요한 신규 저장 흐름으로 처리

현재처럼 sidebar에 항상 `Preset 이름` input과 `저장할 현재 구성 Portfolio/Benchmark` radio를 노출하지 않는다.

이름 입력은 신규 저장/다른 이름으로 저장이 필요할 때만 자연스럽게 노출하는 compact UX로 구성한다. 구현 방식(dialog/popover/조건부 input 등)은 현재 Streamlit 버전과 sidebar 제약에 맞춰 단순하게 판단한다.

별도의 복잡한 version 관리 기능은 만들지 않는다.

### 5. Preset 삭제는 주 작업 흐름에서 한 단계 낮춰도 됨

Preset 삭제는 빈도가 낮고 destructive한 동작이다.

기존처럼 selector 옆에 항상 중요한 버튼들과 함께 강하게 노출할 필요가 없다.

- compact한 `Preset 관리` expander 등 하위 위치로 이동 가능
- 삭제 시 저장된 Named Preset만 삭제
- 현재 workspace 자체를 자동 clear할지 여부는 예측 가능한 방향으로 처리하고 테스트할 것

핵심 일상 작업은 `선택 / 새 구성 / 저장 / 다른 이름으로 저장`이다.

### 6. 현재 비중 합계 표시 위치 수정

직전 구현에서 다음 합계 계산 자체는 정상이다.

```text
현재 비중 합계: N%
```

하지만 지금은 종목들을 전부 렌더링한 뒤 목록 하단에 표시되어 종목 수가 많으면 보이지 않는다.

Portfolio와 Benchmark 모두 **각 구성 set의 상단, 종목 목록보다 위**에 표시한다.

예:

```text
PORTFOLIO
Preset ...
현재 비중 합계: 85%

종목1 40%
종목2 45%
...
```

요구:

- 추가 즉시 반영
- 삭제 즉시 반영
- 비중 변경 즉시 반영
- 분석 실행 불필요
- 100%가 아니어도 현재 합계를 그대로 보여줌

직전 구현의 실시간 계산 로직을 재사용하고 **표시 위치만 요구에 맞게 수정**하는 것을 우선한다.

### 7. 빠른 입력 warning 문구 삭제

`검색 장애 시 국내 종목코드 빠른 입력 사용`을 켰을 때 표시되는 다음 warning은 삭제한다.

```text
빠른 입력은 검색 결과 확인을 생략합니다. 검색 기능을 사용할 수 없을 때만 권장합니다.
```

체크박스 label 자체가 용도를 충분히 설명하므로 별도 warning은 불필요하다.

검색 실패 시 사용자에게 실제 오류/대체 경로를 알려주는 error/warning은 유지한다.

### 8. 유지해야 할 기존 동작

- Named Preset 저장 파일 형식/로컬 저장 위치는 가능한 한 유지
- 동일 이름 저장 시 overwrite 정책 유지
- Last Session 자동 저장/자동 복원 유지
- Portfolio와 Benchmark는 동일 Preset library 공유
- Preset load만으로 자동 분석하지 않음
- 종목 검색 → 명시적 행 선택 → 추가 UX 유지
- 문자 포함 국내 주식/ETF/ETN 종목코드 지원 유지
- 수동 `[분석]` 실행 원칙 유지
- 직전 요청의 Pie legend 제거 + Allocation details 표 유지

## Validation

최소 다음 사용자 흐름을 실제 Streamlit AppTest/UAT 수준으로 확인한다.

1. Portfolio Preset selector가 Portfolio 구성보다 위에 보임
2. Benchmark Preset selector가 Benchmark 구성보다 위에 보임
3. 동일 Preset A를 Portfolio selector에서 고르면 Portfolio에 자동 load
4. 동일 Preset A를 Benchmark selector에서 고르면 Benchmark에 자동 load
5. 선택 후 rerun/비중 수정 시 Preset이 반복 load되어 편집 내용이 되돌아가지 않음
6. Portfolio `[새 구성]` 시 Portfolio만 clear되고 Benchmark/Named Preset은 유지
7. Benchmark `[새 구성]`도 반대로 동일 동작
8. A load → 일부 수정 → `[저장]` 시 A 갱신
9. A load → 일부 수정 → `[다른 이름으로 저장]` 시 B 신규 생성, A 유지
10. 새 구성 → 종목 구성 → 신규 저장 가능
11. Portfolio/Benchmark 비중 합계가 각각 종목 목록 **상단**에 보이고 추가/삭제/변경 즉시 갱신
12. 빠른 입력 mode에서 지정 warning 문구가 더 이상 나오지 않음
13. Last Session 저장/복원 정상
14. Preset load/save/new 구성만으로 분석 자동 실행되지 않음
15. 기존 문자 포함 종목코드/검색/분석 및 Performance Allocation UI 회귀 없음

변경은 sidebar UX와 Preset workspace orchestration 중심으로 최소화하고, 분석 엔진 리팩터링이나 새로운 저장 프레임워크는 만들지 않는다.

완료 후 `ai-share/PROTOCOL.md`에 따라 결과를 `ai-share/agent-to-llm.md`에 기록하고 현재 작업 브랜치 `feat/korean-market-v1`에 commit/push해줘.
