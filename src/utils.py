import sys
import logging
import pandas as pd
import re
from dateutil import relativedelta
import pytz
import holidays
import configparser


def load_config(config_path: str):
    config = configparser.ConfigParser()
    return config.read(config_path)

def split_tenor_string(entry):
    regex = re.compile("^(?P<numbers>\d*)(?P<letters>\w*)$")
    (numbers, letters) = regex.search(entry).groups()
    numbers = 1 if numbers == "" else numbers
    return (int(numbers), letters or None)

def calc_intraday_time_points(time_interval: str, start_timestamp: pd.Timestamp, end_timestamp: pd.Timestamp) -> int:
    time_diff = (end_timestamp - start_timestamp).total_seconds()
    interval_seconds = pd.Timedelta(time_interval).total_seconds()

    return int(time_diff // interval_seconds) + 1

def timezone_from_calendar(calendar: str) -> str:
    if calendar == "NYSE":
        return pytz.timezone("US/Eastern")
    elif calendar == "LSE":
        return pytz.timezone("Europe/London")
    else:
        raise ValueError("Calendar not recognized")

def market_open(market_calendar='NYSE'):
    # Get the current time in the market's timezone as a pd.Timestamp
    timezone = timezone_from_calendar(market_calendar)
    now = pd.Timestamp.now(tz=timezone)

    market_open = pd.Timestamp(now.year, now.month, now.day, 9, 30, tz=timezone)
    market_close = pd.Timestamp(now.year, now.month, now.day, 16, 0, tz=timezone)

    # Check if it's a weekend
    if now.dayofweek > 4:
        logging.warning(f"Market is closed. It's the weekend. Shutting down...")
        sys.exit()

    # Check if it's a holiday
    market_holidays = holidays.NYSE() if market_calendar == 'NYSE' else holidays.UnitedKingdom()  # Add more calendars as needed
    if now.strftime('%Y-%m-%d') in market_holidays:
        message = f"Market is closed today for {market_holidays.get(now.strftime('%Y-%m-%d'))}."
        message += f"Shutting down..."
        logging.warning(message)
        sys.exit()

    # Check if it's within market hours
    if market_open <= now <= market_close:
        return True
    else:
        logging.warning(f"It's currently outside of trading hours: {now}. Shutting down...")
        sys.exit()


class Period: ...

def shift_date_by_period(period: Period, input_date: pd.Timestamp, direction: str = "+") -> pd.Timestamp:
    if direction not in ("+", "-"):
        raise ValueError("Operation to be performed not recognized")

    # Determine the number of units to adjust
    units = period.units if direction == "+" else -period.units

    # Adjust the input_date based on period.tenor
    if period.tenor.upper() == "W":  # Weeks
        input_date += pd.Timedelta(weeks=units)
    elif period.tenor.upper() == "M":  # Months
        input_date += pd.offsets.DateOffset(months=units)
    elif period.tenor.upper() == "Q":  # Quarters
        input_date += pd.offsets.DateOffset(months=3 * units)
    elif period.tenor.upper() == "SA":  # Semi-Annual
        input_date += pd.offsets.DateOffset(months=6 * units)
    elif period.tenor.upper() == "Y":  # Years
        input_date += pd.offsets.DateOffset(years=units)
    elif period.tenor.upper() == "D":  # Days
        input_date += pd.Timedelta(days=units)
    elif period.tenor.upper() == "B":  # Business Days
        input_date += pd.offsets.BusinessDay(n=units)
    else:
        raise ValueError("Period tenor not recognized")

    return input_date
