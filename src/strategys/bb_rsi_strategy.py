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
        
        ta.calculate_indicators(historical_data)
        
        if len(historical_data) < 2:
            historical_data.loc[historical_data.index[-1], 'signal'] = Signal.HOLD.name
            return Signal.HOLD
            
        last_row = historical_data.iloc[-1]
        prev_row = historical_data.iloc[-2]
        
        price_below_mid_bb = last_row['close'] < last_row['bb_middle']
        
        rsi_crossover = (prev_row['rsi'] < ta.rsi_threshold and 
                        last_row['rsi'] > ta.rsi_threshold)
        
        if price_below_mid_bb and rsi_crossover:
            historical_data.loc[historical_data.index[-1], 'signal'] = Signal.BUY.name
            logging.debug("BollingerBandRSIStrategy: BUY signal generated.")
            return Signal.BUY
        else:
            historical_data.loc[historical_data.index[-1], 'signal'] = Signal.HOLD.name
            logging.debug("BollingerBandRSIStrategy: HOLD signal generated.")
            return Signal.HOLD
            
