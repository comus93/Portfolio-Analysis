# AI Share

state: active
id: 20260821T125500+0900-llm
created_at: 2026-08-21T12:55:00+09:00
type: request
reply_to: 20260821T123324+0900-agent

## Context

직전 Portfolio/Benchmark Preset workspace UX 재구성 결과를 확인했다. 이번 요청은 그 구조를 유지하면서 sidebar 사용 흐름을 더 단순화하는 후속 UAT 개선이다.

핵심은 다음 세 가지다.

1. 별도 `검색 장애 시 국내 종목코드 빠른 입력 사용` 모드를 완전히 제거하고, 기존 Portfolio/Benchmark 검색 입력창 하나가 종목명 검색과 종목코드 직접 입력을 모두 처리하게 한다.
2. `[분석]` 버튼을 sidebar 최하단이 아니라 `Portfolio Analyzer` 타이틀 바로 아래 최상단으로 이동한다.
3. 기존 `Preset 관리` 영역을 `[Delete] [Export] [Import]` 중심으로 확장한다.

분석 엔진/가격 데이터/최적화 구조는 변경하지 말고 기존 session state, `LocalPortfolioStore`, 검색/종목 metadata 구조를 최대한 재사용한다.

## Message

### 1. 별도 빠른 입력 mode 완전 제거

현재의 다음 UI와 관련 분기 흐름을 제거한다.

```text
검색 장애 시 국내 종목코드 빠른 입력 사용
```

즉 사용자가 checkbox로 별도 mode를 켜서 Portfolio/Benchmark 코드와 비중을 text input으로 입력하는 UX는 더 이상 노출하지 않는다.

이 기능을 없애는 대신 기존 Portfolio/Benchmark의 `종목코드 또는 종목명` 검색 입력창이 직접 코드 입력까지 처리한다.

### 2. 기존 검색창 하나에서 이름 검색 / 단일 코드 / 복수 코드 입력을 자동 판별

Portfolio와 Benchmark 검색창 모두 동일하게 동작한다.

#### A. 일반 종목명/검색어 입력

예:

```text
삼성전자
KODEX 200
은액티브
```

기존 UX를 유지한다.

```text
검색 → 결과 표 → 사용자가 행 명시적 선택 → 추가
```

첫 검색 결과를 자동 선택하거나 자동 추가하지 않는다.

#### B. 정확한 국내 종목코드 1개 입력

예:

```text
005930
0137V0
0172V0
```

입력 전체가 유효한 국내 종목코드 1개로 판별되면 사용자가 이미 종목을 명시적으로 지정한 것으로 보고 검색 결과 선택 단계를 생략하여 해당 workspace에 바로 추가한다.

- Portfolio 검색창이면 Portfolio에 추가
- Benchmark 검색창이면 Benchmark에 추가
- 숫자 코드와 영숫자 코드를 모두 지원
- 대소문자 normalization 등 기존 국내 코드 처리 규칙 재사용
- 중복 종목은 중복 추가하지 않음
- 성공 후 입력/search result state는 기존 add UX와 동일하게 정리

#### C. 쉼표로 구분한 복수 종목코드 입력

예:

```text
005930,069500,0137V0,0172V0
```

모든 token이 유효한 국내 종목코드이면 batch direct-add로 처리한다.

- 입력 순서 보존
- 이미 workspace에 있는 코드는 중복 추가하지 않음
- 유효한 신규 코드들은 한 번에 추가
- 기존 문자 포함 KRX 코드 규칙 지원

이번 범위에서는 다음과 같은 이름+코드 혼합 batch 입력까지 일반화하지 않는다.

```text
삼성전자,069500,금현물
```

입력 전체가 코드 리스트가 아니면 기존 일반 검색으로 처리하는 단순한 규칙을 사용한다.

### 3. 직접 코드 입력은 별도 UX 안내를 표시하지 않음

이 기능을 설명하는 별도 caption, warning, help text, 사용법 문구를 추가하지 않는다.

