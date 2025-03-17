import datetime
import pytz
from config_loader import config



class RiskManager:
    def __init__(self):
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
        now = datetime.datetime.now(TIMEZONE)
        cutoff = now - datetime.timedelta(hours=24)
        
        self.trades_history = [
            trade for trade in self.trades_history
            if trade['time'] > cutoff
        ]
        
    def get_24h_pnl(self):
        """Calculate total P&L for the last 24 hours"""
        return sum(trade['pnl'] for trade in self.trades_history)
    
    def should_pause_trading(self):
        """Check if trading should be paused based on 24h losses"""
        # If already paused, check if pause period is over
        if self.is_paused():
            return True
            
        # Check if losses exceed threshold
        total_pnl = self.get_24h_pnl()
        if total_pnl < -MAX_24H_LOSS:
            self.pause_start_time = datetime.datetime.now(TIMEZONE)
            self.pause_end_time = self.pause_start_time + datetime.timedelta(hours=TRADING_PAUSE_HOURS)
            return True
            
        return False
    
    def is_paused(self):
        """Check if trading is currently paused"""
        if not self.pause_end_time:
            return False
            
        now = datetime.datetime.now(TIMEZONE)
        if now < self.pause_end_time:
            return True
            
        # Reset pause times if pause period is over
        if now >= self.pause_end_time:
            self.pause_start_time = None
            self.pause_end_time = None
            return False
            
        return False
    
    def get_pause_end_time(self):
        """Get the time when trading pause will end"""
        return self.pause_end_time
    
    def is_trading_hours(self):
        """Check if current time is within trading hours"""
        now = datetime.datetime.now(TIMEZONE)
        current_time = now.time()
        
        # Trading hours are from 9 PM to 4 PM EST next day
        if TRADING_START < TRADING_END:
            return TRADING_START <= current_time <= TRADING_END
        else:
            return current_time >= TRADING_START or current_time <= TRADING_END
            
    def is_trading_day(self):
        """Check if today is a trading day (Sunday night through Friday evening)"""
        now = datetime.datetime.now(TIMEZONE)
        weekday = now.weekday()
        current_time = now.time()
        
        # Sunday (6) after 9 PM
        if weekday == 6 and current_time >= TRADING_START:
            return True
            
        # Monday through Thursday (0-3)
        if 0 <= weekday <= 3:
            return True
            
        # Friday (4) before 4 PM
        if weekday == 4 and current_time <= TRADING_END:
            return True
            
        return False

    def calculate_stop_loss_price(self, entry_price):
        """Calculate stop loss price based on ticks"""
        return entry_price - (config['STOP_LOSS_TICKS'] * config['MNQ_TICK_SIZE'])

    def calculate_take_profit_price(self, entry_price):
        """Calculate take profit price based on ticks"""
        return entry_price + (config['TAKE_PROFIT_TICKS'] * config['MNQ_TICK_SIZE']) 