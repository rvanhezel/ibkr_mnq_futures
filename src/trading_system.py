from src.utilities.logger import Logger
import time
from datetime import datetime
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
        self.api = IBConnection(
            cfg.ib_host, 
            cfg.ib_port, 
            cfg.ib_client_id, 
            cfg.timeout,
            cfg.timezone)
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
        previous_day = pd.Timestamp.now(tz=self.config.timezone).date()

        while True:
            logging.info(f"Starting trading loop")
            loop_sleep_time = 30

            now = pd.Timestamp.now(tz=self.config.timezone)
            if now.date() > previous_day:
                Logger(now.date()) # Create new log file for new day to avoid excessively large files
                previous_day = now.date()

            if not self.risk_manager.is_trading_day(now):
                logging.warning("Not a trading day. Waiting...")
                time.sleep(60)
                continue
                
            if not self.risk_manager.is_trading_hours(now):
                logging.warning("Outside trading hours. Waiting...")
                self.portfolio_manager.clear_orders_statuses_positions()
                time.sleep(60)
                continue
            
            if not self.risk_manager.can_resume_trading_after_pause(now):
                logging.warning(f"Trading paused triggered until {self.risk_manager.pause_end_time}. Waiting...")
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

            if self.risk_manager.should_pause_trading(pnl, self.config.number_of_contracts):
                logging.warning(f"PnL: {pnl} is below max 24h loss. Pausing trading.")
                self.risk_manager.set_trading_pause_time(self.db)

                logging.warning(f"Trading paused until {self.risk_manager.pause_end_time}")
                time.sleep(60)
                continue

            self._check_trading_opportunities()

            # Check if it's near end of trading day (3:59 PM or later)
            now = pd.Timestamp.now(tz=self.config.timezone)
            if self.risk_manager.perform_eod_close(
                now, 
                self.config.eod_exit_time,
                self.config.trading_end_time,
                self.portfolio_manager):
                eod_pnl = self.portfolio_manager.daily_pnl()
                df = pd.DataFrame({'pnl': [eod_pnl]})
                df.to_csv(os.path.join(os.getcwd(), 'output', 'eod_pnl.csv'), index=False)
                logging.info(f"End of day PnL: {eod_pnl}")

            if self.config.save_market_data:
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
        
        if isinstance(new_bars_df, pd.DataFrame) and not new_bars_df.empty:

            if self.market_data.empty:
                self.market_data = new_bars_df

            else:

                if new_bars_df.index[-1] == self.market_data.index[-1]:
                    logging.debug(f"Latest data timestamp obtained: {new_bars_df.index[-1]}. No new data since last loop.")
                    return
                else:
                    logging.debug(f"Latest data timestamp obtained: {new_bars_df.index[-1]}. New data since last loop.")

                self.market_data = pd.concat([
                    self.market_data, 
                    new_bars_df[~new_bars_df.index.isin(self.market_data.index)]
                    ])
                self.market_data = self.market_data[~self.market_data.index.duplicated(keep='last')]
                self.market_data.sort_index(inplace=True)

        else:
            logging.error("No data returned from IBKR API")
            return
                
        if self.config.strategy == 'bollinger_rsi':
            signal = self.strategy.generate_signals(self.market_data, self.config)
        elif self.config.strategy == 'buy':
            signal = Signal.BUY #for testing
        else:
            raise ValueError(f"Invalid strategy: {self.config.strategy}")

        logging.info(f"Market data tail: {self.market_data.tail(10)}")
        logging.info(f"Signal generated: {signal.name}")

        position_quantity = self.portfolio_manager.current_position_quantity()
        if position_quantity > 0 and signal == Signal.BUY:
            logging.info(f"Currently holding {position_quantity} shares of {self.config.ticker}. Cannot enter more.")

        elif self.portfolio_manager.has_pending_orders() and signal == Signal.BUY:
            logging.info("Orders are pending. Cannot enter more.")

        elif position_quantity == 0 and signal == Signal.BUY:
            self.portfolio_manager.place_bracket_order()

        else:
            logging.info("Not placing any orders")

    def _save_config(self):
        """Save configuration file to outputs for audit purposes"""
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%d%m%Y")
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