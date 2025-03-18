import time
from datetime import datetime
import pytz
from src.risk_manager import RiskManager
import logging
from src.ibkr_api import IBConnection
from src.configuration import Configuration
from src.strategys.bb_rsi_strategy import BollingerBandRSIStrategy
from src.utilities.enums import Signal
import pandas as pd
import os
import shutil


class TradingSystem:

    def __init__(self, cfg: Configuration):
        self.api = IBConnection(cfg.ib_host, cfg.ib_port, cfg.ib_client_id)
        self.risk_manager = RiskManager(
            cfg.timezone, 
            cfg.trading_start_time, 
            cfg.trading_end_time, 
            cfg.max_24h_loss_per_contract, 
            cfg.trading_pause_hours, 
            cfg.mnq_tick_size, 
            cfg.stop_loss_ticks, 
            cfg.take_profit_ticks)
        self.strategy = BollingerBandRSIStrategy()
        self.config = cfg

        self.position = 0
        self.active_orders = []
        self.historical_data = pd.DataFrame()
        
        
    def start(self):
        """Start the trading system"""
        try:
            self._save_config()
            logging.info("Starting trading system...")

            self.api.connect()
            while True:
                try:
                    self._trading_loop()
                except Exception as e:
                    logging.error(f"Error in trading loop: {str(e)}")
                    time.sleep(10)  # Wait before retrying

        except ConnectionError as e:
            logging.error(f"Failed to connect to Interactive Brokers: {str(e)}")

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt - Shutting down trading system...")

        except Exception as e:
            logging.error(f"Unexpected error within trading system: {str(e)}")

        finally:
            self.api.disconnect()
            self._save_historical_data()

            logging.info("Trading system shut down")
            
            
    def _trading_loop(self):
        """Main trading loop"""
        while True:
            # Check if it's trading hours
            if not self.risk_manager.is_trading_day():
                logging.info("Not a trading day. Waiting...")
                time.sleep(60)
                continue
                
            if not self.risk_manager.is_trading_hours():
                logging.info("Outside trading hours. Waiting...")
                time.sleep(60)
                continue
                
            # Check if trading is paused due to losses
            if self.risk_manager.should_pause_trading():
                pause_end = self.risk_manager.get_pause_end_time()
                logging.info(f"Trading paused until {pause_end}")
                time.sleep(60)
                continue
                
            # Check for contract rollover
            if self.api.should_rollover(self.config.roll_contract_days_before):
                logging.info("Rolling over to next contract")
                self._handle_rollover()
                
            # Get market data and check for trading opportunities
            # self._check_trading_opportunities()
            
            # Sleep for 1 minute before next iteration
            time.sleep(60)
            
    def _handle_rollover(self):
        """Handle contract rollover process"""
        # Close any existing positions
        if self.position != 0:
            self._close_all_positions()
            
        # Switch to new contract
        self.api.rollover_contract(self.config.ticker, self.config.exchange, self.config.currency)
        logging.info("Rolled over to new contract")
        
    def _check_trading_opportunities(self):
        """Check for trading opportunities based on strategy"""
        # Get historical data
        new_bars = self.api.get_historical_data(
            self.config.ticker, 
            self.config.exchange, 
            self.config.currency
        )
        if not new_bars:
            logging.warning("No historical data available")
            return
            
        new_data = pd.DataFrame({
            'datetime': [bar.date for bar in new_bars],
            'open': [bar.open for bar in new_bars],
            'high': [bar.high for bar in new_bars],
            'low': [bar.low for bar in new_bars],
            'close': [bar.close for bar in new_bars],
            'volume': [bar.volume for bar in new_bars]
        })
        new_data.set_index('datetime', inplace=True)
        
        # Append new data to historical data
        if self.historical_data.empty:
            self.historical_data = new_data
        else:
            # Concatenate and remove duplicates based on index
            self.historical_data = pd.concat([self.historical_data, new_data])

            #check this
            self.historical_data = self.historical_data[~self.historical_data.index.duplicated(keep='last')]
            
            self.historical_data.sort_index(inplace=True)
        
        # Get current contract
        contract = self.api.get_current_contract(
            self.config.ticker,
            self.config.exchange,
            self.config.currency
        )
        if not contract:
            logging.error("No active contract available")
            return
            
        # Generate signals using the strategy
        signal = self.strategy.generate_signals(self.historical_data, self.config)
        
        # Check for entry conditions if no position
        if self.position == 0 and signal == Signal.BUY:
            self._enter_position()
            
    def _enter_position(self):
        """Enter a new long position"""
        contract = self.api.get_current_contract(
            self.config.ticker,
            self.config.exchange,
            self.config.currency
        )
        if not contract:
            logging.error("No active contract available")
            return
            
        # Place market order
        entry_order = self.api.place_market_order('BUY', self.config.contract_number)
        if not entry_order:
            logging.error("Failed to place entry order")
            return
            
        # Wait for fill
        fill_price = entry_order.orderStatus.avgFillPrice
        if not fill_price:
            logging.error("Entry order not filled")
            return
            
        # Calculate stop loss and take profit prices
        stop_price = fill_price - (self.config.stop_loss_ticks * self.config.mnq_tick_size)
        profit_price = fill_price + (self.config.take_profit_ticks * self.config.mnq_tick_size)
        
        # Place stop loss and take profit orders
        stop_order = self.api.place_stop_loss_order(entry_order, self.config.contract_number, stop_price)
        profit_order = self.api.place_profit_taker_order(entry_order, self.config.contract_number, profit_price)
        
        self.position = self.config.contract_number
        self.active_orders.extend([stop_order, profit_order])
        
        logging.info(f"Entered long position: {self.config.contract_number} contracts at {fill_price}")
        logging.info(f"Stop loss: {stop_price}, Take profit: {profit_price}")
        
    def _close_all_positions(self):
        """Close all open positions"""
        if self.position == 0:
            return
            
        # Cancel all active orders
        for order in self.active_orders:
            self.api.cancelOrder(order)
        
        # Close position with market order
        close_order = self.api.place_market_order(
            'SELL' if self.position > 0 else 'BUY',
            abs(self.position)
        )
        
        if close_order:
            self.position = 0
            self.active_orders = []
            logging.info("Closed all positions")
        else:
            logging.error("Failed to close positions")

    def _save_config(self):
        """Save configuration file TO outputs for audit purposes"""
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output", "config")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        filename = f"config_{timestamp}.cfg"
        filepath = os.path.join(output_dir, filename)
        
        shutil.copy2('run.cfg', filepath)
        logging.info(f"Configuration saved to {filepath}")

    def _save_historical_data(self):
        """Save historical data to CSV file"""
        if not self.historical_data.empty:
            logging.info("Saving historical data to CSV file...")

            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.getcwd(), "output", "historical_data")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"historical_data_{self.config.ticker}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            # Save to CSV
            self.historical_data.to_csv(filepath, index=True)
            logging.info(f"Historical data saved to {filepath}")