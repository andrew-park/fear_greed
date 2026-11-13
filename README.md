# S&P 500 · KOSPI Fear & Greed Proxy

미국 S&P 500과 한국 KOSPI의 일별 가격 데이터를 바탕으로 시장 심리 점수를 계산하는 Python 스크립트입니다. 결과는 **공식 CNN Fear & Greed Index가 아니라, 공개 가격 데이터만으로 재현 가능한 시장 심리 대용지표(proxy)**입니다.

## 빠른 시작

Python 3.10 이상을 권장합니다.

```bash
git clone https://github.com/andrew-park/fear_greed.git
cd fear_greed
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python fear_greed.py
```

기본 실행은 S&P 500(`^GSPC`)과 KOSPI(`^KS11`)를 계산해 JSON으로 출력합니다. 특정 시장만 계산하거나 전체 일별 결과를 CSV로 저장할 수도 있습니다.

```bash
python fear_greed.py --markets sp500
python fear_greed.py --markets kospi --period 5y
python fear_greed.py --output output/daily_scores.csv
```

## 점수 해석

점수 범위는 0(두려움 쪽)부터 100(탐욕 쪽)까지입니다. 각 신호를 해당 신호의 과거 분포에서의 백분위로 바꾼 뒤 동일 가중 평균합니다. 기본 비교 구간은 최근 756거래일(약 3년)이며, 최소 252개의 유효 관측이 필요합니다.

| 신호 | 계산 방식 | 점수가 높을 때 |
|---|---|---|
| 125일 추세 | 종가와 125일 이동평균의 차이를 과거 백분위화 | 지수가 이동평균 위에 있는 편 |
| 20일 모멘텀 | 최근 20거래일 수익률의 과거 백분위 | 단기 상승세가 강한 편 |
| 52주 가격 위치 | 최근 252거래일 고가·저가 범위에서 현재 종가의 위치 | 연중 고점에 가까운 편 |
| 252일 낙폭 | 252거래일 고점 대비 낙폭의 과거 백분위 | 고점 대비 회복된 편 |
| 20일 변동성 | 20일 실현변동성의 과거 백분위를 역산 | 변동성이 낮은 편 |

표시 구간은 `0–25 Extreme Fear`, `25 초과–45 Fear`, `45 초과–55 Neutral`, `55 초과–75 Greed`, `75 초과–100 Extreme Greed`입니다. 이는 읽기 쉬운 구간 라벨이며 CNN의 분류 결과를 재현한다는 뜻은 아닙니다.

## 범위와 주의사항

- CNN은 모멘텀, 주가 강도, 시장 breadth, 풋/콜 옵션, 정크본드 수요, 시장 변동성, 안전자산 수요 등 7개 신호를 사용한다고 설명합니다. 이 저장소는 종가만으로 안정적으로 계산할 수 있는 5개 가격 신호를 사용하며, 옵션·신용스프레드·시장 breadth 데이터는 포함하지 않습니다. 그러므로 두 지수의 방향을 비교하는 참고용으로 활용하고 공식 지수와 직접 비교하지 마세요.
- 양 시장에 같은 수식을 적용하되, 각 시장 자체의 과거 분포에 맞춰 점수를 표준화합니다. 점수는 투자 권유나 매매 신호가 아닙니다.
- 데이터는 `yfinance`를 통해 Yahoo Finance에서 가져옵니다. 데이터의 정확성·지연·가용성은 보장되지 않으며, Yahoo의 이용 약관과 데이터 사용 조건을 확인하세요. `yfinance`는 Yahoo와 제휴·승인된 서비스가 아닙니다.
- 유효한 점수 계산을 위해 약 2년 이상의 일별 기록이 필요합니다. 최근 거래일은 각 시장의 휴장일과 데이터 제공 시점에 따라 다를 수 있습니다.

## 재현성 테스트

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## 참고 자료

- [CNN Fear & Greed Index: 7개 지표 및 계산 개요](https://www.cnn.com/markets/fear-and-greed)
- [yfinance 프로젝트 및 데이터 사용 안내](https://github.com/ranaroussi/yfinance)
