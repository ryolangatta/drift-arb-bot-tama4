"""
Risk Management Module

Implements risk controls and position limits for the arbitrage strategy.
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from core.logger import get_logger


class RiskLevel(str, Enum):
    """Risk level enumeration"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskStatus:
    """Current risk status"""
    level: RiskLevel
    daily_loss: Decimal
    open_exposure: Decimal
    consecutive_losses: int
    is_trading_allowed: bool
    cooldown_until: Optional[datetime]
    warnings: List[str]


class RiskManager:
    """
    Manages risk limits and trading controls.
    
    Features:
    - Position size limits
    - Daily loss limits
    - Drawdown protection
    - Cooldown periods
    - Exposure management
    """
    
    def __init__(self, config: dict):
        """
        Initialize risk manager.
        
        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Risk parameters
        self.max_drawdown = Decimal(str(config.max_drawdown))
        self.max_trades_per_day = config.max_trades_per_day
        self.cooldown_after_losses = config.cooldown_after_losses
        self.cooldown_duration = timedelta(minutes=config.cooldown_duration_min)
        self.max_position_size = Decimal(str(config.trade_size_usdc)) * 3
        
        # Tracking
        self.daily_trades = 0
        self.daily_loss = Decimal("0")
        self.consecutive_losses = 0
        self.cooldown_until: Optional[datetime] = None
        self.open_positions: Dict[str, Decimal] = {}
        
    async def check_trade_allowed(
        self,
        size: Decimal
    ) -> Tuple[bool, str]:
        """
        Check if a new trade is allowed under risk limits.
        
        Args:
            size: Proposed trade size
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check cooldown
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).seconds // 60
            return False, f"In cooldown for {remaining} more minutes"
        
        # Check daily trade limit
        if self.daily_trades >= self.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.max_trades_per_day})"
        
        # Check drawdown limit
        if abs(self.daily_loss) >= self.max_drawdown:
            return False, f"Daily loss limit reached ({self.max_drawdown:.1%})"
        
        # Check position size
        total_exposure = sum(self.open_positions.values()) + size
        if total_exposure > self.max_position_size:
            return False, f"Position size limit exceeded"
        
        return True, "Trade allowed"
    
    async def record_trade_result(
        self,
        profit: Decimal,
        size: Decimal
    ) -> None:
        """
        Record the result of a trade for risk tracking.
        
        Args:
            profit: Trade profit/loss
            size: Trade size
        """
        self.daily_trades += 1
        self.daily_loss += profit
        
        if profit < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.cooldown_after_losses:
                self.cooldown_until = datetime.now() + self.cooldown_duration
                self.logger.warning(f"Entering cooldown until {self.cooldown_until}")
        else:
            self.consecutive_losses = 0
            
    async def get_risk_status(self) -> RiskStatus:
        """
        Get current risk status.
        
        Returns:
            Current risk status
        """
        # Determine risk level
        if abs(self.daily_loss) > self.max_drawdown * Decimal("0.8"):
            level = RiskLevel.CRITICAL
        elif abs(self.daily_loss) > self.max_drawdown * Decimal("0.5"):
            level = RiskLevel.HIGH
        elif self.consecutive_losses >= 2:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
            
        # Compile warnings
        warnings = []
        if self.daily_trades > self.max_trades_per_day * 0.8:
            warnings.append(f"Approaching daily trade limit")
        if abs(self.daily_loss) > self.max_drawdown * Decimal("0.5"):
            warnings.append(f"High daily loss: {self.daily_loss}")
            
        return RiskStatus(
            level=level,
            daily_loss=self.daily_loss,
            open_exposure=sum(self.open_positions.values()),
            consecutive_losses=self.consecutive_losses,
            is_trading_allowed=self.cooldown_until is None,
            cooldown_until=self.cooldown_until,
            warnings=warnings
        )
    
    async def reset_daily_limits(self) -> None:
        """Reset daily tracking (call at start of trading day)."""
        self.logger.info("Resetting daily risk limits")
        self.daily_trades = 0
        self.daily_loss = Decimal("0")
        self.consecutive_losses = 0
