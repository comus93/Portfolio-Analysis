# AGENTS.md

## 프로젝트

이 저장소는 `engineerinvestor/Portfolio-Analysis`의 fork다.

이 fork의 목표는 가능한 범위에서 원본 프로젝트의 아키텍처, 분석 로직,
최적화 로직, 시각화와 Streamlit UI를 재사용하면서 국내 상장 주식과 ETF를
지원하도록 기존 포트폴리오 분석 애플리케이션을 확장하는 것이다.

명확한 이유 없이 원본 프로젝트에서 이미 정상 동작하는 기능을 다시 구현하지
않는다.

## 기준 문서

구현을 시작하기 전에 다음을 읽는다.

1. `AGENTS.md`
2. `docs/specification.md`
3. `ai-share/PROTOCOL.md`
4. 작업과 관련된 기존 소스 코드와 테스트

`CLAUDE.md`는 원본 저장소에서 상속된 문서이며 기존 아키텍처를 이해하기 위한
참고 자료로 사용할 수 있다.

`CLAUDE.md`가 `AGENTS.md` 또는 `docs/specification.md`와 충돌하면 fork 전용
문서인 `AGENTS.md`와 `docs/specification.md`를 우선한다.

## 개발 원칙

- 광범위한 재작성보다 작고 집중된 변경을 우선한다.
- 가능한 경우 기존 분석 및 최적화 코드를 재사용한다.
- 명세상 변경이 필요한 경우가 아니라면 기존 공개 API를 보존한다.
- 시장 데이터 관련 책임과 포트폴리오 분석 로직을 분리한다.
- 불필요한 framework, 추상화 또는 dependency를 추가하지 않는다.
- 명시적으로 요청받지 않은 후순위 기능을 구현하지 않는다.
- 기능 작업 중 관련 없는 코드 정리나 refactoring을 하지 않는다.
- 원본 프로젝트의 MIT license와 attribution을 보존한다.

## 개발 환경

- Python 3.12를 기본 개발 환경으로 사용한다.
- 로컬 Python 환경과 dependency 관리에는 `uv`를 우선 사용한다.
- 프로젝트 dependency는 `pyproject.toml`에 선언한다.
- 가상환경, secret, credential 또는 로컬 설정을 commit하지 않는다.

## 테스트 및 검증 범위

작업을 완료하기 전에 다음 원칙에 따라 검증한다.

- 기본적으로 변경된 기능과 직접 관련된 기존 테스트를 실행한다.
- 변경된 동작에 대한 테스트를 추가하거나 수정한다.
- 공통 코드 또는 공개 API가 변경된 경우에만 합리적인 범위의 인접 회귀
  테스트를 추가로 실행한다.
- 에이전트는 전체 테스트 suite를 기본적으로 실행하지 않는다.
- 전체 테스트 suite는 사용자가 명시적으로 요청한 경우에만 실행한다.
- 가능한 경우 unit test가 실제 외부 시장 데이터 서비스에 의존하지 않도록
  외부 호출을 mock 또는 dependency injection으로 분리한다.
- UI 또는 데이터 계층을 변경한 경우 전체 Python 테스트 대신 관련 테스트와
  Streamlit 기동 또는 집중된 smoke/AppTest 검증을 수행한다.
- 문서만 변경한 경우 코드 테스트를 실행하지 않아도 된다. 대신 링크, 서식,
  `git diff --check` 등 변경 내용에 맞는 검증을 수행한다.
- 테스트 또는 환경 blocker를 조용히 우회하지 말고 보고한다.
- 최종 결과에는 수행한 검증의 정확한 범위를 명시한다.
- 전체 테스트를 실행하지 않았다면 `전체 회귀 테스트: 미실행 (사용자 요청 없음)`
  이라고 명시한다.
- 일부 관련 테스트만 실행한 결과를 전체 회귀 테스트 결과처럼 표현하지 않는다.

## Git

- `main`에서 직접 구현하지 않는다.
- 현재 feature 또는 fix branch에서 개발한다.
- `main`으로 merge하지 않는다.
- force push하지 않는다.
- 완료된 작업은 현재 작업 branch에만 push한다.
- 개발 환경에 이미 설정된 Git identity를 사용한다.
- 원본 작성자의 identity로 commit authorship을 덮어쓰지 않는다.

사용자는 `main`으로 merge하기 전에 작업 branch를 검토한다.

## AI 협업

ChatGPT와 Codex 간 통신 및 session handover는 다음 문서를 따른다.

`./ai-share/PROTOCOL.md`

작업을 완료하면 해당 규약에 따라 필요한 구현 요약, 테스트 결과, blocker와
관련 결정을 기록한다.
