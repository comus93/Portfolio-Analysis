# Portfolio-Analysis 국내 시장 지원 v1 명세

## 1. 목적

이 프로젝트는 `engineerinvestor/Portfolio-Analysis`를 fork하여 국내 상장 주식/ETF를 분석할 수 있도록 확장한다.

새로운 포트폴리오 분석 엔진을 처음부터 다시 만드는 것이 목적이 아니다.

기존 프로젝트가 이미 제공하는 분석, 최적화, 시각화, Streamlit UI를 최대한 재사용하고, 국내 시장 지원에 필요한 데이터 계층과 입력 UI를 중심으로 최소한의 변경을 수행한다.

---

## 2. 개발 순서

개발은 아래 두 단계로 진행한다.

1. Phase 1: 원본 프로젝트 정상 동작 확인
2. Phase 2: 국내 시장 지원 v1 구현

**Phase 1의 정상 동작이 확인되기 전에는 Phase 2 구현을 시작하지 않는다.**

---

## 3. Phase 1: 원본 프로젝트 정상 동작 확인

### 3.1 목적

현재 fork 상태에서 기존 프로젝트가 정상 동작하는지 먼저 확인한다.

이 단계는 이후 국내 시장 기능을 추가했을 때 발생하는 문제를 기존 문제와 구분하기 위한 기준선(baseline)을 확보하는 것이 목적이다.

### 3.2 확인 항목

다음을 확인한다.

- Python 개발 환경 구성
- 프로젝트 의존성 설치
- 기존 테스트 실행
- Streamlit 애플리케이션 실행
- 기존 Yahoo Finance 데이터 조회
- 기존 Portfolio Performance 분석
- 기존 Portfolio Optimization 기본 동작

기존 Yahoo Finance ticker를 사용하는 간단한 포트폴리오로 end-to-end 동작을 확인한다.

### 3.3 최소 완료 기준

최소한 아래 조건을 만족해야 한다.

1. 기존 테스트 실행 결과를 확인한다.
2. Streamlit 앱이 정상적으로 시작된다.
3. Yahoo Finance를 통한 기존 종목 데이터 조회가 성공한다.
4. 기존 Portfolio Performance 분석이 실행된다.
5. Max Sharpe 최적화가 실행된다.
6. Minimum Volatility 최적화가 실행된다.

### 3.4 기존 문제 발견 시 처리

Phase 1에서 문제가 발견되면 다음 원칙을 따른다.

- 먼저 원인을 확인한다.
- 개발 환경/의존성 문제인지 기존 코드 문제인지 구분한다.
- 국내 시장 지원과 관계없는 대규모 수정이나 리팩터링은 하지 않는다.
- 정상 동작 확인에 꼭 필요한 최소 수정만 수행한다.
- 해결할 수 없는 문제는 blocker로 보고한다.

### 3.5 결과 보고

Phase 1 검증 결과는 `ai-share/PROTOCOL.md`에 따라 `ai-share/agent-to-llm.md`에 기록하고 GitHub에 push한다.

최소한 다음 내용을 포함한다.

- 사용한 Python 버전
- 개발 환경 및 의존성 설치 방법
- 기존 테스트 결과
- Streamlit 실행 결과
- 실제 검증에 사용한 ticker
- Portfolio Performance 실행 결과
- Max Sharpe / Minimum Volatility 실행 결과
- 발견된 기존 문제 또는 blocker

---

## 4. Phase 2: 국내 시장 지원 v1

### 4.1 기본 방향

국내 상장 주식과 ETF의 가격 데이터를 FinanceDataReader(FDR)를 통해 사용할 수 있도록 기존 데이터 계층을 확장한다.

가능한 경우 기존 분석 엔진, 최적화 로직, 시각화 로직, Streamlit 구조는 그대로 재사용한다.

기존 Yahoo Finance 지원을 불필요하게 제거하지 않는다. 구조적으로 무리가 없다면 기존 provider와 국내 시장 provider가 공존할 수 있도록 한다.

국내 시장 지원을 위해 기존 전체 구조를 재작성하지 않는다.

### 4.2 데이터 조회

필수 요구사항:

- FinanceDataReader를 사용해 국내 상장 주식과 국내 상장 ETF의 가격 데이터를 조회할 수 있어야 한다.
- 입력 종목은 국내 6자리 종목코드를 기준으로 한다.
- 사용자가 시작일과 종료일을 지정할 수 있어야 한다.
- 여러 종목의 가격 데이터를 동일 기간 기준으로 분석에 사용할 수 있어야 한다.
- 데이터 누락이나 조회 실패 시 사용자에게 원인을 이해할 수 있는 오류를 보여준다.

