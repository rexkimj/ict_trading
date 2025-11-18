"""
데이터 처리 유틸리티
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple


class DataHandler:
    """시장 데이터 처리 클래스"""

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> bool:
        """
        OHLCV 데이터 유효성 검증

        Args:
            df: OHLCV 데이터프레임

        Returns:
            유효성 여부
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_columns)

    @staticmethod
    def resample_timeframe(
        df: pd.DataFrame,
        timeframe: str
    ) -> pd.DataFrame:
        """
        타임프레임 리샘플링

        Args:
            df: 원본 OHLCV 데이터
            timeframe: 목표 타임프레임 (예: '1H', '4H', '1D')

        Returns:
            리샘플링된 데이터
        """
        if not DataHandler.validate_ohlcv(df):
            raise ValueError("Invalid OHLCV data")

        # 인덱스가 datetime이 아니면 변환
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # 리샘플링
        resampled = df.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        return resampled.dropna()

    @staticmethod
    def calculate_pivot_points(
        df: pd.DataFrame,
        lookback: int = 5
    ) -> Tuple[pd.Series, pd.Series]:
        """
        피벗 고점/저점 계산

        Args:
            df: OHLCV 데이터
            lookback: 룩백 기간

        Returns:
            (피벗 고점, 피벗 저점) 시리즈
        """
        pivot_highs = pd.Series(index=df.index, dtype=float)
        pivot_lows = pd.Series(index=df.index, dtype=float)

        for i in range(lookback, len(df) - lookback):
            # 피벗 고점: 양쪽 lookback 기간보다 높은 고점
            window_highs = df['high'].iloc[i-lookback:i+lookback+1]
            if df['high'].iloc[i] == window_highs.max():
                pivot_highs.iloc[i] = df['high'].iloc[i]

            # 피벗 저점: 양쪽 lookback 기간보다 낮은 저점
            window_lows = df['low'].iloc[i-lookback:i+lookback+1]
            if df['low'].iloc[i] == window_lows.min():
                pivot_lows.iloc[i] = df['low'].iloc[i]

        return pivot_highs, pivot_lows

    @staticmethod
    def calculate_atr(
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.Series:
        """
        ATR (Average True Range) 계산

        Args:
            df: OHLCV 데이터
            period: 계산 기간

        Returns:
            ATR 시리즈
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range 계산
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR = TR의 이동평균
        atr = tr.rolling(window=period).mean()

        return atr
