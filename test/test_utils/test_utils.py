import pytest
import pandas as pd
from src.utilities.utils import trading_day_start_time_ts



class TestUtils:

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method."""
        self.timezone = "US/Eastern"

    def test_trading_day_start_time_morning(self):
        """Test trading day start time for morning trading"""
        start_time = "0930"
        expected_time = pd.Timestamp("2025-03-01 09:30:00", tz=self.timezone)
        now_test_date = pd.Timestamp("2025-03-01 11:00:00", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: now_test_date)

            result = trading_day_start_time_ts(start_time, self.timezone, day_offset=0)

        assert result == expected_time

    def test_trading_day_start_time_evening(self):
        """Test trading day start time for evening trading"""
        start_time = "2100"
        expected_time = pd.Timestamp("2025-03-01 21:00:00", tz=self.timezone)
        now_test_date = pd.Timestamp("2025-03-02 11:00:00", tz=self.timezone)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('pandas.Timestamp.now', lambda tz=None: now_test_date)

            result = trading_day_start_time_ts(start_time, self.timezone, day_offset=-1)
        assert result == expected_time
