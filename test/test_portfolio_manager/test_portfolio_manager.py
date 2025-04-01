import pytest
import pandas as pd
from src.utilities.utils import trading_day_start_time_ts
from src.portfolio.portfolio_manager import PortfolioManager
from src.db.database import Database
import os
from src.configuration import Configuration
from unittest.mock import patch


class TestPortfolioManager:

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method."""
        self.cfg = Configuration(os.path.join(os.getcwd(), 
                                        "test", 
                                        "test_portfolio_manager", 
                                        "test_run.cfg"))
        self.db = Database(self.cfg.timezone, 
                           os.path.join(os.getcwd(), 
                                        "test", 
                                        "test_portfolio_manager", 
                                        "test_trading.db"))
        self.portfolio_manager = PortfolioManager(self.cfg, None, self.db)

    def test_populate_from_db_intr_day_orders(self):
        """Test trading day start time for morning trading"""

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('src.portfolio.portfolio_manager.PortfolioManager._get_order_status', 
                      lambda self, order_id: {'status': 'Filled'})

            loaded_inventory = self.portfolio_manager.populate_from_db(check_state=False)
            expected_inventory = (3, 3, 1)

            assert loaded_inventory == expected_inventory

    def test_populate_from_db_previous_day_orders(self):
        """Test trading day start time for morning trading"""

        fixed_start_time = pd.Timestamp("2025-04-01 21:00:00", tz=self.cfg.timezone)
        
        # Create a mock for both functions
        with patch('src.portfolio.portfolio_manager.trading_day_start_time_ts', 
                  return_value=fixed_start_time), \
             patch('src.portfolio.portfolio_manager.PortfolioManager._get_order_status', 
                  return_value={'status': 'Filled'}):
            
            loaded_inventory = self.portfolio_manager.populate_from_db(check_state=False)
            expected_inventory = (0, 0, 0)

            assert loaded_inventory == expected_inventory


