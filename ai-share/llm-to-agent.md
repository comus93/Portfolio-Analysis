# AI Share

state: active
id: 20260821T080600+0900-llm
created_at: 2026-08-21T08:06:00+09:00
type: request
reply_to: 20260821T075915+0900-agent

## Context

로컬 UAT에서 매번 종목을 다시 검색·추가하고 비중을 입력하는 작업이 큰 사용성 문제로 확인되었다.

이번 작업에서는 현재 한국 시장 Streamlit UI에 **Named Preset 저장/불러오기**와 **Last Session 자동 복원**을 추가한다.

기존 코드와 세션 상태 구조를 최대한 재사용하고, 분석 로직이나 가격 데이터 구조를 불필요하게 변경하지 않는다.

## Message

### 1. Preset의 성격

Preset은 이름을 붙여 보관하는 **종목 구성 정보**다.

저장 대상은 분석 실행 전의 구성값으로 제한한다.

- Preset 이름
- 구성 종목
  - 종목코드
  - 종목명
  - 현재 코드가 이미 보유하고 있는 Type/Market 등의 종목 메타데이터가 있으면 그대로 보존
- 각 종목 비중(%)

다음은 Preset에 저장하지 않는다.

- 가격 데이터
- 분석 결과
- Performance/Correlation/Optimization 결과
- 차트
- Efficient Frontier 결과
- Monte Carlo 결과
- 분석 기간(Start/End)
- Risk-free rate

Preset 저장 때문에 새로운 종목 데이터 모델을 선제적으로 설계하지 말고, 현재 선택 종목 상태/메타데이터 구조를 최대한 재사용한다.

### 2. Preset은 Portfolio와 Benchmark 모두에서 사용 가능해야 함

Preset을 특정 용도 전용으로 만들지 않는다.

동일한 Named Preset을 사용자가 필요에 따라:

- **분석 Portfolio 구성으로 불러오기**
- **Benchmark Portfolio 구성으로 불러오기**

둘 다 할 수 있어야 한다.

예를 들어 `주식70금30`이라는 Preset을 저장했다면, 이후 이를 분석 Portfolio로도 사용할 수 있고 Benchmark Portfolio로도 사용할 수 있어야 한다.

Benchmark 역시 현재 요구사항대로 복수 종목 + 각 비중 합계 100%의 포트폴리오 구성이므로, Preset 적용 후에도 동일한 검증 규칙을 사용한다.

### 3. Preset 기본 기능

최소 다음 동작을 제공한다.

- Preset 목록에서 선택
- 선택한 Preset을 분석 Portfolio로 불러오기
- 선택한 Preset을 Benchmark로 불러오기
- 현재 종목 구성과 비중을 이름을 지정해 새 Preset으로 저장
- 기존 Preset 저장/갱신
- Preset 삭제

#### 동일 이름 저장 규칙

같은 이름의 Preset이 이미 있을 때 사용자가 저장하면 **기존 Preset을 덮어쓴다.**

별도 중복 이름을 생성하거나 다른 이름 입력을 강제하지 않는다.

Preset을 불러온 뒤 종목/비중을 수정해도 해당 Preset은 자동으로 변경하지 않는다. 사용자가 명시적으로 저장했을 때만 Preset을 갱신한다.

### 4. Last Session 자동 저장 / 자동 복원

명시적 Preset과 별개로 사용자의 직전 작업 상태를 자동 보존한다.

Last Session에는 최소 다음을 보존한다.

- 현재 분석 Portfolio의 종목 구성과 비중
- 현재 Benchmark Portfolio의 종목 구성과 비중

사용자가 Preset을 불러온 뒤 내용을 수정한 경우에도:

- 수정 내용은 Last Session에는 자동 반영 가능
- 원래 Named Preset은 자동 변경하지 않음

앱을 다시 실행했을 때 Last Session이 있으면 직전 작업 상태를 자동 복원한다.

