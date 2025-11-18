"""
시장 구조(Market Structure) 모듈

시장의 추세와 구조 변화를 분석합니다.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional, List
from enum import Enum
from dataclasses import dataclass


class TrendDirection(Enum):
    """추세 방향"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"


class StructureType(Enum):
    """구조 타입"""
    HIGHER_HIGH = "HH"  # 고점 갱신
    HIGHER_LOW = "HL"   # 저점 상승
    LOWER_HIGH = "LH"   # 고점 하락
    LOWER_LOW = "LL"    # 저점 갱신
    EQUAL_HIGH = "EH"   # 동일 고점
    EQUAL_LOW = "EL"    # 동일 저점


@dataclass
class StructurePoint:
    """구조 포인트"""
    price: float
    timestamp: pd.Timestamp
    structure_type: StructureType
    is_break: bool = False  # 구조 붕괴 여부


class MarketStructureAnalyzer:
    """시장 구조 분석 클래스"""

    def __init__(self, equal_threshold: float = 0.001):
        """
        Args:
            equal_threshold: 동일 레벨 판단 임계값
        """
        self.equal_threshold = equal_threshold
        self.structure_points: List[StructurePoint] = []
        self.current_trend: TrendDirection = TrendDirection.RANGING

    def identify_structure(
        self,
        df: pd.DataFrame,
        lookback: int = 5
    ) -> List[StructurePoint]:
        """
        시장 구조 식별

        Args:
            df: OHLCV 데이터프레임
            lookback: 스윙 포인트 룩백 기간

        Returns:
            구조 포인트 리스트
        """
        structure_points = []

        # 스윙 포인트 찾기
        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(df) - lookback):
            # 스윙 고점
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                swing_highs.append((i, df['high'].iloc[i]))

            # 스윙 저점
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                swing_lows.append((i, df['low'].iloc[i]))

        # 고점 구조 분석
        for i in range(1, len(swing_highs)):
            prev_high = swing_highs[i-1][1]
            curr_high = swing_highs[i][1]
            idx = swing_highs[i][0]

            if curr_high > prev_high * (1 + self.equal_threshold):
                structure_type = StructureType.HIGHER_HIGH
            elif curr_high < prev_high * (1 - self.equal_threshold):
                structure_type = StructureType.LOWER_HIGH
            else:
                structure_type = StructureType.EQUAL_HIGH

            structure_points.append(StructurePoint(
                price=curr_high,
                timestamp=df.index[idx],
                structure_type=structure_type
            ))

        # 저점 구조 분석
        for i in range(1, len(swing_lows)):
            prev_low = swing_lows[i-1][1]
            curr_low = swing_lows[i][1]
            idx = swing_lows[i][0]

            if curr_low > prev_low * (1 + self.equal_threshold):
                structure_type = StructureType.HIGHER_LOW
            elif curr_low < prev_low * (1 - self.equal_threshold):
                structure_type = StructureType.LOWER_LOW
            else:
                structure_type = StructureType.EQUAL_LOW

            structure_points.append(StructurePoint(
                price=curr_low,
                timestamp=df.index[idx],
                structure_type=structure_type
            ))

        # 시간순 정렬
        structure_points.sort(key=lambda x: x.timestamp)

        self.structure_points = structure_points
        return structure_points

    def determine_trend(self, recent_count: int = 4) -> TrendDirection:
        """
        현재 추세 판단

        Args:
            recent_count: 최근 구조 포인트 개수

        Returns:
            추세 방향
        """
        if len(self.structure_points) < recent_count:
            return TrendDirection.RANGING

        recent_structures = self.structure_points[-recent_count:]

        # HH와 HL 카운트
        hh_hl_count = sum(1 for s in recent_structures
                         if s.structure_type in [StructureType.HIGHER_HIGH, StructureType.HIGHER_LOW])

        # LL와 LH 카운트
        ll_lh_count = sum(1 for s in recent_structures
                         if s.structure_type in [StructureType.LOWER_LOW, StructureType.LOWER_HIGH])

        # 추세 판단
        if hh_hl_count >= recent_count * 0.75:
            self.current_trend = TrendDirection.BULLISH
        elif ll_lh_count >= recent_count * 0.75:
            self.current_trend = TrendDirection.BEARISH
        else:
            self.current_trend = TrendDirection.RANGING

        return self.current_trend

    def detect_break_of_structure(
        self,
        df: pd.DataFrame,
        current_idx: int
    ) -> Optional[StructurePoint]:
        """
        BOS (Break of Structure) 탐지

        Args:
            df: OHLCV 데이터프레임
            current_idx: 현재 인덱스

        Returns:
            붕괴된 구조 포인트 (없으면 None)
        """
        current_price = df['close'].iloc[current_idx]

        # 최근 구조 포인트 확인
        for structure_point in reversed(self.structure_points):
            if structure_point.is_break:
                continue

            # 강세 추세에서 최근 저점(HL) 하향 돌파
            if (self.current_trend == TrendDirection.BULLISH and
                structure_point.structure_type == StructureType.HIGHER_LOW):
                if current_price < structure_point.price:
                    structure_point.is_break = True
                    return structure_point

            # 약세 추세에서 최근 고점(LH) 상향 돌파
            if (self.current_trend == TrendDirection.BEARISH and
                structure_point.structure_type == StructureType.LOWER_HIGH):
                if current_price > structure_point.price:
                    structure_point.is_break = True
                    return structure_point

        return None

    def get_trend_direction(self) -> TrendDirection:
        """현재 추세 방향 반환"""
        return self.current_trend

    def is_bullish(self) -> bool:
        """강세 추세 여부"""
        return self.current_trend == TrendDirection.BULLISH

    def is_bearish(self) -> bool:
        """약세 추세 여부"""
        return self.current_trend == TrendDirection.BEARISH

    def is_ranging(self) -> bool:
        """횡보 여부"""
        return self.current_trend == TrendDirection.RANGING
