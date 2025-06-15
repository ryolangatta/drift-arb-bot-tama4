"""
Database Manager

Handles all database operations for trade history and metrics.
"""

from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from core.logger import get_logger


class DatabaseManager:
    """
    Simple database manager using JSON files.
    
    Can be upgraded to SQLite/PostgreSQL later.
    """
    
    def __init__(self, config: dict):
        """Initialize database manager."""
        self.config = config
        self.logger = get_logger(__name__)
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.trades_file = self.data_dir / "trades.json"
        self.metrics_file = self.data_dir / "metrics.json"
        
    async def save_trade(self, trade: Dict) -> bool:
        """Save trade record."""
        try:
            trades = await self.load_trades()
            trades.append(trade)
            
            with open(self.trades_file, 'w') as f:
                json.dump(trades, f, indent=2, default=str)
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to save trade: {e}")
            return False
    
    async def load_trades(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Load trade records."""
        if not self.trades_file.exists():
            return []
            
        try:
            with open(self.trades_file, 'r') as f:
                trades = json.load(f)
                
            # Filter by date if provided
            if start_date or end_date:
                filtered = []
                for trade in trades:
                    trade_time = datetime.fromisoformat(trade['timestamp'])
                    if start_date and trade_time < start_date:
                        continue
                    if end_date and trade_time > end_date:
                        continue
                    filtered.append(trade)
                return filtered
                
            return trades
        except Exception as e:
            self.logger.error(f"Failed to load trades: {e}")
            return []
    
    async def save_metrics(
        self,
        metrics: Dict
    ) -> bool:
        """Save performance metrics."""
        try:
            metrics['timestamp'] = datetime.now().isoformat()
            
            all_metrics = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    all_metrics = json.load(f)
                    
            all_metrics.append(metrics)
            
            with open(self.metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2, default=str)
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")
            return False
    
    async def get_latest_metrics(self) -> Optional[Dict]:
        """Get most recent metrics."""
        if not self.metrics_file.exists():
            return None
            
        try:
            with open(self.metrics_file, 'r') as f:
                all_metrics = json.load(f)
                
            return all_metrics[-1] if all_metrics else None
        except Exception as e:
            self.logger.error(f"Failed to load metrics: {e}")
            return None
