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


def generate_sample_data(days: int = 365) -> pd.DataFrame:
    """
    샘플 OHLCV 데이터 생성

    Args:
        days: 데이터 일수

    Returns:
        OHLCV 데이터프레임
    """
    print("샘플 데이터 생성 중...")

    # 5분봉 데이터 생성
    periods = days * 24 * 12  # 5분봉
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=periods,
        freq='5T'
    )

    # 시뮬레이션된 가격 데이터
    np.random.seed(42)

    # 추세 + 노이즈
    trend = np.linspace(100, 150, periods)
    noise = np.random.randn(periods) * 2
    close_prices = trend + noise

    # OHLC 생성
    data = {
        'open': close_prices + np.random.randn(periods) * 0.5,
        'high': close_prices + abs(np.random.randn(periods)) * 1.5,
        'low': close_prices - abs(np.random.randn(periods)) * 1.5,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, periods)
    }

    df = pd.DataFrame(data, index=dates)

    # OHLC 일관성 보장
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)

    return df


def run_basic_backtest():
    """기본 백테스트 실행"""
    print("=== ICT 트레이딩 전략 백테스트 ===\n")

    # 1. 샘플 데이터 생성
    df = generate_sample_data(days=365)
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
