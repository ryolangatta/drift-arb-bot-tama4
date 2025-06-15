"""
Price monitoring for Binance spot and Drift perps
Professional grade with proper error handling
"""
import asyncio
import aiohttp
from typing import Dict, Optional, Callable
from datetime import datetime
from loguru import logger

class PriceMonitor:
    """Monitors prices from Binance spot and Drift perps"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.running = False
        self.price_callback = None
        self.last_prices = {
            'binance': {},
            'drift': {}
        }
        self.session = None
        
    async def initialize(self):
        """Initialize connections"""
        try:
            logger.info("Price monitor initializing...")
            
            # Create aiohttp session for API calls
            self.session = aiohttp.ClientSession()
            
            # Test Binance connection
            await self.test_binance_connection()
            
            logger.info("Price monitor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize price monitor: {e}")
            raise
            
    async def test_binance_connection(self):
        """Test Binance API connection"""
        try:
            async with self.session.get('https://api.binance.com/api/v3/ping') as response:
                if response.status == 200:
                    logger.info("Binance connection verified")
                else:
                    raise Exception(f"Binance ping failed: {response.status}")
        except Exception as e:
            logger.error(f"Binance connection test failed: {e}")
            raise
            
    async def get_binance_price(self, symbol: str) -> Optional[float]:
        """Get spot price from Binance using REST API"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    
                    self.last_prices['binance'][symbol] = {
                        'price': price,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    return price
                else:
                    logger.error(f"Binance API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Binance price for {symbol}: {e}")
            return None
            
    async def get_drift_price(self, symbol: str) -> Optional[float]:
        """Get perp price from Drift (simulated for now)"""
        try:
            # Map Drift symbol to Binance symbol for simulation
            base_symbol = symbol.replace('PERP', 'USDT')
            spot_price = self.last_prices['binance'].get(base_symbol, {}).get('price')
            
            if not spot_price:
                # Get fresh spot price if not cached
                spot_price = await self.get_binance_price(base_symbol)
            
            if spot_price:
                # Simulate realistic perp premium (0.05% to 0.3%)
                import random
                premium = 1 + (random.uniform(0.0005, 0.003))
                perp_price = spot_price * premium
                
                self.last_prices['drift'][symbol] = {
                    'price': perp_price,
                    'timestamp': datetime.utcnow().isoformat(),
                    'simulated': True
                }
                
                return perp_price
                
        except Exception as e:
            logger.error(f"Error getting Drift price: {e}")
            
        return None
        
    async def monitor_pair(self, spot_symbol: str, perp_symbol: str):
        """Monitor a trading pair for arbitrage"""
        while self.running:
            try:
                # Get spot price first
                spot_price = await self.get_binance_price(spot_symbol)
                
                # Then get perp price (which uses cached spot for simulation)
                perp_price = await self.get_drift_price(perp_symbol)
                
                if spot_price and perp_price and self.price_callback:
                    await self.price_callback(
                        spot_symbol=spot_symbol,
                        perp_symbol=perp_symbol,
                        spot_price=spot_price,
                        perp_price=perp_price
                    )
                    
                # Rate limit: 2 second intervals (Binance allows 1200 requests/min)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)  # Back off on error
                
    async def start(self, pairs: list, callback: Callable):
        """Start monitoring multiple pairs"""
        self.price_callback = callback
        self.running = True
        
        # Create monitoring tasks for each pair
        tasks = []
        for pair_config in pairs:
            task = asyncio.create_task(
                self.monitor_pair(
                    pair_config['spot_symbol'],
                    pair_config['perp_symbol']
                )
            )
            tasks.append(task)
            
        logger.info(f"Started monitoring {len(pairs)} pairs")
        
        try:
            # Wait for all tasks
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Monitor tasks cancelled")
            
    async def stop(self):
        """Stop monitoring"""
        self.running = False
        
        # Close aiohttp session
        if self.session:
            await self.session.close()
            
        logger.info("Price monitor stopped")
