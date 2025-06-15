"""
Improved arbitrage bot with better trade management
"""
import asyncio
import json
import random
from typing import Dict
from modules.price_monitor import PriceMonitor
from modules.arbitrage import ArbitrageDetector
from modules.paper_trader import PaperTrader
from core.logger import logger

class ImprovedArbitrageBot:
    """Improved arbitrage bot with exit strategies"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.price_monitor = PriceMonitor(config)
        self.arb_detector = ArbitrageDetector(config)
        self.paper_trader = PaperTrader(config)
        self.running = True
        self.auto_trade = config.get('auto_trade', True)
        self.max_open_trades = config.get('max_open_trades', 3)
        self.exit_strategy = config.get('exit_strategy', 'spread_target')
        
    async def price_callback(self, spot_symbol: str, perp_symbol: str, 
                           spot_price: float, perp_price: float):
        """Handle new prices and check for arbitrage"""
        
        # Check existing positions for exit
        await self.check_exit_conditions(spot_symbol, perp_symbol, spot_price, perp_price)
        
        # Calculate spread
        spread = ((perp_price - spot_price) / spot_price) * 100
        
        # Check for new opportunities only if we have capacity
        if len(self.paper_trader.open_trades) < self.max_open_trades:
            opportunity = self.arb_detector.check_opportunity(
                spot_symbol, perp_symbol, spot_price, perp_price
            )
            
            if opportunity and self.auto_trade:
                # Additional filters for better trades
                if self.should_take_trade(opportunity):
                    trade = self.paper_trader.execute_trade(opportunity.to_dict())
                else:
                    logger.debug(f"Skipped opportunity: spread {opportunity.spread_percent:.3f}% below quality threshold")
        
    def should_take_trade(self, opportunity) -> bool:
        """Apply additional filters for trade quality"""
        # Only take trades with higher profit potential
        min_profit = self.config.get('min_profit_usdt', 1.0)
        
        # Require higher spread during volatile periods
        quality_spread = opportunity.spread_percent > (self.config['min_spread_percent'] + 0.2)
        
        return opportunity.potential_profit_usdt >= min_profit and quality_spread
        
    async def check_exit_conditions(self, spot_symbol: str, perp_symbol: str, 
                                   spot_price: float, perp_price: float):
        """Check if any open trades should be closed"""
        
        for trade_id, trade in list(self.paper_trader.open_trades.items()):
            # Only check exits for matching symbols
            if trade.spot_symbol != spot_symbol:
                continue
                
            current_spread = ((perp_price - spot_price) / spot_price) * 100
            
            # Calculate position P&L
            entry_spread = trade.spread_percent
            spread_change = entry_spread - current_spread
            unrealized_pnl = (spread_change / 100) * trade.trade_size_usdt - (trade.trade_size_usdt * 0.0015)
            
            # Exit conditions
            should_exit = False
            reason = ""
            
            if self.exit_strategy == 'spread_target':
                # Exit when spread narrows to 0.1% or less
                if current_spread <= 0.1:
                    should_exit = True
                    reason = "Target spread reached"
                    
            # Stop loss: Exit if losing more than $2
            if unrealized_pnl < -2:
                should_exit = True
                reason = "Stop loss triggered"
                
            # Take profit: Exit if profitable and spread is narrowing
            if unrealized_pnl > 0 and current_spread < (entry_spread * 0.5):
                should_exit = True
                reason = "Take profit"
                
            # Time-based: Exit if trade is older than 60 seconds
            trade_age = (asyncio.get_event_loop().time() - trade.timestamp.timestamp()) if hasattr(trade.timestamp, 'timestamp') else 60
            if trade_age > 60:
                should_exit = True
                reason = "Max time reached"
                
            if should_exit:
                logger.info(f"Closing trade #{trade_id}: {reason} | Unrealized P&L: ${unrealized_pnl:.2f}")
                self.paper_trader.close_trade(trade_id, spot_price, perp_price)
                
    async def run(self):
        """Run the bot"""
        try:
            # Initialize price monitor
            await self.price_monitor.initialize()
            
            # Log configuration
            logger.info("=" * 60)
            logger.info("🚀 IMPROVED ARBITRAGE BOT V2")
            logger.info("=" * 60)
            logger.info(f"Mode: {self.config['mode']}")
            logger.info(f"Max Open Trades: {self.max_open_trades}")
            logger.info(f"Exit Strategy: {self.exit_strategy}")
            logger.info(f"Min Profit Filter: ${self.config.get('min_profit_usdt', 1.0)}")
            logger.info(f"Current Balance: ${self.paper_trader.balance:.2f}")
            
            logger.info("=" * 60)
            
            # Define pairs to monitor
            pairs = [
                {"spot_symbol": "SOLUSDT", "perp_symbol": "SOLPERP"},
            ]
            
            # Start monitoring
            await self.price_monitor.start(pairs, self.price_callback)
            
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
        finally:
            await self.stop()
            
    async def stop(self):
        """Clean shutdown"""
        self.running = False
        await self.price_monitor.stop()
        
        # Close any remaining open trades
        logger.info("Closing remaining open positions...")
        for trade_id in list(self.paper_trader.open_trades.keys()):
            trade = self.paper_trader.open_trades[trade_id]
            # Use last known prices
            spot_price = self.price_monitor.last_prices.get('binance', {}).get(trade.spot_symbol, {}).get('price', trade.spot_price)
            perp_price = self.price_monitor.last_prices.get('drift', {}).get(trade.perp_symbol, {}).get('price', trade.perp_price)
            self.paper_trader.close_trade(trade_id, spot_price, perp_price)
        
        # Print final summary
        logger.info("=" * 60)
        logger.info("📊 FINAL RESULTS")
        logger.info("=" * 60)
        
        # Trading summary
        trade_summary = self.paper_trader.get_performance_summary()
        logger.info(f"Total Trades: {trade_summary['total_trades']}")
        logger.info(f"Win Rate: {trade_summary['win_rate']:.1f}%")
        logger.info(f"Total P&L: ${trade_summary['total_profit']:.2f}")
        logger.info(f"ROI: {trade_summary['roi']:.2f}%")
        logger.info(f"Final Balance: ${trade_summary['current_balance']:.2f}")
        
        # Best/Worst trade
        if self.paper_trader.trades:
            closed_trades = [t for t in self.paper_trader.trades if t.status == "CLOSED" and t.actual_profit is not None]
            if closed_trades:
                best_trade = max(closed_trades, key=lambda t: t.actual_profit)
                worst_trade = min(closed_trades, key=lambda t: t.actual_profit)
                logger.info(f"Best Trade: ${best_trade.actual_profit:.2f}")
                logger.info(f"Worst Trade: ${worst_trade.actual_profit:.2f}")
        
        logger.info("=" * 60)

async def main():
    """Entry point"""
    # Improved configuration
    config = {
        'mode': 'PAPER_TRADING',
        'min_spread_percent': 0.05,     # Base minimum spread
        'trade_size_usdt': 1000,        # $1000 per trade
        'initial_balance': 10000,       # $10k starting balance
        'auto_trade': True,             # Automatically execute trades
        'max_open_trades': 3,           # Maximum concurrent trades
        'min_profit_usdt': 1.0,         # Minimum $1 profit to take trade
        'exit_strategy': 'spread_target' # Exit based on spread targets
    }
    
    bot = ImprovedArbitrageBot(config)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
