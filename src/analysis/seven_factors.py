"""
7가지 필수 요소 종합 분석 모듈

ICT 트레이딩의 7가지 핵심 요소를 통합 분석합니다:
1. 유동성(Liquidity)
2. 시장 구조(Market Structure)
3. BO(Break of Structure)
4. FVG/인밸런스
5. 디스카운트/프리미엄
6. 타임프레임(Timeframe)
7. SMT(Smart Money Technique)
"""
import pandas as pd
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..core.liquidity import LiquidityAnalyzer, LiquidityLevel
from ..core.market_structure import MarketStructureAnalyzer, TrendDirection, StructurePoint
from ..core.fvg import FVGAnalyzer, FVG
from ..core.order_block import OrderBlockAnalyzer, OrderBlock
from ..core.poi import POIManager
from ..core.smt import SMTAnalyzer, SMTDivergence
from .timeframe import MultiTimeframeAnalyzer, TimeframeAnalysis


@dataclass
class SevenFactorAnalysis:
    """7가지 요소 종합 분석 결과"""
    # 1. 유동성
    liquidity_grabbed: bool
    nearest_liquidity: Optional[LiquidityLevel]

    # 2. 시장 구조
    market_trend: TrendDirection
    trend_strength: float

    # 3. BOS (Break of Structure)
    bos_detected: bool
    bos_point: Optional[StructurePoint]

    # 4. FVG/인밸런스
    fvg_present: bool
    nearest_fvg: Optional[FVG]

    # 5. 디스카운트/프리미엄
    price_zone: str  # 'discount', 'premium', 'equilibrium'
    zone_percentage: float  # 0-1

    # 6. 타임프레임
    htf_alignment: bool
    htf_bias: Optional[str]

    # 7. SMT
    smt_divergence: Optional[SMTDivergence]

    # 종합 점수
    total_score: float  # 0-1
    entry_signal: bool
    timestamp: datetime


