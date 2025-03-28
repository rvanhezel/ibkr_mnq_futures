import pytest
from datetime import datetime, time
import pytz
from src.risk_manager import RiskManager


class TestRiskManager:

    @pytest.fixture
    def risk_manager(self):
        """Create a RiskManager instance with trading hours from run.cfg"""
        return RiskManager(
            trading_start_time="2100",  # 9:00 PM ET
            trading_end_time="1600",    # 4:00 PM ET
            timezone="US/Eastern",
            stop_loss_ticks=120,
            take_profit_ticks=300,
            max_24h_loss=360,
            trading_pause_hours=24,
            mnq_tick_size=0.25
        )

    def test_is_trading_day(self, risk_manager):
        """Test is_trading_day function with various dates"""
        et_tz = pytz.timezone("US/Eastern")
        
        # Test a regular trading day (Monday)
        monday = datetime(2024, 3, 18, tzinfo=et_tz)  # Monday
        assert risk_manager.is_trading_day(monday) == True
        
        # Test a weekend day (Saturday)
        saturday = datetime(2024, 3, 16, tzinfo=et_tz)  # Saturday
        assert risk_manager.is_trading_day(saturday) == False
        
        # Test a weekend day (Sunday)
        sunday = datetime(2024, 3, 17, tzinfo=et_tz)  # Sunday
        assert risk_manager.is_trading_day(sunday) == False
        
        # Test a holiday (Christmas)
        christmas = datetime(2024, 12, 25, tzinfo=et_tz)  # Christmas
        assert risk_manager.is_trading_day(christmas) == False
        
        # Test a holiday (New Year's Day)
        new_year = datetime(2024, 1, 1, tzinfo=et_tz)  # New Year's Day
        assert risk_manager.is_trading_day(new_year) == False

    def test_is_trading_hours(self, risk_manager):
        """Test is_trading_hours function with various times"""
        et_tz = pytz.timezone("US/Eastern")
        
        # Test during trading hours (10:00 PM ET)
        trading_time = datetime(2024, 3, 18, 22, 0, tzinfo=et_tz)  # Monday 10:00 PM ET
        assert risk_manager.is_trading_hours(trading_time) == True
        
        # Test during trading hours (2:00 PM ET)
        trading_time = datetime(2024, 3, 18, 14, 0, tzinfo=et_tz)  # Monday 2:00 PM ET
        assert risk_manager.is_trading_hours(trading_time) == True
        
        # Test outside trading hours (5:00 PM ET)
        non_trading_time = datetime(2024, 3, 18, 17, 0, tzinfo=et_tz)  # Monday 5:00 PM ET
        assert risk_manager.is_trading_hours(non_trading_time) == False
        
        # Test outside trading hours (8:00 PM ET)
        non_trading_time = datetime(2024, 3, 18, 20, 0, tzinfo=et_tz)  # Monday 8:00 PM ET
        assert risk_manager.is_trading_hours(non_trading_time) == False
        
        # Test exactly at trading start (9:00 PM ET)
        start_time = datetime(2024, 3, 18, 21, 0, tzinfo=et_tz)  # Monday 9:00 PM ET
        assert risk_manager.is_trading_hours(start_time) == True
        
        # Test exactly at trading end (4:00 PM ET)
        end_time = datetime(2024, 3, 18, 16, 0, tzinfo=et_tz)  # Monday 4:00 PM ET
        assert risk_manager.is_trading_hours(end_time) == True

    def test_is_trading_hours_overnight(self, risk_manager):
        """Test is_trading_hours function with overnight trading hours"""
        et_tz = pytz.timezone("US/Eastern")
        
        # Test during overnight trading (2:00 AM ET)
        overnight_time = datetime(2024, 3, 18, 2, 0, tzinfo=et_tz)  # Monday 2:00 AM ET
        assert risk_manager.is_trading_hours(overnight_time) == True
        
        # Test during overnight trading (4:00 AM ET)
        overnight_time = datetime(2024, 3, 18, 4, 0, tzinfo=et_tz)  # Monday 4:00 AM ET
        assert risk_manager.is_trading_hours(overnight_time) == True
        
        # Test during overnight trading (6:00 AM ET)
        overnight_time = datetime(2024, 3, 18, 6, 0, tzinfo=et_tz)  # Monday 6:00 AM ET
        assert risk_manager.is_trading_hours(overnight_time) == True 