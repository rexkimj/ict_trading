"""
리스크 관리 모듈

자본 보호를 위한 리스크 관리 시스템을 구현합니다.
"""
import pandas as pd
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """포지션 정보"""
    entry_time: datetime
    direction: str  # 'long' or 'short'
    entry_price: float
    size: float
    stop_loss: float
    take_profit_levels: List[tuple]
    risk_amount: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    is_open: bool = True


@dataclass
class RiskMetrics:
    """리스크 지표"""
    total_capital: float
    available_capital: float
    total_risk: float
    risk_percentage: float
    max_positions: int
    current_positions: int
    max_risk_per_trade: float
    is_within_limit: bool


class RiskManager:
    """리스크 관리 클래스"""

    def __init__(
        self,
        initial_capital: float,
        max_risk_per_trade: float = 0.02,  # 2%
        min_risk_per_trade: float = 0.01,  # 1%
        max_open_positions: int = 3,
        max_total_risk: float = 0.06  # 6%
    ):
        """
        Args:
            initial_capital: 초기 자본
            max_risk_per_trade: 최대 거래당 리스크 비율
            min_risk_per_trade: 최소 거래당 리스크 비율
            max_open_positions: 최대 동시 포지션 수
            max_total_risk: 최대 총 리스크 비율
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.min_risk_per_trade = min_risk_per_trade
        self.max_open_positions = max_open_positions
        self.max_total_risk = max_total_risk

        self.positions: List[Position] = []
        self.trade_history: List[Dict] = []

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        risk_percentage: Optional[float] = None
    ) -> tuple:
        """
        포지션 사이즈 계산

        Args:
            entry_price: 진입 가격
            stop_loss: 손절가
            direction: 진입 방향
            risk_percentage: 리스크 비율 (None이면 기본값 사용)

        Returns:
            (포지션 사이즈, 리스크 금액)
        """
        # 리스크 비율 결정
        if risk_percentage is None:
            risk_percentage = self.max_risk_per_trade
        else:
            risk_percentage = max(
                self.min_risk_per_trade,
                min(risk_percentage, self.max_risk_per_trade)
            )

        # 리스크 금액
        risk_amount = self.current_capital * risk_percentage

        # 손절까지의 거리
        if direction == 'long':
            distance = abs(entry_price - stop_loss)
        else:  # short
            distance = abs(stop_loss - entry_price)

        if distance == 0:
            return 0, 0

        # 포지션 사이즈 = 리스크 금액 / 손절 거리
        position_size = risk_amount / distance

        return position_size, risk_amount

    def can_open_position(self) -> tuple:
        """
        포지션 오픈 가능 여부 확인

        Returns:
            (가능 여부, 이유)
        """
        # 동시 포지션 수 확인
        open_positions = [p for p in self.positions if p.is_open]
        if len(open_positions) >= self.max_open_positions:
            return False, f"최대 포지션 수({self.max_open_positions}) 도달"

        # 총 리스크 확인
        total_risk = sum(p.risk_amount for p in open_positions)
        risk_pct = total_risk / self.current_capital

        if risk_pct >= self.max_total_risk:
            return False, f"최대 총 리스크({self.max_total_risk*100}%) 초과"

        # 자본 확인
        if self.current_capital <= self.initial_capital * 0.5:
            return False, "자본이 초기 자본의 50% 이하로 감소"

        return True, "포지션 오픈 가능"

    def open_position(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        take_profit_levels: List[tuple],
        risk_percentage: Optional[float] = None
    ) -> Optional[Position]:
        """
        포지션 오픈

        Args:
            entry_price: 진입 가격
            stop_loss: 손절가
            direction: 진입 방향
            take_profit_levels: TP 레벨 리스트
            risk_percentage: 리스크 비율

        Returns:
            생성된 포지션 (실패 시 None)
        """
        # 오픈 가능 여부 확인
        can_open, reason = self.can_open_position()
        if not can_open:
            print(f"포지션 오픈 불가: {reason}")
            return None

        # 포지션 사이즈 계산
        position_size, risk_amount = self.calculate_position_size(
            entry_price, stop_loss, direction, risk_percentage
        )

        if position_size == 0:
            print("포지션 사이즈 계산 실패")
            return None

        # 포지션 생성
        position = Position(
            entry_time=datetime.now(),
            direction=direction,
            entry_price=entry_price,
            size=position_size,
            stop_loss=stop_loss,
            take_profit_levels=take_profit_levels,
            risk_amount=risk_amount,
            current_price=entry_price
        )

        self.positions.append(position)
        return position

    def update_position(
        self,
        position: Position,
        current_price: float
    ) -> None:
        """
        포지션 업데이트

        Args:
            position: 업데이트할 포지션
            current_price: 현재 가격
        """
        if not position.is_open:
            return

        position.current_price = current_price

        # 미실현 손익 계산
        if position.direction == 'long':
            position.unrealized_pnl = (current_price - position.entry_price) * position.size
        else:  # short
            position.unrealized_pnl = (position.entry_price - current_price) * position.size

    def close_position(
        self,
        position: Position,
        exit_price: float,
        reason: str
    ) -> float:
        """
        포지션 청산

        Args:
            position: 청산할 포지션
            exit_price: 청산 가격
            reason: 청산 이유

        Returns:
            실현 손익
        """
        if not position.is_open:
            return 0.0

        # 실현 손익 계산
        if position.direction == 'long':
            realized_pnl = (exit_price - position.entry_price) * position.size
        else:  # short
            realized_pnl = (position.entry_price - exit_price) * position.size

        # 자본 업데이트
        self.current_capital += realized_pnl

        # 포지션 종료
        position.is_open = False
        position.current_price = exit_price
        position.unrealized_pnl = 0.0

        # 거래 기록
        self.trade_history.append({
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'direction': position.direction,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'size': position.size,
            'pnl': realized_pnl,
            'pnl_pct': (realized_pnl / position.risk_amount) * 100,
            'reason': reason
        })

        return realized_pnl

    def get_risk_metrics(self) -> RiskMetrics:
        """
        현재 리스크 지표 조회

        Returns:
            리스크 지표
        """
        open_positions = [p for p in self.positions if p.is_open]
        total_risk = sum(p.risk_amount for p in open_positions)
        risk_percentage = (total_risk / self.current_capital) if self.current_capital > 0 else 0

        available_capital = self.current_capital - total_risk

        return RiskMetrics(
            total_capital=self.current_capital,
            available_capital=available_capital,
            total_risk=total_risk,
            risk_percentage=risk_percentage,
            max_positions=self.max_open_positions,
            current_positions=len(open_positions),
            max_risk_per_trade=self.max_risk_per_trade,
            is_within_limit=risk_percentage <= self.max_total_risk
        )

    def get_performance_stats(self) -> Dict:
        """
        성과 통계 조회

        Returns:
            성과 통계 딕셔너리
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0
            }

        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in self.trade_history)

        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # 최대 낙폭 계산
        capital_history = [self.initial_capital]
        running_capital = self.initial_capital

        for trade in self.trade_history:
            running_capital += trade['pnl']
            capital_history.append(running_capital)

        peak = capital_history[0]
        max_drawdown = 0

        for capital in capital_history:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_pnl_pct': (total_pnl / self.initial_capital) * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100
        }

    def check_kill_switch(self) -> tuple:
        """
        Kill Switch 확인 - 비정상 상황 감지

        Returns:
            (중단 필요 여부, 이유)
        """
        # 일일 손실 한도 확인
        daily_loss_limit = self.initial_capital * 0.05  # 5%
        daily_pnl = sum(
            t['pnl'] for t in self.trade_history
            if (datetime.now() - t['exit_time']).days == 0
        ) if self.trade_history else 0

        if daily_pnl < -daily_loss_limit:
            return True, f"일일 손실 한도({daily_loss_limit}) 초과"

        # 연속 손실 확인
        if len(self.trade_history) >= 5:
            recent_trades = self.trade_history[-5:]
            if all(t['pnl'] < 0 for t in recent_trades):
                return True, "연속 5회 손실"

        # 자본 감소 확인
        if self.current_capital < self.initial_capital * 0.5:
            return True, "자본이 초기 자본의 50% 이하로 감소"

        # 총 리스크 한도 초과
        metrics = self.get_risk_metrics()
        if metrics.risk_percentage > self.max_total_risk * 1.5:
            return True, f"총 리스크 한도({self.max_total_risk*100}%) 크게 초과"

        return False, "정상"
