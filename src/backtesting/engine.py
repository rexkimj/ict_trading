"""
백테스팅 엔진

ICT 트레이딩 전략의 백테스팅을 지원합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import yaml

from ..core.liquidity import LiquidityAnalyzer
from ..core.market_structure import MarketStructureAnalyzer
from ..core.fvg import FVGAnalyzer
from ..core.order_block import OrderBlockAnalyzer
from ..core.poi import POIManager
from ..core.smt import SMTAnalyzer
from ..analysis.timeframe import MultiTimeframeAnalyzer
from ..analysis.seven_factors import SevenFactorAnalyzer
from ..strategy.entry import EntryStrategy
from ..strategy.exit import ExitStrategy
from ..strategy.risk_management import RiskManager
from ..execution.vwap import VWAPExecutor
from ..execution.slippage import SlippageManager
from ..execution.order_executor import OrderExecutor


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float
    start_date: str
    end_date: str
    max_risk_per_trade: float
    commission: float
    higher_timeframe: str
    entry_timeframe: str
    confirmation_timeframe: str


class BacktestEngine:
    """백테스팅 엔진 클래스"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로
        """
        # 설정 로드
        if config_path:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = self._get_default_config()

        self.config = BacktestConfig(
            initial_capital=config_data.get('backtesting', {}).get('initial_capital', 10000),
            start_date=config_data.get('backtesting', {}).get('start_date', '2023-01-01'),
            end_date=config_data.get('backtesting', {}).get('end_date', '2024-01-01'),
            max_risk_per_trade=config_data.get('risk_management', {}).get('max_risk_per_trade', 0.02),
            commission=config_data.get('backtesting', {}).get('commission', 0.001),
            higher_timeframe=config_data.get('timeframes', {}).get('higher_timeframe', '4H'),
            entry_timeframe=config_data.get('timeframes', {}).get('entry_timeframe', '15M'),
            confirmation_timeframe=config_data.get('timeframes', {}).get('confirmation_timeframe', '5M')
        )

        # 컴포넌트 초기화
        self._initialize_components()

        # 백테스트 결과
        self.trades = []
        self.equity_curve = []

    def _get_default_config(self) -> Dict:
        """기본 설정 반환"""
        return {
            'risk_management': {
                'max_risk_per_trade': 0.02,
                'max_open_positions': 3
            },
            'timeframes': {
                'higher_timeframe': '4H',
                'entry_timeframe': '15M',
                'confirmation_timeframe': '5M'
            },
            'backtesting': {
                'initial_capital': 10000,
                'commission': 0.001,
                'start_date': '2023-01-01',
                'end_date': '2024-01-01'
            }
        }

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
        self.mtf_analyzer = MultiTimeframeAnalyzer(
            higher_timeframe=self.config.higher_timeframe,
            entry_timeframe=self.config.entry_timeframe,
            confirmation_timeframe=self.config.confirmation_timeframe
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
        self.entry_strategy = EntryStrategy(
            self.seven_factor_analyzer,
            self.mtf_analyzer,
            self.poi_manager
        )

        self.exit_strategy = ExitStrategy(
            self.liquidity_analyzer,
            self.fvg_analyzer
        )

        # Risk manager
        self.risk_manager = RiskManager(
            initial_capital=self.config.initial_capital,
            max_risk_per_trade=self.config.max_risk_per_trade
        )

        # Execution
        self.vwap_executor = VWAPExecutor()
        self.slippage_manager = SlippageManager(commission_rate=self.config.commission)
        self.order_executor = OrderExecutor(
            self.vwap_executor,
            self.slippage_manager
        )

    def run(self, df: pd.DataFrame) -> Dict:
        """
        백테스트 실행

        Args:
            df: OHLCV 데이터프레임

        Returns:
            백테스트 결과
        """
        print(f"백테스트 시작: {self.config.start_date} ~ {self.config.end_date}")
        print(f"초기 자본: ${self.config.initial_capital}")

        # 데이터 필터링
        df = df[(df.index >= self.config.start_date) & (df.index <= self.config.end_date)]

        if len(df) == 0:
            print("데이터가 없습니다")
            return {}

        # 초기 자본 기록
        self.equity_curve.append({
            'timestamp': df.index[0],
            'equity': self.config.initial_capital
        })

        # 백테스트 루프
        lookback = 100
        current_position = None

        for i in range(lookback, len(df)):
            current_idx = i
            current_timestamp = df.index[i]
            current_price = df['close'].iloc[i]

            # 과거 데이터
            historical_df = df.iloc[:i+1]

            # 분석 업데이트
            self._update_analysis(historical_df)

            # 다중 타임프레임 분석
            self.mtf_analyzer.analyze_all_timeframes(
                historical_df,
                self.poi_managers
            )

            # Kill Switch 확인
            should_stop, reason = self.risk_manager.check_kill_switch()
            if should_stop:
                print(f"\nKill Switch 발동: {reason}")
                if current_position:
                    self._close_position(current_position, current_price, "Kill Switch")
                break

            # 포지션 관리
            if current_position:
                # 기존 포지션 청산 확인
                self._check_exit(current_position, historical_df, current_price)
            else:
                # 새 진입 확인
                self._check_entry(historical_df, current_price)

            # 자본 기록
            self.equity_curve.append({
                'timestamp': current_timestamp,
                'equity': self.risk_manager.current_capital
            })

            # 진행 상황 출력 (10% 단위)
            if i % (len(df) // 10) == 0:
                progress = (i / len(df)) * 100
                print(f"진행: {progress:.1f}% - 자본: ${self.risk_manager.current_capital:.2f}")

        # 백테스트 결과 생성
        results = self._generate_results()

        print(f"\n백테스트 완료!")
        print(f"최종 자본: ${results['final_capital']:.2f}")
        print(f"총 수익: ${results['total_pnl']:.2f} ({results['total_pnl_pct']:.2f}%)")
        print(f"총 거래: {results['total_trades']}")
        print(f"승률: {results['win_rate']*100:.2f}%")

        return results

    def _update_analysis(self, df: pd.DataFrame):
        """분석 업데이트"""
        # POI 업데이트
        self.poi_manager.update_all_pois(df)

        # 시장 구조 분석
        self.market_structure_analyzer.identify_structure(df)
        self.market_structure_analyzer.determine_trend()

    def _check_entry(self, df: pd.DataFrame, current_price: float):
        """진입 확인"""
        # 진입 가능 여부 확인
        can_open, reason = self.risk_manager.can_open_position()
        if not can_open:
            return

        # 진입 신호 확인
        entry_signal = self.entry_strategy.check_entry(df, current_price)

        if entry_signal and entry_signal.confidence >= 0.7:
            # 청산 레벨 계산
            exit_levels = self.exit_strategy.calculate_exit_levels(
                df,
                entry_price=current_price,
                direction=entry_signal.direction,
                risk_amount=self.config.initial_capital * self.config.max_risk_per_trade
            )

            # 포지션 오픈
            position = self.risk_manager.open_position(
                entry_price=current_price,
                stop_loss=exit_levels.stop_loss,
                direction=entry_signal.direction,
                take_profit_levels=exit_levels.take_profit_levels
            )

            if position:
                self.trades.append({
                    'entry_time': position.entry_time,
                    'direction': position.direction,
                    'entry_price': position.entry_price,
                    'size': position.size,
                    'stop_loss': position.stop_loss,
                    'confidence': entry_signal.confidence,
                    'reason': entry_signal.reason,
                    'position': position,
                    'exit_levels': exit_levels
                })

    def _check_exit(self, trade: Dict, df: pd.DataFrame, current_price: float):
        """청산 확인"""
        position = trade['position']
        exit_levels = trade['exit_levels']

        # 포지션 업데이트
        self.risk_manager.update_position(position, current_price)

        # 청산 신호 확인
        exit_signal = self.exit_strategy.check_exit(
            current_price=current_price,
            entry_price=position.entry_price,
            direction=position.direction,
            exit_levels=exit_levels
        )

        if exit_signal:
            self._close_position(trade, exit_signal.exit_price, exit_signal.reason)

    def _close_position(self, trade: Dict, exit_price: float, reason: str):
        """포지션 청산"""
        position = trade['position']

        realized_pnl = self.risk_manager.close_position(
            position,
            exit_price,
            reason
        )

        trade['exit_time'] = datetime.now()
        trade['exit_price'] = exit_price
        trade['pnl'] = realized_pnl
        trade['exit_reason'] = reason

    def _generate_results(self) -> Dict:
        """백테스트 결과 생성"""
        performance = self.risk_manager.get_performance_stats()

        return {
            'initial_capital': self.config.initial_capital,
            'final_capital': self.risk_manager.current_capital,
            'total_pnl': performance['total_pnl'],
            'total_pnl_pct': performance['total_pnl_pct'],
            'total_trades': performance['total_trades'],
            'winning_trades': performance['winning_trades'],
            'losing_trades': performance['losing_trades'],
            'win_rate': performance['win_rate'],
            'avg_win': performance['avg_win'],
            'avg_loss': performance['avg_loss'],
            'profit_factor': performance['profit_factor'],
            'max_drawdown': performance['max_drawdown'],
            'max_drawdown_pct': performance['max_drawdown_pct'],
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
