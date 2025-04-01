import pytest
import pandas as pd
import pytz
from src.risk_manager import RiskManager


class TestRiskManager:

    @pytest.fixture
    def risk_manager(self):
        """Create a RiskManager instance with trading hours from run.cfg"""
        return RiskManager(
            trading_start_time="2100",  # 9:00 PM ET
            trading_end_time="1600",    # 4:00 PM ET
            timezone="US/Central",
            stop_loss_ticks=120,
            take_profit_ticks=300,
            max_24h_loss=360,
            trading_pause_hours=24,
            mnq_tick_size=0.25
        )

    def test_is_trading_day(self, risk_manager: RiskManager):
        """Test is_trading_day function with various dates"""
        et_tz = risk_manager.timezone
        
        monday = pd.Timestamp("2025-03-17", tz=et_tz)  # Monday
        assert risk_manager.is_trading_day(monday) == True
        
        tuesday = pd.Timestamp("2025-03-18", tz=et_tz)  # Tuesday
        assert risk_manager.is_trading_day(tuesday) == True
        
        wednesday = pd.Timestamp("2025-03-19", tz=et_tz)  # Wednesday
        assert risk_manager.is_trading_day(wednesday) == True

        thursday = pd.Timestamp("2025-03-20", tz=et_tz)  # Thursday
        assert risk_manager.is_trading_day(thursday) == True

        friday = pd.Timestamp("2025-03-21", tz=et_tz)  # Friday
        assert risk_manager.is_trading_day(friday) == True

        saturday = pd.Timestamp("2025-03-22", tz=et_tz)  # Saturday
        assert risk_manager.is_trading_day(saturday) == False

        sunday_morning = pd.Timestamp("2025-03-23 09:00", tz=et_tz)  # Sunday
        assert risk_manager.is_trading_day(sunday_morning) == False

        sunday_afternoon = pd.Timestamp("2025-03-23 18:00", tz=et_tz)  # Sunday
        assert risk_manager.is_trading_day(sunday_afternoon) == False

        sunday_evening = pd.Timestamp("2025-03-23 21:00", tz=et_tz)  # Sunday
        assert risk_manager.is_trading_day(sunday_evening) == True
        
        christmas = pd.Timestamp("2025-12-25", tz=et_tz)  # Christmas
        assert risk_manager.is_trading_day(christmas) == False
        
        new_year = pd.Timestamp("2025-01-01", tz=et_tz)  # New Year's Day
        assert risk_manager.is_trading_day(new_year) == False

    def test_is_trading_hours(self, risk_manager: RiskManager):
        """Test is_trading_hours function with various times"""
        et_tz = risk_manager.timezone
        
        # Test during trading hours (10:00 PM ET)
        trading_time = pd.Timestamp("2025-03-18 22:00", tz=et_tz)  # Tuesday 10:00 PM ET
        assert risk_manager.is_trading_hours(trading_time) == True
        
        # Test during trading hours (2:00 PM ET)
        trading_time = pd.Timestamp("2025-03-18 14:00", tz=et_tz)  # Tuesday 2:00 PM ET
        assert risk_manager.is_trading_hours(trading_time) == True
        
        # Test outside trading hours (5:00 PM ET)
        non_trading_time = pd.Timestamp("2025-03-18 17:00", tz=et_tz)  # Tuesday 5:00 PM ET
        assert risk_manager.is_trading_hours(non_trading_time) == False
        
        # Test outside trading hours (8:00 PM ET)
        non_trading_time = pd.Timestamp("2025-03-18 20:00", tz=et_tz)  # Tuesday 8:00 PM ET
        assert risk_manager.is_trading_hours(non_trading_time) == False
        
        # Test exactly at trading start (9:00 PM ET)
        start_time = pd.Timestamp("2025-03-18 21:00", tz=et_tz)  # Tuesday 9:00 PM ET
        assert risk_manager.is_trading_hours(start_time) == True
        
        # Test exactly at trading end (4:00 PM ET)
        end_time = pd.Timestamp("2025-03-18 16:00", tz=et_tz)  # Tuesday 4:00 PM ET
        assert risk_manager.is_trading_hours(end_time) == False

    def test_is_trading_hours_overnight(self, risk_manager: RiskManager):
        """Test is_trading_hours function with overnight trading hours"""
        et_tz = risk_manager.timezone
        
        # Test during overnight trading (2:00 AM ET)
        overnight_time = pd.Timestamp("2025-03-17 02:00", tz=et_tz)  # Monday 2:00 AM ET
        assert risk_manager.is_trading_hours(overnight_time) == True
        
        # Test during overnight trading (4:00 AM ET)
        overnight_time = pd.Timestamp("2025-03-17 04:00", tz=et_tz)  # Monday 4:00 AM ET
        assert risk_manager.is_trading_hours(overnight_time) == True
        
        # Test during overnight trading (6:00 AM ET)
        overnight_time = pd.Timestamp("2025-03-17 06:00", tz=et_tz)  # Monday 6:00 AM ET
        assert risk_manager.is_trading_hours(overnight_time) == True 