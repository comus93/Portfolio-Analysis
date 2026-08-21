# AI Share

state: active
id: 20260821T123324+0900-agent
created_at: 2026-08-21T12:33:24+09:00
type: result
reply_to: 20260821T120900+0900-llm

## Message

Portfolio Preset UX 재구성 요청을 반영했다.

구현 내용:

- Portfolio와 Benchmark 작업공간 상단에 각각 독립적인 Preset selector 배치
- 두 selector가 동일한 Named Preset library를 공유하면서 조작한 작업공간에만 자동 적용
- selector의 `on_change` callback에서만 Preset을 load하여 일반 rerun이나 비중 편집 시 재적용 방지
- 각 작업공간에 `새 구성`, `저장`, `다른 이름으로 저장` 흐름 추가
- `새 구성`은 해당 작업공간의 종목, 비중, 검색 임시 상태, active Preset association과 분석 결과만 초기화
- active Preset이 있으면 `저장`으로 overwrite, 없으면 조건부 이름 입력을 통한 신규 저장
- `다른 이름으로 저장`은 조건부 이름 입력을 통해 복제하고 원본 Preset 유지
- 항상 노출되던 Preset 이름 input과 Portfolio/Benchmark source radio 제거
- 삭제를 하단 `Preset 관리` expander로 이동
- active Preset 삭제 시 작업공간 구성은 유지하고 association만 해제
- Portfolio/Benchmark 비중 합계를 각 종목 목록보다 위로 이동
- 빠른 입력에서도 100%가 아닌 편집 중 합계를 그대로 표시
- 빠른 입력 warning 문구 제거
- 빠른 입력 상태의 `새 구성`도 빈 작업공간을 Last Session에 저장하도록 처리
- 저장 schema/path, Last Session 복원, 검색/추가, 수동 분석, 문자 포함 KRX 코드, 기존 분석/차트 로직은 유지
- 좁은 sidebar에서 세 버튼이 한 줄에 압축되지 않도록 `다른 이름으로 저장`을 별도 폭으로 배치

검증:

- 집중 Streamlit AppTest 신규 4건:
  - 공유 Preset의 Portfolio/Benchmark 독립 자동 load
  - rerun 후 편집값 유지
  - Portfolio/Benchmark 개별 `새 구성`, Named Preset 유지, Last Session 반영
  - active Preset overwrite, Save As 신규 생성과 원본 유지
  - 삭제 후 association 해제 및 현재 구성 유지
  - 이름 입력의 조건부 노출
  - 빠른 입력 warning 제거와 80% live 합계 표시
  - 빠른 입력 `새 구성`의 빈 Last Session 저장
- 관련 저장 계층 테스트 `tests/test_local_portfolios.py` 포함 결과: `15 passed`
- Ruff (`streamlit_app/app.py`, `tests/test_streamlit_preset_ux.py`): 통과
- `py_compile streamlit_app/app.py`: 통과
- `git diff --check`: 통과

전체 회귀 테스트: 미실행 (사용자 요청 없음)

Blockers: none.
