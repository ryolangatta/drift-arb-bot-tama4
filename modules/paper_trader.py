"""
Paper trading simulator for tracking virtual trades
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from dataclasses import dataclass, asdict

@dataclass
class PaperTrade:
    """Represents a paper trade"""
    id: int
    timestamp: str
    spot_symbol: str
    perp_symbol: str
    spot_price: float
    perp_price: float
    trade_size_usdt: float
    spread_percent: float
    expected_profit: float
    status: str = "OPEN"
    close_spot_price: Optional[float] = None
    close_perp_price: Optional[float] = None
    actual_profit: Optional[float] = None
    close_timestamp: Optional[str] = None
    
class PaperTrader:
    """Simulates trade execution and tracks performance"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.initial_balance = config.get('initial_balance', 10000)  # $10k starting balance
        self.balance = self.initial_balance
        self.trades: List[PaperTrade] = []
        self.open_trades: Dict[int, PaperTrade] = {}
        self.trade_counter = 0
        
        # Load existing trades if any
        self.trades_file = 'data/paper_trades.json'
        self.load_trades()
        
    def load_trades(self):
        """Load trades from file"""
        try:
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r') as f:
                    data = json.load(f)
                    self.balance = data.get('balance', self.initial_balance)
                    self.trade_counter = data.get('trade_counter', 0)
                    # Convert trades back to PaperTrade objects
                    self.trades = [PaperTrade(**trade) for trade in data.get('trades', [])]
                    logger.info(f"Loaded {len(self.trades)} existing trades. Balance: ${self.balance:.2f}")
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
            
    def save_trades(self):
        """Save trades to file"""
        try:
            os.makedirs('data', exist_ok=True)
            data = {
                'balance': self.balance,
                'trade_counter': self.trade_counter,
                'trades': [asdict(trade) for trade in self.trades],
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.trades_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
            
    def execute_trade(self, opportunity: Dict) -> Optional[PaperTrade]:
        """Execute a paper trade based on opportunity"""
        
        # Check if we have enough balance
        if self.balance < opportunity['trade_size_usdt']:
            logger.warning(f"Insufficient balance: ${self.balance:.2f} < ${opportunity['trade_size_usdt']}")
            return None
            
        # Create trade
        self.trade_counter += 1
        trade = PaperTrade(
            id=self.trade_counter,
            timestamp=datetime.utcnow().isoformat(),
            spot_symbol=opportunity['spot_symbol'],
            perp_symbol=opportunity['perp_symbol'],
            spot_price=opportunity['spot_price'],
            perp_price=opportunity['perp_price'],
            trade_size_usdt=opportunity['trade_size_usdt'],
            spread_percent=opportunity['spread_percent'],
            expected_profit=opportunity['potential_profit_usdt']
        )
        
        # Deduct from balance (simulating capital in use)
        self.balance -= trade.trade_size_usdt
        
        # Add to trades
        self.trades.append(trade)
        self.open_trades[trade.id] = trade
        
        logger.info(
            f"📝 PAPER TRADE #{trade.id} EXECUTED | "
            f"Size: ${trade.trade_size_usdt} | "
            f"Expected Profit: ${trade.expected_profit:.2f} | "
            f"Balance: ${self.balance:.2f}"
        )
        
        self.save_trades()
        return trade
        
    def close_trade(self, trade_id: int, current_spot: float, current_perp: float) -> Optional[float]:
        """Close a paper trade and calculate actual profit"""
        
        if trade_id not in self.open_trades:
            logger.error(f"Trade #{trade_id} not found in open trades")
            return None
            
        trade = self.open_trades[trade_id]
        
        # Calculate actual profit
        # We bought spot and sold perp at open
        # Now we sell spot and buy perp to close
        entry_spread = trade.perp_price - trade.spot_price
        exit_spread = current_perp - current_spot
        spread_captured = entry_spread - exit_spread
        
        # Convert to profit (considering fees)
        gross_profit = (spread_captured / trade.spot_price) * trade.trade_size_usdt
        fees = trade.trade_size_usdt * 0.0015  # 0.15% total fees
        actual_profit = gross_profit - fees
        
        # Update trade
        trade.close_spot_price = current_spot
        trade.close_perp_price = current_perp
        trade.actual_profit = actual_profit
        trade.close_timestamp = datetime.utcnow().isoformat()
        trade.status = "CLOSED"
        
        # Return capital + profit
        self.balance += trade.trade_size_usdt + actual_profit
        
        # Remove from open trades
        del self.open_trades[trade_id]
        
        # Log result
        emoji = "✅" if actual_profit > 0 else "❌"
        logger.info(
            f"{emoji} TRADE #{trade_id} CLOSED | "
            f"Actual Profit: ${actual_profit:.2f} | "
            f"Expected: ${trade.expected_profit:.2f} | "
            f"Balance: ${self.balance:.2f}"
        )
        
        self.save_trades()
        return actual_profit
        
    def get_performance_summary(self) -> Dict:
        """Get trading performance summary"""
        closed_trades = [t for t in self.trades if t.status == "CLOSED"]
        
        if not closed_trades:
            return {
                'total_trades': len(self.trades),
                'closed_trades': 0,
                'open_trades': len(self.open_trades),
                'total_profit': 0,
                'win_rate': 0,
                'roi': 0,
                'current_balance': self.balance
            }
            
        # Calculate metrics
        total_profit = sum(t.actual_profit for t in closed_trades if t.actual_profit)
        winning_trades = [t for t in closed_trades if t.actual_profit and t.actual_profit > 0]
        
        return {
            'total_trades': len(self.trades),
            'closed_trades': len(closed_trades),
            'open_trades': len(self.open_trades),
            'total_profit': total_profit,
            'win_rate': len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0,
            'roi': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'current_balance': self.balance,
            'initial_balance': self.initial_balance
        }
