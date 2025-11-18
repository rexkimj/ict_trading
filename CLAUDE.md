# CLAUDE.md - ICT Trading Project Guide

## Project Overview

**Project Name:** ICT Trading
**Primary Language:** Python
**Domain:** Algorithmic Trading & Technical Analysis
**Focus:** Inner Circle Trader (ICT) Methodology Implementation

This is a Python-based trading system that implements ICT (Inner Circle Trader) concepts and strategies for financial market analysis and automated trading.

---

## Repository Structure

### Current State
The repository is in its initial setup phase. The following structure is recommended as the project develops:

```
ict_trading/
├── src/                          # Source code
│   ├── strategies/               # Trading strategies (ICT concepts)
│   │   ├── order_blocks.py      # Order block detection
│   │   ├── fair_value_gaps.py   # FVG identification
│   │   ├── liquidity.py         # Liquidity pool detection
│   │   ├── market_structure.py  # BOS, CHoCH analysis
│   │   └── smart_money.py       # Smart money concepts
│   ├── data/                    # Data handling
│   │   ├── providers/           # Data source integrations
│   │   ├── preprocessing.py     # Data cleaning & normalization
│   │   └── storage.py           # Data persistence
│   ├── backtesting/             # Backtesting framework
│   │   ├── engine.py            # Backtest execution
│   │   ├── metrics.py           # Performance metrics
│   │   └── visualizations.py    # Results visualization
│   ├── execution/               # Trade execution
│   │   ├── broker_api.py        # Broker integrations
│   │   ├── risk_management.py   # Position sizing & risk
│   │   └── order_manager.py     # Order lifecycle management
│   ├── analysis/                # Technical analysis tools
│   │   ├── indicators.py        # Custom indicators
│   │   ├── patterns.py          # Pattern recognition
│   │   └── timeframes.py        # Multi-timeframe analysis
│   └── utils/                   # Utility functions
│       ├── config.py            # Configuration management
│       ├── logging.py           # Logging setup
│       └── helpers.py           # Helper functions
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data & fixtures
├── notebooks/                   # Jupyter notebooks for research
│   ├── research/                # Strategy research & development
│   └── analysis/                # Market analysis notebooks
├── data/                        # Data directory (gitignored)
│   ├── raw/                     # Raw market data
│   ├── processed/               # Processed datasets
│   └── cache/                   # Cached computations
├── configs/                     # Configuration files
│   ├── strategies/              # Strategy configurations
│   ├── brokers/                 # Broker configurations
│   └── environments/            # Environment-specific configs
├── scripts/                     # Utility scripts
│   ├── download_data.py         # Data download scripts
│   ├── run_backtest.py          # Backtest runner
│   └── deploy.py                # Deployment scripts
├── docs/                        # Documentation
│   ├── architecture.md          # Architecture overview
│   ├── strategies.md            # Strategy documentation
│   └── api.md                   # API documentation
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore patterns
├── pyproject.toml              # Project metadata & dependencies
├── requirements.txt            # Python dependencies
├── README.md                   # Project README
└── CLAUDE.md                   # This file

```

---

## Development Workflows

### Environment Setup

1. **Python Version**: Use Python 3.10+
2. **Dependency Management**: Prefer `poetry` or `uv` for modern projects
3. **Virtual Environment**: Always use virtual environments

```bash
# Using poetry
poetry install

# Using pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Coding Standards

#### Python Style
- **Style Guide**: Follow PEP 8
- **Formatter**: Use `black` with default settings (88 char line length)
- **Linter**: Use `ruff` for fast, comprehensive linting
- **Type Hints**: Use type annotations for all functions and methods
- **Docstrings**: Use Google-style docstrings

Example:
```python
from typing import List, Optional
import pandas as pd

def detect_order_blocks(
    df: pd.DataFrame,
    threshold: float = 0.5,
    lookback: int = 20
) -> List[dict]:
    """Detect order blocks in price data.

    Args:
        df: DataFrame with OHLC data
        threshold: Minimum size threshold for order blocks
        lookback: Number of candles to look back

    Returns:
        List of dictionaries containing order block information

    Raises:
        ValueError: If DataFrame is missing required columns
    """
    pass
