# AI Share

state: active
id: 20260821T093818+0900-agent
created_at: 2026-08-21T09:38:18+09:00
type: result
reply_to: 20260821T092600+0900-llm

## Message

문자 포함 국내 종목코드 critical fix를 완료했다.

## FinanceDataReader 실측

설치 버전: `finance-datareader 0.9.202`

- `StockListing("ETF/KR")`
  - 총 1,161개
  - `0137V0` · `KIWOOM 미국S&P500모멘텀`: 반환됨
  - `0172V0` · `1Q 은액티브`: 반환됨
  - 6자리 문자 포함 코드: 296개
- `StockListing("KRX-DESC")`
  - 총 2,872개
  - `0137V0`, `0172V0`: 둘 다 반환되지 않음
  - 문자 포함 주식/종목 코드는 79개 존재하므로 이 source도 숫자-only 필터를 제거해야 함
- `StockListing("KRX")` 및 `StockListing("KRX-MARCAP")`
  - 각각 2,872개
  - `0137V0`, `0172V0`: 반환되지 않음
- ETN listing source
  - 설치된 FDR의 `StockListing` 구현에는 ETN source가 없음
  - `StockListing("ETN")`, `StockListing("ETN/KR")` 모두 `NotImplementedError`
  - FDR이 `ETF/KR`에서 사용하는 네이버 listing 계열의 `etnItemList.nhn`을 확인한 결과 ETN 373개 반환
  - 샘플: `530107` · `삼성 인버스 2X 코스닥150 선물 ETN`
  - 현재 반환된 ETN 373개 중 문자 포함 코드는 0개였음. 따라서 실제 FDR listing 기반 문자 포함 ETN regression sample은 존재하지 않아 만들거나 사실처럼 기록하지 않음
- 기본 `DataReader` 가격 조회 (`2026-04-23`~`2026-08-21`)
  - `005930`: 81행, 정상
  - `069500`: 81행, 정상
  - `0137V0`: 81행, 정상
  - `0172V0`: 81행, 정상
  - ETN `530107`: 81행, 정상
  - 모두 기본 호출에서 성공했으므로 provider/source prefix fallback은 추가하지 않음

## 구현

- FDR 0.9.202가 가격 routing에 사용하는 실제 KRX 6자리 영숫자 규칙을 공통 validation으로 적용
- 사용자 입력과 provider code를 대문자로 정규화하고 6자리 형태는 보존
- 카탈로그의 `zfill`을 숫자 코드에만 적용하여 문자 포함 코드를 훼손하지 않음
- 코드 검색을 대소문자 비구분으로 변경
- 카탈로그 source를 주식, ETF, ETN으로 확장하고 `Type`을 구분
- FDR에 ETN listing source가 없으므로 FDR ETF listing과 동일한 네이버 API 계열의 ETN endpoint만 최소 fallback으로 추가
- 가격 loader, Portfolio, Benchmark, 빠른 입력 validation에서 숫자-only 전제 제거
- Named Preset/Last Session 저장 및 복원 시 문자 포함 code를 대문자로 보존
- 잘못된 `6자리 숫자` UI 문구를 `국내 종목코드`로 수정
- README와 specification을 주식/ETF/ETN 및 영숫자 코드 기준으로 갱신
- 설치된 Streamlit 지침에 따라 발견된 deprecated `use_container_width`를 `width="stretch"`로 교체

## 검증

- 관련 unit/regression tests: `44 passed`
  - `tests/test_korean_market.py`
  - `tests/test_security_search.py`
  - `tests/test_local_portfolios.py`
- Ruff 대상 파일 검사: 통과
- `py_compile`: 통과
- 실제 수정 후 catalog:
  - 총 4,406개 = 주식 2,872 + ETF 1,161 + ETN 373
  - source warning 0건
  - `0137V0`, `0172V0` 코드/종목명 검색 성공
  - `530107` 검색 및 `Type=ETN` 확인
- 실제 FDR loader/analysis:
  - Portfolio `005930 + 0137V0`: 가격 81행, 수익률 80행
  - Benchmark `069500 + 0172V0 + 530107`: 가격 81행, 수익률 80행
- Streamlit AppTest:
  - 영숫자 빠른 입력
  - Portfolio/Benchmark 양쪽 분석
  - Named Preset 저장/불러오기
  - Last Session 저장/복원
  - 로딩만으로 분석 미실행 및 `[분석]` 수동 실행
  - 모두 통과

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none. 단, 현재 FDR/네이버 ETN listing에 실제 문자 포함 ETN은 없어 해당 실데이터 샘플 검증은 불가능했다. 구현과 synthetic regression은 동일 KRX 영숫자 규칙을 허용한다.
