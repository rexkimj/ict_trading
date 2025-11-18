"""
SMT (Smart Money Technique) 모듈

스마트 머니 다이버전스를 탐지합니다.
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class SMTDivergence:
    """SMT 다이버전스 데이터 클래스"""
    timestamp: pd.Timestamp
    divergence_type: str  # 'bullish' or 'bearish'
    asset1_price: float
    asset2_price: float
    strength: float


class SMTAnalyzer:
    """SMT 분석 클래스"""

    def __init__(self, correlation_threshold: float = 0.7):
        """
        Args:
            correlation_threshold: 상관관계 임계값
        """
        self.correlation_threshold = correlation_threshold

    def detect_smt_divergence(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        lookback: int = 20
    ) -> Optional[SMTDivergence]:
        """
        두 상관 자산 간 SMT 다이버전스 탐지

        예: ES와 NQ, 또는 BTC와 ETH 등

        Args:
            df1: 자산1의 OHLCV 데이터
            df2: 자산2의 OHLCV 데이터
            lookback: 룩백 기간

        Returns:
            SMT 다이버전스 (없으면 None)
        """
        if len(df1) < lookback or len(df2) < lookback:
            return None

        # 최근 고점/저점
        asset1_high = df1['high'].iloc[-lookback:].max()
        asset1_low = df1['low'].iloc[-lookback:].min()
        asset2_high = df2['high'].iloc[-lookback:].max()
        asset2_low = df2['low'].iloc[-lookback:].min()

        # 이전 기간 고점/저점
        prev_asset1_high = df1['high'].iloc[-lookback*2:-lookback].max()
        prev_asset1_low = df1['low'].iloc[-lookback*2:-lookback].min()
        prev_asset2_high = df2['high'].iloc[-lookback*2:-lookback].max()
        prev_asset2_low = df2['low'].iloc[-lookback*2:-lookback].min()

        # Bearish SMT: 자산1은 신고점, 자산2는 고점 미달
        if asset1_high > prev_asset1_high and asset2_high < prev_asset2_high:
            strength = abs(
                (asset1_high - prev_asset1_high) / prev_asset1_high -
                (asset2_high - prev_asset2_high) / prev_asset2_high
            )
            return SMTDivergence(
                timestamp=df1.index[-1],
                divergence_type='bearish',
                asset1_price=asset1_high,
                asset2_price=asset2_high,
                strength=min(1.0, strength * 10)
            )

        # Bullish SMT: 자산1은 신저점, 자산2는 저점 미달
        if asset1_low < prev_asset1_low and asset2_low > prev_asset2_low:
            strength = abs(
                (prev_asset1_low - asset1_low) / asset1_low -
                (prev_asset2_low - asset2_low) / asset2_low
            )
            return SMTDivergence(
                timestamp=df1.index[-1],
                divergence_type='bullish',
                asset1_price=asset1_low,
                asset2_price=asset2_low,
                strength=min(1.0, strength * 10)
            )

        return None

    def calculate_correlation(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        period: int = 50
    ) -> float:
        """
        두 자산 간 상관관계 계산

        Args:
            df1: 자산1의 OHLCV 데이터
            df2: 자산2의 OHLCV 데이터
            period: 계산 기간

        Returns:
            상관계수 (-1 ~ 1)
        """
        if len(df1) < period or len(df2) < period:
            return 0.0

        # 수익률 계산
        returns1 = df1['close'].pct_change().iloc[-period:]
        returns2 = df2['close'].pct_change().iloc[-period:]

        # 상관계수
        correlation = returns1.corr(returns2)

        return correlation if not np.isnan(correlation) else 0.0
