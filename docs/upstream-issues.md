# 원본 프로젝트에서 발견한 문제와 수정 내역

이 문서는 국내 시장 지원 작업 중 원본 `engineerinvestor/Portfolio-Analysis`
코드에서 발견한 문제를 기록한다. 국내시장 신규 기능 자체는 포함하지 않는다.

검증 환경은 Python 3.12.13이며, 최초 기준선 검사에는 pandas 3.0.5,
Matplotlib 3.11.1, yfinance 1.6.0을 사용했다.

## 1. pandas 3에서 월말·연말 resample 실패

### 증상

기존 테스트 실행 시 다음 오류로 14개 테스트가 실패했다.

```text
ValueError: 'Y' is no longer supported for offsets. Please use 'YE' instead.
ValueError: 'M' is no longer supported for offsets. Please use 'ME' instead.
```

영향을 받은 기능은 연환산 수익률, Sharpe/Sortino 계산, 월별·연도별
리포트와 월간 수익률 조회였다.

### 원인

원본 코드가 `resample("M")`과 `resample("Y")` 문자열 별칭에 의존했다.
이 별칭은 pandas 3에서 제거됐다. 단순히 `ME`와 `YE` 문자열로 교체하면
프로젝트가 선언한 이전 pandas 버전과의 호환성이 저하될 수 있다.

### 수정

구버전과 신버전 pandas에서 모두 사용할 수 있는 offset 객체로 교체했다.

- `portfolio_analysis/data/loader.py`: `pd.offsets.MonthEnd()` 사용
- `portfolio_analysis/metrics/performance.py`: `pd.offsets.YearEnd()` 사용
- `portfolio_analysis/reporting/sections/returns.py`: `MonthEnd()`와 `YearEnd()` 사용

수정 커밋: `4ec58f2` (`phase-1-baseline`)

## 2. 최신 Matplotlib에서 factor exposure legend 생성 실패

### 증상

`TestFactorVisualization.test_plot_factor_exposures`가 다음 오류로 실패했다.

```text
TypeError: When passing handles and labels, they must both be passed
positionally or both as keywords.
```

### 원인

`plt.legend()` 호출에서 labels는 위치 인자로, handles는 키워드 인자로
혼합 전달하고 있었다. 최신 Matplotlib은 두 값을 동일한 방식으로 전달하도록
검증한다.

### 수정

`portfolio_analysis/factors/visualization.py`에서 labels와 handles를 모두
명시적인 키워드 인자로 전달하도록 변경했다.

수정 커밋: `4ec58f2` (`phase-1-baseline`)

## 3. BenchmarkComparison의 정상 초기화 순서 오류

### 증상

올바른 포트폴리오 데이터와 비중으로 `BenchmarkComparison`을 생성해도 다음
오류가 발생할 수 있었다.

```text
AttributeError: 'BenchmarkComparison' object has no attribute 'portfolio_returns'
```

### 원인

생성자가 `_validate_weights()`를 먼저 호출했는데, 이 메서드가 비중 검증뿐
아니라 벤치마크 조회와 날짜 정렬까지 수행했다. 날짜 정렬 과정에서는
`self.portfolio_returns`를 사용하지만 해당 속성은 `_validate_weights()` 호출
이후에 생성되고 있었다.

### 수정

초기화 순서를 다음과 같이 분리했다.

1. 비중의 개수와 합계 검증
2. 포트폴리오 일별 수익률 생성
3. 벤치마크 조회 및 공통 날짜 정렬

공통 날짜가 전혀 없을 때는 `DataError`로 명확히 보고하도록 보강했다.

수정 파일: `portfolio_analysis/metrics/benchmark.py`  
수정 커밋: `bbd1430` (`feat:korean-market-v1`)

## 4. Yahoo 다종목 조회 결과와 입력 비중의 종목 순서 불일치

### 증상

다음 입력으로 Yahoo Finance E2E 검증을 수행했을 때:

```python
DataLoader(["SPY", "BND"], ...)
```

반환된 DataFrame 열 순서는 `BND, SPY`였다. `PortfolioAnalysis`는 DataFrame
열 순서와 비중 배열의 위치를 결합하므로, 사용자가 `SPY, BND` 순서로 입력한
비중이 반대 종목에 적용될 수 있었다. 계산은 예외 없이 완료되므로 결과가
조용히 왜곡되는 문제였다.

### 원인

yfinance의 다종목 응답 열 순서를 그대로 사용했으며, 사용자가 요청한 ticker
순서로 재정렬하지 않았다.

### 수정

`portfolio_analysis/data/loader.py`에서 조회 결과를 `self.tickers` 순서로
명시적으로 재정렬했다. 함께 다음 오류 처리도 추가했다.

- 요청 종목 일부가 응답에 없으면 누락 ticker를 포함한 `DataError` 발생
- 공통 가격 날짜가 없으면 원인을 설명하는 `DataError` 발생
- 빈 ticker 목록, 중복 ticker, 잘못된 기간 검증

회귀 테스트 `test_yahoo_loader_preserves_requested_ticker_order`를 추가했다.

수정 커밋: `bbd1430` (`feat:korean-market-v1`)

## 검증 결과

- 수정 전 기준선: 199개 중 184개 통과, 15개 실패
- 호환성 문제 수정 후 Phase 1: 199개 전체 통과
- 국내시장 기능과 회귀 테스트 추가 후 최종: 209개 전체 통과
- Ruff 검사 통과
- Yahoo Finance `SPY/BND` 실제 데이터 E2E 통과
- Streamlit 기동 및 health check 통과

현재 확인된 blocker는 없다.
