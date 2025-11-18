"""
오더 블록(Order Block) 모듈

기관의 주문 집중 영역을 식별합니다.
"""
import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class OrderBlock:
    """오더 블록 데이터 클래스"""
    top: float
    bottom: float
    timestamp: pd.Timestamp
    ob_type: str  # 'bullish' or 'bearish'
    strength: float  # 강도 (0-1)
    is_tested: bool = False
    volume: float = 0.0


class OrderBlockAnalyzer:
    """오더 블록 분석 클래스"""

    def __init__(
        self,
        box_range_level: float = 0.5,
        min_volume_ratio: float = 1.5
    ):
        """
        Args:
            box_range_level: 박스권 레벨 (0.5 = 50%)
            min_volume_ratio: 최소 거래량 비율 (평균 대비)
        """
        self.box_range_level = box_range_level
        self.min_volume_ratio = min_volume_ratio
        self.order_blocks: List[OrderBlock] = []

    def identify_order_blocks(
        self,
        df: pd.DataFrame,
        lookback: int = 20
    ) -> List[OrderBlock]:
        """
        오더 블록 식별

        오더 블록은 가격 반전 직전의 마지막 반대 방향 캔들입니다.

        Args:
            df: OHLCV 데이터프레임
            lookback: 룩백 기간

        Returns:
            식별된 오더 블록 리스트
        """
        order_blocks = []

        # 평균 거래량 계산
        avg_volume = df['volume'].rolling(window=lookback).mean()

        for i in range(lookback, len(df) - 1):
            current_close = df['close'].iloc[i]
            current_open = df['open'].iloc[i]
            current_volume = df['volume'].iloc[i]
            next_close = df['close'].iloc[i+1]

            # 거래량 조건
            if current_volume < avg_volume.iloc[i] * self.min_volume_ratio:
                continue

            # Bullish Order Block: 하락 캔들 후 상승 반전
            if current_close < current_open and next_close > df['close'].iloc[i]:
                # 최근 하락 추세 확인
                recent_trend_down = all(
                    df['close'].iloc[j] < df['close'].iloc[j-1]
                    for j in range(max(0, i-3), i)
                    if j > 0
                )

                if recent_trend_down:
                    ob = OrderBlock(
                        top=df['high'].iloc[i],
                        bottom=df['low'].iloc[i],
                        timestamp=df.index[i],
                        ob_type='bullish',
                        strength=min(1.0, current_volume / avg_volume.iloc[i] / self.min_volume_ratio),
                        volume=current_volume
                    )
                    order_blocks.append(ob)

            # Bearish Order Block: 상승 캔들 후 하락 반전
            elif current_close > current_open and next_close < df['close'].iloc[i]:
                # 최근 상승 추세 확인
                recent_trend_up = all(
                    df['close'].iloc[j] > df['close'].iloc[j-1]
                    for j in range(max(0, i-3), i)
                    if j > 0
                )

                if recent_trend_up:
                    ob = OrderBlock(
                        top=df['high'].iloc[i],
                        bottom=df['low'].iloc[i],
                        timestamp=df.index[i],
                        ob_type='bearish',
                        strength=min(1.0, current_volume / avg_volume.iloc[i] / self.min_volume_ratio),
                        volume=current_volume
                    )
                    order_blocks.append(ob)

        self.order_blocks = order_blocks
        return order_blocks

    def identify_box_range_ob(
        self,
        df: pd.DataFrame,
        range_threshold: float = 0.02
    ) -> List[OrderBlock]:
        """
        박스권(Range) 내 오더 블록 식별

        박스권의 0.5 레벨에 위치한 오더 블록을 찾습니다.

        Args:
            df: OHLCV 데이터프레임
            range_threshold: 박스권 판단 임계값

        Returns:
            박스권 오더 블록 리스트
        """
        box_obs = []

        # 박스권 탐지
        lookback = 50
        if len(df) < lookback:
            return box_obs

        recent_high = df['high'].iloc[-lookback:].max()
        recent_low = df['low'].iloc[-lookback:].min()
        price_range = recent_high - recent_low

        # 박스권 여부 확인 (변동성이 작으면 박스권)
        if price_range / recent_low > range_threshold:
            return box_obs  # 박스권이 아님

        # 박스권 0.5 레벨
        mid_level = recent_low + price_range * self.box_range_level

        # 0.5 레벨 근처의 오더 블록 찾기
        tolerance = price_range * 0.1  # 10% 허용 범위

        for ob in self.order_blocks:
            ob_mid = (ob.top + ob.bottom) / 2

            if abs(ob_mid - mid_level) <= tolerance:
                box_obs.append(ob)

        return box_obs

    def check_ob_test(
        self,
        ob: OrderBlock,
        current_price: float
    ) -> bool:
        """
        오더 블록 테스트 여부 확인

        Args:
            ob: 확인할 오더 블록
            current_price: 현재 가격

        Returns:
            테스트 여부
        """
        if ob.is_tested:
            return True

        # 가격이 오더 블록 영역에 진입했는지 확인
        if current_price >= ob.bottom and current_price <= ob.top:
            ob.is_tested = True
            return True

        return False

    def get_nearest_ob(
        self,
        current_price: float,
        ob_type: Optional[str] = None,
        only_untested: bool = True
    ) -> Optional[OrderBlock]:
        """
        가장 가까운 오더 블록 찾기

        Args:
            current_price: 현재 가격
            ob_type: 오더 블록 타입 ('bullish', 'bearish', None)
            only_untested: 테스트 안 된 것만 찾기

        Returns:
            가장 가까운 오더 블록 (없으면 None)
        """
        available_obs = self.order_blocks

        # 필터링
        if only_untested:
            available_obs = [ob for ob in available_obs if not ob.is_tested]

        if ob_type:
            available_obs = [ob for ob in available_obs if ob.ob_type == ob_type]

        if not available_obs:
            return None

        # 거리 계산 (오더 블록 중심점 기준)
        def distance(ob: OrderBlock) -> float:
            ob_center = (ob.top + ob.bottom) / 2
            return abs(ob_center - current_price)

        return min(available_obs, key=distance)

    def get_strongest_ob(
        self,
        ob_type: Optional[str] = None,
        only_untested: bool = True
    ) -> Optional[OrderBlock]:
        """
        가장 강한 오더 블록 찾기

        Args:
            ob_type: 오더 블록 타입
            only_untested: 테스트 안 된 것만 찾기

        Returns:
            가장 강한 오더 블록 (없으면 None)
        """
        available_obs = self.order_blocks

        # 필터링
        if only_untested:
            available_obs = [ob for ob in available_obs if not ob.is_tested]

        if ob_type:
            available_obs = [ob for ob in available_obs if ob.ob_type == ob_type]

        if not available_obs:
            return None

        return max(available_obs, key=lambda ob: ob.strength)

    def update_order_blocks(self, df: pd.DataFrame, lookback: int = 20) -> None:
        """
        오더 블록 리스트 업데이트

        Args:
            df: OHLCV 데이터프레임
            lookback: 룩백 기간
        """
        self.identify_order_blocks(df, lookback)