사용자는 기존 `종목코드 또는 종목명` 입력창을 그대로 사용한다.

검색 장애 시에도 정확한 종목코드 직접 입력 경로가 기존 빠른 입력 fallback 역할을 최대한 대체하도록 한다.

가능하면:

- catalog 조회 가능 시 Code에 대응하는 Name/Type/Market metadata를 기존 catalog에서 보강
- catalog/search source가 일시적으로 불가능하더라도 정확한 유효 코드 자체는 기존 `KoreanDataLoader` 가격 조회 경로로 전달 가능한 fallback을 유지

단, 이 목적 때문에 새로운 종목 master/별도 provider를 만들지 않는다. 기존 구조 안에서 최소 구현한다.

### 4. `[분석]` 버튼을 sidebar 최상단으로 이동

현재 `[분석]` 버튼을 누르려면 긴 Portfolio/Benchmark 구성과 Analysis period 아래까지 scroll해야 한다.

sidebar 배치를 다음처럼 변경한다.

```text
Portfolio Analyzer

[ 분석 ]

PORTFOLIO
Preset ...
...
```

즉 기존 빠른 입력 mode UI가 있던 상단 위치에 `[분석]` 버튼을 둔다.

중요:

- sidebar의 분석 버튼은 하나만 존재해야 함
- 하단 기존 분석 버튼은 제거
- 버튼 UI를 위에서 먼저 렌더링하되 실제 분석 실행은 Portfolio/Benchmark/date/risk-free 등 모든 현재 입력 state가 준비된 뒤 기존 validation/분석 로직을 그대로 실행하도록 구성
- 예: 상단에서 `analyze_requested = st.sidebar.button(...)`만 받고 아래에서 `if analyze_requested:` 처리하는 방식 가능
- `[분석]` 수동 실행 원칙은 그대로 유지

### 5. `Preset 관리` 영역을 `[Delete] [Export] [Import]`로 구성

직전 구현에서 하위 관리 영역으로 내려간 `Preset 관리`를 유지하되 기능을 다음처럼 정리한다.

```text
Preset 관리
[Delete] [Export] [Import]
```

좁은 sidebar에서 실제 widget 폭에 따라 1행/2행 배치는 적절히 판단해도 되지만, 기능 명칭은 단순하게 유지한다.

#### Delete

- 기존 `선택한 Preset 삭제` 기능의 동작은 그대로 유지
- 버튼/액션 명칭만 `Delete`로 단순화
- 선택된 관리 대상 Preset을 삭제
- active workspace 처리 정책도 직전 구현 결과를 유지

#### Export

- `Preset 관리`에서 선택한 Preset 하나를 JSON 파일로 로컬 다운로드 가능하게 한다.
- 앱이 이메일/메신저/클라우드 공유 자체를 담당하지 않는다.
- 사용자가 다운로드한 JSON을 원하는 수단으로 전달한다.

Export JSON은 **Preset 구성 정보만** 포함한다.

포함:

- format/version 식별용 `version` (현재 `1` 권장)
- Preset `name`
- assets
  - Code
  - Name
  - Type
  - Market
  - Weight

제외:

- 가격 데이터
- 분석 결과
- 차트
- Start/End date
- Risk-free rate
- Benchmark 계산 결과
- Last Session

현재 LocalPortfolioStore의 asset record 구조를 최대한 재사용하고 별도 복잡한 export 모델을 만들지 않는다.

다운로드 파일명은 사용자에게 식별 가능한 형태로 한다. 예:

```text
주식70금30.portfolio.json
```

파일명 unsafe character 처리는 필요한 최소 범위로 한다.

#### Import

- 사용자가 Export된 `.json` 파일을 업로드할 수 있게 한다.
- 파일을 읽어 schema/version/name/assets를 검증한다.
- 정상 파일이면 로컬 Named Preset library에 등록한다.
- Import만으로 Portfolio나 Benchmark workspace에 자동 적용하지 않는다.
- 등록 후 기존 Portfolio/Benchmark Preset selector에서 일반 Preset과 동일하게 선택해 사용한다.

