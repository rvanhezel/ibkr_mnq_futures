import os
from src.utilities.period import Period
import configparser
import logging
from datetime import datetime
import pytz
from src.utilities.period import Period


class Configuration:

    def __init__(self, path_to_config: str):
        self.config = configparser.ConfigParser()
        self.config.read(path_to_config)

        # Run section
        self.log_level = self._configure_log(self.config.get('Run', 'log_level'))
        logger = logging.getLogger()
        logger.setLevel(self.log_level)

        # Trading section
        self.ticker = self.config.get('Trading', 'ticker')
        self.order_type = self.config.get('Trading', 'order_type')
        self.exchange = self.config.get('Trading', 'exchange')
        self.number_of_contracts = self._check_contract_number(self.config.getint('Trading', 'number_of_contracts'))
        self.currency = self.config.get('Trading', 'currency')
        self.trading_start_time = self.config.get('Trading', 'trading_start_time')
        self.trading_end_time = self.config.get('Trading', 'trading_end_time')
        self.eod_exit_time = self.config.get('Trading', 'eod_exit_time')
        self.timezone = self.config.get('Trading', 'timezone')
        self.roll_contract_days_before = self.config.getint('Trading', 'roll_contract_days_before')
        self.resubmit_cancelled_order = self.config.getboolean('Trading', 'resubmit_cancelled_order')
        self.strategy = self.config.get('Trading', 'strategy')

        # Risk Management section
        self.stop_loss_ticks = self.config.getfloat('Risk_Management', 'stop_loss_ticks')
        self.take_profit_ticks = self.config.getfloat('Risk_Management', 'take_profit_ticks')
        self.max_24h_loss_per_contract = self.config.getfloat('Risk_Management', 'max_24h_loss_per_contract')
        self.trading_pause_hours = self.config.getint('Risk_Management', 'trading_pause_hours')
        self.no_endofday_risk = self.config.getboolean('Risk_Management', 'no_endofday_risk')

        # Market Data section
        self.mnq_tick_size = self.config.getfloat('Market_Data', 'mnq_tick_size')
        self.mnq_point_value = self.config.getfloat('Market_Data', 'mnq_point_value')
        self.bar_size = Period(self.config.get('Market_Data', 'bar_size'))
        self.horizon = Period(self.config.get('Market_Data', 'horizon'))

        # API section
        self.api = self.config.get('API', 'API')
        self.ib_host = self.config.get('API', 'ib_host')
        self.ib_client_id = self.config.getint('API', 'ib_client_id')
        self.paper_trading = self._check_paper_trading(self.config.getboolean('API', 'paper_trading'))
        self.ib_port = self._set_ib_port()
        self.timeout = self.config.getint('API', 'timeout')

        # Technical Indicators section
        self.bollinger_period = self.config.getint('Technical_Indicators', 'bollinger_period')
        self.bollinger_std = self.config.getint('Technical_Indicators', 'bollinger_std')
        self.rsi_period = self.config.getint('Technical_Indicators', 'rsi_period')
        self.rsi_threshold = self.config.getint('Technical_Indicators', 'rsi_threshold')

    def _configure_log(self, log_level: str):
        if log_level == "Debug":
            return logging.DEBUG
        elif log_level == "Info":
            return logging.INFO
        elif log_level == "Warning":
            return logging.WARNING
        elif log_level == "Error":
            return logging.ERROR
        else:
            raise ValueError("Log level not recognized")
        
    def _set_ib_port(self):
        if self.api == 'TWS':
            return 7497 if self.paper_trading else 7496
        elif self.api == 'IBG':
            return 4002 if self.paper_trading else 4001
        else:
            raise ValueError(f"Unknown API type: {self.api}. Must be either 'TWS' or 'IBG'")

    def _check_contract_number(self, contract_number: int):
        if contract_number != 2 :
            raise ValueError("Contract number must be 2")
        return contract_number
    
    def _check_paper_trading(self, paper_trading: bool):
        if paper_trading:
            return True
        else:
            raise ValueError("Paper trading must be enabled for testing")
