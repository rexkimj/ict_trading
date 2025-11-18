"""
유동성(Liquidity) 모듈

스마트 머니가 타겟하는 유동성 영역을 식별하고 추적합니다.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LiquidityLevel:
    """유동성 레벨 데이터 클래스"""
    price: float
    timestamp: pd.Timestamp
    level_type: str  # 'high', 'low', 'pdh', 'pdl', 'swing_high', 'swing_low'
    strength: float  # 유동성 강도 (0-1)
    is_grabbed: bool = False  # 유동성 확보 여부


class LiquidityAnalyzer:
    """유동성 분석 클래스"""

    def __init__(self, liquidity_grab_threshold: float = 0.001):
        """
        Args:
            liquidity_grab_threshold: 유동성 확보 판단 임계값
        """
        self.liquidity_grab_threshold = liquidity_grab_threshold
        self.liquidity_levels: List[LiquidityLevel] = []

    def identify_pdh_pdl(self, df: pd.DataFrame) -> Tuple[List[LiquidityLevel], List[LiquidityLevel]]:
        """
        PDH (Previous Day High) / PDL (Previous Day Low) 식별

        Args:
            df: OHLCV 데이터프레임

        Returns:
            (PDH 레벨 리스트, PDL 레벨 리스트)
        """
        pdh_levels = []
        pdl_levels = []

        # 일별로 그룹화
        daily_data = df.resample('1D').agg({
            'high': 'max',
            'low': 'min',
            'close': 'last'
        })

        for i in range(1, len(daily_data)):
            # 전일 고점
            pdh = LiquidityLevel(
                price=daily_data['high'].iloc[i-1],
                timestamp=daily_data.index[i],
                level_type='pdh',
                strength=0.8  # PDH/PDL은 높은 강도
            )
            pdh_levels.append(pdh)

            # 전일 저점
            pdl = LiquidityLevel(
                price=daily_data['low'].iloc[i-1],
                timestamp=daily_data.index[i],
                level_type='pdl',
                strength=0.8
            )
            pdl_levels.append(pdl)

        return pdh_levels, pdl_levels

    def identify_swing_points(
        self,
        df: pd.DataFrame,
        lookback: int = 5
    ) -> Tuple[List[LiquidityLevel], List[LiquidityLevel]]:
        """
        스윙 고점/저점 식별

        Args:
            df: OHLCV 데이터프레임
            lookback: 스윙 포인트 탐지 룩백 기간

        Returns:
            (스윙 고점 리스트, 스윙 저점 리스트)
        """
        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(df) - lookback):
            # 스윙 고점: 양쪽 lookback 기간의 최고점
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                swing_high = LiquidityLevel(
                    price=df['high'].iloc[i],
                    timestamp=df.index[i],
                    level_type='swing_high',
                    strength=0.6
                )
                swing_highs.append(swing_high)

            # 스윙 저점: 양쪽 lookback 기간의 최저점
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                swing_low = LiquidityLevel(
                    price=df['low'].iloc[i],
                    timestamp=df.index[i],
                    level_type='swing_low',
                    strength=0.6
                )
                swing_lows.append(swing_low)

        return swing_highs, swing_lows

    def check_liquidity_grab(
        self,
        current_price: float,
        liquidity_level: LiquidityLevel,
        is_bullish: bool
    ) -> bool:
        """
        유동성 확보(Liquidity Grab) 여부 확인

        Args:
            current_price: 현재 가격
            liquidity_level: 확인할 유동성 레벨
            is_bullish: 강세 방향 여부

        Returns:
            유동성 확보 여부
        """
        if liquidity_level.is_grabbed:
            return False

        if is_bullish:
            # 강세 시: 저점 유동성 확보 (가격이 저점 아래로 터치 후 복귀)
            if liquidity_level.level_type in ['pdl', 'swing_low', 'low']:
                price_diff = (liquidity_level.price - current_price) / liquidity_level.price
                if price_diff >= -self.liquidity_grab_threshold:
                    liquidity_level.is_grabbed = True
                    return True
        else:
            # 약세 시: 고점 유동성 확보 (가격이 고점 위로 터치 후 복귀)
            if liquidity_level.level_type in ['pdh', 'swing_high', 'high']:
                price_diff = (current_price - liquidity_level.price) / liquidity_level.price
                if price_diff >= -self.liquidity_grab_threshold:
                    liquidity_level.is_grabbed = True
                    return True

        return False

    def get_nearest_liquidity(
        self,
        current_price: float,
        direction: str = 'both'
    ) -> Optional[LiquidityLevel]:
        """
        가장 가까운 유동성 레벨 찾기

        Args:
            current_price: 현재 가격
            direction: 'above', 'below', 'both'

        Returns:
            가장 가까운 유동성 레벨 (없으면 None)
        """
        available_levels = [level for level in self.liquidity_levels if not level.is_grabbed]

        if not available_levels:
            return None

        if direction == 'above':
            above_levels = [l for l in available_levels if l.price > current_price]
            if above_levels:
                return min(above_levels, key=lambda x: abs(x.price - current_price))
        elif direction == 'below':
            below_levels = [l for l in available_levels if l.price < current_price]
            if below_levels:
                return min(below_levels, key=lambda x: abs(x.price - current_price))
        else:  # both
            return min(available_levels, key=lambda x: abs(x.price - current_price))

        return None

    def update_liquidity_levels(
        self,
        df: pd.DataFrame,
        lookback: int = 5
    ) -> None:
        """
        유동성 레벨 업데이트

        Args:
            df: OHLCV 데이터프레임
            lookback: 스윙 포인트 룩백 기간
        """
        self.liquidity_levels.clear()

        # PDH/PDL 추가
        pdh_levels, pdl_levels = self.identify_pdh_pdl(df)
        self.liquidity_levels.extend(pdh_levels)
        self.liquidity_levels.extend(pdl_levels)

        # 스윙 포인트 추가
        swing_highs, swing_lows = self.identify_swing_points(df, lookback)
        self.liquidity_levels.extend(swing_highs)
        self.liquidity_levels.extend(swing_lows)