최소 validation:

- 지원하는 version인지
- name이 유효한지
- assets가 올바른 list인지
- 각 asset의 Code/Weight 및 필요한 metadata 구조가 유효한지
- 국내 영숫자 종목코드 보존
- malformed/손상 JSON이 앱 전체를 중단시키지 않고 이해 가능한 오류로 처리

Export → Import round-trip 시 동일한 Preset 구성과 metadata/weight가 보존되어야 한다.

동일 이름 Preset을 Import할 경우에는 현재 Named Preset의 동일 이름 저장 정책과 일관되게 overwrite 처리하되, 기존 저장 계층의 정책을 재사용한다.

### 6. 유지해야 할 기존 동작

- Portfolio/Benchmark 각각의 상단 Preset selector
- `새 구성 / 저장 / 다른 이름으로 저장`
- 동일 Preset library 공유
- Last Session 자동 저장/복원
- 비중 합계의 구성 상단 실시간 표시
- 종목명 검색 시 명시적 결과 행 선택
- 문자 포함 국내 주식/ETF/ETN 코드 지원
- Preset load만으로 자동 분석하지 않음
- Performance Pie legend 제거 + Allocation details 표
- 분석 엔진/가격 loader/optimization/Benchmark 계산 AS-IS

## Validation

최소 다음을 실제 Streamlit 흐름과 테스트로 확인한다.

1. `검색 장애 시 국내 종목코드 빠른 입력 사용` checkbox/UI가 완전히 사라짐
2. Portfolio 검색창에 `005930` 입력 시 직접 추가 가능
3. Portfolio 검색창에 `0137V0` 같은 영숫자 코드 직접 추가 가능
4. Portfolio 검색창에 `005930,069500,0137V0` 입력 시 batch 추가 가능
5. Benchmark 검색창에서도 동일하게 단일/복수 코드 direct-add 가능
6. 일반 종목명 입력은 기존 검색 결과 → 명시적 행 선택 → 추가 흐름 유지
7. direct code 기능에 대한 별도 안내 caption/warning이 표시되지 않음
8. 중복 코드 batch 입력/기존 종목 중복 시 중복 추가 없음
9. 검색/catalog 장애 상황에서 정확한 코드 직접 입력 fallback이 가능한 범위에서 유지됨
10. `[분석]` 버튼이 `Portfolio Analyzer` 타이틀 바로 아래에 보임
11. sidebar 하단의 기존 분석 버튼은 없어 분석 버튼이 하나만 존재
12. 상단 분석 버튼 클릭 시 기존 input validation과 분석이 정상 실행
13. `Preset 관리`에 `Delete`, `Export`, `Import` 제공
14. Delete는 기존 선택 Preset 삭제 동작 유지
15. Export한 JSON에 version/name/assets만 필요한 구조로 포함되고 분석 데이터는 없음
16. Export 파일을 Import하면 Named Preset library에 동일 구성이 복원됨
17. Import가 workspace에 자동 적용되거나 분석을 자동 실행하지 않음
18. malformed/지원하지 않는 JSON Import가 앱 전체를 죽이지 않음
19. 동일 이름 Import overwrite가 기존 정책과 일관되게 동작
20. 기존 Preset/Last Session/영숫자 코드/분석/Allocation UI 회귀 없음

관련 unit test 및 Streamlit AppTest를 보완하고, 완료 후 `ai-share/PROTOCOL.md`에 따라 결과를 `ai-share/agent-to-llm.md`에 기록한 뒤 현재 작업 브랜치 `feat/korean-market-v1`에 commit/push해줘.

## Addendum — 검색 결과 테이블 가독성 개선

위 요청의 기존 내용은 그대로 유지하고 아래 UX 개선을 추가한다.

현재 Portfolio/Benchmark 종목명 검색 결과 표는 긴 `Name` 때문에 sidebar 내부에서 가로 스크롤이 필요해지는 경우가 있다. cell-level hover tooltip을 위해 custom component/table로 교체하지 말고, 현재 `st.dataframe`의 single-row selection UX를 유지하면서 **컬럼을 단순화하고 Name에 최대한 폭을 할당**한다.

