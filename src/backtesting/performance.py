"""
성과 분석 모듈

백테스팅 결과의 성과를 분석하고 시각화합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """성과 지표"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_trade_duration: float


class PerformanceAnalyzer:
    """성과 분석 클래스"""

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Args:
            risk_free_rate: 무위험 수익률 (연율)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_metrics(
        self,
        equity_curve: List[Dict],
        trades: List[Dict],
        initial_capital: float
    ) -> PerformanceMetrics:
        """
        성과 지표 계산

        Args:
            equity_curve: 자본 곡선
            trades: 거래 내역
            initial_capital: 초기 자본

        Returns:
            성과 지표
        """
        # 데이터프레임 변환
        df_equity = pd.DataFrame(equity_curve)
        if len(df_equity) == 0:
            return self._empty_metrics()

        df_equity['timestamp'] = pd.to_datetime(df_equity['timestamp'])
        df_equity.set_index('timestamp', inplace=True)

        # 수익률 계산
        df_equity['returns'] = df_equity['equity'].pct_change()

        # 총 수익률
        total_return = (df_equity['equity'].iloc[-1] - initial_capital) / initial_capital

        # 연율화 수익률
        days = (df_equity.index[-1] - df_equity.index[0]).days
        annualized_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0

        # 샤프 비율
        sharpe_ratio = self._calculate_sharpe_ratio(df_equity['returns'])

        # 소르티노 비율
        sortino_ratio = self._calculate_sortino_ratio(df_equity['returns'])

        # 최대 낙폭
        max_drawdown = self._calculate_max_drawdown(df_equity['equity'])

        # 거래 통계
        if trades:
            win_trades = [t for t in trades if t.get('pnl', 0) > 0]
            win_rate = len(win_trades) / len(trades)

            total_wins = sum(t['pnl'] for t in win_trades)
            total_losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
            profit_factor = total_wins / total_losses if total_losses > 0 else 0

            # 평균 거래 기간
            durations = []
            for t in trades:
                if 'exit_time' in t and 'entry_time' in t:
                    duration = (t['exit_time'] - t['entry_time']).total_seconds() / 3600
                    durations.append(duration)
            avg_trade_duration = np.mean(durations) if durations else 0
        else:
            win_rate = 0
            profit_factor = 0
            avg_trade_duration = 0

        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_duration=avg_trade_duration
        )

    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """샤프 비율 계산"""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        excess_returns = returns.mean() - (self.risk_free_rate / 252)  # 일별 무위험 수익률
        sharpe = (excess_returns / returns.std()) * np.sqrt(252)  # 연율화

        return sharpe

    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """소르티노 비율 계산 (하락 변동성만 고려)"""
        if len(returns) == 0:
            return 0.0

        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        excess_returns = returns.mean() - (self.risk_free_rate / 252)
        sortino = (excess_returns / downside_returns.std()) * np.sqrt(252)

        return sortino

    def _calculate_max_drawdown(self, equity: pd.Series) -> float:
        """최대 낙폭 계산"""
        if len(equity) == 0:
            return 0.0

        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak

        return abs(drawdown.min())

    def _empty_metrics(self) -> PerformanceMetrics:
        """빈 메트릭 반환"""
        return PerformanceMetrics(
            total_return=0.0,
            annualized_return=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_trade_duration=0.0
        )

    def generate_report(self, metrics: PerformanceMetrics) -> str:
        """
        성과 리포트 생성

        Args:
            metrics: 성과 지표

        Returns:
            리포트 문자열
        """
        report = f"""
=== 성과 분석 리포트 ===

수익률:
  총 수익률: {metrics.total_return*100:.2f}%
  연율화 수익률: {metrics.annualized_return*100:.2f}%

리스크 조정 수익률:
  샤프 비율: {metrics.sharpe_ratio:.2f}
  소르티노 비율: {metrics.sortino_ratio:.2f}
  최대 낙폭: {metrics.max_drawdown*100:.2f}%

거래 통계:
  승률: {metrics.win_rate*100:.2f}%
  Profit Factor: {metrics.profit_factor:.2f}
  평균 거래 기간: {metrics.avg_trade_duration:.2f}시간

========================
        """

        return report
