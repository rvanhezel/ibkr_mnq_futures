import pandas as pd
from ibapi.contract import Contract


class TradingOrder:

    def __init__(self, 
            order_type,
            action,
            quantity,
            contract: Contract, 
            order_id, 
            status, 
            timezone, 
            parent_order_id=None,
            aux_price=None,
            transmit=True):
        self.order_type = order_type # MKT, STP, LMT
        self.action = action # BUY, SELL
        self.quantity = quantity

        self.symbol = contract.symbol
        self.security = contract.secType
        self.exchange = contract.exchange   
        self.currency = contract.currency
        self.expiry = contract.lastTradeDateOrContractMonth

        self.order_id = order_id
        self.parent_order_id = parent_order_id
        self.aux_price = aux_price
        self.transmit = transmit

        self.status = status
        self.timezone = timezone
        self.time_sent = pd.Timestamp.now(tz=self.timezone)
        self.time_filled = None

    def update_post_fill(self, status=None, order_id=None):
        self.order_id = order_id
        self.status = status
        if status == 'Filled':
            self.time_filled = pd.Timestamp.now(tz=self.timezone)

    @property
    def contract(self):
        contract = Contract()
        contract.symbol = self.symbol
        contract.secType = self.security
        contract.exchange = self.exchange
        contract.currency = self.currency
        contract.lastTradeDateOrContractMonth = self.expiry
        return contract
    
    @contract.setter
    def contract(self, contract: Contract):
        raise AttributeError("Contract is read-only")

    def __str__(self):
        return (
            f"TradingOrder("
            f"order_id={self.order_id}, "
            f"parent_order_id={self.parent_order_id}, "
            f"order_type='{self.order_type}', "
            f"action='{self.action}', "
            f"quantity={self.quantity}, "
            f"ticker='{self.symbol}', "
            f"security='{self.security}', "
            f"exchange='{self.exchange}', "
            f"currency='{self.currency}', "
            f"expiry='{self.expiry}', "
            f"status='{self.status}', "
            f"time_sent={self.time_sent}, "
            f"time_filled={self.time_filled}, "
            f"aux_price={self.aux_price}, "
            f"transmit={self.transmit}"
            f")"
        )