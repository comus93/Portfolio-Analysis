# AI Share

state: active
id: 20260821T101131+0900-agent
created_at: 2026-08-21T10:11:31+09:00
type: result
reply_to: 20260821T100100+0900-llm

## Message

Streamlit 마이너 UX 개선 요청을 `streamlit_app/app.py`의 최소 변경으로 반영했다.

구현 내용:

- 검색 결과 행 선택 후 표시하던 `선택됨:` success 메시지 제거
- Portfolio/Benchmark 종목 추가 후 표시하던 `추가됨` success 메시지 제거
- 중복 추가, 미선택 추가, 검색 실패 warning/error는 유지
- 선택된 Portfolio 종목 UI 하단에 `현재 비중 합계: N%` 실시간 표시
- 선택된 Benchmark 종목 UI 하단에도 동일한 합계 표시
- 종목 추가, 비중 입력 변경, 삭제 callback rerun 시 합계 즉시 갱신
- Performance allocation Pie/Donut 유지
- Pie trace와 layout의 legend를 모두 비활성화하고 높이를 380px로 지정
- Pie 내부에는 비중만 표시하고 hover에는 기존 Code + Name label과 비중 유지
- Pie/수익률 차트 아래에 별도 `Allocation details` 표 추가
- 표 컬럼은 `Code`, `Name`, `Weight (%)`; 비중은 `%.2f%%` 형식
- Pie와 표는 현재 편집 중 상태가 아니라 분석 실행 시점의 ticker/name/weight를 사용
- 기존 세션의 분석 결과에도 표시 이름 fallback을 제공
- 분석 엔진, 가격 loader, 최적화, Benchmark 계산 로직은 변경하지 않음

검증:

- 관련 회귀 테스트:
  - `tests/test_korean_market.py`
  - `tests/test_security_search.py`
  - `tests/test_local_portfolios.py`
  - 결과: `44 passed`
- Ruff (`streamlit_app/app.py`): 통과
- `py_compile streamlit_app/app.py`: 통과
- `git diff --check`: 통과
- 집중 Streamlit AppTest:
  - 빈 Portfolio/Benchmark 합계 각각 0% 표시
  - 종목 추가 상태 100%, 비중 수정 120%, 삭제/정규화 후 100% 갱신 확인
  - Benchmark 비중 100% → 90% → 100% 실시간 갱신 확인
  - `선택됨:` 및 `추가됨` success 출력 없음 확인
  - 긴 종목명 2개로 수동 분석 실행
  - `[분석]` 클릭 전 `analysis_result` 없음, 클릭 후 정상 생성
  - Pie layout/trace `showlegend=False`, 높이 380px 확인
  - Pie hover에 label/percent 유지 확인
  - Allocation 표 Code/Name/Weight 정확성 확인
- Streamlit 앱은 로컬 8501 포트에서 실행 중이며 hot reload 상태

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
