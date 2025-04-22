from src.api.message_queue import MessageQueue
from src.portfolio.portfolio_manager import PortfolioManager
import time
import datetime
import pytz
import pandas as pd
import os
from src.db.database import Database
import logging
from src.utilities.utils import trading_day_start_time_ts
import holidays


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
    
    def should_pause_trading(self, pnl, num_contracts):
        """Check if trading should be paused based on daily PnL"""
        if pnl <= -self.max_24h_loss * num_contracts:
            return True
        return False
    
    def set_trading_pause_time(self, db: Database = None):
        """Set the start time for trading pause"""
        self.pause_start_time = pd.Timestamp.now(tz=self.timezone)
        self.pause_end_time = self.pause_start_time + pd.Timedelta(hours=self.trading_pause_hours)

        if db is not None:
            db.add_trading_pause(self.pause_start_time, self.pause_end_time)

    def can_resume_trading_after_pause(self, now: pd.Timestamp):
        """Check if trading can resume after pause"""
        if self.pause_start_time is None:
            return True
        
        if now >= self.pause_end_time:
            msg = f"RiskManager: Trading pause from {self.pause_start_time}" 
            msg += f" to {self.pause_end_time} has ended. Resetting pause times."
            logging.info(msg)
            self.pause_start_time = None
            self.pause_end_time = None
            return True
        return False
    
    def is_trading_hours(self, now: pd.Timestamp):
        """Check if current time is within trading hours"""
        logging.debug(f"RiskManager: Checking trading time. Current timestamp: {now}")
        current_time = now.time()
        
        # Trading hours are generally from 9 PM to 4 PM EST next day
        if self.trading_start < self.trading_end:
            return self.trading_start <= current_time < self.trading_end
        else:
            return current_time >= self.trading_start or current_time < self.trading_end
            
    def is_trading_day(self, now_timestamp: pd.Timestamp):
        """Check if today is a trading day (Sunday through Friday)"""
        logging.debug(f"RiskManager: Checking trading day. Current timestamp: {now_timestamp}")
        us_holidays = holidays.UnitedStates()
        weekday = now_timestamp.weekday()

        if now_timestamp.date() in us_holidays:
            return False
        
        # Sunday through Friday (6-4)
        elif 0 <= weekday <= 4 or (weekday == 6 and now_timestamp.time() >= self.trading_start):
            return True
            
        else:
            return False

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
    
    def perform_eod_close(self, 
                           now: pd.Timestamp, 
                           eod_exit_time: str, 
                           market_close_time: str,
                           ptf_manager: PortfolioManager, 
                           message_queue: MessageQueue):
        """Perform end of day checks"""
        eod_cutoff = pd.Timestamp(
                now.year, 
                now.month, 
                now.day, 
                int(eod_exit_time[:2]),           
                int(eod_exit_time[2:]),           
                tz=self.timezone)
        
        market_close_time = pd.Timestamp(
                now.year, 
                now.month, 
                now.day, 
                int(market_close_time[:2]),           
                int(market_close_time[2:]),           
                tz=self.timezone)

        if market_close_time >= now >= eod_cutoff:
            msg = f"Current time: {now} - End of day approaching - closing all positions and cancelling orders"
            logging.info(msg)
            message_queue.add_message(msg)
            
            ptf_manager.cancel_all_orders()
            ptf_manager.close_all_positions()

            seconds_until_close = (market_close_time - now).total_seconds()
            logging.info(f"Sleeping for {seconds_until_close} seconds until market close")
            time.sleep(seconds_until_close)
            return True
        
        return False
