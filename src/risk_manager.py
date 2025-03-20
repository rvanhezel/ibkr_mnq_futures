import datetime
import pytz
import pandas as pd
import os


class RiskManager:
    def __init__(self, 
                 timezone, 
                 trading_start_time, 
                 trading_end_time, 
                 max_24h_loss, 
                 trading_pause_hours, 
                 mnq_tick_size,
                 stop_loss_ticks, 
                 take_profit_ticks):        
        self.timezone = timezone
        self.trading_start = pd.to_datetime(trading_start_time, format='%H%M').time()
        self.trading_end = pd.to_datetime(trading_end_time, format='%H%M').time()
        self.max_24h_loss = max_24h_loss
        self.trading_pause_hours = trading_pause_hours
        self.mnq_tick_size = mnq_tick_size
        self.stop_loss_ticks = stop_loss_ticks
        self.take_profit_ticks = take_profit_ticks

        self.trades_history = []
        self.pause_start_time = None
        self.pause_end_time = None
        
    def add_trade(self, trade_time, pnl):
        """Add a trade to the history"""
        self.trades_history.append({
            'time': trade_time,
            'pnl': pnl
        })
        self._cleanup_old_trades()
        
    def _cleanup_old_trades(self):
        """Remove trades older than 24 hours"""
        now = pd.Timestamp.now(tz=self.timezone)
        cutoff = now - pd.Timedelta(hours=24)
        
        self.trades_history = [
            trade for trade in self.trades_history
            if trade['time'] > cutoff
        ]
        
    def get_24h_pnl(self):
        """Calculate total P&L for the last 24 hours"""
        return sum(trade['pnl'] for trade in self.trades_history)
    
    def should_pause_trading(self, num_positions, pnl_details):
        """Check if trading should be paused based on daily PnL"""
        if pnl_details['unrealized_pnl'] <= -self.max_24h_loss * num_positions:
            return True
        return False

    def get_pause_end_time(self):
        """Get the time when trading can resume"""
        if self.pause_start is None:
            return None
        return self.pause_start + pd.Timedelta(hours=self.trading_pause_hours)

    def can_resume_trading(self):
        """Check if trading can resume after pause"""
        if self.pause_start is None:
            return True
        pause_end = self.get_pause_end_time()
        if pd.Timestamp.now(tz=self.timezone) >= pause_end:
            self.pause_start = None
            return True
        return False
    
    def is_trading_hours(self):
        """Check if current time is within trading hours"""
        now = pd.Timestamp.now(tz=self.timezone)
        current_time = now.time()
        
        # Trading hours are generally from 9 PM to 4 PM EST next day
        if self.trading_start < self.trading_end:
            return self.trading_start <= current_time < self.trading_end
        else:
            return not self.trading_end <= current_time < self.trading_start
            
    def is_trading_day(self):
        """Check if today is a trading day (Sunday through Friday)"""
        now = pd.Timestamp.now(tz=self.timezone)
        weekday = now.weekday()
        
        # Sunday through Friday (6-4)
        if 0 <= weekday <= 4 or (weekday == 6 and now.time() >= self.trading_start):
            return True
            
        return False

    def calculate_stop_loss_price(self, entry_price):
        """Calculate stop loss price based on ticks"""
        return entry_price - (self.stop_loss_ticks * self.mnq_tick_size)

    def calculate_take_profit_price(self, entry_price):
        """Calculate take profit price based on ticks"""
        return entry_price + (self.take_profit_ticks * self.mnq_tick_size) 