"""
Alert System

Sends notifications through various channels.
"""

from typing import Dict, Optional
from datetime import datetime
import aiohttp

from core.logger import get_logger


class AlertManager:
    """
    Manages alerts and notifications.
    
    Supports:
    - Discord webhooks
    - Email (future)
    - Telegram (future)
    """
    
    def __init__(self, config: dict):
        """Initialize alert manager."""
        self.config = config
        self.logger = get_logger(__name__)
        self.discord_webhook = config.get("discord_webhook_url")
        
    async def send_trade_alert(
        self,
        trade_info: Dict
    ) -> bool:
        """Send trade execution alert."""
        message = f"🎯 Trade Executed\n"
        message += f"Symbol: {trade_info.get('symbol')}\n"
        message += f"Profit: ${trade_info.get('profit', 0):.2f}"
        
        return await self.send_discord(message)
    
    async def send_error_alert(
        self,
        error: str,
        critical: bool = False
    ) -> bool:
        """Send error alert."""
        emoji = "🚨" if critical else "⚠️"
        message = f"{emoji} Error: {error}"
        
        return await self.send_discord(message)
    
    async def send_daily_report(
        self,
        metrics: Dict
    ) -> bool:
        """Send daily performance report."""
        message = f"📊 Daily Report\n"
        message += f"ROI: {metrics.get('roi', 0):.2f}%\n"
        message += f"Trades: {metrics.get('trades', 0)}\n"
        message += f"Profit: ${metrics.get('profit', 0):.2f}"
        
        return await self.send_discord(message)
    
    async def send_discord(
        self,
        message: str
    ) -> bool:
        """Send message to Discord."""
        if not self.discord_webhook:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "content": message,
                    "username": "Arbitrage Bot"
                }
                async with session.post(
                    self.discord_webhook,
                    json=payload
                ) as response:
                    return response.status == 204
        except Exception as e:
            self.logger.error(f"Failed to send Discord alert: {e}")
            return False
