"""
POI (Point of Interest) 모듈

관심 구간(POI)을 통합 관리합니다.
"""
import pandas as pd
from typing import List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .order_block import OrderBlock, OrderBlockAnalyzer
from .fvg import FVG, FVGAnalyzer
from .liquidity import LiquidityLevel, LiquidityAnalyzer


class POIType(Enum):
    """POI 타입"""
    ORDER_BLOCK = "order_block"
    FVG = "fvg"
    LIQUIDITY = "liquidity"


@dataclass
class POI:
    """통합 POI 데이터 클래스"""
    poi_type: POIType
    price_top: float
    price_bottom: float
    timestamp: pd.Timestamp
    direction: str  # 'bullish' or 'bearish'
    strength: float  # 강도 (0-1)
    is_activated: bool = False
    data: Union[OrderBlock, FVG, LiquidityLevel] = None


class POIManager:
    """POI 관리 클래스"""

    def __init__(
        self,
        ob_analyzer: OrderBlockAnalyzer,
        fvg_analyzer: FVGAnalyzer,
        liquidity_analyzer: LiquidityAnalyzer
    ):
        """
        Args:
            ob_analyzer: 오더 블록 분석기
            fvg_analyzer: FVG 분석기
            liquidity_analyzer: 유동성 분석기
        """
        self.ob_analyzer = ob_analyzer
        self.fvg_analyzer = fvg_analyzer
        self.liquidity_analyzer = liquidity_analyzer
        self.poi_list: List[POI] = []

    def update_all_pois(self, df: pd.DataFrame) -> None:
        """
        모든 POI 업데이트

        Args:
            df: OHLCV 데이터프레임
        """
        self.poi_list.clear()

        # 오더 블록 추가
        self.ob_analyzer.update_order_blocks(df)
        for ob in self.ob_analyzer.order_blocks:
            poi = POI(
                poi_type=POIType.ORDER_BLOCK,
                price_top=ob.top,
                price_bottom=ob.bottom,
                timestamp=ob.timestamp,
                direction=ob.ob_type,
                strength=ob.strength,
                is_activated=ob.is_tested,
                data=ob
            )
            self.poi_list.append(poi)

        # FVG 추가
        self.fvg_analyzer.update_fvg_list(df)
        for fvg in self.fvg_analyzer.fvg_list:
            poi = POI(
                poi_type=POIType.FVG,
                price_top=fvg.top,
                price_bottom=fvg.bottom,
                timestamp=fvg.timestamp,
                direction=fvg.direction,
                strength=0.7,  # FVG 기본 강도
                is_activated=fvg.is_rebalanced,
                data=fvg
            )
            self.poi_list.append(poi)

        # 유동성 레벨 추가
        self.liquidity_analyzer.update_liquidity_levels(df)
        for liq in self.liquidity_analyzer.liquidity_levels:
            direction = 'bullish' if liq.level_type in ['pdl', 'swing_low', 'low'] else 'bearish'
            poi = POI(
                poi_type=POIType.LIQUIDITY,
                price_top=liq.price,
                price_bottom=liq.price,
                timestamp=liq.timestamp,
                direction=direction,
                strength=liq.strength,
                is_activated=liq.is_grabbed,
                data=liq
            )
            self.poi_list.append(poi)

    def get_pois_by_type(
        self,
        poi_type: POIType,
        only_inactive: bool = True
    ) -> List[POI]:
        """
        타입별 POI 조회

        Args:
            poi_type: POI 타입
            only_inactive: 비활성화된 것만 조회

        Returns:
            필터링된 POI 리스트
        """
        filtered = [poi for poi in self.poi_list if poi.poi_type == poi_type]

        if only_inactive:
            filtered = [poi for poi in filtered if not poi.is_activated]

        return filtered

    def get_pois_by_direction(
        self,
        direction: str,
        only_inactive: bool = True
    ) -> List[POI]:
        """
        방향별 POI 조회

        Args:
            direction: 방향 ('bullish' or 'bearish')
            only_inactive: 비활성화된 것만 조회

        Returns:
            필터링된 POI 리스트
        """
        filtered = [poi for poi in self.poi_list if poi.direction == direction]

        if only_inactive:
            filtered = [poi for poi in filtered if not poi.is_activated]

        return filtered

    def get_nearest_poi(
        self,
        current_price: float,
        direction: Optional[str] = None,
        poi_type: Optional[POIType] = None,
        only_inactive: bool = True
    ) -> Optional[POI]:
        """
        가장 가까운 POI 찾기

        Args:
            current_price: 현재 가격
            direction: 방향 필터
            poi_type: POI 타입 필터
            only_inactive: 비활성화된 것만 조회

        Returns:
            가장 가까운 POI (없으면 None)
        """
        filtered = self.poi_list

        if only_inactive:
            filtered = [poi for poi in filtered if not poi.is_activated]

        if direction:
            filtered = [poi for poi in filtered if poi.direction == direction]

        if poi_type:
            filtered = [poi for poi in filtered if poi.poi_type == poi_type]

        if not filtered:
            return None

        # 거리 계산
        def distance(poi: POI) -> float:
            poi_center = (poi.price_top + poi.price_bottom) / 2
            return abs(poi_center - current_price)

        return min(filtered, key=distance)

    def get_strongest_pois(
        self,
        top_n: int = 5,
        direction: Optional[str] = None,
        only_inactive: bool = True
    ) -> List[POI]:
        """
        가장 강한 POI들 조회

        Args:
            top_n: 조회할 개수
            direction: 방향 필터
            only_inactive: 비활성화된 것만 조회

        Returns:
            강도순 정렬된 POI 리스트
        """
        filtered = self.poi_list

        if only_inactive:
            filtered = [poi for poi in filtered if not poi.is_activated]

        if direction:
            filtered = [poi for poi in filtered if poi.direction == direction]

        # 강도순 정렬
        sorted_pois = sorted(filtered, key=lambda poi: poi.strength, reverse=True)

        return sorted_pois[:top_n]

    def check_poi_confluence(
        self,
        price_range: tuple,
        min_confluence: int = 2
    ) -> List[POI]:
        """
        POI 컨플루언스(집중) 확인

        여러 POI가 겹치는 영역을 찾습니다.

        Args:
            price_range: (하한, 상한) 가격 범위
            min_confluence: 최소 컨플루언스 개수

        Returns:
            컨플루언스가 있는 POI 리스트
        """
        lower, upper = price_range
        confluence_pois = []

        for poi in self.poi_list:
            if poi.is_activated:
                continue

            # POI가 가격 범위와 겹치는지 확인
            if not (poi.price_bottom > upper or poi.price_top < lower):
                confluence_pois.append(poi)

        if len(confluence_pois) >= min_confluence:
            return confluence_pois

        return []
