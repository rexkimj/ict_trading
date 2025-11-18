"""
청산 전략 모듈

ICT 트레이딩의 올바른 청산 원칙을 구현합니다.
"""
import pandas as pd
from typing import Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from ..core.liquidity import LiquidityAnalyzer, LiquidityLevel
from ..core.fvg import FVGAnalyzer, FVG


@dataclass
class ExitSignal:
    """청산 신호"""
    timestamp: datetime
    exit_type: str  # 'take_profit', 'stop_loss', 'trailing_stop'
    exit_price: float
    reason: str


@dataclass
class ExitLevels:
    """청산 레벨"""
    take_profit_levels: List[Tuple[float, float]]  # [(가격, 비율), ...]
    stop_loss: float
    trailing_stop: Optional[float] = None


class ExitStrategy:
    """청산 전략 클래스"""

    def __init__(
        self,
        liquidity_analyzer: LiquidityAnalyzer,
        fvg_analyzer: FVGAnalyzer
    ):
        """
        Args:
            liquidity_analyzer: 유동성 분석기
            fvg_analyzer: FVG 분석기
        """
        self.liquidity_analyzer = liquidity_analyzer
        self.fvg_analyzer = fvg_analyzer

    def calculate_exit_levels(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: str,
        risk_amount: float
    ) -> ExitLevels:
        """
        청산 레벨 계산

        Args:
            df: OHLCV 데이터
            entry_price: 진입 가격
            direction: 진입 방향 ('long' or 'short')
            risk_amount: 리스크 금액

        Returns:
            청산 레벨
        """
        # Take Profit 레벨 계산
        tp_levels = self._calculate_take_profit_levels(
            df, entry_price, direction
        )

        # Stop Loss 계산
        stop_loss = self._calculate_stop_loss(
            df, entry_price, direction
        )

        return ExitLevels(
            take_profit_levels=tp_levels,
            stop_loss=stop_loss
        )

    def _calculate_take_profit_levels(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: str
    ) -> List[Tuple[float, float]]:
        """
        Take Profit 레벨 계산

        유동성 레벨과 FVG를 목표로 설정합니다.

        Args:
            df: OHLCV 데이터
            entry_price: 진입 가격
            direction: 진입 방향

        Returns:
            [(TP 가격, 청산 비율), ...] 리스트
        """
        tp_levels = []

        if direction == 'long':
            # 롱: 위쪽 유동성 목표
            upper_liquidity = self.liquidity_analyzer.get_nearest_liquidity(
                entry_price, direction='above'
            )

            if upper_liquidity:
                # TP1: 가장 가까운 유동성의 50%
                tp_levels.append((upper_liquidity.price, 0.5))

                # TP2: 가장 가까운 유동성의 100%
                # 추가 유동성 레벨 찾기
                additional_liq = self._find_next_liquidity(
                    entry_price, direction='above', exclude_price=upper_liquidity.price
                )
                if additional_liq:
                    tp_levels.append((additional_liq.price, 0.3))

            # FVG 목표
            upper_fvg = self.fvg_analyzer.get_nearest_fvg(
                entry_price, direction='bullish', only_unrebalanced=True
            )
            if upper_fvg and upper_fvg.top > entry_price:
                tp_levels.append((upper_fvg.top, 0.2))

        else:  # short
            # 숏: 아래쪽 유동성 목표
            lower_liquidity = self.liquidity_analyzer.get_nearest_liquidity(
                entry_price, direction='below'
            )

            if lower_liquidity:
                # TP1: 가장 가까운 유동성의 50%
                tp_levels.append((lower_liquidity.price, 0.5))

                # TP2: 추가 유동성 레벨
                additional_liq = self._find_next_liquidity(
                    entry_price, direction='below', exclude_price=lower_liquidity.price
                )
                if additional_liq:
                    tp_levels.append((additional_liq.price, 0.3))

            # FVG 목표
            lower_fvg = self.fvg_analyzer.get_nearest_fvg(
                entry_price, direction='bearish', only_unrebalanced=True
            )
            if lower_fvg and lower_fvg.bottom < entry_price:
                tp_levels.append((lower_fvg.bottom, 0.2))

        # 가격순 정렬
        tp_levels.sort(key=lambda x: x[0], reverse=(direction == 'short'))

        return tp_levels

    def _calculate_stop_loss(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: str
    ) -> float:
        """
        Stop Loss 계산

        유동성 확보(LQG) 후 고점/저점 뒤에 설정합니다.

        Args:
            df: OHLCV 데이터
            entry_price: 진입 가격
            direction: 진입 방향

        Returns:
            Stop Loss 가격
        """
        if direction == 'long':
            # 롱: 유동성 확보된 저점 아래
            grabbed_lows = [
                liq for liq in self.liquidity_analyzer.liquidity_levels
                if liq.is_grabbed and liq.level_type in ['pdl', 'swing_low', 'low']
                and liq.price < entry_price
            ]

            if grabbed_lows:
                # 가장 가까운 확보된 저점
                nearest_low = max(grabbed_lows, key=lambda x: x.price)
                # 저점 아래 0.1% 버퍼
                stop_loss = nearest_low.price * 0.999
            else:
                # 대체: 최근 저점 아래
                lookback = 20
                recent_low = df['low'].iloc[-lookback:].min()
                stop_loss = recent_low * 0.999

        else:  # short
            # 숏: 유동성 확보된 고점 위
            grabbed_highs = [
                liq for liq in self.liquidity_analyzer.liquidity_levels
                if liq.is_grabbed and liq.level_type in ['pdh', 'swing_high', 'high']
                and liq.price > entry_price
            ]

            if grabbed_highs:
                # 가장 가까운 확보된 고점
                nearest_high = min(grabbed_highs, key=lambda x: x.price)
                # 고점 위 0.1% 버퍼
                stop_loss = nearest_high.price * 1.001
            else:
                # 대체: 최근 고점 위
                lookback = 20
                recent_high = df['high'].iloc[-lookback:].max()
                stop_loss = recent_high * 1.001

        return stop_loss

    def _find_next_liquidity(
        self,
        current_price: float,
        direction: str,
        exclude_price: float
    ) -> Optional[LiquidityLevel]:
        """
        다음 유동성 레벨 찾기

        Args:
            current_price: 현재 가격
            direction: 방향 ('above' or 'below')
            exclude_price: 제외할 가격

        Returns:
            다음 유동성 레벨 (없으면 None)
        """
        available_levels = [
            liq for liq in self.liquidity_analyzer.liquidity_levels
            if not liq.is_grabbed and abs(liq.price - exclude_price) > 0.0001
        ]

        if not available_levels:
            return None

        if direction == 'above':
            above_levels = [l for l in available_levels if l.price > current_price]
            if above_levels:
                return min(above_levels, key=lambda x: x.price)
        else:  # below
            below_levels = [l for l in available_levels if l.price < current_price]
            if below_levels:
                return max(below_levels, key=lambda x: x.price)

        return None

    def check_exit(
        self,
        current_price: float,
        entry_price: float,
        direction: str,
        exit_levels: ExitLevels
    ) -> Optional[ExitSignal]:
        """
        청산 신호 확인

        Args:
            current_price: 현재 가격
            entry_price: 진입 가격
            direction: 진입 방향
            exit_levels: 청산 레벨

        Returns:
            청산 신호 (없으면 None)
        """
        # Stop Loss 확인
        if direction == 'long':
            if current_price <= exit_levels.stop_loss:
                return ExitSignal(
                    timestamp=datetime.now(),
                    exit_type='stop_loss',
                    exit_price=exit_levels.stop_loss,
                    reason="Stop Loss 도달"
                )
        else:  # short
            if current_price >= exit_levels.stop_loss:
                return ExitSignal(
                    timestamp=datetime.now(),
                    exit_type='stop_loss',
                    exit_price=exit_levels.stop_loss,
                    reason="Stop Loss 도달"
                )

        # Take Profit 확인
        for tp_price, tp_ratio in exit_levels.take_profit_levels:
            if direction == 'long':
                if current_price >= tp_price:
                    return ExitSignal(
                        timestamp=datetime.now(),
                        exit_type='take_profit',
                        exit_price=tp_price,
                        reason=f"Take Profit 도달 ({tp_ratio*100:.0f}% 청산)"
                    )
            else:  # short
                if current_price <= tp_price:
                    return ExitSignal(
                        timestamp=datetime.now(),
                        exit_type='take_profit',
                        exit_price=tp_price,
                        reason=f"Take Profit 도달 ({tp_ratio*100:.0f}% 청산)"
                    )

        return None

    def update_trailing_stop(
        self,
        current_price: float,
        entry_price: float,
        direction: str,
        exit_levels: ExitLevels,
        trail_pct: float = 0.5
    ) -> Optional[float]:
        """
        추적 손절매 업데이트

        Args:
            current_price: 현재 가격
            entry_price: 진입 가격
            direction: 진입 방향
            exit_levels: 청산 레벨
            trail_pct: 추적 비율

        Returns:
            업데이트된 추적 손절매 가격 (없으면 None)
        """
        if direction == 'long':
            # 롱: 가격이 상승하면 손절가 올림
            profit_pct = (current_price - entry_price) / entry_price

            if profit_pct > 0.01:  # 1% 이상 수익
                new_trailing_stop = current_price * (1 - trail_pct / 100)

                if exit_levels.trailing_stop is None or new_trailing_stop > exit_levels.trailing_stop:
                    exit_levels.trailing_stop = new_trailing_stop
                    return new_trailing_stop

        else:  # short
            # 숏: 가격이 하락하면 손절가 내림
            profit_pct = (entry_price - current_price) / entry_price

            if profit_pct > 0.01:  # 1% 이상 수익
                new_trailing_stop = current_price * (1 + trail_pct / 100)

                if exit_levels.trailing_stop is None or new_trailing_stop < exit_levels.trailing_stop:
                    exit_levels.trailing_stop = new_trailing_stop
                    return new_trailing_stop

        return None
