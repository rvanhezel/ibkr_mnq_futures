from src.strategys.abstract_strategy import AbstractStrategy
from src.technical_analysis import TechnicalAnalysis
from utilities.enums import Signal


class BollingerBandRSIStrategy(AbstractStrategy):
    """
    A trading strategy based on Bollinger Bands and RSI indicators.
    Generates buy signals when price is below middle BB and RSI crosses above threshold.
    """
    
    @staticmethod
    def generate_signals(historical_data, cfg):        
        # Initialize technical analysis with config
        ta = TechnicalAnalysis(cfg)
        
        # Get historical data and calculate indicators
        current_data = ta.calculate_indicators(historical_data)
        
        # Check entry conditions
        if len(current_data) < 2:
            return Signal.HOLD
            
        # Get the last two rows for RSI crossing check
        last_row = current_data.iloc[-1]
        prev_row = current_data.iloc[-2]
        
        # Check if price is below middle BB
        price_below_mid_bb = last_row['close'] < last_row['bb_middle']
        
        # Check if RSI crosses above threshold
        rsi_crossover = (prev_row['rsi'] < ta.rsi_threshold and 
                        last_row['rsi'] > ta.rsi_threshold)
        
        # Generate signal based on conditions
        if price_below_mid_bb and rsi_crossover:
            return Signal.BUY
        else:
            return Signal.HOLD
            
