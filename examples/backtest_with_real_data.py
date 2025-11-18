"""
실제 거래소 데이터로 백테스트 실행

CCXT를 통해 실제 거래소 데이터를 받아 백테스트를 수행합니다.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.exchange.connector import ExchangeConnector
from src.backtesting.engine import BacktestEngine
from src.backtesting.performance import PerformanceAnalyzer
import pandas as pd


def run_backtest_with_real_data():
    """실제 데이터로 백테스트 실행"""
    print("=== 실제 데이터 백테스트 ===\n")

    # 1. 거래소 연결 (API 키 없이도 과거 데이터 조회 가능)
    print("거래소 연결 중...")
    exchange = ExchangeConnector(
        exchange_id='binance',
        testnet=False  # 실제 데이터 사용
    )
    print("연결 완료\n")

    # 2. 과거 데이터 다운로드
    symbol = 'BTC/USDT'
    timeframe = '5m'
    start_date = '2024-01-01'
    end_date = '2024-03-31'

    print(f"과거 데이터 다운로드 중...")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {timeframe}")
    print(f"기간: {start_date} ~ {end_date}\n")

    df = exchange.fetch_historical_data(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    )

    print(f"데이터 다운로드 완료: {len(df)} 캔들")
    print(f"기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"가격 범위: ${df['low'].min():.2f} ~ ${df['high'].max():.2f}\n")

    # 데이터 저장 (옵션)
    df.to_csv(f'data_{symbol.replace("/", "_")}_{timeframe}.csv')
    print("데이터 저장 완료\n")

    # 3. 백테스트 실행
    print("백테스트 엔진 초기화 중...")
    backtest = BacktestEngine(config_path='config/config.yaml')
    print("초기화 완료\n")

    print("백테스트 실행 중...\n")
    results = backtest.run(df)

    # 4. 성과 분석
    print("\n" + "="*60)
    print("=== 성과 분석 ===")
    print("="*60)

    analyzer = PerformanceAnalyzer()
    metrics = analyzer.calculate_metrics(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        initial_capital=results['initial_capital']
    )

    # 리포트 출력
    print(analyzer.generate_report(metrics))

    # 5. 거래 상세
    print("="*60)
    print("=== 거래 상세 (전체) ===")
    print("="*60)

    if results['trades']:
        for i, trade in enumerate(results['trades'], 1):
            print(f"\n거래 #{i}:")
            print(f"  진입 시간: {trade.get('entry_time')}")
            print(f"  방향: {trade.get('direction')}")
            print(f"  진입가: ${trade.get('entry_price', 0):.2f}")
            print(f"  청산가: ${trade.get('exit_price', 0):.2f}")
            print(f"  손익: ${trade.get('pnl', 0):.2f}")
            print(f"  신뢰도: {trade.get('confidence', 0)*100:.1f}%")
            print(f"  사유: {trade.get('reason', 'N/A')}")
            if 'exit_time' in trade:
                print(f"  청산 시간: {trade.get('exit_time')}")
                print(f"  청산 사유: {trade.get('exit_reason', 'N/A')}")
    else:
        print("\n거래 없음")

    # 6. 요약
    print("\n" + "="*60)
    print("=== 백테스트 요약 ===")
    print("="*60)
    print(f"초기 자본: ${results['initial_capital']:.2f}")
    print(f"최종 자본: ${results['final_capital']:.2f}")
    print(f"총 수익: ${results['total_pnl']:.2f} ({results['total_pnl_pct']:.2f}%)")
    print(f"총 거래: {results['total_trades']}")
    print(f"승률: {results['win_rate']*100:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"최대 낙폭: {results['max_drawdown_pct']:.2f}%")
    print(f"샤프 비율: {metrics.sharpe_ratio:.2f}")
    print(f"소르티노 비율: {metrics.sortino_ratio:.2f}")
    print("="*60)

    return results, metrics


def main():
    """메인 함수"""
    try:
        results, metrics = run_backtest_with_real_data()

        print("\n✅ 백테스트 성공!")

        # 결과 해석
        print("\n📊 결과 해석:")
        if results['total_pnl'] > 0:
            print("  ✓ 수익 발생")
        else:
            print("  ✗ 손실 발생")

        if results['win_rate'] >= 0.5:
            print(f"  ✓ 승률 양호 ({results['win_rate']*100:.1f}%)")
        else:
            print(f"  ✗ 승률 낮음 ({results['win_rate']*100:.1f}%)")

        if metrics.sharpe_ratio >= 1.0:
            print(f"  ✓ 샤프 비율 양호 ({metrics.sharpe_ratio:.2f})")
        else:
            print(f"  ⚠ 샤프 비율 낮음 ({metrics.sharpe_ratio:.2f})")

        if results['max_drawdown_pct'] <= 20:
            print(f"  ✓ 낙폭 관리 양호 ({results['max_drawdown_pct']:.1f}%)")
        else:
            print(f"  ⚠ 높은 낙폭 ({results['max_drawdown_pct']:.1f}%)")

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
