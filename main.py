from ibapi.client import EClient, Order
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

from src.api.ibkr_api import IBConnection
from src.utilities.logger import Logger
from src.configuration import Configuration

from dotenv import load_dotenv
from src.trading_system import TradingSystem
import time
import logging
import os


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    trading_system = TradingSystem(cfg)
    trading_system.start()
