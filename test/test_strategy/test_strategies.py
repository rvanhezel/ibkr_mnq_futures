import unittest
import pandas as pd
import numpy as np
import os
from src.strategys.bb_rsi_strategy import BollingerBandRSIStrategy
from src.utilities.enums import Signal
from src.configuration import Configuration


class TestBollingerBandRSIStrategy(unittest.TestCase):

    def setUp(self):
        # Get the path to the test config file
        config_path = os.path.join(os.getcwd(), 
                                   "test", 
                                   "test_strategy", 
                                   "test_run.cfg")
        self.cfg = Configuration(config_path)
        self.strategy = BollingerBandRSIStrategy()

    def test_generate_hold_signal(self):
        """Test that a HOLD signal is generated when conditions for BUY are not met"""
        historical_data = pd.DataFrame({
            'close': [100, 95, 90, 85, 80]  
        })

        signal = self.strategy.generate_signals(historical_data, self.cfg)
        self.assertEqual(signal, Signal.HOLD)

    def test_generate_buy_signal(self):
        """Test that a BUY signal is generated when conditions for BUY are met"""
        # Create historical data with 20 points that will generate a buy signal
        # Price starts at 100, gradually decreases to 80 (below BB middle)
        # RSI starts at 30, gradually increases to 45 (crosses above threshold)
        historical_data = pd.DataFrame({
            'close': [
                100, 98, 96, 94, 92,  # First 5 points
                90, 88, 86, 84, 82,  # Next 5 points
                81, 80, 80, 80, 80,  # Next 5 points (price stabilizes)
                80, 80, 80, 80, 80   # Last 5 points
            ]
        })

        signal = self.strategy.generate_signals(historical_data, self.cfg)        
        self.assertEqual(signal, Signal.BUY)

if __name__ == '__main__':
    unittest.main()
