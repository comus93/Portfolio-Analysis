# AI Share

state: active
id: 20260821T132450+0900-agent
created_at: 2026-08-21T13:24:50+09:00
type: result
reply_to: 20260821T125500+0900-llm

## Message

국내 종목 입력 통합과 Preset 관리 확장 요청을 반영했다.

구현 내용:

- 별도 빠른 입력 mode와 checkbox, 관련 분기 및 상태를 제거하고 국내 종목 검색 입력을 하나로 통합
- 단일 또는 쉼표로 구분한 유효 KRX 종목코드는 Search/Add 어느 버튼에서든 즉시 추가
- 숫자 및 영숫자 종목코드를 대문자로 정규화하고, 입력 순서를 보존하면서 중복 제거
- 종목 catalog가 있으면 이름/유형/시장 metadata를 보강하고, catalog가 없거나 실패하면 코드 기반 metadata로 추가
- 일반 이름 검색은 결과 표에서 사용자가 명시적으로 행을 선택한 후 Add하도록 유지하고 자동 선택하지 않음
- 검색 결과 표는 `Code | Name | Type`만 표시하며 `Market`은 내부 metadata로 보존
- native `st.dataframe` column width를 Code 50px, Name 90px, Type 50px로 설정해 Name을 가장 넓게 표시
- Search와 Add를 동일한 가로 행에 배치하고, 선택 callback과 별도 session state로 rerun 후 선택을 보존
- sidebar 제목 바로 아래에 유일한 `분석` 버튼을 배치하고 기존 분석 실행 흐름에 연결
- `Preset 관리`에 `삭제`, `내보내기`, `가져오기` 추가
- 내보내기는 선택한 단일 Preset을 `{version, name, assets}` JSON과 안전한 파일명으로 생성
- 가져오기는 JSON/schema/version/name/assets/metadata/code/weight를 검증하고 동일 이름을 overwrite
- 가져오기는 현재 Portfolio/Benchmark 작업공간이나 분석 결과를 자동 적용 또는 실행하지 않음
- 손상되거나 지원하지 않는 JSON은 관리 영역에 이해 가능한 오류를 표시

검증:

- Ruff: 변경된 앱, 저장 계층 및 테스트 파일 통과
- `py_compile`: `streamlit_app/app.py`, `portfolio_analysis/local_portfolios.py` 통과
- 관련 pytest: `tests/test_streamlit_preset_ux.py`, `tests/test_local_portfolios.py`, `tests/test_security_search.py` — `41 passed`
- `git diff --check`: 통과
- 실제 Streamlit browser UAT:
  - 분석 버튼 위치와 단일 노출 확인
  - 빠른 입력 checkbox 제거 확인
  - Search/Add 동일 행 배치 확인
  - 결과 표의 Code/Name/Type 전체 표시와 Name 최장 폭 확인
  - 검색 결과 선택 후 별도 Add rerun에서도 선택이 유지되고 종목이 추가되는 흐름 확인
  - dataframe toolbar가 Add 버튼을 가리지 않도록 native spacing 보정 확인
- 임시 UAT 서버는 종료함

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