class SevenFactorAnalyzer:
    """7가지 요소 종합 분석 클래스"""

    def __init__(
        self,
        liquidity_analyzer: LiquidityAnalyzer,
        market_structure_analyzer: MarketStructureAnalyzer,
        fvg_analyzer: FVGAnalyzer,
        ob_analyzer: OrderBlockAnalyzer,
        poi_manager: POIManager,
        mtf_analyzer: MultiTimeframeAnalyzer,
        smt_analyzer: Optional[SMTAnalyzer] = None
    ):
        """
        Args:
            liquidity_analyzer: 유동성 분석기
            market_structure_analyzer: 시장 구조 분석기
            fvg_analyzer: FVG 분석기
            ob_analyzer: 오더 블록 분석기
            poi_manager: POI 매니저
            mtf_analyzer: 다중 타임프레임 분석기
            smt_analyzer: SMT 분석기 (옵션)
        """
        self.liquidity_analyzer = liquidity_analyzer
        self.market_structure_analyzer = market_structure_analyzer
        self.fvg_analyzer = fvg_analyzer
        self.ob_analyzer = ob_analyzer
        self.poi_manager = poi_manager
        self.mtf_analyzer = mtf_analyzer
        self.smt_analyzer = smt_analyzer

    def analyze(
        self,
        df: pd.DataFrame,
        current_price: float,
        direction: str,
        correlated_df: Optional[pd.DataFrame] = None
    ) -> SevenFactorAnalysis:
        """
        7가지 요소 종합 분석

        Args:
            df: OHLCV 데이터
            current_price: 현재 가격
            direction: 진입 방향 ('long' or 'short')
            correlated_df: 상관 자산 데이터 (SMT 분석용, 옵션)

        Returns:
            7가지 요소 종합 분석 결과
        """
        # 1. 유동성 분석
        liquidity_grabbed, nearest_liquidity = self._analyze_liquidity(
            df, current_price, direction
        )

        # 2. 시장 구조 분석
        market_trend = self.market_structure_analyzer.get_trend_direction()
        trend_strength = self._calculate_trend_strength(df, market_trend)

        # 3. BOS 분석
        bos_detected, bos_point = self._analyze_bos(df)

        # 4. FVG 분석
        fvg_present, nearest_fvg = self._analyze_fvg(current_price, direction)

        # 5. 디스카운트/프리미엄 분석
        price_zone, zone_percentage = self._analyze_discount_premium(
            df, current_price, direction
        )

        # 6. 타임프레임 분석
        htf_alignment = self.mtf_analyzer.check_trend_alignment()
        htf_bias = self.mtf_analyzer.get_htf_bias()

        # 7. SMT 분석 (옵션)
        smt_divergence = None
        if self.smt_analyzer and correlated_df is not None:
            smt_divergence = self.smt_analyzer.detect_smt_divergence(
                df, correlated_df
            )

        # 종합 점수 계산
        total_score = self._calculate_total_score(
            liquidity_grabbed=liquidity_grabbed,
            trend_strength=trend_strength,
            bos_detected=bos_detected,
            fvg_present=fvg_present,
            price_zone=price_zone,
            htf_alignment=htf_alignment,
            smt_divergence=smt_divergence,
            direction=direction,
            htf_bias=htf_bias
        )

        # 진입 신호 판단
        entry_signal = self._determine_entry_signal(
            total_score=total_score,
            liquidity_grabbed=liquidity_grabbed,
            htf_alignment=htf_alignment,
            price_zone=price_zone,
            direction=direction
        )

        return SevenFactorAnalysis(
            liquidity_grabbed=liquidity_grabbed,
            nearest_liquidity=nearest_liquidity,
            market_trend=market_trend,
            trend_strength=trend_strength,
            bos_detected=bos_detected,
            bos_point=bos_point,
            fvg_present=fvg_present,
            nearest_fvg=nearest_fvg,
            price_zone=price_zone,
            zone_percentage=zone_percentage,
            htf_alignment=htf_alignment,
            htf_bias=htf_bias,
            smt_divergence=smt_divergence,
            total_score=total_score,
            entry_signal=entry_signal,
            timestamp=datetime.now()
        )

    def _analyze_liquidity(
        self,
        df: pd.DataFrame,
        current_price: float,
        direction: str
    ) -> Tuple[bool, Optional[LiquidityLevel]]:
        """유동성 분석"""
        # 유동성 확보 확인
        liquidity_grabbed = False
        is_bullish = direction == 'long'

        for liq_level in self.liquidity_analyzer.liquidity_levels:
            if self.liquidity_analyzer.check_liquidity_grab(
                current_price, liq_level, is_bullish
            ):
                liquidity_grabbed = True
                break

        # 가장 가까운 유동성 레벨
        nearest_liquidity = self.liquidity_analyzer.get_nearest_liquidity(
            current_price
        )

        return liquidity_grabbed, nearest_liquidity

    def _analyze_bos(
        self,
        df: pd.DataFrame
    ) -> Tuple[bool, Optional[StructurePoint]]:
        """BOS 분석"""
        if len(df) == 0:
            return False, None

        bos_point = self.market_structure_analyzer.detect_break_of_structure(
            df, len(df) - 1
        )

        return bos_point is not None, bos_point

    def _analyze_fvg(
        self,
        current_price: float,
        direction: str
    ) -> Tuple[bool, Optional[FVG]]:
        """FVG 분석"""
        fvg_direction = 'bullish' if direction == 'long' else 'bearish'

        nearest_fvg = self.fvg_analyzer.get_nearest_fvg(
            current_price,
            direction=fvg_direction,
            only_unrebalanced=True
        )

        return nearest_fvg is not None, nearest_fvg

    def _analyze_discount_premium(
        self,
        df: pd.DataFrame,
        current_price: float,
        direction: str
    ) -> Tuple[str, float]:
        """디스카운트/프리미엄 분석"""
        lookback = 50
        if len(df) < lookback:
            return 'equilibrium', 0.5

        recent_high = df['high'].iloc[-lookback:].max()
        recent_low = df['low'].iloc[-lookback:].min()

        # 현재 가격의 범위 내 위치 (0-1)
        zone_percentage = (current_price - recent_low) / (recent_high - recent_low)

        # 구간 판단
        if zone_percentage < 0.4:
            price_zone = 'discount'  # 할인 구간 (매수 유리)
        elif zone_percentage > 0.6:
            price_zone = 'premium'  # 프리미엄 구간 (매도 유리)
        else:
            price_zone = 'equilibrium'  # 균형 구간

        return price_zone, zone_percentage

    def _calculate_trend_strength(
        self,
        df: pd.DataFrame,
        trend: TrendDirection,
        period: int = 20
    ) -> float:
        """추세 강도 계산"""
        if len(df) < period:
            return 0.5

        recent_data = df.iloc[-period:]

        if trend == TrendDirection.BULLISH:
            bullish_candles = sum(recent_data['close'] > recent_data['open'])
            return bullish_candles / period
        elif trend == TrendDirection.BEARISH:
            bearish_candles = sum(recent_data['close'] < recent_data['open'])
            return bearish_candles / period
        else:
            return 0.5

    def _calculate_total_score(
        self,
        liquidity_grabbed: bool,
        trend_strength: float,
        bos_detected: bool,
        fvg_present: bool,
        price_zone: str,
        htf_alignment: bool,
        smt_divergence: Optional[SMTDivergence],
        direction: str,
        htf_bias: Optional[str]
    ) -> float:
        """종합 점수 계산 (0-1)"""
        score = 0.0
        max_score = 7.0

        # 1. 유동성 확보 (가장 중요)
        if liquidity_grabbed:
            score += 1.5

        # 2. 시장 구조 및 추세 강도
        score += trend_strength

        # 3. BOS
        if bos_detected:
            score += 1.0

        # 4. FVG
        if fvg_present:
            score += 1.0

        # 5. 디스카운트/프리미엄
        if direction == 'long' and price_zone == 'discount':
            score += 1.0
        elif direction == 'short' and price_zone == 'premium':
            score += 1.0
        elif price_zone == 'equilibrium':
            score += 0.5

        # 6. 타임프레임 정렬
        if htf_alignment:
            score += 1.0

        # 7. SMT (옵션)
        if smt_divergence:
            if (direction == 'long' and smt_divergence.divergence_type == 'bullish') or \
               (direction == 'short' and smt_divergence.divergence_type == 'bearish'):
                score += 0.5

        return score / max_score

    def _determine_entry_signal(
        self,
        total_score: float,
        liquidity_grabbed: bool,
        htf_alignment: bool,
        price_zone: str,
        direction: str
    ) -> bool:
        """진입 신호 판단"""
        # 필수 조건
        if not liquidity_grabbed:
            return False

        if not htf_alignment:
            return False

        # 디스카운트/프리미엄 확인
        if direction == 'long' and price_zone == 'premium':
            return False
        if direction == 'short' and price_zone == 'discount':
            return False

        # 종합 점수 기준
        if total_score >= 0.7:  # 70% 이상
            return True

        return False
