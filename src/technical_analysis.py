import pandas as pd
import numpy as np
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator



class TechnicalAnalysis:
    def __init__(self, config):
        """
        Initialize TechnicalAnalysis with configuration parameters
        
        Args:
            config: Configuration instance containing technical indicator parameters
        """
        # Store indicator parameters as member variables
        self.bollinger_period = config.bollinger_period
        self.bollinger_std = config.bollinger_std
        self.rsi_period = config.rsi_period
        self.rsi_threshold = config.rsi_threshold
        
    def calculate_bollinger_bands(self, close_prices):
        """Calculate Bollinger Bands for the given close prices"""
        indicator_bb = BollingerBands(
            close=close_prices,
            window=self.bollinger_period,
            window_dev=self.bollinger_std
        )
        
        return {
            'middle': indicator_bb.bollinger_mavg(),
            'upper': indicator_bb.bollinger_hband(),
            'lower': indicator_bb.bollinger_lband()
        }
    
    def calculate_rsi(self, close_prices):
        """Calculate RSI for the given close prices"""
        indicator_rsi = RSIIndicator(
            close=close_prices,
            window=self.rsi_period
        )
        return indicator_rsi.rsi()
        
    def calculate_indicators(self, historical_data):
        """Calculate Bollinger Bands and RSI for the given historical data"""
        # Convert IB historical data to pandas DataFrame
        df = pd.DataFrame({
            'datetime': [bar.date for bar in historical_data],
            'open': [bar.open for bar in historical_data],
            'high': [bar.high for bar in historical_data],
            'low': [bar.low for bar in historical_data],
            'close': [bar.close for bar in historical_data],
            'volume': [bar.volume for bar in historical_data]
        })
        
        # Calculate Bollinger Bands
        bb_data = self.calculate_bollinger_bands(close_prices=df['close'])
        
        df['bb_middle'] = bb_data['middle']
        df['bb_upper'] = bb_data['upper']
        df['bb_lower'] = bb_data['lower']
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(close_prices=df['close'])
        
        return df 