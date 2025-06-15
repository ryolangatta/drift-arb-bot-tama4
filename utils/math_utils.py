"""
Mathematical Utilities

Common calculations for arbitrage trading.
"""

from decimal import Decimal, ROUND_DOWN
from typing import Tuple, Optional


def calculate_spread_percentage(
    price1: Decimal,
    price2: Decimal
) -> Decimal:
    """Calculate percentage spread between two prices."""
    if price1 == 0:
        return Decimal("0")
    return ((price2 - price1) / price1) * Decimal("100")


def round_size(
    size: Decimal,
    step: Decimal = Decimal("0.01")
) -> Decimal:
    """Round size to valid step."""
    return (size // step) * step


def calculate_profit_after_fees(
    entry_price: Decimal,
    exit_price: Decimal,
    size: Decimal,
    total_fee_rate: Decimal
) -> Decimal:
    """Calculate profit after fees."""
    gross_profit = (exit_price - entry_price) * size
    fees = size * entry_price * total_fee_rate
    return gross_profit - fees


def is_profitable_spread(
    spread_pct: Decimal,
    fee_rate: Decimal,
    min_profit: Decimal = Decimal("0.001")
) -> bool:
    """Check if spread is profitable after fees."""
    return spread_pct > (fee_rate * Decimal("2") + min_profit)
