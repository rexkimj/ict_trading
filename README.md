# ICT Trading Strategy System

기관의 기회 포착을 위한 ICT(Inner Circle Trader) 트레이딩 전략 시스템

## 개요

이 시스템은 스마트 머니의 움직임과 유동성 확보 알고리즘을 이해하고 추적하여, 가격(Price), 시간(Time), 유동성(Liquidity)을 핵심 요소로 하는 ICT 트레이딩 전략을 구현합니다.

## 핵심 개념

### 7가지 필수 요소
1. **유동성(Liquidity)**: 시장의 유동성 영역 식별 및 추적
2. **시장 구조(Market Structure)**: 추세 및 시장 구조 변화 분석
3. **BO(Break of Structure)**: 구조 붕괴 지점 식별
4. **FVG/인밸런스(Fair Value Gap/Imbalance)**: 가격 불균형 영역 탐지
5. **디스카운트/프리미엄**: 가격 할인/프리미엄 구간 식별
6. **타임프레임(Timeframe)**: 다중 타임프레임 분석
7. **SMT(Smart Money Technique)**: 스마트 머니 기법
8. **시간(Time)**: 시간대별 패턴 분석

### 주요 기능

#### 진입 전략 (Entry)
- 다중 타임프레임 분석을 통한 추세 확인
- POI(Point of Interest) 식별
  - 오더 블록(Order Block)
  - FVG/인밸런스
- 유동성 확보 확인
- 진입 신호 컨펌

#### 청산 전략 (Exit)
- **수익 실현(TP)**
  - 고유동성 레벨 목표 (PDH, PDL 등)
  - 인밸런스 목표
  - VWAP 기반 청산
- **리스크 관리(SL)**
  - 유동성 확보 후 논리적 SL 설정
  - 자본의 1-2% 리스크 제어
  - 추적 손절매

#### 실행 알고리즘
- VWAP(거래량 가중평균 가격) 전략
- 슬리피지 최소화
- 대규모 주문 분할 처리
- Kill Switch 안전장치

## 프로젝트 구조

```
ict_trading/
├── src/
│   ├── core/              # ICT 핵심 개념 구현
│   ├── analysis/          # 분석 모듈
│   ├── strategy/          # 트레이딩 전략
│   ├── execution/         # 실행 시스템
│   ├── backtesting/       # 백테스팅
│   └── utils/             # 유틸리티
├── tests/                 # 테스트
├── examples/              # 예제
└── config/                # 설정 파일
```

## 설치

```bash
pip install -r requirements.txt
```

## 사용 예제

```python
from src.strategy.entry import EntryStrategy
from src.strategy.exit import ExitStrategy
from src.execution.vwap import VWAPExecutor

# 전략 초기화
entry_strategy = EntryStrategy()
exit_strategy = ExitStrategy()

# 트레이딩 실행
# (자세한 예제는 examples/ 디렉토리 참조)
```

## 주의사항

1. **백테스팅 필수**: 실거래 전 반드시 충분한 백테스팅을 수행하세요
2. **리스크 관리**: 자본의 1-2%만 리스크로 설정하세요
3. **Kill Switch**: 비정상 상황 감지 시 즉시 시스템 중단
4. **다중 확인**: 7가지 요소를 모두 확인 후 진입하세요

## 라이선스

MIT License