```

#### Code Organization
- **Single Responsibility**: Each module should have a single, well-defined purpose
- **Separation of Concerns**: Keep strategy logic separate from data handling and execution
- **Configuration Over Hardcoding**: Use configuration files for parameters
- **No Secrets in Code**: Use environment variables for API keys and credentials

### Git Workflow

1. **Branch Naming**:
   - Feature: `feature/description`
   - Bugfix: `bugfix/description`
   - Hotfix: `hotfix/description`
   - Experiments: `experiment/description`

2. **Commit Messages**:
   ```
   <type>: <subject>

   <body>

   <footer>
   ```

   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

   Example:
   ```
   feat: add fair value gap detection algorithm

   Implements FVG detection using 3-candle pattern analysis.
   Includes both bullish and bearish gap identification.

   Closes #42
   ```

3. **Pull Request Process**:
   - Ensure all tests pass
   - Update documentation
   - Add/update tests for new features
   - Request review from team members

### Testing Strategy

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions
3. **Backtests**: Validate strategies on historical data
4. **Paper Trading**: Test in real-time without capital risk

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_order_blocks.py
```

---

## ICT Trading Concepts

When working on this project, AI assistants should understand these key ICT concepts:

### Core Concepts

1. **Order Blocks (OB)**
   - Last opposing candle before a significant price move
   - Represent institutional order placement
   - Used for entry points and support/resistance

2. **Fair Value Gaps (FVG)**
   - 3-candle imbalance patterns
   - Areas where price moved quickly, leaving inefficiency
   - Often get filled (price returns to the gap)

3. **Liquidity Pools**
   - Areas where stop losses cluster (highs/lows)
   - Smart money targets these areas before reversals
   - Equal highs/lows are prime liquidity zones

4. **Market Structure**
   - Break of Structure (BOS): Continuation signal
   - Change of Character (CHoCH): Reversal signal
   - Higher Highs/Higher Lows (bullish)
   - Lower Highs/Lower Lows (bearish)

5. **Kill Zones**
   - London Open: 02:00-05:00 EST
   - New York Open: 07:00-10:00 EST
   - London Close: 10:00-12:00 EST
   - Optimal trading times with highest liquidity

6. **Premium/Discount Arrays**
   - Premium: Above 50% of range (sell zone)
   - Discount: Below 50% of range (buy zone)
   - Equilibrium: 50% level

7. **Optimal Trade Entry (OTE)**
   - Fibonacci retracement levels: 0.62, 0.705, 0.79
   - Used for precise entry timing

### Strategy Implementation Guidelines

When implementing ICT strategies:

1. **Multi-Timeframe Analysis**
   - Higher timeframe: Bias and structure (Daily, 4H)
   - Entry timeframe: Precision entries (15M, 5M, 1M)
   - Always align with higher timeframe bias

2. **Session Awareness**
   - Track trading sessions (Asian, London, New York)
   - Consider session-specific behaviors
   - Respect kill zones for entries

3. **Risk Management**
   - Maximum 1-2% risk per trade
   - Risk-to-reward minimum 1:3
   - Position sizing based on account equity

4. **Data Requirements**
   - OHLC data at multiple timeframes
   - Volume data (if available)
   - Timestamp with timezone awareness
   - Clean data with no gaps

---

## Key Conventions for AI Assistants

### When Adding New Features

1. **Understand the Trading Context**
   - Ask about the ICT concept being implemented
   - Clarify the timeframe and market being targeted
   - Understand risk parameters

2. **Data-Driven Decisions**
   - Always validate strategies with backtests
   - Use statistical measures (Sharpe ratio, win rate, drawdown)
   - Document assumptions and limitations

3. **Safety First**
   - Trading systems can lose money if poorly implemented
   - Add safeguards (max drawdown limits, position limits)
   - Validate all calculations thoroughly
   - Use paper trading before live deployment

4. **Performance Considerations**
   - Optimize for speed in real-time scenarios
   - Use vectorized operations (NumPy, Pandas)
   - Cache expensive computations
   - Profile code for bottlenecks

### Code Review Checklist

Before submitting code, ensure:

- [ ] Type hints are present and correct
- [ ] Docstrings explain purpose, parameters, and returns
- [ ] Unit tests cover main functionality
- [ ] No hardcoded values (use config)
- [ ] No API keys or secrets in code
- [ ] Error handling for edge cases
- [ ] Logging for important operations
- [ ] Code follows PEP 8 / Black formatting
- [ ] Backtests show positive results (if strategy code)
- [ ] Documentation updated

### Common Pitfalls to Avoid

1. **Look-Ahead Bias**
   - Never use future data in backtests
   - Ensure all calculations use only past data
   - Be careful with pandas `.shift()` direction

