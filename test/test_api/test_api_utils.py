import pytest
import pandas as pd
from datetime import datetime
from ibapi.contract import Contract
from src.api.api_utils import get_current_contract


class TestApiUtils:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method."""
        self.timezone = "US/Eastern"
        
    def test_get_current_contract_1st_march(self):
        """Test getting current contract when not near expiry"""
        # Set a fixed date in the middle of a contract period
        test_date = pd.Timestamp("2025-03-01", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            returned_contract = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone=self.timezone
            )
            
            assert isinstance(returned_contract, Contract)
            assert returned_contract.symbol == "MNQ"
            assert returned_contract.secType == "FUT"
            assert returned_contract.exchange == "CME"
            assert returned_contract.currency == "USD"
            assert returned_contract.lastTradeDateOrContractMonth == "202503"
            
    def test_get_current_contract_rollover_case(self):
        """Test getting current contract when near expiry"""
        test_date = pd.Timestamp("2025-03-17", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            returned_contract = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone=self.timezone
            )
            
            assert isinstance(returned_contract, Contract)
            assert returned_contract.symbol == "MNQ"
            assert returned_contract.secType == "FUT"
            assert returned_contract.exchange == "CME"
            assert returned_contract.currency == "USD"
            assert returned_contract.lastTradeDateOrContractMonth == "202506"

    def test_get_current_contract_rollover_edge_case(self):
        """Test getting current contract when near expiry"""
        test_date = pd.Timestamp("2025-03-14", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            returned_contract = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone=self.timezone
            )
            
            assert isinstance(returned_contract, Contract)
            assert returned_contract.symbol == "MNQ"
            assert returned_contract.secType == "FUT"
            assert returned_contract.exchange == "CME"
            assert returned_contract.currency == "USD"
            assert returned_contract.lastTradeDateOrContractMonth == "202506"
            
    def test_get_current_contract_simple_year_end(self):
        """Test getting current contract when transitioning to next year"""
        test_date = pd.Timestamp("2025-12-01", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            returned_contract = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone=self.timezone
            )
            
            assert isinstance(returned_contract, Contract)
            assert returned_contract.symbol == "MNQ"
            assert returned_contract.secType == "FUT"
            assert returned_contract.exchange == "CME"
            assert returned_contract.currency == "USD"
            assert returned_contract.lastTradeDateOrContractMonth == "202512"

    def test_get_current_contract_year_end_transition(self):
        """Test getting current contract when transitioning to next year"""
        test_date = pd.Timestamp("2025-12-25", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            returned_contract = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone=self.timezone
            )
            
            assert isinstance(returned_contract, Contract)
            assert returned_contract.symbol == "MNQ"
            assert returned_contract.secType == "FUT"
            assert returned_contract.exchange == "CME"
            assert returned_contract.currency == "USD"
            assert returned_contract.lastTradeDateOrContractMonth == "202603"
            
    def test_get_current_contract_different_roll_days(self):
        """Test getting current contract with different roll_contract_days_before values"""
        test_date = pd.Timestamp("2025-06-12", tz=self.timezone)
        
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            # Test with 5 days before roll
            contract_5_days = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=5,
                timezone=self.timezone
            )
            
            # Test with 10 days before roll
            contract_10_days = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=10,
                timezone=self.timezone
            )
            
            # Should still be on March contract with 5 days
            assert contract_5_days.lastTradeDateOrContractMonth == "202506"
            # Should have rolled to June contract with 10 days
            assert contract_10_days.lastTradeDateOrContractMonth == "202509"
            
    def test_get_current_contract_different_timezone(self):
        """Test getting current contract with different timezone"""
        test_date = pd.Timestamp("2025-03-01", tz="UTC")
        
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)
            
            # Test with US/Eastern timezone
            contract_eastern = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone="US/Eastern"
            )
            
            # Test with UTC timezone
            contract_utc = get_current_contract(
                ticker="MNQ",
                exchange="CME",
                ccy="USD",
                roll_contract_days_before=7,
                timezone="UTC"
            )
            
            # Should be the same contract regardless of timezone
            assert contract_eastern.lastTradeDateOrContractMonth == contract_utc.lastTradeDateOrContractMonth 