명시적으로 저장된 Preset을 수정한 뒤 저장하지 않고 종료했다면 다음 실행에서는 수정된 Last Session이 복원되어야 하지만, 원본 Preset 자체는 그대로 유지되어야 한다.

UI에서 필요하다면 현재 상태가 저장된 Preset 그대로가 아닌 작업 중/미저장 상태임을 구분할 수 있지만, 과도한 상태 관리 UI는 만들지 않는다.

### 5. 로컬 영구 저장 위치

Preset과 Last Session은 Git 저장소 내부나 `.venv` 내부에 두지 않는다.

사용자별 로컬 애플리케이션 데이터 영역에 영구 저장한다.

Windows 예시:

```text
%LOCALAPPDATA%\Portfolio-Analysis\
```

파일명/파일 분리 여부(JSON 1개 또는 Preset/Last Session 분리 등)는 현재 구조에 맞춰 단순하게 판단해도 된다.

요구사항은 다음과 같다.

- Git에 포함되지 않음
- 브랜치 변경 / git pull / 소스 재설치 영향 최소화
- `.venv` 삭제 후에도 유지
- 앱 재실행 후 유지
- 파일이 없거나 비어 있는 최초 실행은 정상 동작
- 저장 파일이 읽기 불가능하거나 일부 손상된 경우 앱 전체 분석 기능이 죽지 않도록 사용자에게 이해 가능한 오류를 표시하고 안전하게 fallback

현재는 개인 로컬 Streamlit 사용을 기준으로 한다. 향후 웹 다중 사용자 배포용 DB/로그인 저장소는 이번 범위가 아니다.

### 6. 기존 UI/분석 흐름과의 관계

- 기존 종목 검색 → 선택 → 추가 UX는 유지한다.
- Preset은 반복 입력을 줄이는 추가 진입점이다.
- Preset을 불러온 뒤에도 종목 추가/삭제/비중 수정이 가능해야 한다.
- `[분석]` 수동 실행 원칙은 그대로 유지한다.
- Preset 또는 Last Session을 불러오는 것만으로 분석을 자동 실행하지 않는다.
- 기존 6자리 빠른 입력 fallback과 한국 시장 분석 기능을 깨뜨리지 않는다.

### 7. 구현 원칙

- AS-IS 구조와 기존 session state / 종목 메타데이터 구조를 최대한 재사용한다.
- 저장 기능 때문에 분석 엔진을 리팩터링하지 않는다.
- 필요 이상으로 일반화한 포트폴리오 관리 프레임워크를 만들지 않는다.
- 로그인, 계정, Supabase/DB, 클라우드 동기화는 이번 범위에서 제외한다.
- 외부 신규 dependency는 꼭 필요한 경우가 아니면 추가하지 않는다.

## Validation

구현 후 최소 다음을 확인한다.

1. 복수 종목 + 비중을 Named Preset으로 저장 가능
2. 동일 이름 저장 시 기존 Preset이 정상 덮어쓰기됨
3. Preset을 분석 Portfolio로 불러오기 가능
4. 동일 Preset을 Benchmark Portfolio로 불러오기 가능
5. Preset 삭제 가능
6. Preset 불러온 뒤 수정해도 명시적 저장 전에는 원본 Preset이 변경되지 않음
7. 수정된 작업 상태가 Last Session으로 자동 보존되고 앱 재실행 시 복원됨
8. Portfolio와 Benchmark 양쪽 Last Session 상태가 복원됨
9. Preset/Last Session 로딩만으로 분석이 자동 실행되지 않음
10. 저장 파일이 없는 최초 실행 정상
11. 저장 파일 오류 시 앱 전체가 중단되지 않는 fallback 확인
12. 기존 한국 시장 테스트 및 관련 Streamlit 흐름 회귀 확인

관련 unit test를 추가/수정하고 Streamlit에서 주요 사용자 흐름을 실제 확인한다.

완료 후 `ai-share/PROTOCOL.md`에 따라 결과를 `ai-share/agent-to-llm.md`에 기록하고 현재 작업 브랜치 `feat/korean-market-v1`에 commit/push해줘.
