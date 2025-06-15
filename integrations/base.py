"""
Base Exchange Interface

Abstract base class that defines the common interface for all exchange integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    IOC = "IOC"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class Ticker:
    """Market ticker data"""
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    timestamp: datetime


@dataclass
class Balance:
    """Account balance information"""
    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal


@dataclass
class Order:
    """Order information"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    price: Optional[Decimal]
    quantity: Decimal
    filled_quantity: Decimal
    status: OrderStatus
    timestamp: datetime
    fee: Optional[Decimal] = None


@dataclass
class Trade:
    """Trade execution information"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    fee: Decimal
    fee_asset: str
    timestamp: datetime


class BaseExchange(ABC):
    """Abstract base class for exchange integrations."""
    
    def __init__(self, name: str, config: dict):
        """Initialize base exchange."""
        self.name = name
        self.config = config
        self.connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current ticker data for a symbol."""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str) -> Optional[Balance]:
        """Get balance for a specific asset."""
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None
    ) -> Optional[Order]:
        """Place an order on the exchange."""
        pass
