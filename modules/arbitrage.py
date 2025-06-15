"""
Arbitrage detection and opportunity tracking
"""
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger
from dataclasses import dataclass, asdict

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    timestamp: str
    spot_symbol: str
    perp_symbol: str
    spot_price: float
    perp_price: float
    spread_percent: float
    potential_profit_usdt: float
    trade_size_usdt: float
    
    def to_dict(self) -> Dict:
        return asdict(self)

class ArbitrageDetector:
    """Detects and tracks arbitrage opportunities"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_spread_percent = config.get('min_spread_percent', 0.2)
        self.trade_size_usdt = config.get('trade_size_usdt', 100)
        
        # Fees (approximate)
        self.binance_fee_percent = 0.1  # 0.1% taker fee
        self.drift_fee_percent = 0.05   # 0.05% taker fee
        self.total_fees_percent = self.binance_fee_percent + self.drift_fee_percent
        
        # Track opportunities
        self.opportunities: List[ArbitrageOpportunity] = []
        self.total_opportunities = 0
        
    def calculate_spread(self, spot_price: float, perp_price: float) -> float:
        """Calculate spread percentage"""
        return ((perp_price - spot_price) / spot_price) * 100
        
    def calculate_profit(self, spread_percent: float, trade_size_usdt: float) -> float:
        """Calculate potential profit after fees"""
        # Gross profit from spread
        gross_profit_percent = spread_percent - self.total_fees_percent
        
        # Net profit in USDT
        if gross_profit_percent > 0:
            return (gross_profit_percent / 100) * trade_size_usdt
        return 0
        
    def check_opportunity(
        self, 
        spot_symbol: str, 
        perp_symbol: str,
        spot_price: float, 
        perp_price: float
    ) -> Optional[ArbitrageOpportunity]:
        """Check if current prices present an arbitrage opportunity"""
        
        # Calculate spread
        spread_percent = self.calculate_spread(spot_price, perp_price)
        
        # Check if spread exceeds minimum threshold (including fees)
        if spread_percent > (self.min_spread_percent + self.total_fees_percent):
            # Calculate potential profit
            potential_profit = self.calculate_profit(spread_percent, self.trade_size_usdt)
            
            if potential_profit > 0:
                opportunity = ArbitrageOpportunity(
                    timestamp=datetime.utcnow().isoformat(),
                    spot_symbol=spot_symbol,
                    perp_symbol=perp_symbol,
                    spot_price=spot_price,
                    perp_price=perp_price,
                    spread_percent=spread_percent,
                    potential_profit_usdt=potential_profit,
                    trade_size_usdt=self.trade_size_usdt
                )
                
                self.opportunities.append(opportunity)
                self.total_opportunities += 1
                
                logger.success(
                    f"🎯 ARBITRAGE OPPORTUNITY DETECTED! "
                    f"Spread: {spread_percent:.3f}% | "
                    f"Profit: ${potential_profit:.2f}"
                )
                
                return opportunity
                
        return None
        
    def get_summary(self) -> Dict:
        """Get summary of detected opportunities"""
        if not self.opportunities:
            return {
                'total_opportunities': 0,
                'potential_profits': 0,
                'average_spread': 0,
                'best_opportunity': None
            }
            
        total_profits = sum(opp.potential_profit_usdt for opp in self.opportunities)
        avg_spread = sum(opp.spread_percent for opp in self.opportunities) / len(self.opportunities)
        best_opp = max(self.opportunities, key=lambda x: x.potential_profit_usdt)
        
        return {
            'total_opportunities': self.total_opportunities,
            'potential_profits': total_profits,
            'average_spread': avg_spread,
            'best_opportunity': best_opp.to_dict() if best_opp else None,
            'recent_opportunities': [opp.to_dict() for opp in self.opportunities[-5:]]
        }
