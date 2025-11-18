"""
기본 ICT 트레이딩 전략 예제

이 예제는 ICT 트레이딩 시스템의 기본 사용법을 보여줍니다.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.backtesting.engine import BacktestEngine
from src.backtesting.performance import PerformanceAnalyzer


def generate_sample_data(start_date: str = '2023-01-01', end_date: str = '2024-01-01') -> pd.DataFrame:
    """
    샘플 OHLCV 데이터 생성

    Args:
        start_date: 시작일
        end_date: 종료일

    Returns:
        OHLCV 데이터프레임
    """
    print("샘플 데이터 생성 중...")

    # 날짜 범위 계산
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    # 5분봉 데이터 생성
    dates = pd.date_range(start=start, end=end, freq='5T')

    periods = len(dates)

    # 시뮬레이션된 가격 데이터 (더 현실적인 패턴)
    np.random.seed(42)

    # 기본 가격
    base_price = 40000  # BTC 스타일

    # 1. 전체 추세 (상승)
    trend = np.linspace(0, 5000, periods)

    # 2. 사이클 (주기적 변동)
    cycles = 2000 * np.sin(np.linspace(0, 8 * np.pi, periods))

    # 3. 랜덤 워크 (누적 노이즈)
    random_walk = np.cumsum(np.random.randn(periods) * 50)

    # 4. 일일 변동성
    daily_noise = np.random.randn(periods) * 200

    # 최종 종가
    close_prices = base_price + trend + cycles + random_walk + daily_noise

    # OHLC 생성 (더 현실적인 범위)
    open_prices = close_prices + np.random.randn(periods) * 100
    high_prices = np.maximum(close_prices, open_prices) + abs(np.random.randn(periods)) * 150
    low_prices = np.minimum(close_prices, open_prices) - abs(np.random.randn(periods)) * 150

    data = {
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': np.random.uniform(100, 1000, periods)  # 거래량
    }

    df = pd.DataFrame(data, index=dates)

    # OHLC 일관성 보장
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)

    # 음수 방지
    df[df < 0] = abs(df[df < 0])

    return df


def run_basic_backtest():
    """기본 백테스트 실행"""
    print("=== ICT 트레이딩 전략 백테스트 ===\n")

    # 1. 샘플 데이터 생성 (config와 동일한 날짜 범위)
    start_date = '2023-01-01'
    end_date = '2024-01-01'

    df = generate_sample_data(start_date=start_date, end_date=end_date)
    print(f"데이터 생성 완료: {len(df)} 캔들")
    print(f"기간: {df.index[0]} ~ {df.index[-1]}\n")

    # 2. 백테스트 엔진 초기화
    print("백테스트 엔진 초기화 중...")
    config_path = "config/config.yaml"
    backtest = BacktestEngine(config_path=config_path)
    print("초기화 완료\n")

    # 3. 백테스트 실행
    results = backtest.run(df)

    # 4. 성과 분석
    print("\n=== 성과 분석 ===")
    analyzer = PerformanceAnalyzer()
    metrics = analyzer.calculate_metrics(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        initial_capital=results['initial_capital']
    )

    # 리포트 출력
    print(analyzer.generate_report(metrics))

    # 5. 거래 상세
    print("=== 거래 상세 (최근 5개) ===")
    recent_trades = results['trades'][-5:]
    for i, trade in enumerate(recent_trades, 1):
        print(f"\n거래 #{i}:")
        print(f"  진입 시간: {trade.get('entry_time')}")
        print(f"  방향: {trade.get('direction')}")
        print(f"  진입가: ${trade.get('entry_price', 0):.2f}")
        print(f"  청산가: ${trade.get('exit_price', 0):.2f}")
        print(f"  손익: ${trade.get('pnl', 0):.2f}")
        print(f"  신뢰도: {trade.get('confidence', 0)*100:.1f}%")
        print(f"  사유: {trade.get('reason', 'N/A')}")

    return results, metrics


def main():
    """메인 함수"""
    try:
        results, metrics = run_basic_backtest()

        print("\n" + "="*50)
        print("백테스트 성공!")
        print("="*50)

    except Exception as e:
        print(f"\n에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
