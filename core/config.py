"""
Configuration Management Module

Handles all configuration loading, validation, and access for the arbitrage bot.
Uses environment variables and provides a centralized config object.
"""

import os
from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class TradingMode(str, Enum):
    """Trading mode enumeration"""
    SIMULATION = "SIMULATION"
    BACKTEST = "BACKTEST"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


class BotConfig(BaseModel):
    """
    Main configuration model for the arbitrage bot.
    
    Validates and provides typed access to all configuration parameters.
    """
    
    # Mode
    mode: TradingMode = Field(default=TradingMode.SIMULATION)
    log_level: str = Field(default="INFO")
    
    # Drift Configuration
    drift_private_key: Optional[str] = Field(default=None)
    solana_rpc_url: str = Field(default="https://api.mainnet-beta.solana.com")
    
    # Binance Configuration
    binance_api_key: Optional[str] = Field(default=None)
    binance_secret_key: Optional[str] = Field(default=None)
    
    # Trading Parameters
    spread_threshold: float = Field(default=0.003, ge=0.0001, le=0.1)
    trade_size_usdc: float = Field(default=100, ge=10, le=10000)
    max_open_positions: int = Field(default=2, ge=1, le=10)
    
    # Risk Parameters
    max_drawdown: float = Field(default=0.05, ge=0.01, le=0.5)
    max_trades_per_day: int = Field(default=50, ge=1, le=1000)
    cooldown_after_losses: int = Field(default=3, ge=1, le=10)
    cooldown_duration_min: int = Field(default=30, ge=5, le=360)
    
    # Backtesting Parameters
    backtest_timeframe: str = Field(default="1m")
    backtest_data_source: str = Field(default="csv")
    backtest_start_date: datetime = Field(default=datetime(2023, 1, 1))
    backtest_end_date: datetime = Field(default=datetime(2024, 6, 1))
    
    # Alerts
    discord_webhook_url: Optional[str] = Field(default=None)
    
    # Database
    database_url: str = Field(default="sqlite:///data/arb_bot.db")
    
    # Server
    port: int = Field(default=8080, ge=1024, le=65535)
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        case_sensitive = False
    
    @validator("mode", pre=True)
    def validate_mode(cls, v):
        """Validate and convert mode to enum"""
        if isinstance(v, str):
            return TradingMode(v.upper())
        return v
    
    @validator("drift_private_key", "binance_api_key")
    def validate_required_in_live_mode(cls, v, values):
        """Ensure required credentials are present in LIVE mode"""
        if values.get("mode") == TradingMode.LIVE and not v:
            raise ValueError(f"API credentials required for LIVE mode")
        return v
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.mode in [TradingMode.LIVE, TradingMode.TESTNET]
    
    def is_backtesting(self) -> bool:
        """Check if running in backtest mode"""
        return self.mode == TradingMode.BACKTEST
    
    def __repr__(self) -> str:
        """String representation hiding sensitive data"""
        return f"BotConfig(mode={self.mode}, spread_threshold={self.spread_threshold})"


def load_config() -> BotConfig:
    """
    Load and validate configuration from environment variables.
    
    Returns:
        BotConfig: Validated configuration object
        
    Raises:
        ValidationError: If configuration is invalid
    """
    # Load .env file if it exists
    load_dotenv()
    
    # Create config instance (will validate automatically)
    config = BotConfig(
        mode=os.getenv("MODE", "SIMULATION"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        drift_private_key=os.getenv("DRIFT_PRIVATE_KEY"),
        solana_rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
        binance_api_key=os.getenv("BINANCE_API_KEY"),
        binance_secret_key=os.getenv("BINANCE_SECRET_KEY"),
        spread_threshold=float(os.getenv("SPREAD_THRESHOLD", "0.003")),
        trade_size_usdc=float(os.getenv("TRADE_SIZE_USDC", "100")),
        max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", "2")),
        max_drawdown=float(os.getenv("MAX_DRAWDOWN", "0.05")),
        max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "50")),
        cooldown_after_losses=int(os.getenv("COOLDOWN_AFTER_LOSSES", "3")),
        cooldown_duration_min=int(os.getenv("COOLDOWN_DURATION_MIN", "30")),
        backtest_timeframe=os.getenv("BACKTEST_TIMEFRAME", "1m"),
        backtest_data_source=os.getenv("BACKTEST_DATA_SOURCE", "csv"),
        backtest_start_date=datetime(2023, 1, 1),
        backtest_end_date=datetime(2024, 6, 1),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/arb_bot.db"),
        port=int(os.getenv("PORT", "8080"))
    )
    
    return config


# Global config instance (singleton pattern)
_config: Optional[BotConfig] = None


def get_config() -> BotConfig:
    """
    Get the global configuration instance.
    
    Returns:
        BotConfig: Global configuration object
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config
