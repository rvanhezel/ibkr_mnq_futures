import time
from datetime import datetime
import pytz
from src.risk_manager import RiskManager
import logging
from src.ibkr_api import IBConnection
from src.configuration import Configuration
from src.strategys.bb_rsi_strategy import BollingerBandRSIStrategy
from src.utilities.enums import Signal
from src.database import Database
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
        self.db = Database()

        self.position = 0
        self.active_order_ids = []
        self.active_market_order_id = []
        self.pnl_request_ids = []
        self.historical_data = pd.DataFrame()
        self.open_contract = None
        
        
    def start(self):
        """Start the trading system"""
        try:
            self._save_config()
            logging.info("Starting trading system...")

            if self.config.paper_trading:
                logging.info("Paper trading mode enabled")
            else:
                logging.info("Live trading mode enabled")

            self.api.connect()
            while True:
                try:
                    self._trading_loop()
                except Exception as e:
                    logging.error(f"Error in trading loop: {str(e)}")
                    time.sleep(10)  

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
            if not self.risk_manager.is_trading_day():
                logging.warning("Not a trading day. Waiting...")
                time.sleep(60)
                continue
                
            if not self.risk_manager.is_trading_hours():
                logging.warning("Outside trading hours. Waiting...")
                time.sleep(60)
                continue
                
            # Check PnL & roll if we have an open position
            if self.position != 0:
                pnl_details = self.api.req_position_pnl(self.open_contract.conId, os.getenv('IBKR_ACCOUNT_ID')) 
                if self.risk_manager.should_pause_trading(self. position, pnl_details):
                    pause_end = self.risk_manager.get_pause_end_time()
                    msg = f"Trading paused until {pause_end} due to daily loss threshold breach: {self.risk_manager.get_24h_pnl()}"
                    logging.warning(msg)
                    time.sleep(60)
                    continue
                
                # Check for contract rollover
                if self.api.should_rollover(self.config.roll_contract_days_before):
                    logging.warning("Rolling over to next contract")
                    self._handle_rollover()
                    
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
        # Get current contract
        contract = self.api.get_current_contract(
            self.config.ticker,
            self.config.exchange,
            self.config.currency
        )
        if not contract:
            logging.error("No active contract available")
            return

        # Get historical data
        new_bars_df = self.api.get_historical_data(contract, self.config.duration, self.config.bar_size)
        if not new_bars_df:
            logging.warning("No historical data available")
            return
        
        # Append new data to historical data
        if self.historical_data.empty:
            self.historical_data = new_bars_df
        else:
            self.historical_data = pd.concat([self.historical_data, new_bars_df])

            #check this
            self.historical_data = self.historical_data[~self.historical_data.index.duplicated(keep='last')]
            self.historical_data.sort_index(inplace=True)
            
        # Generate signals using the strategy
        signal = self.strategy.generate_signals(self.historical_data, self.config)
        
        # Check for entry conditions if no position
        if self.position == 0 and signal == Signal.BUY:
            self._enter_position(contract)
            
    def _enter_position(self, contract):
        """Enter a new long position"""            
        # Place market order
        order_id, order_status = self.api.place_market_order(contract, 'BUY', self.config.contract_number)
        if order_status['status'] != 'Filled':
            logging.warning(f"Entry order status: {order_status}. Waiting 10s for fill...")
            time.sleep(10)
            order_status = self.api.get_order_status(order_id)

        if order_status['status'] != 'Filled':
            logging.warning(f"Order still not filled. Current status: {order_status}. Waiting 1min  ...")
            time.sleep(60)
            order_status = self.api.get_order_status(order_id)

        if order_status['status'] != 'Filled':
            logging.warning(f"Order still not filled. Current status: {order_status}. Waiting 5min  ...")
            time.sleep(300)
            order_status = self.api.get_order_status(order_id)

        if order_status['status'] != 'Filled':
            logging.error("Order still not filled after 5min. Cancelling order...")
            self.api.cancelOrder(order_id)
            return
        
        # Calculate stop loss and take profit prices
        fill_price = order_status['avg_fill_price']       
        stop_price = fill_price - (self.config.stop_loss_ticks * self.config.mnq_tick_size)
        profit_price = fill_price + (self.config.take_profit_ticks * self.config.mnq_tick_size)
        
        # Place stop loss and take profit orders
        stop_order_id, stop_order_status = self.api.place_stop_loss_order(contract, order_id, self.config.contract_number, stop_price)
        profit_order_id, profit_order_status = self.api.place_profit_taker_order(contract, order_id, self.config.contract_number, profit_price)
        
        time.sleep(self.config.timeout)
        logging.info(f"Stop loss order status: {stop_order_status}")
        logging.info(f"Profit taker order status: {profit_order_status}")

        self.position = self.config.contract_number
        self.active_order_ids.extend([order_id, stop_order_id, profit_order_id])
        self.active_market_order_id.extend([order_id])
        
        logging.info(f"Entered long position: {self.config.contract_number} contracts at {fill_price}")
        logging.info(f"Entered Stop loss: {stop_price}, Take profit: {profit_price}")

    def _add_contract_to_db(self, contract):
        """Add contract id to database. The id is only available after entering a position
        and so must be extracted from the active positions"""
        positions = self.api.get_positions()
        
        matching_position = None
        for position in positions:
            pos_contract = position['contract']
            
            if (pos_contract.symbol == contract.symbol and
                pos_contract.secType == contract.secType and
                pos_contract.exchange == contract.exchange and
                pos_contract.currency == contract.currency and
                pos_contract.lastTradeDateOrContractMonth == contract.lastTradeDateOrContractMonth):
                
                matching_position = pos_contract
                break
 
        if matching_position:
            if self.db.add_contract(matching_position):
                logging.info(f"Successfully added contract {matching_position.conId} to database")
                return
            else:
                msg = "Failed to add contract to database"
                logging.error(msg)
                raise Exception(msg)
        else:
            msg = f"No matching position found for contract filled contract"
            raise Exception(msg)

    def _remove_contract_from_db(self, contract):
        """Remove contract from database"""
        if hasattr(contract, 'conId'):
            if self.db.remove_contract(contract.conId):
                logging.info(f"Successfully removed contract {contract.conId} from database")
            else:
                logging.error(f"Failed to remove contract {contract.conId} from database")
        else:
            raise AttributeError(f"Contract has no conId: {contract}")

    def _close_all_positions(self):
        """Close all open positions"""
        if self.position == 0:
            return
            
        # Cancel PnL requests
        self.api.cancel_all_pnl_requests()
            
        # Cancel all active orders
        for order in self.active_market_orders:
            self.api.cancelOrder(order) #TODO: STP/LMT with parentId - cancelled diff?
        
        # Close position with market order
        close_order = self.api.place_market_order(
            'SELL' if self.position > 0 else 'BUY',
            abs(self.position)
        )
        
        if close_order:
            self.position = 0
            self.active_market_orders = []
            logging.info("Closed all positions")
        else:
            logging.error("Failed to close positions")

    def _save_config(self):
        """Save configuration file to outputs for audit purposes"""
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