2. **Over-Optimization**
   - Don't over-fit to historical data
   - Use walk-forward analysis
   - Test on out-of-sample data

3. **Ignoring Transaction Costs**
   - Include spread, commission, slippage
   - Model realistic execution
   - Account for market impact

4. **Data Quality Issues**
   - Check for missing data
   - Handle timezone conversions properly
   - Validate data integrity

5. **Unrealistic Assumptions**
   - Don't assume perfect fills
   - Account for liquidity constraints
   - Model realistic order execution

---

## Dependencies & Tools

### Core Libraries

```toml
[tool.poetry.dependencies]
python = "^3.10"
pandas = "^2.0"              # Data manipulation
numpy = "^1.24"              # Numerical computing
scipy = "^1.10"              # Scientific computing
matplotlib = "^3.7"          # Plotting
seaborn = "^0.12"           # Statistical visualization
plotly = "^5.14"            # Interactive plots
ta-lib = "^0.4"             # Technical analysis (optional)
ccxt = "^4.0"               # Crypto exchange API
yfinance = "^0.2"           # Yahoo Finance data
python-dotenv = "^1.0"      # Environment variables

[tool.poetry.group.dev.dependencies]
pytest = "^7.3"              # Testing framework
pytest-cov = "^4.1"          # Coverage reporting
black = "^23.3"              # Code formatting
ruff = "^0.0.270"           # Linting
mypy = "^1.3"               # Type checking
jupyter = "^1.0"            # Notebooks
ipython = "^8.14"           # Interactive shell
```

### Recommended Tools

- **IDE**: VS Code, PyCharm, or Cursor (AI-enhanced)
- **Notebooks**: Jupyter or Marimo (reactive notebooks)
- **Data Visualization**: TradingView for chart analysis
- **Backtesting**: Custom framework or backtrader
- **Monitoring**: Prometheus + Grafana for live systems

---

## Environment Variables

Create a `.env` file (never commit this):

```bash
# API Keys
BROKER_API_KEY=your_broker_api_key
BROKER_API_SECRET=your_broker_api_secret
DATA_PROVIDER_KEY=your_data_provider_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ict_trading

# Trading Configuration
ENVIRONMENT=development  # development, staging, production
MAX_POSITION_SIZE=10000
MAX_DAILY_LOSS=1000
RISK_PER_TRADE=0.02

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading.log

# Timezone
TIMEZONE=America/New_York
```

---

## Documentation Standards

### Code Documentation

1. **Module-level docstring**: Explain the module's purpose
2. **Class docstring**: Describe the class and its responsibilities
3. **Method docstring**: Use Google-style with Args, Returns, Raises
4. **Inline comments**: Explain "why", not "what"

### Strategy Documentation

For each strategy, document:

1. **Concept**: What ICT concept does it implement?
2. **Entry Rules**: Precise conditions for entering trades
3. **Exit Rules**: When to close positions
4. **Risk Management**: How risk is managed
5. **Timeframes**: Which timeframes to use
6. **Expected Performance**: Historical backtest results
7. **Market Conditions**: When the strategy works best

Example structure for `docs/strategies/order_block_strategy.md`:

```markdown
# Order Block Strategy

## Overview
This strategy trades reversals from key order blocks aligned with higher timeframe bias.

## Entry Rules
1. Identify higher timeframe trend (4H or Daily)
2. Wait for price to retrace to discount/premium array
3. Locate order block on 15M timeframe
4. Enter on first candle close within order block
5. Stop loss below/above order block

## Exit Rules
- Target: Recent high/low or FVG
- Risk-to-reward: Minimum 1:3
- Partial profits at 1:2

## Backtest Results
- Period: 2020-2024
- Win Rate: 58%
- Profit Factor: 2.1
- Max Drawdown: 12%
- Sharpe Ratio: 1.8

## Notes
Works best during London and New York sessions.
Avoid during high-impact news events.
```

---

## Performance Metrics

When evaluating strategies, calculate and report:

### Essential Metrics

1. **Net Profit**: Total profit/loss
2. **Win Rate**: Percentage of profitable trades
3. **Profit Factor**: Gross profit / Gross loss
4. **Average Win/Loss**: Mean profit per winning/losing trade
5. **Sharpe Ratio**: Risk-adjusted returns
6. **Maximum Drawdown**: Largest peak-to-trough decline
7. **Recovery Factor**: Net profit / Max drawdown
8. **Expectancy**: Average expected profit per trade

