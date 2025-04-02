from src.utilities.logger import Logger
from src.configuration import Configuration
from dotenv import load_dotenv
from src.trading_system import TradingSystem


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    trading_system = TradingSystem(cfg)
    trading_system.start()
