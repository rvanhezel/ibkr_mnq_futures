import time
from datetime import datetime
import pytz
from src.risk_manager import RiskManager
import logging
from src.api.ibkr_api import IBConnection
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
        self.db = Database(self.config.timezone)
        self.portfolio_manager = PortfolioManager(cfg, self.api, self.db)

        self.market_data = pd.DataFrame()
        
        
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
            self.risk_manager.populate_from_db(self.db)

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
            self._save_market_data()

            logging.info("Trading system shut down")
            
            
    def _trading_loop(self):
        """Main trading loop"""
        loop_sleep_time = 30

        while True:
            logging.info(f"Starting trading loop")

            if not self.risk_manager.is_trading_day():
                logging.warning("Not a trading day. Waiting...")
                time.sleep(60)
                continue
                
            if not self.risk_manager.is_trading_hours():
                logging.warning("Outside trading hours. Waiting...")
                self.portfolio_manager.clear_orders_and_positions()
                time.sleep(60)
                continue
            
            if not self.risk_manager.can_resume_trading_after_pause():
                logging.warning("Trading paused triggered. Waiting...")
                time.sleep(60)
                continue

            # Update or create positions from open orders
            self.portfolio_manager.update_positions()

            # Check for cancelled market orders and resubmit them if required
            self.portfolio_manager.check_cancelled_market_order()
                
            # Check PnL for trading pause
            logging.debug("Checking PnL for trading pause.")
            pnl = self.portfolio_manager.daily_pnl()
            logging.debug(f"PnL: {pnl}")

            if self.risk_manager.should_pause_trading(pnl):
                logging.warning(f"PnL: {pnl} is below max 24h loss. Pausing trading.")
                self.risk_manager.set_trading_pause_time(self.db)

                logging.warning(f"Trading paused until {self.risk_manager.pause_end_time}")
                time.sleep(60)
                continue

            self._check_trading_opportunities()

            # Check if it's near end of trading day (3:59 PM or later)
            current_time = pd.Timestamp.now(tz=self.config.timezone)
            eod_cutoff = pd.Timestamp(
                    current_time.year, 
                    current_time.month, 
                    current_time.day, 
                    int(self.config.eod_exit_time[:2]),           
                    int(self.config.eod_exit_time[2:]),           
                    tz=self.config.timezone)
            
            if current_time >= eod_cutoff:
                logging.info("End of day approaching - closing all positions and cancelling orders")
                
                self.portfolio_manager.cancel_all_orders()
                self.portfolio_manager.close_all_positions()
                loop_sleep_time = 5
            

            self._save_market_data()

            logging.info(f"Trading loop complete. Sleeping for {loop_sleep_time} seconds...")
            time.sleep(loop_sleep_time)
        
    def _check_trading_opportunities(self):
        """Check for trading opportunities based on strategy"""
        logging.debug("Checking for trading opportunities.")

        # Get historical data
        contract = self.portfolio_manager.get_current_contract()
        new_bars_df = self.api.get_historical_data(contract, 
                                                   str(self.config.horizon), 
                                                   str(self.config.bar_size),
                                                   self.config.timezone)

        if new_bars_df.empty:
            logging.warning("No historical data available")
            return
        
        if self.market_data.empty:
            self.market_data = new_bars_df
        else:
            self.market_data = pd.concat([self.market_data, new_bars_df])
            self.market_data = self.market_data[~self.market_data.index.duplicated(keep='last')]
            self.market_data.sort_index(inplace=True)

        logging.info(f"Market data: {self.market_data.tail(10)}")
            
        # signal = self.strategy.generate_signals(self.market_data, self.config)
        signal = Signal.BUY #for testing

        logging.info(f"Signal generated: {signal.name}")

        if (self.portfolio_manager.contract_count_from_open_positions() == 0 and 
            not self.portfolio_manager.has_pending_orders() and 
            signal == Signal.BUY):
            self.portfolio_manager.place_bracket_order()

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

    def _save_market_data(self):
        """Save historical data to CSV file"""
        if not self.market_data.empty:
            logging.info("Saving market data to CSV file...")

            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"market_data_{self.config.ticker}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            self.market_data.to_csv(filepath, index=True)
            logging.info(f"Market data saved to {filepath}")