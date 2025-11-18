"""
다중 타임프레임 분석 모듈

HTF(Higher TimeFrame) → LTF(Lower TimeFrame) 분석을 지원합니다.
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..core.market_structure import MarketStructureAnalyzer, TrendDirection
from ..core.poi import POIManager, POI
from ..utils.data_handler import DataHandler


@dataclass
class TimeframeAnalysis:
    """타임프레임 분석 결과"""
    timeframe: str
    trend: TrendDirection
    key_pois: List[POI]
    support_level: float
    resistance_level: float
    strength: float  # 추세 강도 (0-1)


class MultiTimeframeAnalyzer:
    """다중 타임프레임 분석 클래스"""

    def __init__(
        self,
        higher_timeframe: str = "4H",
        entry_timeframe: str = "15M",
        confirmation_timeframe: str = "5M"
    ):
        """
        Args:
            higher_timeframe: 상위 타임프레임 (추세 확인용)
            entry_timeframe: 진입 타임프레임
            confirmation_timeframe: 진입 확인 타임프레임
        """
        self.higher_timeframe = higher_timeframe
        self.entry_timeframe = entry_timeframe
        self.confirmation_timeframe = confirmation_timeframe

        self.htf_analysis: Optional[TimeframeAnalysis] = None
        self.etf_analysis: Optional[TimeframeAnalysis] = None
        self.ctf_analysis: Optional[TimeframeAnalysis] = None

    def analyze_timeframe(
        self,
        df: pd.DataFrame,
        timeframe: str,
        poi_manager: POIManager
    ) -> TimeframeAnalysis:
        """
        단일 타임프레임 분석

        Args:
            df: OHLCV 데이터
            timeframe: 타임프레임
            poi_manager: POI 매니저

        Returns:
            타임프레임 분석 결과
        """
        # 데이터 리샘플링
        resampled_df = DataHandler.resample_timeframe(df, timeframe)

        # 시장 구조 분석
        ms_analyzer = MarketStructureAnalyzer()
        ms_analyzer.identify_structure(resampled_df)
        trend = ms_analyzer.determine_trend()

        # POI 업데이트
        poi_manager.update_all_pois(resampled_df)

        # 추세 방향에 따른 POI 선택
        if trend == TrendDirection.BULLISH:
            key_pois = poi_manager.get_pois_by_direction('bullish', only_inactive=True)
        elif trend == TrendDirection.BEARISH:
            key_pois = poi_manager.get_pois_by_direction('bearish', only_inactive=True)
        else:
            key_pois = poi_manager.get_strongest_pois(top_n=5, only_inactive=True)

        # 지지/저항 레벨
        lookback = 50
        if len(resampled_df) >= lookback:
            support_level = resampled_df['low'].iloc[-lookback:].min()
            resistance_level = resampled_df['high'].iloc[-lookback:].max()
        else:
            support_level = resampled_df['low'].min()
            resistance_level = resampled_df['high'].max()

        # 추세 강도 계산
        strength = self._calculate_trend_strength(resampled_df, trend)

        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            key_pois=key_pois[:5],  # 상위 5개만
            support_level=support_level,
            resistance_level=resistance_level,
            strength=strength
        )

    def _calculate_trend_strength(
        self,
        df: pd.DataFrame,
        trend: TrendDirection,
        period: int = 20
    ) -> float:
        """
        추세 강도 계산

        Args:
            df: OHLCV 데이터
            trend: 추세 방향
            period: 계산 기간

        Returns:
            추세 강도 (0-1)
        """
        if len(df) < period:
            return 0.5

        recent_data = df.iloc[-period:]

        if trend == TrendDirection.BULLISH:
            # 강세: 상승 캔들 비율
            bullish_candles = sum(recent_data['close'] > recent_data['open'])
            strength = bullish_candles / period

        elif trend == TrendDirection.BEARISH:
            # 약세: 하락 캔들 비율
            bearish_candles = sum(recent_data['close'] < recent_data['open'])
            strength = bearish_candles / period

        else:
            # 횡보
            strength = 0.5

        return strength

    def analyze_all_timeframes(
        self,
        df: pd.DataFrame,
        poi_managers: Dict[str, POIManager]
    ) -> Tuple[TimeframeAnalysis, TimeframeAnalysis, TimeframeAnalysis]:
        """
        모든 타임프레임 분석

        Args:
            df: 원본 OHLCV 데이터
            poi_managers: 각 타임프레임별 POI 매니저

        Returns:
            (HTF 분석, ETF 분석, CTF 분석)
        """
        # HTF 분석
        self.htf_analysis = self.analyze_timeframe(
            df,
            self.higher_timeframe,
            poi_managers['htf']
        )

        # ETF 분석
        self.etf_analysis = self.analyze_timeframe(
            df,
            self.entry_timeframe,
            poi_managers['etf']
        )

        # CTF 분석
        self.ctf_analysis = self.analyze_timeframe(
            df,
            self.confirmation_timeframe,
            poi_managers['ctf']
        )

        return self.htf_analysis, self.etf_analysis, self.ctf_analysis

    def check_trend_alignment(self) -> bool:
        """
        타임프레임 간 추세 정렬 확인

        Returns:
            추세 정렬 여부
        """
        if not all([self.htf_analysis, self.etf_analysis, self.ctf_analysis]):
            return False

        # HTF와 ETF의 추세가 일치하는지 확인
        htf_trend = self.htf_analysis.trend
        etf_trend = self.etf_analysis.trend

        # 횡보는 제외하고 추세 방향이 같은지 확인
        if htf_trend == TrendDirection.RANGING or etf_trend == TrendDirection.RANGING:
            return False

        return htf_trend == etf_trend

    def get_htf_bias(self) -> Optional[str]:
        """
        HTF 바이어스(편향) 반환

        Returns:
            'bullish', 'bearish', 또는 None
        """
        if not self.htf_analysis:
            return None

        if self.htf_analysis.trend == TrendDirection.BULLISH:
            return 'bullish'
        elif self.htf_analysis.trend == TrendDirection.BEARISH:
            return 'bearish'

        return None

    def should_enter(
        self,
        current_price: float,
        direction: str
    ) -> Tuple[bool, str]:
        """
        진입 가능 여부 판단

        Args:
            current_price: 현재 가격
            direction: 진입 방향 ('long' or 'short')

        Returns:
            (진입 가능 여부, 이유)
        """
        if not all([self.htf_analysis, self.etf_analysis, self.ctf_analysis]):
            return False, "타임프레임 분석 미완료"

        # 1. HTF 추세 확인
        htf_bias = self.get_htf_bias()
        if not htf_bias:
            return False, "HTF 추세가 불명확함"

        # 2. 진입 방향과 HTF 추세 일치 확인
        if direction == 'long' and htf_bias != 'bullish':
            return False, f"HTF 추세({htf_bias})와 진입 방향(long) 불일치"
        if direction == 'short' and htf_bias != 'bearish':
            return False, f"HTF 추세({htf_bias})와 진입 방향(short) 불일치"

        # 3. 타임프레임 간 추세 정렬 확인
        if not self.check_trend_alignment():
            return False, "타임프레임 간 추세 불일치"

        # 4. ETF에서 POI 근처 확인
        if not self.etf_analysis.key_pois:
            return False, "ETF에 유효한 POI 없음"

        nearest_poi = min(
            self.etf_analysis.key_pois,
            key=lambda poi: abs((poi.price_top + poi.price_bottom) / 2 - current_price)
        )

        poi_center = (nearest_poi.price_top + nearest_poi.price_bottom) / 2
        distance_pct = abs(poi_center - current_price) / current_price

        if distance_pct > 0.01:  # 1% 이상 떨어져 있으면
            return False, f"가장 가까운 POI가 {distance_pct*100:.2f}% 떨어져 있음"

        # 5. CTF에서 확인 신호
        if self.ctf_analysis.trend != self.htf_analysis.trend:
            return False, "CTF에서 진입 확인 안 됨"

        return True, "모든 조건 충족"