초기 버전에서는 종목명 검색이나 autocomplete를 구현하지 않는다.

예시 입력:

```text
069500, 411060, 487240
```

### 4.3 Streamlit 입력

Streamlit 웹 UI에서 최소한 다음 항목을 직접 입력할 수 있어야 한다.

- 종목코드
- 분석 시작일
- 분석 종료일
- 각 종목의 포트폴리오 비중
- Benchmark 종목코드

비중은 합계가 100% 또는 1.0이 되도록 검증한다.

초기 버전에서는 프리셋 검색 UI나 종목명 기반 자동완성을 요구하지 않는다.

### 4.4 Performance 분석

기존 Portfolio Performance 기능을 국내 종목 데이터에서도 사용할 수 있어야 한다.

가능한 범위에서 기존 계산 로직과 출력 구조를 재사용한다.

### 4.5 Correlation Matrix

포트폴리오 구성 종목 간 수익률 상관관계 행렬을 제공한다.

최소 요구사항:

- 일별 수익률을 기준으로 상관계수를 계산한다.
- 표 또는 heatmap 형태로 Streamlit UI에서 확인할 수 있어야 한다.
- 기존 visualization 구조를 재사용할 수 있으면 우선 활용한다.

### 4.6 Portfolio Optimization

기존 최적화 로직을 재사용하여 국내 종목 데이터에서도 아래 기능이 동작해야 한다.

- Max Sharpe
- Minimum Volatility
- Risk Parity
- Efficient Frontier

기존 공개 API를 불필요하게 변경하지 않는다.

### 4.7 Benchmark 비교

사용자가 국내 종목코드 또는 ETF 코드를 Benchmark로 지정할 수 있어야 한다.

기존 Benchmark Comparison 기능을 가능한 한 재사용한다.

Benchmark와 포트폴리오 데이터의 날짜를 적절히 정렬하여 비교해야 한다.

---

## 5. v1 필수 기능

v1의 필수 범위는 다음과 같다.

1. 국내 주식 / 국내 ETF 데이터 조회
2. Streamlit 웹에서 6자리 종목코드 직접 입력
3. 분석 기간 입력
4. 포트폴리오 비중 입력
5. Portfolio Performance 분석
6. Correlation Matrix
7. Max Sharpe
8. Minimum Volatility
9. Risk Parity
10. Efficient Frontier
11. Benchmark 비교

---

## 6. v1 후순위 기능

아래 기능은 이번 v1 범위에 포함하지 않는다.

- 종목명 검색 / autocomplete
- HTML Tear Sheet 개선
- Monte Carlo 개선 또는 국내화
- Factor Analysis
- 별도 Backtest framework
- 포트폴리오 저장
- 로그인 / 계정 기능

기존 기능이 이미 존재하더라도 국내시장 v1 구현을 위해 필요하지 않다면 확장하거나 재작성하지 않는다.

---

## 7. 구현 원칙

- 기존 구현을 최대한 재사용한다.
- 변경 범위는 국내 시장 지원에 필요한 부분에 집중한다.
- 데이터 provider와 분석 로직의 결합을 불필요하게 키우지 않는다.
- 기존 공개 API와 테스트를 가능한 한 보존한다.
- 라이브 외부 데이터에 의존하지 않아도 되는 로직은 unit test에서 외부 호출과 분리한다.
- 불필요한 추상화, framework, dependency를 추가하지 않는다.
- 관련 없는 코드 정리나 대규모 리팩터링을 함께 수행하지 않는다.

---

## 8. Phase 2 완료 기준

다음을 만족하면 국내 시장 지원 v1 구현이 완료된 것으로 본다.

- 국내 6자리 종목코드로 가격 조회가 가능하다.
- 2개 이상의 국내 종목/ETF로 포트폴리오 분석이 가능하다.
- 사용자가 기간과 비중을 Streamlit에서 입력할 수 있다.
- Performance 분석이 정상 실행된다.
- Correlation Matrix가 표시된다.
- Max Sharpe, Minimum Volatility, Risk Parity가 정상 실행된다.
- Efficient Frontier가 표시된다.
- 국내 종목/ETF Benchmark와 비교가 가능하다.
- 관련 테스트가 통과한다.
- Streamlit 앱이 정상적으로 시작되고 위 기능을 end-to-end로 실행할 수 있다.

작업 완료 결과는 `ai-share/PROTOCOL.md`에 따라 `ai-share/agent-to-llm.md`에 요약하여 GitHub에 push한다.
