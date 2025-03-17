from abc import ABC, abstractmethod



class AbstractStrategy(ABC):
    """
    Abstract interface for trading strategies.

    Defines methods for processing market data and generating trade signals.
    """
    @staticmethod
    @abstractmethod
    def generate_signals(historical_data, cfg):        
        """
        Generate a trade signal based on the provided market data.

        :param historical_data: Time series of historical data
        :param cfg: Configuration instance
        :return: Signal
        """
        pass
