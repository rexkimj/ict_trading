"""
FVG (Fair Value Gap) / 인밸런스(Imbalance) 모듈

가격의 불균형 영역을 탐지하고 리밸런스를 추적합니다.
"""
import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class FVG:
    """FVG (Fair Value Gap) 데이터 클래스"""
    start_idx: int
    end_idx: int
    top: float
    bottom: float
    timestamp: pd.Timestamp
    direction: str  # 'bullish' or 'bearish'
    is_rebalanced: bool = False
    rebalance_percentage: float = 0.0


class FVGAnalyzer:
    """FVG 분석 클래스"""

    def __init__(
        self,
        min_fvg_size: float = 0.0005,
        rebalance_threshold: float = 0.5
    ):
        """
        Args:
            min_fvg_size: 최소 FVG 크기 (비율)
            rebalance_threshold: 리밸런스 판단 임계값 (0.5 = 50%)
        """
        self.min_fvg_size = min_fvg_size
        self.rebalance_threshold = rebalance_threshold
        self.fvg_list: List[FVG] = []

    def identify_fvg(self, df: pd.DataFrame) -> List[FVG]:
        """
        FVG 식별

        FVG는 3개의 연속된 캔들로 구성:
        - Bullish FVG: 캔들1 high < 캔들3 low (중간에 갭 존재)
        - Bearish FVG: 캔들1 low > 캔들3 high

        Args:
            df: OHLCV 데이터프레임

        Returns:
            식별된 FVG 리스트
        """
        fvg_list = []

        for i in range(2, len(df)):
            candle1_high = df['high'].iloc[i-2]
            candle1_low = df['low'].iloc[i-2]
            candle2_high = df['high'].iloc[i-1]
            candle2_low = df['low'].iloc[i-1]
            candle3_high = df['high'].iloc[i]
            candle3_low = df['low'].iloc[i]

            # Bullish FVG: 캔들1의 고점이 캔들3의 저점보다 낮음
            if candle1_high < candle3_low:
                gap_size = (candle3_low - candle1_high) / candle1_high
                if gap_size >= self.min_fvg_size:
                    fvg = FVG(
                        start_idx=i-2,
                        end_idx=i,
                        top=candle3_low,
                        bottom=candle1_high,
                        timestamp=df.index[i],
                        direction='bullish'
                    )
                    fvg_list.append(fvg)

            # Bearish FVG: 캔들1의 저점이 캔들3의 고점보다 높음
            elif candle1_low > candle3_high:
                gap_size = (candle1_low - candle3_high) / candle3_high
                if gap_size >= self.min_fvg_size:
                    fvg = FVG(
                        start_idx=i-2,
                        end_idx=i,
                        top=candle1_low,
                        bottom=candle3_high,
                        timestamp=df.index[i],
                        direction='bearish'
                    )
                    fvg_list.append(fvg)

        self.fvg_list = fvg_list
        return fvg_list

    def check_rebalance(
        self,
        fvg: FVG,
        current_price: float
    ) -> bool:
        """
        FVG 리밸런스 확인

        Args:
            fvg: 확인할 FVG
            current_price: 현재 가격

        Returns:
            리밸런스 여부
        """
        if fvg.is_rebalanced:
            return True

        # FVG 영역 내 침투 정도 계산
        if fvg.direction == 'bullish':
            if current_price <= fvg.top and current_price >= fvg.bottom:
                # 리밸런스 비율 계산
                fvg.rebalance_percentage = (fvg.top - current_price) / (fvg.top - fvg.bottom)

                if fvg.rebalance_percentage >= self.rebalance_threshold:
                    fvg.is_rebalanced = True
                    return True

        elif fvg.direction == 'bearish':
            if current_price >= fvg.bottom and current_price <= fvg.top:
                # 리밸런스 비율 계산
                fvg.rebalance_percentage = (current_price - fvg.bottom) / (fvg.top - fvg.bottom)

                if fvg.rebalance_percentage >= self.rebalance_threshold:
                    fvg.is_rebalanced = True
                    return True

        return False

    def get_nearest_fvg(
        self,
        current_price: float,
        direction: Optional[str] = None,
        only_unrebalanced: bool = True
    ) -> Optional[FVG]:
        """
        가장 가까운 FVG 찾기

        Args:
            current_price: 현재 가격
            direction: FVG 방향 필터 ('bullish', 'bearish', None)
            only_unrebalanced: 리밸런스 안 된 것만 찾기

        Returns:
            가장 가까운 FVG (없으면 None)
        """
        available_fvgs = self.fvg_list

        # 필터링
        if only_unrebalanced:
            available_fvgs = [fvg for fvg in available_fvgs if not fvg.is_rebalanced]

        if direction:
            available_fvgs = [fvg for fvg in available_fvgs if fvg.direction == direction]

        if not available_fvgs:
            return None

        # 거리 계산 (FVG 중심점 기준)
        def distance(fvg: FVG) -> float:
            fvg_center = (fvg.top + fvg.bottom) / 2
            return abs(fvg_center - current_price)

        return min(available_fvgs, key=distance)

    def filter_fvg_by_fibonacci(
        self,
        df: pd.DataFrame,
        lookback: int = 50,
        fib_level: float = 0.5
    ) -> List[FVG]:
        """
        피보나치 레벨로 FVG 필터링

        피보나치 0.5 레벨 근처의 FVG를 우선순위로 합니다.

        Args:
            df: OHLCV 데이터프레임
            lookback: 피보나치 계산 룩백 기간
            fib_level: 피보나치 레벨 (0.5 = 50%)

        Returns:
            필터링된 FVG 리스트
        """
        if len(df) < lookback:
            return self.fvg_list

        # 최근 lookback 기간의 고점/저점
        recent_high = df['high'].iloc[-lookback:].max()
        recent_low = df['low'].iloc[-lookback:].min()

        # 피보나치 레벨 계산
        fib_price = recent_low + (recent_high - recent_low) * fib_level

        # FVG를 피보나치 레벨과의 거리로 정렬
        filtered_fvgs = []
        for fvg in self.fvg_list:
            fvg_center = (fvg.top + fvg.bottom) / 2
            distance_to_fib = abs(fvg_center - fib_price)

            # 피보나치 레벨 근처의 FVG만 선택
            price_range = recent_high - recent_low
            if distance_to_fib <= price_range * 0.1:  # 10% 이내
                filtered_fvgs.append(fvg)

        return filtered_fvgs

    def update_fvg_list(self, df: pd.DataFrame) -> None:
        """
        FVG 리스트 업데이트

        Args:
            df: OHLCV 데이터프레임
        """
        self.identify_fvg(df)