요구:

- Portfolio와 Benchmark 검색 결과 모두 동일하게 적용
- 검색 결과 사용자 표시 컬럼은 기본적으로 `Code | Name | Type`으로 단순화
- `Market`은 검색 결과 표에서는 숨긴다. 단, 내부 security metadata에서는 기존대로 보존한다.
- `Code`는 필요한 최소/compact 폭
- `Type`도 필요한 최소/compact 폭
- 남는 가로폭은 `Name`에 최대한 할당
- Name 원문 자체를 truncate하거나 변형하지 말고 display column 폭만 최적화한다.
- 현재의 `st.dataframe` single-row selection / 행 강조 / `[추가]` 동작은 그대로 유지한다.
- tooltip 구현을 위해 custom HTML/component나 별도 grid dependency를 추가하지 않는다.
- 목적은 sidebar 안에서 긴 종목명을 가능한 한 많이 바로 읽을 수 있게 하고 불필요한 가로 스크롤을 줄이는 것이다.

추가 Validation:

21. Portfolio 검색 결과가 `Code | Name | Type` 중심으로 표시되고 `Market`은 보이지 않음
22. Benchmark 검색 결과도 동일
23. Code/Type보다 Name 컬럼에 상대적으로 가장 큰 폭이 배정됨
24. 긴 종목명이 있는 검색 결과에서도 기존보다 가로 스크롤 의존성이 줄어듦
25. 행 선택 및 `[추가]` 동작은 기존과 동일하게 정상 작동

## Addendum — 검색/추가 액션을 같은 위치에 배치

위 요청과 기존 Addendum은 그대로 유지하고 다음 UX 개선을 추가한다.

현재 종목 검색 결과에서 행을 선택한 뒤 `[추가]` 버튼을 누르기 위해 sidebar를 다시 scroll해야 하는 경우가 있다. 이 반복 scroll을 줄이기 위해 **검색 버튼 바로 오른쪽에 추가 버튼을 배치**한다.

개념 배치:

```text
종목코드 또는 종목명
[ 입력........................ ]
[ 검색 ] [ 추가 ]

검색 결과 표
...
```

정확한 폭 비율은 좁은 sidebar에 맞게 판단해도 된다.

요구:

- Portfolio 검색/추가와 Benchmark 검색/추가 모두 동일하게 적용
- `[검색]`과 `[추가]`는 같은 액션 행에 나란히 배치하고 `[추가]`는 `[검색]`의 바로 오른쪽에 둔다.
- 일반 종목명 검색에서는 검색 결과 표에서 사용자가 명시적으로 행을 선택한 뒤 `[추가]`로 반영하는 기존 의미를 유지한다.
- 검색 결과 첫 행을 자동 선택하거나 자동 추가하지 않는다.
- 선택된 행 상태가 Streamlit rerun 때문에 불필요하게 사라져 `[추가]`가 동작하지 않는 문제가 없도록 현재 selection state 흐름을 확인한다.
- 정확한 단일/복수 종목코드 direct-add 흐름은 본 요청의 기존 규칙을 유지한다. 이 경우 검색 결과 행 선택을 요구하지 않는다.
- 버튼 이동 때문에 별도 안내 문구나 success/info 메시지를 추가하지 않는다.
- 목적은 검색 → 결과 선택 → 추가 과정에서 sidebar의 반복 vertical scroll을 줄이는 것이다.

추가 Validation:

26. Portfolio 검색 영역에서 `[검색] [추가]`가 같은 행에 표시됨
27. Benchmark 검색 영역도 동일
28. 검색 결과 행 선택 후 상단 `[추가]`로 정상 추가됨
29. 행 선택 없이 `[추가]` 시 기존 warning/error 정책이 유지됨
30. 단일/복수 종목코드 direct-add 및 종목명 검색 흐름에 회귀 없음
