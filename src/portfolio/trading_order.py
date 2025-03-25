import pandas as pd
from ibkr_api import Contract


class TradingOrder:

    def __init__(self, 
            order_type,
            action,
            quantity,
            contract, 
            order_id, 
            status, 
            timezone, 
            parent_order_id=None,
            aux_price=None):
        self.order_type = order_type # MKT, STP, LMT
        self.action = action # BUY, SELL
        self.quantity = quantity

        self.ticker = contract.ticker
        self.security = contract.security
        self.exchange = contract.exchange
        self.currency = contract.currency
        self.expiry = contract.expiry

        self.order_id = order_id
        self.parent_order_id = parent_order_id
        self.aux_price = aux_price

        self.status = status
        self.time_sent = pd.Timestamp.now(tz=timezone)
        self.time_filled = None

    def update_post_fill(self, status=None, order_id=None):
        self.order_id = order_id
        self.status = status
        if status == 'Filled':
            self.time_filled = pd.Timestamp.now(tz=self.timezone)

    def get_contract(self):
        return Contract(
            ticker=self.ticker,
            security=self.security,
            exchange=self.exchange,
            currency=self.currency,
            expiry=self.expiry
        )