import time
from datetime import datetime
import pytz
from src.risk_manager import RiskManager
import logging
from src.ibkr_api import IBConnection
from src.configuration import Configuration
from src.strategys.bb_rsi_strategy import BollingerBandRSIStrategy
from src.utilities.enums import Signal
from src.db.database import Database
import pandas as pd
import os
import shutil
from src.portfolio.portfolio_manager import PortfolioManager



class TradingSystem:

    def __init__(self, cfg: Configuration):
        self.api = IBConnection(cfg.ib_host, cfg.ib_port, cfg.ib_client_id, cfg.timeout)
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

        self.portfolio_manager = PortfolioManager(cfg, self.api)

        # self.position = 0
        # self.active_order_ids = []
        # self.active_market_order_id = []
        # self.pnl_request_ids = []
        self.historical_data = pd.DataFrame()
        # self.open_contract = None
        
        
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
            self.portfolio_manager.populate_from_db()

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

            self.portfolio_manager.check_order_statuses()

            self._check_trading_opportunities()
                
            # Check PnL & roll if we have an open position
            if self.position != 0:
                pnl_details = self.api.req_position_pnl(self.open_contract.conId, os.getenv('IBKR_ACCOUNT_ID')) 
                if self.risk_manager.should_pause_trading(self. position, pnl_details):
                    pause_end = self.risk_manager.get_pause_end_time()
                    msg = f"Trading paused until {pause_end} due to daily loss threshold breach: {self.risk_manager.get_24h_pnl()}"
                    logging.warning(msg)
                    time.sleep(60)
                    continue
                
                # Check contract roll
                # check closing positions at EOD
                # check trading pause

                # Check for contract rollover
                # if self.api.should_rollover(self.config.roll_contract_days_before):
                #     logging.warning("Rolling over to next contract")
                #     self._handle_rollover()
            
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
        
        if self.historical_data.empty:
            self.historical_data = new_bars_df
        else:
            self.historical_data = pd.concat([self.historical_data, new_bars_df])

            #check this
            self.historical_data = self.historical_data[~self.historical_data.index.duplicated(keep='last')]
            self.historical_data.sort_index(inplace=True)
            
        signal = self.strategy.generate_signals(self.historical_data, self.config)

        if (self.portfolio_manager.open_contract_number() == 0 and 
            not self.portfolio_manager.has_pending_orders() and 
            signal == Signal.BUY):
            self.portfolio_manager.enter_position(contract)

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