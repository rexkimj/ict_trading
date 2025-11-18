"""
라이브 트레이딩 엔진

실시간 데이터를 기반으로 ICT 전략을 실행합니다.
"""
import pandas as pd
import time
from typing import Optional, Dict
from datetime import datetime
import traceback

from .connector import ExchangeConnector
from ..core.liquidity import LiquidityAnalyzer
from ..core.market_structure import MarketStructureAnalyzer
from ..core.fvg import FVGAnalyzer
from ..core.order_block import OrderBlockAnalyzer
from ..core.poi import POIManager
from ..analysis.timeframe import MultiTimeframeAnalyzer
from ..analysis.seven_factors import SevenFactorAnalyzer
from ..strategy.entry import EntryStrategy
from ..strategy.exit import ExitStrategy
from ..strategy.risk_management import RiskManager
from ..utils.logger import setup_logger


class LiveTradingEngine:
    """라이브 트레이딩 엔진"""

    def __init__(
        self,
        exchange_connector: ExchangeConnector,
        symbol: str,
        initial_capital: float,
        config: Dict
    ):
        """
        Args:
            exchange_connector: 거래소 커넥터
            symbol: 거래 심볼
            initial_capital: 초기 자본
            config: 설정
        """
        self.exchange = exchange_connector
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.config = config

        self.logger = setup_logger('LiveTradingEngine')

        # 컴포넌트 초기화
        self._initialize_components()

        # 상태
        self.is_running = False
        self.current_position = None
        self.last_update = None

        self.logger.info(f"라이브 트레이딩 엔진 초기화: {symbol}")

    def _initialize_components(self):
        """컴포넌트 초기화"""
        # Core analyzers
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.market_structure_analyzer = MarketStructureAnalyzer()
        self.fvg_analyzer = FVGAnalyzer()
        self.ob_analyzer = OrderBlockAnalyzer()

        # POI Manager
        self.poi_manager = POIManager(
            self.ob_analyzer,
            self.fvg_analyzer,
            self.liquidity_analyzer
        )

        # Multi-timeframe analyzer
        timeframes = self.config.get('timeframes', {})
        self.mtf_analyzer = MultiTimeframeAnalyzer(
            higher_timeframe=timeframes.get('higher_timeframe', '4H'),
            entry_timeframe=timeframes.get('entry_timeframe', '15M'),
            confirmation_timeframe=timeframes.get('confirmation_timeframe', '5M')
        )

        # POI managers for each timeframe
        self.poi_managers = {
            'htf': POIManager(
                OrderBlockAnalyzer(),
                FVGAnalyzer(),
                LiquidityAnalyzer()
            ),
            'etf': POIManager(
                OrderBlockAnalyzer(),
                FVGAnalyzer(),
                LiquidityAnalyzer()
            ),
            'ctf': POIManager(
                OrderBlockAnalyzer(),
                FVGAnalyzer(),
                LiquidityAnalyzer()
            )
        }

        # Seven factor analyzer
        self.seven_factor_analyzer = SevenFactorAnalyzer(
            self.liquidity_analyzer,
            self.market_structure_analyzer,
            self.fvg_analyzer,
            self.ob_analyzer,
            self.poi_manager,
            self.mtf_analyzer
        )

        # Strategies
        entry_config = self.config.get('entry', {})
        self.entry_strategy = EntryStrategy(
            self.seven_factor_analyzer,
            self.mtf_analyzer,
            self.poi_manager,
            min_confidence=entry_config.get('min_confidence', 0.7)
        )

        self.exit_strategy = ExitStrategy(
            self.liquidity_analyzer,
            self.fvg_analyzer
        )

        # Risk manager
        risk_config = self.config.get('risk_management', {})
        self.risk_manager = RiskManager(
            initial_capital=self.initial_capital,
            max_risk_per_trade=risk_config.get('max_risk_per_trade', 0.02),
            max_open_positions=risk_config.get('max_open_positions', 3)
        )

    def start(self, update_interval: int = 60):
        """
        트레이딩 시작

        Args:
            update_interval: 업데이트 간격 (초)
        """
        self.is_running = True
        self.logger.info("라이브 트레이딩 시작")

        try:
            while self.is_running:
                try:
                    # 데이터 업데이트 및 분석
                    self._update_and_analyze()

                    # 포지션 관리
                    if self.current_position:
                        self._manage_position()
                    else:
                        self._check_entry()

                    # Kill Switch 확인
                    should_stop, reason = self.risk_manager.check_kill_switch()
                    if should_stop:
                        self.logger.warning(f"Kill Switch 발동: {reason}")
                        if self.current_position:
                            self._emergency_close()
                        self.stop()
                        break

                    # 대기
                    time.sleep(update_interval)

                except Exception as e:
                    self.logger.error(f"루프 실행 중 오류: {e}")
                    self.logger.error(traceback.format_exc())
                    time.sleep(update_interval)

        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 중단됨")
        finally:
            self.stop()

    def stop(self):
        """트레이딩 중지"""
        self.is_running = False
        self.logger.info("라이브 트레이딩 중지")

        # 성과 통계 출력
        stats = self.risk_manager.get_performance_stats()
        self.logger.info(f"최종 자본: ${self.risk_manager.current_capital:.2f}")
        self.logger.info(f"총 거래: {stats['total_trades']}")
        self.logger.info(f"승률: {stats['win_rate']*100:.2f}%")

    def _update_and_analyze(self):
        """데이터 업데이트 및 분석"""
        try:
            # 데이터 조회
            df = self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe='5m',
                limit=500
            )

            if df.empty:
                self.logger.warning("데이터 없음")
                return

            # 분석 업데이트
            self.poi_manager.update_all_pois(df)
            self.market_structure_analyzer.identify_structure(df)
            self.market_structure_analyzer.determine_trend()

            # 다중 타임프레임 분석
            self.mtf_analyzer.analyze_all_timeframes(df, self.poi_managers)

            self.last_update = datetime.now()
            self.logger.debug("데이터 업데이트 완료")

        except Exception as e:
            self.logger.error(f"데이터 업데이트 실패: {e}")

    def _check_entry(self):
        """진입 확인"""
        try:
            # 진입 가능 여부
            can_open, reason = self.risk_manager.can_open_position()
            if not can_open:
                self.logger.debug(f"진입 불가: {reason}")
                return

            # 현재 가격
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']

            # 데이터 조회
            df = self.exchange.fetch_ohlcv(self.symbol, '5m', 500)

            # 진입 신호 확인
            entry_signal = self.entry_strategy.check_entry(df, current_price)

            if entry_signal and entry_signal.confidence >= 0.7:
                self.logger.info(f"진입 신호 발견: {entry_signal.direction} (신뢰도: {entry_signal.confidence*100:.1f}%)")
                self.logger.info(f"사유: {entry_signal.reason}")

                # 청산 레벨 계산
                exit_levels = self.exit_strategy.calculate_exit_levels(
                    df,
                    entry_price=current_price,
                    direction=entry_signal.direction,
                    risk_amount=self.initial_capital * 0.02
                )

                # 포지션 오픈
                success = self._open_position(
                    direction=entry_signal.direction,
                    entry_price=current_price,
                    stop_loss=exit_levels.stop_loss,
                    take_profit_levels=exit_levels.take_profit_levels
                )

                if success:
                    self.current_position = {
                        'entry_signal': entry_signal,
                        'exit_levels': exit_levels,
                        'entry_time': datetime.now()
                    }

        except Exception as e:
            self.logger.error(f"진입 확인 중 오류: {e}")
            self.logger.error(traceback.format_exc())

    def _open_position(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit_levels: list
    ) -> bool:
        """포지션 오픈"""
        try:
            # 포지션 사이즈 계산
            size, risk_amount = self.risk_manager.calculate_position_size(
                entry_price, stop_loss, direction
            )

            if size == 0:
                self.logger.error("포지션 사이즈 0")
                return False

            # 주문 실행
            side = 'buy' if direction == 'long' else 'sell'
            order = self.exchange.create_market_order(
                symbol=self.symbol,
                side=side,
                amount=size
            )

            self.logger.info(f"포지션 오픈 성공: {order['id']}")

            # 리스크 매니저에 등록
            position = self.risk_manager.open_position(
                entry_price=entry_price,
                stop_loss=stop_loss,
                direction=direction,
                take_profit_levels=take_profit_levels
            )

            return position is not None

        except Exception as e:
            self.logger.error(f"포지션 오픈 실패: {e}")
            return False

    def _manage_position(self):
        """포지션 관리"""
        try:
            # 현재 가격
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']

            # 데이터 조회
            df = self.exchange.fetch_ohlcv(self.symbol, '5m', 500)

            # 청산 확인
            exit_signal = self.exit_strategy.check_exit(
                current_price=current_price,
                entry_price=self.current_position['entry_signal'].entry_price,
                direction=self.current_position['entry_signal'].direction,
                exit_levels=self.current_position['exit_levels']
            )

            if exit_signal:
                self.logger.info(f"청산 신호: {exit_signal.exit_type} - {exit_signal.reason}")
                self._close_position(exit_signal.exit_price, exit_signal.reason)

        except Exception as e:
            self.logger.error(f"포지션 관리 중 오류: {e}")

    def _close_position(self, exit_price: float, reason: str):
        """포지션 청산"""
        try:
            if not self.current_position:
                return

            entry_signal = self.current_position['entry_signal']

            # 주문 실행
            side = 'sell' if entry_signal.direction == 'long' else 'buy'

            # 포지션 크기 조회
            positions = self.exchange.fetch_positions([self.symbol])
            if not positions:
                self.logger.warning("청산할 포지션 없음")
                return

            position_size = abs(float(positions[0].get('contracts', 0)))

            order = self.exchange.close_position(
                symbol=self.symbol,
                side=side,
                amount=position_size
            )

            self.logger.info(f"포지션 청산 성공: {order['id']} - {reason}")

            # 리스크 매니저 업데이트
            # (실제 구현에서는 포지션 객체를 추적해야 함)

            self.current_position = None

        except Exception as e:
            self.logger.error(f"포지션 청산 실패: {e}")

    def _emergency_close(self):
        """긴급 청산"""
        self.logger.warning("긴급 청산 실행")
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            for position in positions:
                size = abs(float(position.get('contracts', 0)))
                if size > 0:
                    side = 'sell' if float(position.get('contracts', 0)) > 0 else 'buy'
                    self.exchange.close_position(self.symbol, side, size)
                    self.logger.info("긴급 청산 완료")
        except Exception as e:
            self.logger.error(f"긴급 청산 실패: {e}")
