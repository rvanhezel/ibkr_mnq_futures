from ibapi.contract import Contract
from ibapi.order import Order
import pandas as pd
from src.utilities.utils import get_third_friday


def order_from_dict(order_dict: dict) -> Order:
    """Convert an order dictionary (from database) into an IBKR Order object
    
    Args:
        order_dict (dict): Dictionary containing order details from database
            Expected keys:
            - order_id: int
            - action: str
            - order_type: str
            - quantity: int
            - aux_price: float
            - lmt_price: float
            - parent_id: int
            - transmit: bool
            - created_timestamp: str
            
    Returns:
        Order: IBKR Order object with the specified parameters
    """
    order = Order()
    
    # Set all order attributes from the dictionary
    order.orderId = order_dict['order_id']
    order.action = order_dict['action']
    order.orderType = order_dict['order_type']
    order.totalQuantity = order_dict['quantity']
    order.auxPrice = order_dict['aux_price']
    order.lmtPrice = order_dict['lmt_price']
    order.parentId = order_dict['parent_id']
    order.transmit = order_dict['transmit']
    
    return order


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