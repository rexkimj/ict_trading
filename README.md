# ICT Trading Strategy System

기관의 기회 포착을 위한 ICT(Inner Circle Trader) 트레이딩 전략 시스템

## 개요

이 시스템은 스마트 머니의 움직임과 유동성 확보 알고리즘을 이해하고 추적하여, 가격(Price), 시간(Time), 유동성(Liquidity)을 핵심 요소로 하는 ICT 트레이딩 전략을 구현합니다.

**🚀 주요 업데이트**: CCXT를 활용한 실제 거래소 연동 및 라이브 트레이딩 지원

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
# 의존성 설치
pip install -r requirements.txt

# 환경 설정
cp .env.example .env
# .env 파일을 편집하여 API 키 설정
```

## 빠른 시작

### 1. 시뮬레이션 데이터로 백테스트

```bash
python examples/basic_strategy.py
```

### 2. 실제 거래소 데이터로 백테스트

```bash
python examples/backtest_with_real_data.py
```

이 예제는 Binance에서 실제 과거 데이터를 다운로드하여 백테스트를 수행합니다.

### 3. 페이퍼 트레이딩 (모의 거래)

```bash
python examples/paper_trading.py
```

실제 시장 데이터를 사용하지만 실제 주문은 하지 않는 모의 거래입니다.

### 4. 라이브 트레이딩 (실거래)

⚠️ **주의**: 반드시 테스트넷에서 먼저 테스트하세요!

```bash
# .env 파일 설정 필수
python examples/live_trading_example.py
```

## 🔧 설정

### 환경 변수 (.env)

```bash
# 거래소 API 설정
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_API_SECRET=your_api_secret_here

# 거래소 설정
EXCHANGE_ID=binance
SYMBOL=BTC/USDT
TESTNET=true  # 반드시 true로 시작하세요!

# 트레이딩 설정
INITIAL_CAPITAL=1000
UPDATE_INTERVAL=60
```

### 전략 설정 (config/config.yaml)

- 리스크 관리 파라미터
- 타임프레임 설정
- FVG/유동성 임계값
- VWAP 실행 설정

## 📊 백테스트 검증

실제 Binance 데이터로 백테스트한 결과:

```bash
python examples/backtest_with_real_data.py
```

**샘플 결과**:
- 기간: 2024-01-01 ~ 2024-03-31 (3개월)
- 심볼: BTC/USDT (5분봉)
- 데이터 포인트: 약 26,000 캔들

백테스트는 다음을 검증합니다:
- ✅ 7가지 필수 요소 통합 분석
- ✅ 유동성 확보 후 진입
- ✅ 리스크 관리 (1-2% 리스크)
- ✅ Kill Switch 안전장치

## 🤖 지원 거래소

CCXT를 통해 다음 거래소를 지원합니다:

- ✅ Binance (현물/선물)
- ✅ Bybit (선물)
- ✅ OKX
- ✅ 기타 CCXT 지원 거래소 100+

## ⚠️ 중요 주의사항

### 실거래 전 필수 확인사항

1. **백테스팅**:
   - ✅ 시뮬레이션 데이터로 먼저 테스트
   - ✅ 실제 과거 데이터로 백테스트
   - ✅ 최소 3개월 이상 데이터로 검증

2. **페이퍼 트레이딩**:
   - ✅ 실시간 시장 데이터로 최소 1주일 테스트
   - ✅ 다양한 시장 상황에서 검증

3. **테스트넷**:
   - ✅ 반드시 테스트넷에서 먼저 실행
   - ✅ 모든 기능이 정상 작동하는지 확인

4. **실거래**:
   - ⚠️ 소액으로 시작
   - ⚠️ 점진적으로 포지션 크기 확대
   - ⚠️ 지속적인 모니터링 필수

### 리스크 경고

- 이 시스템은 실험적이며 손실 위험이 있습니다
- 투자 손실에 대한 책임은 사용자에게 있습니다
- 자신의 리스크 허용도를 이해하고 사용하세요
- 감당할 수 있는 범위 내에서만 투자하세요

## 🛡️ 안전장치

### Kill Switch

다음 상황에서 자동으로 시스템이 중단됩니다:

- 일일 손실 한도 초과 (5%)
- 연속 5회 손실
- 자본이 초기 자본의 50% 이하로 감소
- 총 리스크 한도 초과

### API 키 보안

- `.env` 파일을 절대 커밋하지 마세요
- API 키는 읽기 전용 권한만 부여하세요 (백테스트용)
- 실거래용 키는 IP 화이트리스트를 설정하세요
- 출금 권한은 절대 부여하지 마세요

## 🧪 테스트

```bash
# 단위 테스트 실행
pytest tests/ -v

# 커버리지 확인
pytest tests/ --cov=src --cov-report=html
```

## 📈 성과 모니터링

시스템은 다음 지표를 자동으로 추적합니다:

- 총 수익률 / 연율화 수익률
- 샤프 비율 / 소르티노 비율
- 최대 낙폭 (Max Drawdown)
- 승률 / Profit Factor
- 거래 빈도 / 평균 보유 시간

## 🔄 업데이트 내역

### v0.2.0 (2025-01-XX)
- 🆕 CCXT 거래소 연동
- 🆕 실시간 데이터 수신
- 🆕 라이브 트레이딩 엔진
- 🆕 페이퍼 트레이딩 모드
- 🆕 실제 데이터 백테스트
- ✨ 안전장치 강화

### v0.1.0
- 초기 ICT 전략 구현
- 7가지 요소 분석
- 백테스팅 프레임워크

## 🤝 기여

이슈와 풀 리퀘스트를 환영합니다!

## 📝 라이선스

MIT License

## 📞 지원

문제가 발생하면 GitHub Issues에 보고해주세요.
