"""
슬리피지 관리 모듈

슬리피지를 최소화하고 실행 비용을 관리합니다.
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionResult:
    """실행 결과"""
    timestamp: datetime
    intended_price: float
    actual_price: float
    size: float
    slippage: float
    slippage_bps: float
    commission: float
    total_cost: float


class SlippageManager:
    """슬리피지 관리 클래스"""

    def __init__(
        self,
        max_slippage_bps: float = 20.0,  # 20 bps = 0.2%
        commission_rate: float = 0.001,  # 0.1%
        liquidity_threshold: float = 0.1  # 거래량의 10% 이하로 제한
    ):
        """
        Args:
            max_slippage_bps: 최대 허용 슬리피지 (basis points)
            commission_rate: 수수료율
            liquidity_threshold: 유동성 임계값
        """
        self.max_slippage_bps = max_slippage_bps
        self.commission_rate = commission_rate
        self.liquidity_threshold = liquidity_threshold

        self.execution_history = []

    def estimate_slippage(
        self,
        intended_price: float,
        size: float,
        current_volume: float,
        volatility: float,
        order_type: str = 'market'
    ) -> float:
        """
        슬리피지 추정

        Args:
            intended_price: 의도한 가격
            size: 주문 크기
            current_volume: 현재 거래량
            volatility: 변동성 (ATR 등)
            order_type: 주문 타입 ('market' or 'limit')

        Returns:
            추정 슬리피지 (bps)
        """
        if order_type == 'limit':
            # 리밋 오더는 슬리피지 없음 (미체결 리스크는 있음)
            return 0.0

        # 시장 충격 추정
        size_ratio = size / current_volume if current_volume > 0 else 1.0
        market_impact = size_ratio * 100  # 간소화된 모델

        # 변동성 기반 슬리피지
        volatility_impact = (volatility / intended_price) * 10000 if intended_price > 0 else 0

        # 총 슬리피지 추정 (bps)
        estimated_slippage = market_impact + volatility_impact

        return estimated_slippage

    def check_slippage_acceptable(
        self,
        estimated_slippage_bps: float
    ) -> Tuple[bool, str]:
        """
        슬리피지 허용 여부 확인

        Args:
            estimated_slippage_bps: 추정 슬리피지 (bps)

        Returns:
            (허용 여부, 이유)
        """
        if estimated_slippage_bps <= self.max_slippage_bps:
            return True, "슬리피지 허용 범위 내"

        return False, f"슬리피지 {estimated_slippage_bps:.2f} bps가 최대 허용치 {self.max_slippage_bps} bps 초과"

    def check_liquidity_sufficient(
        self,
        size: float,
        current_volume: float
    ) -> Tuple[bool, str]:
        """
        유동성 충분 여부 확인

        Args:
            size: 주문 크기
            current_volume: 현재 거래량

        Returns:
            (충분 여부, 이유)
        """
        if current_volume == 0:
            return False, "거래량 0"

        size_ratio = size / current_volume

        if size_ratio <= self.liquidity_threshold:
            return True, f"주문 크기가 거래량의 {size_ratio*100:.2f}%"

        return False, f"주문 크기가 거래량의 {size_ratio*100:.2f}%로 임계값 {self.liquidity_threshold*100}% 초과"

    def execute_with_slippage(
        self,
        intended_price: float,
        size: float,
        direction: str,
        current_price: float,
        slippage_bps: Optional[float] = None
    ) -> ExecutionResult:
        """
        슬리피지를 고려한 실행

        Args:
            intended_price: 의도한 가격
            size: 주문 크기
            direction: 방향 ('long' or 'short')
            current_price: 현재 시장 가격
            slippage_bps: 실제 슬리피지 (None이면 추정치 사용)

        Returns:
            실행 결과
        """
        # 슬리피지 적용
        if slippage_bps is None:
            slippage_bps = 10.0  # 기본 슬리피지

        slippage_amount = intended_price * (slippage_bps / 10000)

        if direction == 'long':
            # 롱: 가격이 올라가면 불리
            actual_price = intended_price + slippage_amount
        else:  # short
            # 숏: 가격이 내려가면 불리
            actual_price = intended_price - slippage_amount

        # 수수료 계산
        commission = size * actual_price * self.commission_rate

        # 슬리피지 비용
        slippage_cost = abs(actual_price - intended_price) * size

        # 총 비용
        total_cost = slippage_cost + commission

        result = ExecutionResult(
            timestamp=datetime.now(),
            intended_price=intended_price,
            actual_price=actual_price,
            size=size,
            slippage=slippage_amount,
            slippage_bps=slippage_bps,
            commission=commission,
            total_cost=total_cost
        )

        self.execution_history.append(result)
        return result

    def get_average_slippage(self, recent_n: Optional[int] = None) -> float:
        """
        평균 슬리피지 조회

        Args:
            recent_n: 최근 n개 거래 (None이면 전체)

        Returns:
            평균 슬리피지 (bps)
        """
        if not self.execution_history:
            return 0.0

        history = self.execution_history[-recent_n:] if recent_n else self.execution_history

        avg_slippage = sum(r.slippage_bps for r in history) / len(history)
        return avg_slippage

    def get_total_costs(self) -> dict:
        """
        총 거래 비용 통계

        Returns:
            비용 통계 딕셔너리
        """
        if not self.execution_history:
            return {
                'total_slippage_cost': 0.0,
                'total_commission': 0.0,
                'total_cost': 0.0,
                'avg_slippage_bps': 0.0,
                'executions': 0
            }

        total_slippage_cost = sum(abs(r.slippage) * r.size for r in self.execution_history)
        total_commission = sum(r.commission for r in self.execution_history)
        total_cost = sum(r.total_cost for r in self.execution_history)
        avg_slippage = self.get_average_slippage()

        return {
            'total_slippage_cost': total_slippage_cost,
            'total_commission': total_commission,
            'total_cost': total_cost,
            'avg_slippage_bps': avg_slippage,
            'executions': len(self.execution_history)
        }

    def optimize_order_size(
        self,
        intended_size: float,
        current_volume: float,
        max_impact_bps: float = 50.0
    ) -> float:
        """
        시장 충격을 고려한 최적 주문 크기

        Args:
            intended_size: 의도한 주문 크기
            current_volume: 현재 거래량
            max_impact_bps: 최대 허용 시장 충격 (bps)

        Returns:
            최적화된 주문 크기
        """
        if current_volume == 0:
            return 0.0

        # 최대 허용 크기 (유동성 임계값 기준)
        max_size = current_volume * self.liquidity_threshold

        # 시장 충격 기준 최대 크기
        max_impact_size = (max_impact_bps / 100) * current_volume

        # 최소값 선택
        optimal_size = min(intended_size, max_size, max_impact_size)

        return optimal_size
