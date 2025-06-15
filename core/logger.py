"""
Logging Module

Production-grade logging with rotation, multiple outputs, and structured formatting.
Optimized for both development (Codespaces) and production (Render).
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional

from loguru import logger


class BotLogger:
    """
    Centralized logging configuration for the arbitrage bot.
    
    Features:
    - Structured logging with loguru
    - File rotation to prevent disk space issues
    - Different log levels for different components
    - JSON formatting for production
    - Colorized output for development
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize logger with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
        
    def setup(self, log_level: str = "INFO", mode: str = "SIMULATION") -> None:
        """
        Configure logging based on environment.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            mode: Bot mode (affects log formatting)
        """
        if self._initialized:
            return
            
        # Remove default logger
        logger.remove()
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Console logging (always enabled)
        if mode in ["SIMULATION", "BACKTEST"]:
            # Colorized output for development
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level=log_level,
                colorize=True
            )
        else:
            # Structured output for production
            logger.add(
                sys.stdout,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level=log_level,
                colorize=False
            )
        
        # File logging - Main log file (rotated daily)
        logger.add(
            log_dir / "bot_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # Rotate at midnight
            retention="30 days",  # Keep 30 days of logs
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            compression="zip"  # Compress old logs
        )
        
        # Error log file (persistent)
        logger.add(
            log_dir / "errors.log",
            level="ERROR",
            rotation="10 MB",  # Rotate when file reaches 10MB
            retention="90 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}\n{exception}",
            backtrace=True,
            diagnose=True
        )
        
        # Trade log file (for audit trail)
        logger.add(
            log_dir / "trades_{time:YYYY-MM}.log",
            filter=lambda record: "TRADE" in record["extra"],
            rotation="1 month",
            retention="1 year",
            format="{time:YYYY-MM-DD HH:mm:ss} | TRADE | {message}",
            serialize=True  # JSON format for trade logs
        )
        
        self._initialized = True
        logger.info(f"Logger initialized | Level: {log_level} | Mode: {mode}")
    
    def get_logger(self, name: str) -> 'logger':
        """
        Get a named logger instance.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Logger instance with context
        """
        return logger.bind(name=name)
    
    @staticmethod
    def log_trade(trade_data: dict) -> None:
        """
        Log trade information for audit trail.
        
        Args:
            trade_data: Trade information dictionary
        """
        logger.bind(TRADE=True).info(f"Trade executed: {trade_data}")
    
    @staticmethod
    def log_performance(metrics: dict) -> None:
        """
        Log performance metrics.
        
        Args:
            metrics: Performance metrics dictionary
        """
        logger.info(f"Performance update: {metrics}")


# Global logger instance
_bot_logger: Optional[BotLogger] = None


def setup_logger(log_level: str = "INFO", mode: str = "SIMULATION") -> BotLogger:
    """
    Setup and return the global logger instance.
    
    Args:
        log_level: Logging level
        mode: Bot mode
        
    Returns:
        Configured BotLogger instance
    """
    global _bot_logger
    if _bot_logger is None:
        _bot_logger = BotLogger()
        _bot_logger.setup(log_level, mode)
    return _bot_logger


def get_logger(name: str = __name__) -> 'logger':
    """
    Get a logger instance for a module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
    """
    if _bot_logger is None:
        setup_logger()
    return logger.bind(name=name)


# Convenience exports
__all__ = ['setup_logger', 'get_logger', 'BotLogger']
