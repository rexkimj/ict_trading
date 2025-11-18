"""
VWAP (Volume Weighted Average Price) 실행 전략

대규모 주문을 시장 충격 없이 효율적으로 처리합니다.
"""
import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class VWAPSlice:
    """VWAP 주문 슬라이스"""
    timestamp: datetime
    size: float
    target_price: float
    executed: bool = False
    actual_price: Optional[float] = None


class VWAPExecutor:
    """VWAP 실행 알고리즘"""

    def __init__(
        self,
        participation_rate: float = 0.1,  # 시장 거래량의 10% 참여
        min_slice_size: float = 0.01,
        max_slice_size: float = 0.2
    ):
        """
        Args:
            participation_rate: 시장 거래량 대비 참여율
            min_slice_size: 최소 슬라이스 크기 (전체 대비 비율)
            max_slice_size: 최대 슬라이스 크기 (전체 대비 비율)
        """
        self.participation_rate = participation_rate
        self.min_slice_size = min_slice_size
        self.max_slice_size = max_slice_size

    def calculate_vwap(
        self,
        df: pd.DataFrame,
        period: int = 20
    ) -> pd.Series:
        """
        VWAP 계산

        Args:
            df: OHLCV 데이터
            period: 계산 기간

        Returns:
            VWAP 시리즈
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(window=period).sum() / \
               df['volume'].rolling(window=period).sum()

        return vwap

    def split_order(
        self,
        total_size: float,
        df: pd.DataFrame,
        duration_minutes: int = 60
    ) -> List[VWAPSlice]:
        """
        주문을 VWAP 기반으로 분할

        Args:
            total_size: 총 주문 크기
            df: 과거 OHLCV 데이터 (거래량 패턴 분석용)
            duration_minutes: 실행 기간 (분)

        Returns:
            VWAP 슬라이스 리스트
        """
        slices = []

        # 과거 거래량 패턴 분석
        if len(df) >= 100:
            hourly_volume_profile = self._analyze_volume_profile(df)
        else:
            # 균등 분할
            hourly_volume_profile = [1.0] * (duration_minutes // 5)

        # 시간대별 분할
        total_weight = sum(hourly_volume_profile[:duration_minutes // 5])
        current_time = datetime.now()

        for i, weight in enumerate(hourly_volume_profile[:duration_minutes // 5]):
            # 슬라이스 크기 계산
            slice_ratio = (weight / total_weight)
            slice_ratio = max(self.min_slice_size, min(slice_ratio, self.max_slice_size))
            slice_size = total_size * slice_ratio

            # 실행 시간
            exec_time = current_time + timedelta(minutes=i * 5)

            # VWAP 기준 가격 (현재는 현재가 사용, 실제로는 예측 VWAP)
            target_price = df['close'].iloc[-1] if len(df) > 0 else 0

            slices.append(VWAPSlice(
                timestamp=exec_time,
                size=slice_size,
                target_price=target_price
            ))

        # 크기 정규화 (합이 total_size가 되도록)
        total_allocated = sum(s.size for s in slices)
        if total_allocated > 0:
            for slice in slices:
                slice.size = (slice.size / total_allocated) * total_size

        return slices

    def _analyze_volume_profile(
        self,
        df: pd.DataFrame,
        lookback: int = 100
    ) -> List[float]:
        """
        거래량 프로파일 분석

        Args:
            df: OHLCV 데이터
            lookback: 룩백 기간

        Returns:
            시간대별 거래량 가중치 리스트
        """
        recent_data = df.iloc[-lookback:]

        # 5분봉 기준 거래량 패턴 (간소화)
        if len(recent_data) == 0:
            return [1.0] * 12

        # 거래량의 이동평균 계산
        volume_ma = recent_data['volume'].rolling(window=5).mean()

        # 정규화
        max_volume = volume_ma.max()
        if max_volume > 0:
            profile = (volume_ma / max_volume).fillna(1.0).tolist()
        else:
            profile = [1.0] * len(volume_ma)

        return profile[-12:]  # 최근 12개 (1시간)

    def execute_slice(
        self,
        slice: VWAPSlice,
        current_price: float,
        current_volume: float
    ) -> tuple:
        """
        슬라이스 실행

        Args:
            slice: 실행할 슬라이스
            current_price: 현재 가격
            current_volume: 현재 거래량

        Returns:
            (실행 여부, 실제 체결 가격)
        """
        if slice.executed:
            return False, None

        # 시장 거래량 대비 슬라이스 크기 확인
        max_executable = current_volume * self.participation_rate

        if slice.size <= max_executable:
            # 실행 가능
            slice.executed = True
            slice.actual_price = current_price
            return True, current_price
        else:
            # 일부만 실행 (간소화)
            return False, None

    def get_execution_quality(
        self,
        slices: List[VWAPSlice],
        benchmark_vwap: float
    ) -> dict:
        """
        실행 품질 평가

        Args:
            slices: 실행된 슬라이스 리스트
            benchmark_vwap: 벤치마크 VWAP

        Returns:
            실행 품질 지표
        """
        executed_slices = [s for s in slices if s.executed and s.actual_price is not None]

        if not executed_slices:
            return {
                'execution_rate': 0.0,
                'avg_price': 0.0,
                'vwap_deviation': 0.0,
                'total_executed': 0.0
            }

        total_size = sum(s.size for s in slices)
        executed_size = sum(s.size for s in executed_slices)

        # 가중평균 실행 가격
        avg_price = sum(s.actual_price * s.size for s in executed_slices) / executed_size

        # VWAP 대비 편차
        vwap_deviation = (avg_price - benchmark_vwap) / benchmark_vwap if benchmark_vwap > 0 else 0

        return {
            'execution_rate': executed_size / total_size if total_size > 0 else 0,
            'avg_price': avg_price,
            'vwap_deviation': vwap_deviation,
            'vwap_deviation_bps': vwap_deviation * 10000,  # basis points
            'total_executed': executed_size,
            'slices_executed': len(executed_slices),
            'slices_total': len(slices)
        }
