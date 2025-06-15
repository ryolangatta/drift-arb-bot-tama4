"""
Real-time performance monitoring and profitability analysis
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger

@dataclass
class PerformanceMetrics:
    """Key performance indicators for the bot"""
    # Trading metrics
    total_opportunities: int = 0
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    
    # Financial metrics
    total_gross_profit: float = 0.0
    total_fees_paid: float = 0.0
    total_net_profit: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Efficiency metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_profit_per_trade: float = 0.0
    roi_percentage: float = 0.0
    
    # Time metrics
    total_runtime_hours: float = 0.0
    trades_per_hour: float = 0.0
    opportunities_per_hour: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'trading': {
                'total_opportunities': self.total_opportunities,
                'total_trades': self.total_trades,
                'profitable_trades': self.profitable_trades,
                'losing_trades': self.losing_trades,
                'win_rate': round(self.win_rate, 2)
            },
            'financial': {
                'gross_profit': round(self.total_gross_profit, 2),
                'fees_paid': round(self.total_fees_paid, 2),
                'net_profit': round(self.total_net_profit, 2),
                'roi_percentage': round(self.roi_percentage, 2),
                'largest_win': round(self.largest_win, 2),
                'largest_loss': round(self.largest_loss, 2)
            },
            'efficiency': {
                'profit_factor': round(self.profit_factor, 2),
                'avg_profit_per_trade': round(self.average_profit_per_trade, 2),
                'trades_per_hour': round(self.trades_per_hour, 2),
                'opportunities_per_hour': round(self.opportunities_per_hour, 2)
            },
            'risk': {
                'max_drawdown': round(self.max_drawdown, 2),
                'current_drawdown': round(self.current_drawdown, 2),
                'sharpe_ratio': round(self.sharpe_ratio, 2)
            }
        }

class PerformanceMonitor:
    """Monitors and analyzes bot performance in real-time"""
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.metrics = PerformanceMetrics()
        self.start_time = datetime.utcnow()
        self.metrics_file = 'data/performance_metrics.json'
        self.hourly_snapshots = []
        self.balance_history = [initial_balance]
        self.peak_balance = initial_balance
        
        # Load existing metrics
        self.load_metrics()
        
    def load_metrics(self):
        """Load historical metrics from file"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    # Restore key metrics
                    if 'metrics' in data:
                        m = data['metrics']
                        self.metrics.total_opportunities = m.get('trading', {}).get('total_opportunities', 0)
                        self.metrics.total_trades = m.get('trading', {}).get('total_trades', 0)
                        # ... restore other metrics
                    logger.info("Loaded historical performance metrics")
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
            
    def save_metrics(self):
        """Save metrics to file"""
        try:
            os.makedirs('data', exist_ok=True)
            data = {
                'metrics': self.metrics.to_dict(),
                'hourly_snapshots': self.hourly_snapshots[-168:],  # Keep 1 week
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            
    def record_opportunity(self, spread: float, potential_profit: float):
        """Record an arbitrage opportunity"""
        self.metrics.total_opportunities += 1
        self.update_time_metrics()
        
    def record_trade(self, trade_result: Dict):
        """Record a completed trade"""
        self.metrics.total_trades += 1
        
        # Extract trade details
        net_profit = trade_result.get('net_profit', 0)
        fees = trade_result.get('fees', {}).get('total_fees', 0)
        
        # Update financial metrics
        self.metrics.total_fees_paid += fees
        self.metrics.total_net_profit += net_profit
        self.metrics.total_gross_profit += (net_profit + fees)
        
        # Update win/loss tracking
        if net_profit > 0:
            self.metrics.profitable_trades += 1
            self.metrics.largest_win = max(self.metrics.largest_win, net_profit)
        else:
            self.metrics.losing_trades += 1
            self.metrics.largest_loss = min(self.metrics.largest_loss, net_profit)
            
        # Update derived metrics
        self.update_derived_metrics()
        self.update_risk_metrics(net_profit)
        
        # Save after each trade
        self.save_metrics()
        
    def update_balance(self, new_balance: float):
        """Update current balance and track drawdown"""
        self.balance_history.append(new_balance)
        
        # Update peak balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
            
        # Calculate current drawdown
        if self.peak_balance > 0:
            self.metrics.current_drawdown = (self.peak_balance - new_balance) / self.peak_balance * 100
            self.metrics.max_drawdown = max(self.metrics.max_drawdown, self.metrics.current_drawdown)
            
    def update_derived_metrics(self):
        """Calculate derived metrics"""
        # Win rate
        if self.metrics.total_trades > 0:
            self.metrics.win_rate = (self.metrics.profitable_trades / self.metrics.total_trades) * 100
            self.metrics.average_profit_per_trade = self.metrics.total_net_profit / self.metrics.total_trades
            
        # Profit factor
        total_wins = self.metrics.profitable_trades * abs(self.metrics.largest_win) if self.metrics.largest_win else 0
        total_losses = self.metrics.losing_trades * abs(self.metrics.largest_loss) if self.metrics.largest_loss else 0
        
        if total_losses > 0:
            self.metrics.profit_factor = total_wins / total_losses
        else:
            self.metrics.profit_factor = total_wins
            
        # ROI
        if self.initial_balance > 0:
            current_balance = self.balance_history[-1] if self.balance_history else self.initial_balance
            self.metrics.roi_percentage = ((current_balance - self.initial_balance) / self.initial_balance) * 100
            
    def update_time_metrics(self):
        """Update time-based metrics"""
        runtime = datetime.utcnow() - self.start_time
        self.metrics.total_runtime_hours = runtime.total_seconds() / 3600
        
        if self.metrics.total_runtime_hours > 0:
            self.metrics.trades_per_hour = self.metrics.total_trades / self.metrics.total_runtime_hours
            self.metrics.opportunities_per_hour = self.metrics.total_opportunities / self.metrics.total_runtime_hours
            
    def update_risk_metrics(self, last_profit: float):
        """Update risk metrics including Sharpe ratio"""
        # Simple Sharpe ratio calculation
        if len(self.balance_history) > 2:
            returns = []
            for i in range(1, len(self.balance_history)):
                daily_return = (self.balance_history[i] - self.balance_history[i-1]) / self.balance_history[i-1]
                returns.append(daily_return)
                
            if returns:
                import numpy as np
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                
                if std_return > 0:
                    # Annualized Sharpe ratio (assuming 24/7 trading)
                    self.metrics.sharpe_ratio = (avg_return * 365) / (std_return * np.sqrt(365))
                    
    def take_hourly_snapshot(self):
        """Take a snapshot of current metrics"""
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': self.metrics.to_dict(),
            'balance': self.balance_history[-1] if self.balance_history else self.initial_balance
        }
        self.hourly_snapshots.append(snapshot)
        self.save_metrics()
        
    def get_profitability_report(self) -> Dict:
        """Generate comprehensive profitability report"""
        self.update_time_metrics()
        
        report = {
            'summary': {
                'is_profitable': self.metrics.total_net_profit > 0,
                'total_net_profit': round(self.metrics.total_net_profit, 2),
                'roi_percentage': round(self.metrics.roi_percentage, 2),
                'runtime_hours': round(self.metrics.total_runtime_hours, 2)
            },
            'profitability_analysis': {
                'profit_per_hour': round(self.metrics.total_net_profit / max(self.metrics.total_runtime_hours, 1), 2),
                'break_even_trades': self._calculate_breakeven_trades(),
                'projected_monthly_profit': self._project_monthly_profit(),
                'risk_adjusted_return': round(self.metrics.sharpe_ratio * self.metrics.roi_percentage, 2)
            },
            'recommendations': self._generate_recommendations(),
            'detailed_metrics': self.metrics.to_dict()
        }
        
        return report
        
    def _calculate_breakeven_trades(self) -> int:
        """Calculate how many trades needed to break even"""
        if self.metrics.average_profit_per_trade > 0:
            if self.metrics.total_net_profit < 0:
                return int(abs(self.metrics.total_net_profit) / self.metrics.average_profit_per_trade) + 1
        return 0
        
    def _project_monthly_profit(self) -> float:
        """Project monthly profit based on current performance"""
        if self.metrics.total_runtime_hours > 0:
            hourly_profit = self.metrics.total_net_profit / self.metrics.total_runtime_hours
            return round(hourly_profit * 24 * 30, 2)  # 30 days
        return 0.0
        
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Profitability check
        if self.metrics.total_net_profit < 0:
            recommendations.append("⚠️ Bot is currently unprofitable. Consider adjusting spread thresholds.")
        else:
            recommendations.append("✅ Bot is profitable! Current strategy is working.")
            
        # Win rate analysis
        if self.metrics.win_rate < 40:
            recommendations.append("📉 Low win rate. Consider increasing minimum spread threshold.")
        elif self.metrics.win_rate > 70:
            recommendations.append("📈 High win rate! You might lower spread threshold for more opportunities.")
            
        # Trade frequency
        if self.metrics.trades_per_hour < 0.5:
            recommendations.append("🐌 Low trade frequency. Consider monitoring more pairs or lowering thresholds.")
        elif self.metrics.trades_per_hour > 5:
            recommendations.append("⚡ High trade frequency. Monitor for slippage and execution issues.")
            
        # Risk management
        if self.metrics.max_drawdown > 10:
            recommendations.append("⚠️ High drawdown detected. Implement stricter risk management.")
            
        # Efficiency
        if self.metrics.total_fees_paid > abs(self.metrics.total_gross_profit) * 0.5:
            recommendations.append("💸 Fees consuming >50% of profits. Consider larger trade sizes.")
            
        return recommendations
