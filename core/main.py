"""
Production-ready Drift-Binance Arbitrage Bot
With integrated performance monitoring and profitability analysis
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
from modules.discord_notifier import DiscordNotifier
from modules.performance_monitor import PerformanceMonitor

class DriftBinanceArbBot:
    """Main arbitrage bot class with full monitoring"""
    
    def __init__(self):
        self.bot_config = get_config()
        self.config = self.convert_config()
        self.price_monitor = PriceMonitor(self.config)
        self.arb_detector = ArbitrageDetector(self.config)
        self.paper_trader = None
        self.discord = None
        self.performance = None
        self.running = True
        self.last_notification_time = {}
        self.last_performance_report = 0
        
        # Initialize paper trader if in simulation mode
        if self.bot_config.mode in ['SIMULATION', 'PAPER_TRADING']:
            self.paper_trader = PaperTrader(self.config)
            
        # Initialize Discord notifier
        if self.bot_config.discord_webhook_url:
            self.discord = DiscordNotifier(self.bot_config.discord_webhook_url)
            
        # Initialize performance monitor
        initial_balance = self.paper_trader.initial_balance if self.paper_trader else 10000
        self.performance = PerformanceMonitor(initial_balance)
            
    def convert_config(self) -> Dict:
        """Convert BotConfig to dict format expected by modules"""
        return {
            'mode': self.bot_config.mode.value,
            'min_spread_percent': self.bot_config.spread_threshold * 100,
            'trade_size_usdt': self.bot_config.trade_size_usdc,
            'initial_balance': 10000,
            'max_open_trades': self.bot_config.max_open_positions,
            'min_profit_usdt': float(os.getenv('MIN_PROFIT_USDT', '0.05')),
            'discord_webhook': self.bot_config.discord_webhook_url,
            'pairs': self.get_trading_pairs()
        }
        
    def get_trading_pairs(self) -> list:
        """Get trading pairs configuration"""
        return [
            {"spot_symbol": "SOLUSDT", "perp_symbol": "SOLPERP"},
        ]
        
    def should_notify(self, event_type: str, cooldown_seconds: int = 60) -> bool:
        """Check if we should send a notification (with cooldown)"""
        import time
        current_time = time.time()
        last_time = self.last_notification_time.get(event_type, 0)
        
        if current_time - last_time > cooldown_seconds:
            self.last_notification_time[event_type] = current_time
            return True
        return False
        
    async def send_performance_report(self):
        """Send performance report to Discord"""
        if not self.discord:
            return
            
        report = self.performance.get_profitability_report()
        
        # Create Discord embed
        is_profitable = report['summary']['is_profitable']
        color = 0x00ff00 if is_profitable else 0xff0000
        
        fields = [
            {"name": "💰 Net Profit", "value": f"${report['summary']['total_net_profit']}", "inline": True},
            {"name": "📊 ROI", "value": f"{report['summary']['roi_percentage']}%", "inline": True},
            {"name": "⏱️ Runtime", "value": f"{report['summary']['runtime_hours']:.1f}h", "inline": True},
            {"name": "📈 Win Rate", "value": f"{self.performance.metrics.win_rate:.1f}%", "inline": True},
            {"name": "🎯 Total Trades", "value": str(self.performance.metrics.total_trades), "inline": True},
            {"name": "💵 Profit/Hour", "value": f"${report['profitability_analysis']['profit_per_hour']}", "inline": True}
        ]
        
        # Add recommendations
        recommendations = "\n".join(report['recommendations'][:3])  # Top 3 recommendations
        
        await self.discord.send_embed(
            title="🤖 Bot Profitability Report",
            description=f"**Status: {'PROFITABLE' if is_profitable else 'UNPROFITABLE'}**\n\n{recommendations}",
            color=color,
            fields=fields
        )
            
    async def price_callback(self, spot_symbol: str, perp_symbol: str, 
                           spot_price: float, perp_price: float):
        """Handle price updates with performance tracking"""
        
        # Check for arbitrage
        opportunity = self.arb_detector.check_opportunity(
            spot_symbol, perp_symbol, spot_price, perp_price
        )
        
        if opportunity:
            # Record opportunity in performance monitor
            self.performance.record_opportunity(
                opportunity.spread_percent,
                opportunity.potential_profit_usdt
            )
            
            logger.success(
                f"🎯 Arbitrage on {spot_symbol}: "
                f"Spread {opportunity.spread_percent:.3f}% = "
                f"${opportunity.potential_profit_usdt:.2f} profit"
            )
            
            # Send Discord notification
            if self.discord and self.should_notify('opportunity', cooldown_seconds=60):
                await self.discord.send_opportunity_alert(opportunity.to_dict())
            
            # Execute paper trade if enabled
            if self.paper_trader and len(self.paper_trader.open_trades) < self.config['max_open_trades']:
                if opportunity.potential_profit_usdt >= self.config['min_profit_usdt']:
                    trade = self.paper_trader.execute_trade(opportunity.to_dict())
                    
                    if trade:
                        # Notify about trade execution
                        if self.discord:
                            await self.discord.send_trade_notification(trade.__dict__, "opened")
                            
        # Send periodic performance reports (every hour)
        import time
        current_time = time.time()
        if current_time - self.last_performance_report > 3600:  # 1 hour
            self.last_performance_report = current_time
            self.performance.take_hourly_snapshot()
            
            if self.discord and self.performance.metrics.total_trades > 0:
                await self.send_performance_report()
                    
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
        logger.info(f"Discord: {'Enabled' if self.discord else 'Disabled'}")
        logger.info(f"Performance Tracking: Enabled")
        
        if self.paper_trader:
            logger.info(f"Paper Trading Balance: ${self.paper_trader.balance:.2f}")
            # Update performance monitor with current balance
            self.performance.update_balance(self.paper_trader.balance)
            
        logger.info("=" * 60)
        
        # Show initial profitability status
        report = self.performance.get_profitability_report()
        logger.info(f"Current Status: {'PROFITABLE' if report['summary']['is_profitable'] else 'UNPROFITABLE'}")
        logger.info(f"Total P&L: ${report['summary']['total_net_profit']}")
        logger.info("=" * 60)
        
        try:
            # Initialize connections
            await self.price_monitor.initialize()
            
            # Send startup notification
            if self.discord:
                await self.discord.send_startup_notification(self.config)
                logger.info("Discord startup notification sent")
            
            # Start monitoring
            await self.price_monitor.start(self.config['pairs'], self.price_callback)
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
            if self.discord:
                await self.discord.send_message(f"❌ Bot error: {str(e)}")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Graceful shutdown with final profitability report"""
        logger.info("Shutting down...")
        
        self.running = False
        await self.price_monitor.stop()
        
        # Update performance metrics with closed trades
        if self.paper_trader:
            for trade in self.paper_trader.trades:
                if trade.status == "CLOSED" and hasattr(trade, 'actual_profit'):
                    trade_result = {
                        'net_profit': trade.actual_profit,
                        'fees': {'total_fees': abs(trade.actual_profit - trade.expected_profit)}
                    }
                    self.performance.record_trade(trade_result)
                    
            # Update final balance
            self.performance.update_balance(self.paper_trader.balance)
        
        # Generate final profitability report
        final_report = self.performance.get_profitability_report()
        
        # Show final stats
        logger.info("=" * 60)
        logger.info("📊 FINAL PROFITABILITY REPORT")
        logger.info("=" * 60)
        logger.info(f"Bot Status: {'PROFITABLE' if final_report['summary']['is_profitable'] else 'UNPROFITABLE'}")
        logger.info(f"Total Net Profit: ${final_report['summary']['total_net_profit']}")
        logger.info(f"ROI: {final_report['summary']['roi_percentage']}%")
        logger.info(f"Total Runtime: {final_report['summary']['runtime_hours']:.1f} hours")
        logger.info(f"Profit per Hour: ${final_report['profitability_analysis']['profit_per_hour']}")
        logger.info(f"Projected Monthly: ${final_report['profitability_analysis']['projected_monthly_profit']}")
        
        logger.info("\n📋 RECOMMENDATIONS:")
        for rec in final_report['recommendations']:
            logger.info(f"  {rec}")
            
        logger.info("=" * 60)
        
        # Send final report to Discord
        if self.discord:
            await self.send_performance_report()
            await self.discord.send_message(
                f"🛑 Bot stopped. Final status: {'PROFITABLE ✅' if final_report['summary']['is_profitable'] else 'UNPROFITABLE ❌'}\n"
                f"Net P&L: ${final_report['summary']['total_net_profit']}"
            )
            await self.discord.close()
            
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
