from src.strategys.abstract_strategy import AbstractStrategy
from src.utilities.technical_analysis import TechnicalAnalysis
from src.utilities.enums import Signal
import logging
import pandas as pd
from src.configuration import Configuration


class BollingerBandRSIStrategy(AbstractStrategy):
    """
    A trading strategy based on Bollinger Bands and RSI indicators.
    Generates buy signals when price is below middle BB and RSI crosses above threshold.
    """
    
    @staticmethod
    def generate_signals(historical_data: pd.DataFrame, cfg: Configuration):        
        # Initialize technical analysis with config
        logging.debug("Generating signals for Bollinger Band RSI strategy.")

        ta = TechnicalAnalysis(cfg)
        
        # Get historical data and calculate indicators
        ta.calculate_indicators(historical_data)
        
        # Check entry conditions
        if len(historical_data) < 2:
            return Signal.HOLD
            
        # Get the last two rows for RSI crossing check
        last_row = historical_data.iloc[-1]
        prev_row = historical_data.iloc[-2]
        
        # Check if price is below middle BB
        price_below_mid_bb = last_row['close'] < last_row['bb_middle']
        
        # Check if RSI crosses above threshold
        rsi_crossover = (prev_row['rsi'] < ta.rsi_threshold and 
                        last_row['rsi'] > ta.rsi_threshold)
        
        # Generate signal based on conditions
        if price_below_mid_bb and rsi_crossover:
            logging.debug("BUY signal generated.")
            return Signal.BUY
        else:
            logging.debug("HOLD signal generated.")
            return Signal.HOLD
            
