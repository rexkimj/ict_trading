"""
리스크 관리 모듈 테스트
"""
import pytest
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.strategy.risk_management import RiskManager


def test_risk_manager_initialization():
    """리스크 매니저 초기화 테스트"""
    rm = RiskManager(initial_capital=10000)

    assert rm.initial_capital == 10000
    assert rm.current_capital == 10000
    assert rm.max_risk_per_trade == 0.02
    assert len(rm.positions) == 0


def test_calculate_position_size():
    """포지션 사이즈 계산 테스트"""
    rm = RiskManager(initial_capital=10000, max_risk_per_trade=0.02)

    entry_price = 100.0
    stop_loss = 98.0
    direction = 'long'

    size, risk_amount = rm.calculate_position_size(
        entry_price, stop_loss, direction
    )

    assert size > 0
    assert risk_amount == 10000 * 0.02  # 2%


def test_can_open_position():
    """포지션 오픈 가능 여부 테스트"""
    rm = RiskManager(initial_capital=10000, max_open_positions=3)

    can_open, reason = rm.can_open_position()
    assert can_open is True


def test_open_position():
    """포지션 오픈 테스트"""
    rm = RiskManager(initial_capital=10000)

    position = rm.open_position(
        entry_price=100.0,
        stop_loss=98.0,
        direction='long',
        take_profit_levels=[(102.0, 0.5), (104.0, 0.5)]
    )

    assert position is not None
    assert position.is_open is True
    assert len(rm.positions) == 1


def test_close_position():
    """포지션 청산 테스트"""
    rm = RiskManager(initial_capital=10000)

    position = rm.open_position(
        entry_price=100.0,
        stop_loss=98.0,
        direction='long',
        take_profit_levels=[(102.0, 1.0)]
    )

    # 수익 청산
    realized_pnl = rm.close_position(position, 102.0, "Take Profit")

    assert realized_pnl > 0
    assert position.is_open is False
    assert rm.current_capital > 10000


def test_kill_switch():
    """Kill Switch 테스트"""
    rm = RiskManager(initial_capital=10000)

    # 자본을 50% 이하로 감소
    rm.current_capital = 4000

    should_stop, reason = rm.check_kill_switch()
    assert should_stop is True
    assert "50%" in reason


def test_get_performance_stats():
    """성과 통계 테스트"""
    rm = RiskManager(initial_capital=10000)

    # 테스트 거래
    position1 = rm.open_position(100.0, 98.0, 'long', [(102.0, 1.0)])
    rm.close_position(position1, 102.0, "TP")

    position2 = rm.open_position(100.0, 98.0, 'long', [(102.0, 1.0)])
    rm.close_position(position2, 98.0, "SL")

    stats = rm.get_performance_stats()

    assert stats['total_trades'] == 2
    assert stats['winning_trades'] == 1
    assert stats['losing_trades'] == 1
    assert 0 <= stats['win_rate'] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
