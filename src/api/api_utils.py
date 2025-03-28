from ibapi.contract import Contract
import pandas as pd
from src.utilities.utils import get_third_friday



def get_current_contract(ticker, exchange, ccy, roll_contract_days_before, timezone):
    """Determine the active contract based on current date and rollover rules
    
    Args:
        ticker (str): The ticker symbol (e.g., 'MNQ')
        exchange (str): The exchange (e.g., 'CME')
        ccy (str): The currency (e.g., 'USD')
        roll_contract_days_before (int): Days before expiry to roll to next contract
        timezone (str): The timezone to use for date calculations
        
    Returns:
        Contract: The current active contract
    """
    today = pd.Timestamp.now(tz=timezone)
    
    # Contract months (March, June, September, December)
    contract_months = [3, 6, 9, 12]
    current_year = today.year
    
    contract_dates = []
    for year in [current_year, current_year + 1]:
        for month in contract_months:
            expiry_date = get_third_friday(year, month, timezone)
            contract_dates.append(expiry_date)
    
    contract_dates.sort()
    
    for expiry_date in contract_dates:
        if today.date() < (expiry_date - pd.Timedelta(days=roll_contract_days_before)).date():
            contract = Contract()
            contract.symbol = ticker
            contract.secType = "FUT"
            contract.exchange = exchange
            contract.currency = ccy
            contract.lastTradeDateOrContractMonth = expiry_date.strftime("%Y%m")
            return contract
            
    # If we get here, something went wrong
    raise ValueError("Could not determine the current contract")