"""
Production-ready Drift-Binance Arbitrage Bot
Entry point for the application
"""
import asyncio
import sys
import os
from typing import Dict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_config
from core.logger import logger
from modules.price_monitor import PriceMonitor
from modules.arbitrage import ArbitrageDetector
from modules.paper_trader import PaperTrader

class DriftBinanceArbBot:
    """Main arbitrage bot class"""
    
    def __init__(self):
        self.bot_config = get_config()
        self.config = self.convert_config()
        self.price_monitor = PriceMonitor(self.config)
        self.arb_detector = ArbitrageDetector(self.config)
        self.paper_trader = None
        self.running = True
        
        # Initialize paper trader if in simulation mode
        if self.bot_config.mode in ['SIMULATION', 'PAPER_TRADING']:
            self.paper_trader = PaperTrader(self.config)
            
    def convert_config(self) -> Dict:
        """Convert BotConfig to dict format expected by modules"""
        return {
            'mode': self.bot_config.mode.value,
            'min_spread_percent': self.bot_config.spread_threshold * 100,  # Convert to percentage
            'trade_size_usdt': self.bot_config.trade_size_usdc,
            'initial_balance': 10000,  # Default for paper trading
            'max_open_trades': self.bot_config.max_open_positions,
            'min_profit_usdt': 1.0,  # Default minimum profit
            'discord_webhook': self.bot_config.discord_webhook_url,
            'pairs': self.get_trading_pairs()
        }
        
    def get_trading_pairs(self) -> list:
        """Get trading pairs configuration"""
        # For now, use default pairs. Can be extended to read from env
        return [
            {"spot_symbol": "SOLUSDT", "perp_symbol": "SOLPERP"},
            # {"spot_symbol": "BTCUSDT", "perp_symbol": "BTCPERP"},
            # {"spot_symbol": "ETHUSDT", "perp_symbol": "ETHPERP"},
        ]
            
    async def price_callback(self, spot_symbol: str, perp_symbol: str, 
                           spot_price: float, perp_price: float):
        """Handle price updates"""
        
        # Check for arbitrage
        opportunity = self.arb_detector.check_opportunity(
            spot_symbol, perp_symbol, spot_price, perp_price
        )
        
        if opportunity:
            logger.success(
                f"🎯 Arbitrage on {spot_symbol}: "
                f"Spread {opportunity.spread_percent:.3f}% = "
                f"${opportunity.potential_profit_usdt:.2f} profit"
            )
            
            # Execute paper trade if enabled
            if self.paper_trader and len(self.paper_trader.open_trades) < self.config['max_open_trades']:
                if opportunity.potential_profit_usdt >= self.config['min_profit_usdt']:
                    self.paper_trader.execute_trade(opportunity.to_dict())
                    
    async def run(self):
        """Main bot loop"""
        logger.info("=" * 60)
        logger.info("🚀 DRIFT-BINANCE ARBITRAGE BOT")
        logger.info("=" * 60)
        logger.info(f"Mode: {self.bot_config.mode}")
        logger.info(f"Min Spread: {self.bot_config.spread_threshold * 100:.1f}%")
        logger.info(f"Trade Size: ${self.bot_config.trade_size_usdc}")
        logger.info(f"Max Positions: {self.bot_config.max_open_positions}")
        logger.info(f"Monitoring {len(self.config['pairs'])} pairs")
        
        if self.paper_trader:
            logger.info(f"Paper Trading Balance: ${self.paper_trader.balance:.2f}")
            
        logger.info("=" * 60)
        
        try:
            # Initialize connections
            await self.price_monitor.initialize()
            
            # Start monitoring
            await self.price_monitor.start(self.config['pairs'], self.price_callback)
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down...")
        
        self.running = False
        await self.price_monitor.stop()
        
        # Show final stats
        if self.paper_trader:
            stats = self.paper_trader.get_performance_summary()
            logger.info("=" * 60)
            logger.info("📊 SESSION SUMMARY")
            logger.info(f"Total Trades: {stats['total_trades']}")
            logger.info(f"P&L: ${stats['total_profit']:.2f}")
            logger.info(f"ROI: {stats['roi']:.2f}%")
            logger.info(f"Final Balance: ${stats['current_balance']:.2f}")
            logger.info("=" * 60)
            
        logger.info("Shutdown complete")

def main():
    """Entry point"""
    try:
        bot = DriftBinanceArbBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
