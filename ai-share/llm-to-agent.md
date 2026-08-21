# AI Share

state: active
id: 20260821T092600+0900-llm
created_at: 2026-08-21T09:26:00+09:00
type: request
reply_to: 20260821T081937+0900-agent

## Context

로컬 UAT 중 비교적 최근 상장된 국내 종목이 검색되지 않는 critical issue가 확인되었다.

재현 예:

- `0137V0` · `KIWOOM 미국S&P500모멘텀`
- `0172V0` · `Q 은액티브`

현재 구현을 확인해보면 국내 종목코드를 숫자 6자리로만 가정하는 제약이 있다.

- `KoreanSecurityDirectory._normalize_listing()`에서 `Code`를 `\d{6}`으로 필터링
- `KoreanDataLoader.TICKER_PATTERN`이 `^\d{6}$`
- Streamlit UI/빠른 입력/Benchmark validation 등에도 숫자-only 또는 "6자리 숫자" 전제가 있을 가능성이 있음

이번 수정은 위 두 종목만 예외처리하는 것이 아니라, **국내 상장 주식/ETF/ETN의 실제 종목코드 체계에서 문자 포함 코드도 정상 지원하도록 숫자-only 가정 자체를 제거**하는 작업이다.

AS-IS 구조를 최대한 재사용하고 최소 변경으로 해결한다.

## Message

### 1. 먼저 FinanceDataReader 원본 동작을 실측할 것

코드를 수정하기 전에 현재 설치된 FinanceDataReader에서 아래를 직접 확인하고 결과를 `agent-to-llm.md`에 기록해줘.

1. `StockListing("ETF/KR")`에서 `0137V0`, `0172V0`가 반환되는지
2. `StockListing("KRX-DESC")` 등 현재 앱이 사용하는 관련 listing source에서 두 코드가 반환되는지
3. ETN을 제공하는 FDR listing source가 무엇인지 확인하고, 문자 포함 ETN 코드가 실제로 어떤 형태로 반환되는지 샘플 확인
4. `DataReader("0137V0", ...)`, `DataReader("0172V0", ...)`가 가격 데이터를 정상 반환하는지
5. 기본 `DataReader`가 실패하는 경우에만 FDR이 지원하는 provider/source prefix 또는 다른 FDR 경로를 비교 테스트

목적은 **종목 마스터(listing) 문제와 가격 데이터 문제를 분리해서 확인**하는 것이다.

FDR source를 추측만으로 교체하지 말고 실제 호출 결과를 근거로 판단한다.

### 2. 국내 종목코드의 숫자-only 가정을 앱 전체에서 제거

repo 전체에서 아래와 같은 전제를 검색해서 확인한다.

- `isdigit()`
- `\d{6}` / `^\d{6}$`
- "6자리 숫자"
- 숫자형 ticker/code validation
- 숫자-only를 전제로 한 zero-padding/normalization

국내 상장 주식/ETF/ETN의 실제 코드에서 영문자가 포함된 코드를 보존하고 정상 처리해야 한다.

예:

- 기존 숫자 코드: `005930`, `069500`
- 문자 포함 코드: `0137V0`, `0172V0`
- ETN도 실제 FDR listing에서 확인한 문자 포함 코드 샘플을 regression test에 포함

코드에 영문자가 있으면 대소문자 처리 때문에 다른 종목으로 취급되지 않도록 적절히 정규화하되, **실제 provider가 반환한 종목코드를 훼손하지 말 것**.

단순히 특정 regex 하나만 바꾸고 끝내지 말고 검색 → 추가 → 저장 → 가격 조회 → 분석까지 종목코드가 지나가는 경로를 확인한다.

### 3. 검색 카탈로그에 ETF/ETN이 실제 포함되도록 확인

현재 `KoreanSecurityDirectory`의 catalog source가 주식/ETF 중심이다.

