"""
Discord webhook notifications for the arbitrage bot
"""
import aiohttp
import json
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

class DiscordNotifier:
    """Handles Discord webhook notifications"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
        self.session = None
        
        if self.enabled:
            logger.info("Discord notifications enabled")
        else:
            logger.warning("Discord webhook URL not configured - notifications disabled")
    
    async def initialize(self):
        """Initialize aiohttp session"""
        if self.enabled and not self.session:
            self.session = aiohttp.ClientSession()
    
    async def send_message(self, content: str, username: str = "Arbitrage Bot") -> bool:
        """Send a simple text message to Discord"""
        if not self.enabled:
            return False
            
        try:
            if not self.session:
                await self.initialize()
                
            payload = {
                "content": content,
                "username": username
            }
            
            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.debug("Discord message sent successfully")
                    return True
                else:
                    logger.error(f"Discord webhook failed: {response.status}")
                    text = await response.text()
                    logger.error(f"Response: {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return False
    
    async def send_embed(self, title: str, description: str, color: int = 0x00ff00, 
                        fields: Optional[list] = None, username: str = "Arbitrage Bot") -> bool:
        """Send an embedded message to Discord"""
        if not self.enabled:
            return False
            
        try:
            if not self.session:
                await self.initialize()
                
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Drift-Binance Arbitrage Bot"
                }
            }
            
            if fields:
                embed["fields"] = fields
                
            payload = {
                "username": username,
                "embeds": [embed]
            }
            
            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.debug("Discord embed sent successfully")
                    return True
                else:
                    logger.error(f"Discord webhook failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Discord embed: {e}")
            return False
    
    async def send_startup_notification(self, config: Dict) -> bool:
        """Send bot startup notification"""
        fields = [
            {"name": "Mode", "value": config.get('mode', 'Unknown'), "inline": True},
            {"name": "Min Spread", "value": f"{config.get('min_spread_percent', 0)}%", "inline": True},
            {"name": "Trade Size", "value": f"${config.get('trade_size_usdt', 0)}", "inline": True}
        ]
        
        return await self.send_embed(
            title="🚀 Arbitrage Bot Started",
            description="Bot is now monitoring for arbitrage opportunities",
            color=0x00ff00,
            fields=fields
        )
    
    async def send_opportunity_alert(self, opportunity: Dict) -> bool:
        """Send arbitrage opportunity alert"""
        fields = [
            {"name": "Pair", "value": opportunity.get('spot_symbol', 'Unknown'), "inline": True},
            {"name": "Spread", "value": f"{opportunity.get('spread_percent', 0):.3f}%", "inline": True},
            {"name": "Profit", "value": f"${opportunity.get('potential_profit_usdt', 0):.2f}", "inline": True}
        ]
        
        return await self.send_embed(
            title="🎯 Arbitrage Opportunity Detected!",
            description=f"Profitable spread found on {opportunity.get('spot_symbol', 'Unknown')}",
            color=0xffa500,  # Orange
            fields=fields
        )
    
    async def send_trade_notification(self, trade: Dict, action: str = "opened") -> bool:
        """Send trade execution notification"""
        if action == "opened":
            title = "📈 Trade Opened"
            color = 0x00ff00  # Green
        else:
            title = "📉 Trade Closed"
            color = 0xff0000 if trade.get('actual_profit', 0) < 0 else 0x00ff00
            
        fields = [
            {"name": "Trade ID", "value": f"#{trade.get('id', 'Unknown')}", "inline": True},
            {"name": "Size", "value": f"${trade.get('trade_size_usdt', 0)}", "inline": True}
        ]
        
        if action == "closed":
            fields.append({
                "name": "P&L", 
                "value": f"${trade.get('actual_profit', 0):.2f}", 
                "inline": True
            })
            
        return await self.send_embed(
            title=title,
            description=f"Trade {action} for {trade.get('spot_symbol', 'Unknown')}",
            color=color,
            fields=fields
        )
    
    async def send_summary(self, stats: Dict) -> bool:
        """Send performance summary"""
        fields = [
            {"name": "Total Trades", "value": str(stats.get('total_trades', 0)), "inline": True},
            {"name": "Win Rate", "value": f"{stats.get('win_rate', 0):.1f}%", "inline": True},
            {"name": "Total P&L", "value": f"${stats.get('total_profit', 0):.2f}", "inline": True},
            {"name": "ROI", "value": f"{stats.get('roi', 0):.2f}%", "inline": True},
            {"name": "Current Balance", "value": f"${stats.get('current_balance', 0):.2f}", "inline": True}
        ]
        
        return await self.send_embed(
            title="📊 Performance Summary",
            description="Current trading session statistics",
            color=0x0099ff,  # Blue
            fields=fields
        )
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
