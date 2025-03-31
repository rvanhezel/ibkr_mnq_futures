from datetime import datetime
import pandas as pd


class Position:
    def __init__(self, 
                 ticker: str,
                 security: str,
                 currency: str,
                 expiry: str,
                 contract_id: int,
                 quantity: int,
                 avg_price: float,
                 timezone: str):
                #  stop_loss_price: float = None,
                #  take_profit_price: float = None):
        """Initialize a Position object
        
        Args:
            ticker (str): The ticker symbol (e.g., 'MNQ')
            security (str): The security type (e.g., 'FUT')
            currency (str): The currency (e.g., 'USD')
            expiry (str): The contract expiry date
            contract_id (int): The IBKR contract ID
            quantity (int): The quantity of contracts
            avg_price (float): The average entry price
            timezone (str): The timezone for timestamps (default: 'UTC')
            stop_loss_price (float): The stop loss price
            take_profit_price (float): The take profit price
        """
        self.ticker = ticker
        self.security = security
        self.currency = currency
        self.expiry = expiry
        self.contract_id = contract_id
        self.quantity = quantity
        self.avg_price = avg_price
        # self.stop_loss_price = stop_loss_price
        # self.take_profit_price = take_profit_price

        # self.status = "OPEN"  # OPEN, CLOSED
        self.time_opened = pd.Timestamp.now(tz=timezone)
        # self.time_closed = None

        # self.market_value = None
        # self.unrealized_pnl = None

    def __str__(self):
        """Return a string representation of the Position object."""
        return (
            f"Position(\n"
            f"  Ticker: {self.ticker}\n"
            f"  Security: {self.security}\n"
            f"  Currency: {self.currency}\n"
            f"  Expiry: {self.expiry}\n"
            f"  Contract ID: {self.contract_id}\n"
            f"  Quantity: {self.quantity}\n"
            f"  Avg Price: {self.avg_price:.2f} {self.currency}\n"
            # f"  Stop Loss: {f'{self.stop_loss_price:.2f}' if self.stop_loss_price is not None else 'None'}\n"
            # f"  Take Profit: {f'{self.take_profit_price:.2f}' if self.take_profit_price is not None else 'None'}\n"
            f"  Status: {self.status}\n"
            f"  Time Opened: {self.time_opened.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )

