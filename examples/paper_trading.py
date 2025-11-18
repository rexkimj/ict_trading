"""
페이퍼 트레이딩 (모의 거래)

실제 시장 데이터를 사용하지만 실제 주문은 하지 않는 모의 거래입니다.
리스크 없이 전략을 테스트할 수 있습니다.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
import yaml
from datetime import datetime

from src.exchange.connector import ExchangeConnector
from src.core.liquidity import LiquidityAnalyzer
from src.core.market_structure import MarketStructureAnalyzer
from src.core.fvg import FVGAnalyzer
from src.core.order_block import OrderBlockAnalyzer
from src.core.poi import POIManager
from src.analysis.timeframe import MultiTimeframeAnalyzer
from src.analysis.seven_factors import SevenFactorAnalyzer
from src.strategy.entry import EntryStrategy
from src.strategy.exit import ExitStrategy
from src.strategy.risk_management import RiskManager


class PaperTradingEngine:
    """페이퍼 트레이딩 엔진"""

    def __init__(self, symbol: str, initial_capital: float, config: dict):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.config = config

        # 거래소 연결 (API 키 불필요)
        self.exchange = ExchangeConnector(exchange_id='binance', testnet=False)

        # 컴포넌트 초기화
        self._initialize_components()

        # 가상 포지션
        self.paper_position = None
        self.trade_log = []

    def _initialize_components(self):
        """컴포넌트 초기화"""
        # Core
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.market_structure_analyzer = MarketStructureAnalyzer()
        self.fvg_analyzer = FVGAnalyzer()
        self.ob_analyzer = OrderBlockAnalyzer()
        self.poi_manager = POIManager(
            self.ob_analyzer, self.fvg_analyzer, self.liquidity_analyzer
        )

        # Analysis
        timeframes = self.config.get('timeframes', {})
        self.mtf_analyzer = MultiTimeframeAnalyzer(
            higher_timeframe=timeframes.get('higher_timeframe', '4H'),
            entry_timeframe=timeframes.get('entry_timeframe', '15M'),
            confirmation_timeframe=timeframes.get('confirmation_timeframe', '5M')
        )

        self.poi_managers = {
            'htf': POIManager(OrderBlockAnalyzer(), FVGAnalyzer(), LiquidityAnalyzer()),
            'etf': POIManager(OrderBlockAnalyzer(), FVGAnalyzer(), LiquidityAnalyzer()),
            'ctf': POIManager(OrderBlockAnalyzer(), FVGAnalyzer(), LiquidityAnalyzer())
        }

        self.seven_factor_analyzer = SevenFactorAnalyzer(
            self.liquidity_analyzer,
            self.market_structure_analyzer,
            self.fvg_analyzer,
            self.ob_analyzer,
            self.poi_manager,
            self.mtf_analyzer
        )

        # Strategy
        self.entry_strategy = EntryStrategy(
            self.seven_factor_analyzer, self.mtf_analyzer, self.poi_manager
        )
        self.exit_strategy = ExitStrategy(
            self.liquidity_analyzer, self.fvg_analyzer
        )

        # Risk
        risk_config = self.config.get('risk_management', {})
        self.risk_manager = RiskManager(
            initial_capital=self.initial_capital,
            max_risk_per_trade=risk_config.get('max_risk_per_trade', 0.02),
            max_open_positions=risk_config.get('max_open_positions', 3)
        )

    def run(self, duration_hours: int = 24):
        """
        페이퍼 트레이딩 실행

        Args:
            duration_hours: 실행 시간
        """
        print(f"📄 페이퍼 트레이딩 시작: {self.symbol}")
        print(f"⏱️  실행 시간: {duration_hours}시간")
        print(f"💰 초기 자본: ${self.initial_capital}\n")

        start_time = datetime.now()
        iteration = 0

        try:
            while True:
                iteration += 1
                elapsed = (datetime.now() - start_time).total_seconds() / 3600

                if elapsed >= duration_hours:
                    print(f"\n⏰ 설정 시간({duration_hours}시간) 완료")
                    break

                print(f"\n{'='*60}")
                print(f"반복 #{iteration} - 경과 시간: {elapsed:.2f}시간")
                print(f"{'='*60}")

                # 데이터 업데이트
                df = self.exchange.fetch_ohlcv(self.symbol, '5m', 500)
                current_price = df['close'].iloc[-1]

                print(f"💵 현재 가격: ${current_price:.2f}")

                # 분석
                self.poi_manager.update_all_pois(df)
                self.market_structure_analyzer.identify_structure(df)
                self.market_structure_analyzer.determine_trend()
                self.mtf_analyzer.analyze_all_timeframes(df, self.poi_managers)

                # 포지션 관리
                if self.paper_position:
                    self._manage_position(current_price, df)
                else:
                    self._check_entry(current_price, df)

                # Kill Switch
                should_stop, reason = self.risk_manager.check_kill_switch()
                if should_stop:
                    print(f"\n🛑 Kill Switch 발동: {reason}")
                    if self.paper_position:
                        self._close_position(current_price, "Kill Switch")
                    break

                # 현재 상태 출력
                print(f"💼 포지션: {'있음' if self.paper_position else '없음'}")
                print(f"💰 자본: ${self.risk_manager.current_capital:.2f}")

                # 대기
                time.sleep(60)  # 1분 대기

        except KeyboardInterrupt:
            print("\n\n⏸️  사용자에 의해 중단됨")

        finally:
            self._print_summary()

    def _check_entry(self, current_price: float, df):
        """진입 확인"""
        can_open, reason = self.risk_manager.can_open_position()
        if not can_open:
            print(f"  ⚠️  진입 불가: {reason}")
            return

        entry_signal = self.entry_strategy.check_entry(df, current_price)

        if entry_signal and entry_signal.confidence >= 0.7:
            print(f"\n  🎯 진입 신호!")
            print(f"    방향: {entry_signal.direction}")
            print(f"    신뢰도: {entry_signal.confidence*100:.1f}%")
            print(f"    사유: {entry_signal.reason}")

            exit_levels = self.exit_strategy.calculate_exit_levels(
                df, current_price, entry_signal.direction,
                self.initial_capital * 0.02
            )

            # 가상 포지션 생성
            size, risk_amount = self.risk_manager.calculate_position_size(
                current_price, exit_levels.stop_loss, entry_signal.direction
            )

            self.paper_position = {
                'entry_time': datetime.now(),
                'direction': entry_signal.direction,
                'entry_price': current_price,
                'size': size,
                'stop_loss': exit_levels.stop_loss,
                'take_profit_levels': exit_levels.take_profit_levels,
                'exit_levels': exit_levels
            }

            print(f"    ✅ 가상 포지션 오픈")
            print(f"       크기: {size:.4f}")
            print(f"       손절가: ${exit_levels.stop_loss:.2f}")

    def _manage_position(self, current_price: float, df):
        """포지션 관리"""
        print(f"  📊 포지션 관리 중...")

        # 미실현 손익
        if self.paper_position['direction'] == 'long':
            unrealized_pnl = (current_price - self.paper_position['entry_price']) * self.paper_position['size']
        else:
            unrealized_pnl = (self.paper_position['entry_price'] - current_price) * self.paper_position['size']

        print(f"    미실현 손익: ${unrealized_pnl:.2f}")

        # 청산 확인
        exit_signal = self.exit_strategy.check_exit(
            current_price,
            self.paper_position['entry_price'],
            self.paper_position['direction'],
            self.paper_position['exit_levels']
        )

        if exit_signal:
            print(f"\n  🏁 청산 신호: {exit_signal.exit_type}")
            print(f"    사유: {exit_signal.reason}")
            self._close_position(current_price, exit_signal.reason)

    def _close_position(self, exit_price: float, reason: str):
        """포지션 청산"""
        if self.paper_position['direction'] == 'long':
            pnl = (exit_price - self.paper_position['entry_price']) * self.paper_position['size']
        else:
            pnl = (self.paper_position['entry_price'] - exit_price) * self.paper_position['size']

        # 자본 업데이트
        self.risk_manager.current_capital += pnl

        # 기록
        trade_record = {
            'entry_time': self.paper_position['entry_time'],
            'exit_time': datetime.now(),
            'direction': self.paper_position['direction'],
            'entry_price': self.paper_position['entry_price'],
            'exit_price': exit_price,
            'size': self.paper_position['size'],
            'pnl': pnl,
            'reason': reason
        }
        self.trade_log.append(trade_record)

        print(f"    ✅ 가상 포지션 청산")
        print(f"       손익: ${pnl:.2f}")
        print(f"       현재 자본: ${self.risk_manager.current_capital:.2f}")

        self.paper_position = None

    def _print_summary(self):
        """요약 출력"""
        print(f"\n\n{'='*60}")
        print("=== 페이퍼 트레이딩 요약 ===")
        print(f"{'='*60}")

        stats = self.risk_manager.get_performance_stats()

        print(f"\n💰 자본:")
        print(f"  초기: ${self.initial_capital:.2f}")
        print(f"  최종: ${self.risk_manager.current_capital:.2f}")
        print(f"  손익: ${stats['total_pnl']:.2f} ({stats['total_pnl_pct']:.2f}%)")

        print(f"\n📊 거래 통계:")
        print(f"  총 거래: {stats['total_trades']}")
        print(f"  승: {stats['winning_trades']}")
        print(f"  패: {stats['losing_trades']}")
        print(f"  승률: {stats['win_rate']*100:.2f}%")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        print(f"  최대 낙폭: {stats['max_drawdown_pct']:.2f}%")


def main():
    """메인 함수"""
    print("="*60)
    print("=== ICT 페이퍼 트레이딩 ===")
    print("="*60)

    # 설정
    symbol = 'BTC/USDT'
    initial_capital = 10000
    duration_hours = 2  # 2시간

    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 실행
    engine = PaperTradingEngine(symbol, initial_capital, config)
    engine.run(duration_hours=duration_hours)


if __name__ == "__main__":
    main()
