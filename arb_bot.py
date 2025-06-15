"""
Complete arbitrage bot with paper trading
"""
import asyncio
import json
from typing import Dict
from modules.price_monitor import PriceMonitor
from modules.arbitrage import ArbitrageDetector
from modules.paper_trader import PaperTrader
from core.logger import logger

class ArbitrageBotComplete:
    """Complete arbitrage bot with all features"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.price_monitor = PriceMonitor(config)
        self.arb_detector = ArbitrageDetector(config)
        self.paper_trader = PaperTrader(config)
        self.running = True
        self.auto_trade = config.get('auto_trade', True)
        
    async def price_callback(self, spot_symbol: str, perp_symbol: str, 
                           spot_price: float, perp_price: float):
        """Handle new prices and check for arbitrage"""
        
        # Calculate spread for logging
        spread = ((perp_price - spot_price) / spot_price) * 100
        
        # Check for arbitrage opportunity
        opportunity = self.arb_detector.check_opportunity(
            spot_symbol, perp_symbol, spot_price, perp_price
        )
        
        if opportunity:
            # Execute paper trade if auto-trading is enabled
            if self.auto_trade:
                trade = self.paper_trader.execute_trade(opportunity.to_dict())
                
                # Simulate closing the trade after a delay (in real trading, you'd monitor for exit conditions)
                if trade and self.config.get('auto_close', True):
                    asyncio.create_task(self.auto_close_trade(trade.id, 30))  # Close after 30 seconds
        else:
            # Regular price update (no opportunity)
            status = f"Spread: {spread:.3f}% | Min required: {self.config['min_spread_percent'] + 0.15:.3f}%"
            logger.debug(f"{spot_symbol}: ${spot_price:.2f} | {status}")
            
    async def auto_close_trade(self, trade_id: int, delay_seconds: int):
        """Automatically close a trade after delay (for simulation)"""
        await asyncio.sleep(delay_seconds)
        
        # Get current prices for closing
        trade = self.paper_trader.open_trades.get(trade_id)
        if trade:
            # Get latest prices
            spot_price = self.price_monitor.last_prices.get('binance', {}).get(trade.spot_symbol, {}).get('price')
            perp_price = self.price_monitor.last_prices.get('drift', {}).get(trade.perp_symbol, {}).get('price')
            
            if spot_price and perp_price:
                self.paper_trader.close_trade(trade_id, spot_price, perp_price)
                
    async def run(self):
        """Run the bot"""
        try:
            # Initialize price monitor
            await self.price_monitor.initialize()
            
            # Log configuration
            logger.info("=" * 60)
            logger.info("🚀 DRIFT-BINANCE ARBITRAGE BOT STARTED")
            logger.info("=" * 60)
            logger.info(f"Mode: {self.config['mode']}")
            logger.info(f"Auto Trade: {self.auto_trade}")
            logger.info(f"Min Spread: {self.config['min_spread_percent']}%")
            logger.info(f"Trade Size: ${self.config['trade_size_usdt']}")
            logger.info(f"Initial Balance: ${self.paper_trader.initial_balance}")
            logger.info(f"Current Balance: ${self.paper_trader.balance:.2f}")
            
            # Show performance if we have previous trades
            perf = self.paper_trader.get_performance_summary()
            if perf['total_trades'] > 0:
                logger.info(f"Previous Trades: {perf['total_trades']} (P&L: ${perf['total_profit']:.2f})")
            
            logger.info("=" * 60)
            
            # Define pairs to monitor
            pairs = [
                {"spot_symbol": "SOLUSDT", "perp_symbol": "SOLPERP"},
                # {"spot_symbol": "BTCUSDT", "perp_symbol": "BTCPERP"},
                # {"spot_symbol": "ETHUSDT", "perp_symbol": "ETHPERP"},
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
        
        # Print final summary
        logger.info("=" * 60)
        logger.info("📊 FINAL SESSION SUMMARY")
        logger.info("=" * 60)
        
        # Arbitrage summary
        arb_summary = self.arb_detector.get_summary()
        logger.info(f"Opportunities Found: {arb_summary['total_opportunities']}")
        logger.info(f"Total Potential Profits: ${arb_summary['potential_profits']:.2f}")
        
        # Trading summary
        trade_summary = self.paper_trader.get_performance_summary()
        logger.info(f"Trades Executed: {trade_summary['total_trades']}")
        logger.info(f"Closed Trades: {trade_summary['closed_trades']}")
        logger.info(f"Open Trades: {trade_summary['open_trades']}")
        logger.info(f"Total P&L: ${trade_summary['total_profit']:.2f}")
        logger.info(f"Win Rate: {trade_summary['win_rate']:.1f}%")
        logger.info(f"ROI: {trade_summary['roi']:.2f}%")
        logger.info(f"Final Balance: ${trade_summary['current_balance']:.2f}")
        logger.info("=" * 60)

async def main():
    """Entry point"""
    # Configuration
    config = {
        'mode': 'PAPER_TRADING',
        'min_spread_percent': 0.05,     # 0.05% minimum spread
        'trade_size_usdt': 1000,        # $1000 per trade
        'initial_balance': 10000,       # $10k starting balance
        'auto_trade': True,             # Automatically execute trades
        'auto_close': True,             # Auto-close trades after delay
    }
    
    bot = ArbitrageBotComplete(config)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
