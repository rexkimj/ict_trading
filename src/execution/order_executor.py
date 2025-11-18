"""
주문 실행 모듈

통합 주문 실행 및 관리 시스템
"""
import pandas as pd
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from .vwap import VWAPExecutor, VWAPSlice
from .slippage import SlippageManager, ExecutionResult


@dataclass
class Order:
    """주문 정보"""
    order_id: str
    timestamp: datetime
    direction: str  # 'long' or 'short'
    size: float
    order_type: str  # 'market', 'limit', 'vwap'
    intended_price: float
    status: str = 'pending'  # 'pending', 'executing', 'completed', 'failed'
    executed_size: float = 0.0
    avg_execution_price: float = 0.0
    vwap_slices: Optional[List[VWAPSlice]] = None


class OrderExecutor:
    """주문 실행 클래스"""

    def __init__(
        self,
        vwap_executor: VWAPExecutor,
        slippage_manager: SlippageManager
    ):
        """
        Args:
            vwap_executor: VWAP 실행기
            slippage_manager: 슬리피지 관리자
        """
        self.vwap_executor = vwap_executor
        self.slippage_manager = slippage_manager

        self.orders: List[Order] = []
        self.order_counter = 0

    def create_order(
        self,
        direction: str,
        size: float,
        intended_price: float,
        order_type: str = 'market'
    ) -> Order:
        """
        주문 생성

        Args:
            direction: 방향 ('long' or 'short')
            size: 주문 크기
            intended_price: 의도한 가격
            order_type: 주문 타입

        Returns:
            생성된 주문
        """
        self.order_counter += 1
        order_id = f"ORD_{self.order_counter:06d}"

        order = Order(
            order_id=order_id,
            timestamp=datetime.now(),
            direction=direction,
            size=size,
            order_type=order_type,
            intended_price=intended_price
        )

        self.orders.append(order)
        return order

    def execute_market_order(
        self,
        order: Order,
        current_price: float,
        current_volume: float,
        volatility: float
    ) -> ExecutionResult:
        """
        시장가 주문 실행

        Args:
            order: 실행할 주문
            current_price: 현재 가격
            current_volume: 현재 거래량
            volatility: 변동성

        Returns:
            실행 결과
        """
        # 유동성 확인
        sufficient, reason = self.slippage_manager.check_liquidity_sufficient(
            order.size, current_volume
        )

        if not sufficient:
            order.status = 'failed'
            raise ValueError(f"유동성 부족: {reason}")

        # 슬리피지 추정
        estimated_slippage = self.slippage_manager.estimate_slippage(
            intended_price=order.intended_price,
            size=order.size,
            current_volume=current_volume,
            volatility=volatility,
            order_type='market'
        )

        # 슬리피지 허용 여부 확인
        acceptable, reason = self.slippage_manager.check_slippage_acceptable(
            estimated_slippage
        )

        if not acceptable:
            order.status = 'failed'
            raise ValueError(f"슬리피지 초과: {reason}")

        # 실행
        order.status = 'executing'
        result = self.slippage_manager.execute_with_slippage(
            intended_price=order.intended_price,
            size=order.size,
            direction=order.direction,
            current_price=current_price,
            slippage_bps=estimated_slippage
        )

        # 주문 업데이트
        order.executed_size = result.size
        order.avg_execution_price = result.actual_price
        order.status = 'completed'

        return result

    def execute_vwap_order(
        self,
        order: Order,
        df: pd.DataFrame,
        duration_minutes: int = 60
    ) -> List[VWAPSlice]:
        """
        VWAP 주문 실행 (분할 주문)

        Args:
            order: 실행할 주문
            df: OHLCV 데이터
            duration_minutes: 실행 기간

        Returns:
            VWAP 슬라이스 리스트
        """
        order.status = 'executing'

        # 주문 분할
        slices = self.vwap_executor.split_order(
            total_size=order.size,
            df=df,
            duration_minutes=duration_minutes
        )

        order.vwap_slices = slices
        return slices

    def execute_vwap_slice(
        self,
        order: Order,
        slice_idx: int,
        current_price: float,
        current_volume: float
    ) -> bool:
        """
        VWAP 슬라이스 실행

        Args:
            order: 주문
            slice_idx: 슬라이스 인덱스
            current_price: 현재 가격
            current_volume: 현재 거래량

        Returns:
            실행 성공 여부
        """
        if not order.vwap_slices or slice_idx >= len(order.vwap_slices):
            return False

        slice = order.vwap_slices[slice_idx]

        # 슬라이스 실행
        success, actual_price = self.vwap_executor.execute_slice(
            slice=slice,
            current_price=current_price,
            current_volume=current_volume
        )

        if success:
            # 실행 기록
            result = self.slippage_manager.execute_with_slippage(
                intended_price=slice.target_price,
                size=slice.size,
                direction=order.direction,
                current_price=actual_price,
                slippage_bps=5.0  # VWAP는 슬리피지가 적음
            )

            # 주문 업데이트
            order.executed_size += slice.size

            # 가중평균 실행 가격 업데이트
            if order.avg_execution_price == 0.0:
                order.avg_execution_price = actual_price
            else:
                total_value = (order.avg_execution_price * (order.executed_size - slice.size) +
                              actual_price * slice.size)
                order.avg_execution_price = total_value / order.executed_size

            # 모든 슬라이스 실행 완료 확인
            if all(s.executed for s in order.vwap_slices):
                order.status = 'completed'

        return success

    def cancel_order(self, order: Order) -> bool:
        """
        주문 취소

        Args:
            order: 취소할 주문

        Returns:
            취소 성공 여부
        """
        if order.status in ['completed', 'failed']:
            return False

        order.status = 'cancelled'
        return True

    def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        주문 상태 조회

        Args:
            order_id: 주문 ID

        Returns:
            주문 정보 (없으면 None)
        """
        for order in self.orders:
            if order.order_id == order_id:
                return order

        return None

    def get_pending_orders(self) -> List[Order]:
        """대기 중인 주문 조회"""
        return [o for o in self.orders if o.status == 'pending']

    def get_executing_orders(self) -> List[Order]:
        """실행 중인 주문 조회"""
        return [o for o in self.orders if o.status == 'executing']