- ETF 문자 포함 코드가 catalog normalization 단계에서 버려지지 않게 수정
- ETN listing source가 현재 catalog에 없다면 FDR에서 실제 제공되는 source를 확인한 뒤 **기존 catalog 구조를 최대한 유지하면서 필요한 최소 범위로 추가**
- 검색 결과의 `Type`에는 주식/ETF/ETN을 구분할 수 있도록 기존 구조 안에서 반영
- 중복 Code 처리 등 기존 동작은 유지

새로운 종목 마스터 프레임워크나 별도 DB를 만들지 않는다.

### 4. 가격 로더/분석 경로도 문자 포함 코드를 허용

검색에서 종목을 찾을 수 있어도 `KoreanDataLoader`에서 거절되면 해결이 아니다.

- 문자 포함 국내 종목코드를 가격 조회로 전달 가능해야 함
- 기존 숫자 종목코드 동작 유지
- Portfolio와 Benchmark 모두 동일하게 지원
- Named Preset / Last Session에 저장된 문자 포함 코드도 정상 복원 및 분석 가능해야 함
- 빠른 입력 모드가 유지된다면 문자 포함 코드도 입력/분석 가능해야 함

실제 FDR 가격 조회가 특정 상품 유형에서 별도 source 표기를 요구한다면, 1단계 실측 결과를 근거로 AS-IS loader에 최소한의 대응을 추가한다.

### 5. UI 문구 수정

실제 제약이 숫자 6자리가 아니므로 사용자에게 잘못된 정보를 주는 문구를 수정한다.

예:

- `6자리 숫자 코드` → `종목코드` 또는 `국내 종목코드`
- validation 오류 메시지도 숫자-only 표현 제거

기존 UI 구조 자체를 이번 critical fix 때문에 재설계하지 않는다.

### 6. 이번 작업에서 하지 않을 것

- `0137V0`, `0172V0`만 hard-code 예외처리
- 신규 종목 목록을 수동으로 코드/CSV에 박아 넣기
- 근거 없이 FDR을 버리고 별도 데이터 provider로 전환
- 새로운 종목 master DB 구축
- 분석 엔진 리팩터링

먼저 FDR이 실제 데이터를 제공하는지 확인하고, 제공한다면 현재 앱의 잘못된 validation/filtering을 바로잡는 것이 우선이다.

## Validation

최소 다음을 확인해줘.

1. `005930` 검색/추가/가격 조회/분석 정상
2. `069500` 검색/추가/가격 조회/분석 정상
3. `0137V0`가 종목코드와 종목명으로 검색되고 추가 가능
4. `0172V0`가 종목코드와 종목명으로 검색되고 추가 가능
5. `0137V0`, `0172V0` 실제 가격 데이터 조회 및 분석 가능 여부 확인
6. FDR listing에서 확인한 문자 포함 ETN 샘플도 검색/추가/가격 조회 가능 여부 확인
7. Portfolio와 Benchmark 양쪽에서 문자 포함 코드 사용 가능
8. 빠른 입력 모드에서도 문자 포함 코드 사용 가능
9. 문자 포함 종목을 Named Preset으로 저장/불러오기 가능
10. Last Session 자동 복원 후 동일 코드가 보존되고 분석 가능
11. 기존 숫자-only 종목 회귀 없음
12. 관련 unit/regression test 및 Streamlit 사용자 흐름 확인

만약 FDR 자체가 특정 신규 ETF/ETN의 listing 또는 가격을 반환하지 못한다면, **어느 FDR source에서 무엇이 실패하는지 실측 결과를 먼저 보고하고**, 확인된 최소 fallback 방안을 구현하거나 blocker로 명확히 기록한다.

완료 후 `ai-share/PROTOCOL.md`에 따라 결과와 FDR 실측 내용을 `ai-share/agent-to-llm.md`에 기록하고 현재 작업 브랜치 `feat/korean-market-v1`에 commit/push해줘.
