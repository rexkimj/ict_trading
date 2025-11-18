"""
유동성 모듈 테스트
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.liquidity import LiquidityAnalyzer, LiquidityLevel


@pytest.fixture
def sample_data():
    """샘플 OHLCV 데이터"""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1H')
    data = {
        'open': np.random.uniform(95, 105, 100),
        'high': np.random.uniform(100, 110, 100),
        'low': np.random.uniform(90, 100, 100),
        'close': np.random.uniform(95, 105, 100),
        'volume': np.random.randint(1000, 5000, 100)
    }
    df = pd.DataFrame(data, index=dates)

    # OHLC 일관성 보장
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)

    return df


def test_liquidity_analyzer_initialization():
    """유동성 분석기 초기화 테스트"""
    analyzer = LiquidityAnalyzer()
    assert analyzer.liquidity_grab_threshold == 0.001
    assert len(analyzer.liquidity_levels) == 0


def test_identify_pdh_pdl(sample_data):
    """PDH/PDL 식별 테스트"""
    analyzer = LiquidityAnalyzer()
    pdh_levels, pdl_levels = analyzer.identify_pdh_pdl(sample_data)

    assert len(pdh_levels) > 0
    assert len(pdl_levels) > 0
    assert all(isinstance(level, LiquidityLevel) for level in pdh_levels)
    assert all(level.level_type == 'pdh' for level in pdh_levels)
    assert all(level.level_type == 'pdl' for level in pdl_levels)


def test_identify_swing_points(sample_data):
    """스윙 포인트 식별 테스트"""
    analyzer = LiquidityAnalyzer()
    swing_highs, swing_lows = analyzer.identify_swing_points(sample_data)

    assert isinstance(swing_highs, list)
    assert isinstance(swing_lows, list)
    assert all(isinstance(level, LiquidityLevel) for level in swing_highs)


def test_update_liquidity_levels(sample_data):
    """유동성 레벨 업데이트 테스트"""
    analyzer = LiquidityAnalyzer()
    analyzer.update_liquidity_levels(sample_data)

    assert len(analyzer.liquidity_levels) > 0


def test_get_nearest_liquidity(sample_data):
    """가장 가까운 유동성 레벨 찾기 테스트"""
    analyzer = LiquidityAnalyzer()
    analyzer.update_liquidity_levels(sample_data)

    current_price = 100.0
    nearest = analyzer.get_nearest_liquidity(current_price)

    if nearest:
        assert isinstance(nearest, LiquidityLevel)
        assert nearest.price > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