### Code Example

```python
def calculate_metrics(trades: pd.DataFrame) -> dict:
    """Calculate comprehensive trading metrics.

    Args:
        trades: DataFrame with columns ['entry_price', 'exit_price', 'position_size', 'pnl']

    Returns:
        Dictionary containing all performance metrics
    """
    total_trades = len(trades)
    winning_trades = trades[trades['pnl'] > 0]
    losing_trades = trades[trades['pnl'] < 0]

    metrics = {
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': len(winning_trades) / total_trades if total_trades > 0 else 0,
        'net_profit': trades['pnl'].sum(),
        'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
        'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
        'profit_factor': (winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())
                         if len(losing_trades) > 0 else float('inf')),
        'max_drawdown': calculate_max_drawdown(trades),
        'sharpe_ratio': calculate_sharpe_ratio(trades),
    }

    return metrics
```

---

## Deployment Guidelines

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Backtests show consistent profitability
- [ ] Forward tests completed successfully
- [ ] Paper trading results validated
- [ ] Risk limits configured correctly
- [ ] Monitoring and alerting set up
- [ ] Emergency stop mechanism tested
- [ ] Credentials secured (environment variables)
- [ ] Logging configured for production
- [ ] Documentation up to date

### Deployment Stages

1. **Development**: Local testing and development
2. **Staging**: Paper trading with real-time data
3. **Production**: Live trading with real capital

### Monitoring

Monitor these in production:

- Active positions
- Daily P&L
- Drawdown levels
- Error rates
- API latency
- System health
- Strategy performance vs. backtest

---

## Troubleshooting

### Common Issues

#### Data Issues
```python
# Check for missing data
assert not df.isnull().any().any(), "Data contains NaN values"

# Verify timezone
assert df.index.tz is not None, "Datetime index must be timezone-aware"

# Check for duplicates
assert not df.index.duplicated().any(), "Duplicate timestamps found"
```

#### Calculation Issues
```python
# Avoid division by zero
result = numerator / denominator if denominator != 0 else 0

# Handle edge cases
if len(data) < min_periods:
    return None
```

#### API Issues
```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """Decorator to retry failed API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator
```

---

## Resources

### ICT Education
- ICT YouTube Channel (Michael J. Huddleston)
- ICT Trading Concepts Documentation
- ICT Mentorship Materials

### Python Trading
- [QuantConnect](https://www.quantconnect.com/) - Algorithmic trading platform
- [Backtrader](https://www.backtrader.com/) - Backtesting framework
- [VectorBT](https://vectorbt.dev/) - Fast backtesting library
- [TA-Lib](https://ta-lib.org/) - Technical analysis library

### Books
- "Advances in Financial Machine Learning" by Marcos López de Prado
- "Quantitative Trading" by Ernest Chan
- "Python for Finance" by Yves Hilpisch

---

## Contributing

When contributing to this project:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Update documentation
6. Submit a pull request

---

## License

(Specify your license here)

---

## Contact & Support

For questions or support:
- Open an issue on GitHub
- Contact the maintainer

---

## Changelog

### [Unreleased]
- Initial project setup
- CLAUDE.md documentation created

---

## AI Assistant Notes

### Context for Claude and Other AI Assistants

When working on this project:

1. **Always prioritize safety**: Trading systems involve financial risk. Be extra careful with calculations, especially position sizing and risk management.

2. **Validate thoroughly**: Backtest rigorously, check for look-ahead bias, and verify all calculations.

3. **Think probabilistically**: No strategy works 100% of the time. Focus on positive expectancy over time.

4. **Respect market complexity**: Markets are non-stationary and complex. Avoid over-simplification.

5. **Document assumptions**: Clearly state any assumptions made in implementations.

6. **Test edge cases**: Consider what happens during extreme market conditions.

7. **Keep learning**: ICT concepts evolve. Stay updated with the latest methodologies.

### Quick Reference Commands

```bash
# Setup environment
poetry install

# Run tests
pytest

# Format code
black .

# Lint code
ruff check .

# Type check
mypy src/

# Run a backtest
python scripts/run_backtest.py --strategy order_block --start 2020-01-01 --end 2024-01-01

# Download data
python scripts/download_data.py --symbol EURUSD --timeframe 1m --start 2024-01-01

# Start Jupyter notebook
jupyter lab
```

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
**Maintained by**: Project Team
