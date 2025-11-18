"""
진입 전략 모듈

ICT 트레이딩의 올바른 진입 원칙을 구현합니다.
"""
import pandas as pd
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime

from ..analysis.seven_factors import SevenFactorAnalyzer, SevenFactorAnalysis
from ..analysis.timeframe import MultiTimeframeAnalyzer
from ..core.poi import POIManager, POI
from ..core.liquidity import LiquidityAnalyzer


@dataclass
class EntrySignal:
    """진입 신호"""
    timestamp: datetime
    direction: str  # 'long' or 'short'
    entry_price: float
    confidence: float  # 0-1
    poi: Optional[POI]
    reason: str
    seven_factor_analysis: SevenFactorAnalysis


class EntryStrategy:
    """진입 전략 클래스"""

    def __init__(
        self,
        seven_factor_analyzer: SevenFactorAnalyzer,
        mtf_analyzer: MultiTimeframeAnalyzer,
        poi_manager: POIManager,
        min_confidence: float = 0.7
    ):
        """
        Args:
            seven_factor_analyzer: 7가지 요소 분석기
            mtf_analyzer: 다중 타임프레임 분석기
            poi_manager: POI 매니저
            min_confidence: 최소 신뢰도
        """
        self.seven_factor_analyzer = seven_factor_analyzer
        self.mtf_analyzer = mtf_analyzer
        self.poi_manager = poi_manager
        self.min_confidence = min_confidence

    def check_entry(
        self,
        df: pd.DataFrame,
        current_price: float,
        correlated_df: Optional[pd.DataFrame] = None
    ) -> Optional[EntrySignal]:
        """
        진입 기회 확인

        Args:
            df: OHLCV 데이터
            current_price: 현재 가격
            correlated_df: 상관 자산 데이터 (SMT 분석용, 옵션)

        Returns:
            진입 신호 (없으면 None)
        """
        # HTF 바이어스 확인
        htf_bias = self.mtf_analyzer.get_htf_bias()
        if not htf_bias:
            return None

        # 진입 방향 결정
        direction = 'long' if htf_bias == 'bullish' else 'short'

        # 7가지 요소 종합 분석
        analysis = self.seven_factor_analyzer.analyze(
            df=df,
            current_price=current_price,
            direction=direction,
            correlated_df=correlated_df
        )

        # 진입 신호 확인
        if not analysis.entry_signal:
            return None

        # 신뢰도 확인
        if analysis.total_score < self.min_confidence:
            return None

        # 가장 가까운 POI 찾기
        nearest_poi = self.poi_manager.get_nearest_poi(
            current_price=current_price,
            direction=htf_bias,
            only_inactive=False
        )

        # 진입 사유 생성
        reason = self._generate_entry_reason(analysis, direction)

        return EntrySignal(
            timestamp=datetime.now(),
            direction=direction,
            entry_price=current_price,
            confidence=analysis.total_score,
            poi=nearest_poi,
            reason=reason,
            seven_factor_analysis=analysis
        )

    def validate_entry_confirmation(
        self,
        df: pd.DataFrame,
        entry_signal: EntrySignal,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        진입 확인 검증 (LTF에서 확인)

        Args:
            df: LTF OHLCV 데이터
            entry_signal: 진입 신호
            current_price: 현재 가격

        Returns:
            (확인 여부, 이유)
        """
        # POI 근처 확인
        if entry_signal.poi:
            poi_center = (entry_signal.poi.price_top + entry_signal.poi.price_bottom) / 2
            distance_pct = abs(poi_center - current_price) / current_price

            if distance_pct > 0.005:  # 0.5% 이상 떨어짐
                return False, f"POI에서 {distance_pct*100:.2f}% 떨어져 있음"

        # 최근 캔들 확인
        if len(df) < 3:
            return False, "데이터 부족"

        recent_candles = df.iloc[-3:]

        if entry_signal.direction == 'long':
            # 롱 진입: 최근 캔들이 상승 반전 확인
            last_candle_bullish = recent_candles['close'].iloc[-1] > recent_candles['open'].iloc[-1]
            if not last_candle_bullish:
                return False, "상승 반전 캔들 미확인"

        else:  # short
            # 숏 진입: 최근 캔들이 하락 반전 확인
            last_candle_bearish = recent_candles['close'].iloc[-1] < recent_candles['open'].iloc[-1]
            if not last_candle_bearish:
                return False, "하락 반전 캔들 미확인"

        return True, "진입 확인 완료"

    def _generate_entry_reason(
        self,
        analysis: SevenFactorAnalysis,
        direction: str
    ) -> str:
        """진입 사유 생성"""
        reasons = []

        if analysis.liquidity_grabbed:
            reasons.append("유동성 확보 완료")

        if analysis.htf_alignment:
            reasons.append("타임프레임 정렬")

        if analysis.fvg_present:
            reasons.append("FVG 존재")

        if analysis.bos_detected:
            reasons.append("BOS 탐지")

        if direction == 'long' and analysis.price_zone == 'discount':
            reasons.append("할인 구간 진입")
        elif direction == 'short' and analysis.price_zone == 'premium':
            reasons.append("프리미엄 구간 진입")

        if analysis.smt_divergence:
            reasons.append("SMT 다이버전스")

        return ", ".join(reasons) if reasons else "종합 분석 통과"

    def should_wait_for_pullback(
        self,
        df: pd.DataFrame,
        current_price: float,
        direction: str
    ) -> Tuple[bool, Optional[float]]:
        """
        되돌림 대기 여부 및 목표 가격

        Args:
            df: OHLCV 데이터
            current_price: 현재 가격
            direction: 진입 방향

        Returns:
            (대기 여부, 목표 가격)
        """
        # 가장 가까운 POI 찾기
        nearest_poi = self.poi_manager.get_nearest_poi(
            current_price=current_price,
            direction='bullish' if direction == 'long' else 'bearish',
            only_inactive=True
        )

        if not nearest_poi:
            return False, None

        poi_center = (nearest_poi.price_top + nearest_poi.price_bottom) / 2

        # 현재 가격과 POI 간 거리
        distance_pct = abs(poi_center - current_price) / current_price

        # 1% 이상 떨어져 있으면 되돌림 대기
        if distance_pct > 0.01:
            return True, poi_center

        return False, None
