import datetime
import pytz
import pandas as pd
import os
from src.db.database import Database
import logging
from src.utilities.utils import trading_day_start_time


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
        self.trading_start = pd.to_datetime(trading_start_time, format='%H%M').tz_localize(self.timezone).time()
        self.trading_end = pd.to_datetime(trading_end_time, format='%H%M').tz_localize(self.timezone).time()
        self.max_24h_loss = max_24h_loss
        self.trading_pause_hours = trading_pause_hours
        self.mnq_tick_size = mnq_tick_size
        self.stop_loss_ticks = stop_loss_ticks
        self.take_profit_ticks = take_profit_ticks

        self.pause_start_time = None
        self.pause_end_time = None
    
    def should_pause_trading(self, pnl):
        """Check if trading should be paused based on daily PnL"""
        if pnl <= -self.max_24h_loss:
            return True
        return False
    
    def set_trading_pause_time(self, db: Database = None):
        """Set the start time for trading pause"""
        self.pause_start_time = pd.Timestamp.now(tz=self.timezone)
        self.pause_end_time = self.pause_start_time + pd.Timedelta(hours=self.trading_pause_hours)

        if db is not None:
            db.add_trading_pause(self.pause_start_time, self.pause_end_time)

    def can_resume_trading_after_pause(self):
        """Check if trading can resume after pause"""
        if self.pause_start_time is None:
            return True
        
        if pd.Timestamp.now(tz=self.timezone) >= self.pause_end_time:
            msg = f"RiskManager: Trading pause from {self.pause_start_time}" 
            msg += f" to {self.pause_end_time} has ended. Resetting pause times."
            logging.info(msg)
            self.pause_start_time = None
            self.pause_end_time = None
            return True
        return False
    
    def is_trading_hours(self):
        """Check if current time is within trading hours"""
        now = pd.Timestamp.now(tz=self.timezone)
        logging.debug(f"RiskManager: Checking trading time. Current timestamp: {now}")

        current_time = now.time()
        
        # Trading hours are generally from 9 PM to 4 PM EST next day
        if self.trading_start < self.trading_end:
            return self.trading_start <= current_time < self.trading_end
        else:
            # return not self.trading_end <= current_time < self.trading_start
            return current_time < self.trading_start or current_time > self.trading_end
            
    def is_trading_day(self):
        """Check if today is a trading day (Sunday through Friday)"""
        now = pd.Timestamp.now(tz=self.timezone)
        logging.debug(f"RiskManager: Checking trading day status. Current timestamp: {now}")

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

    def populate_from_db(self, db: Database):
        """Load trading pauses from database and simply set the pause times
        based of the latest entry in the db"""
        logging.info(f"RiskManager: Populating trading pause times from DB")

        trading_pauses = db.get_trading_pauses()

        if len(trading_pauses) == 0:
            logging.info("No trading pauses found in database")
            return
        
        latest_pause = trading_pauses[-1]
        self.pause_start_time = latest_pause['start_time']
        self.pause_end_time = latest_pause['end_time']
        logging.debug(f"Loaded trading pause: {latest_pause['start_time']} to {latest_pause['end_time']}")
        return
