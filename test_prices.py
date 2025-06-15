import asyncio
import json
from typing import Dict
from modules.price_monitor import PriceMonitor
from modules.arbitrage import ArbitrageDetector
from core.logger import logger

class ArbBot:
    """Main arbitrage bot combining price monitoring and detection"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.price_monitor = PriceMonitor(config)
        self.arb_detector = ArbitrageDetector(config)
        self.running = True
        
    async def price_callback(self, spot_symbol: str, perp_symbol: str, 
                           spot_price: float, perp_price: float):
        """Handle new prices and check for arbitrage"""
        
        # Calculate spread for logging
        spread = ((perp_price - spot_price) / spot_price) * 100
        
        # Log current prices (with emoji indicators)
        emoji = "🟢" if spread > 0.15 else "🔴"
        logger.info(
            f"{emoji} {spot_symbol}: ${spot_price:.2f} | "
            f"{perp_symbol}: ${perp_price:.2f} | "
            f"Spread: {spread:.3f}% | "
            f"Net after fees: {spread - 0.15:.3f}%"
        )
        
        # Check for arbitrage opportunity
        opportunity = self.arb_detector.check_opportunity(
            spot_symbol, perp_symbol, spot_price, perp_price
        )
        
        if opportunity:
            # Log opportunity details
            logger.success(f"💰 PROFIT OPPORTUNITY: ${opportunity.potential_profit_usdt:.2f} on ${opportunity.trade_size_usdt} trade")
            
    async def run(self):
        """Run the bot"""
        try:
            # Initialize price monitor
            await self.price_monitor.initialize()
            
            # Log configuration
            logger.info("=" * 50)
            logger.info("ARBITRAGE BOT CONFIGURATION")
            logger.info(f"Mode: {self.config['mode']}")
            logger.info(f"Min Spread: {self.config['min_spread_percent']}%")
            logger.info(f"Trade Size: ${self.config['trade_size_usdt']}")
            logger.info(f"Binance Fee: 0.10%")
            logger.info(f"Drift Fee: 0.05%")
            logger.info(f"Total Fees: 0.15%")
            logger.info(f"Required Spread for Profit: >{self.config['min_spread_percent'] + 0.15}%")
            logger.info("=" * 50)
            
            # Define pairs to monitor
            pairs = [
                {"spot_symbol": "SOLUSDT", "perp_symbol": "SOLPERP"},
                # Add more pairs here if needed
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
        
        # Print summary
        summary = self.arb_detector.get_summary()
        logger.info("=" * 50)
        logger.info("SESSION SUMMARY")
        logger.info(f"Total opportunities found: {summary['total_opportunities']}")
        logger.info(f"Potential profits: ${summary['potential_profits']:.2f}")
        if summary['best_opportunity']:
            best = summary['best_opportunity']
            logger.info(f"Best opportunity: {best['spread_percent']:.3f}% spread = ${best['potential_profit_usdt']:.2f} profit")
        logger.info("=" * 50)

async def main():
    """Entry point"""
    # Configuration
    config = {
        'mode': 'SIMULATION',
        'min_spread_percent': 0.05,  # Lowered to 0.05% to see more opportunities
        'trade_size_usdt': 1000,     # $1000 per trade
    }
    
    bot = ArbBot(config)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
