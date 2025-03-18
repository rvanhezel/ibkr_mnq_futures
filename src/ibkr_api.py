import datetime
import threading
import time
import pytz
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
import logging
import socket



class IBConnection(EWrapper, EClient):
    
    def __init__(self, host, port, client_id):
        EClient.__init__(self, self)
        self.host = host
        self.port = port
        self.client_id = client_id

        # Order ID and Request ID needed for the IBKR API
        self.next_order_id = None
        self.next_req_id = 0

        self.contract_details = {}
        self.positions = {}
        self.historical_data = {}

        self.current_contract = None
        self.connected = False

        # Lock to ensure thread-safe operations for tracking request ids
        self.lock = threading.Lock()

    def connect(self):
        """Connect to Interactive Brokers TWS/Gateway"""
        try:
            super().connect(self.host, self.port, self.client_id)
            thread = threading.Thread(target=self.run)
            thread.start()
            
            # Wait for nextValidId to ensure connection is established
            timeout = 10
            while self.next_order_id is None and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            self.connected = self.next_order_id is not None
            if self.connected:
                logging.info("Successfully connected to Interactive Brokers")
            else:
                raise ConnectionError("Connection timed out waiting for order ID")
                
        except (TimeoutError, ConnectionRefusedError, socket.error, ConnectionError) as e:
            self.connected = False
            raise ConnectionError(f"{str(e)}")
        
        except Exception as e:
            logging.error(f"Unexpected error while connecting to Interactive Brokers: {str(e)}")
            self.connected = False
            raise

    def disconnect(self):
        """Disconnect from Interactive Brokers"""
        if self.connected:
            self.done = True
            super().disconnect()
            self.connected = False
            logging.info("Disconnected from Interactive Brokers")

    def nextValidId(self, orderId: int):
        """Callback for next valid order ID"""
        self.next_order_id = orderId

    def get_next_req_id(self):
        """Get next request ID"""
        with self.lock:
            self.next_req_id += 1
            return self.next_req_id

    def get_current_contract(self, ticker, exchange, ccy):
        """Get the current active MNQ futures contract"""
        if self.current_contract is None:
            self.current_contract = self._get_active_contract(ticker, exchange, ccy)
        return self.current_contract

    def _get_active_contract(self, ticker, exchange, ccy):
        """Determine the active contract based on current date"""
        today = datetime.datetime.now(pytz.UTC)
        
        # Contract months (March, June, September, December)
        contract_months = [3, 6, 9, 12]
        
        # Find the next contract month
        current_month = today.month
        current_year = today.year
        
        next_contract_month = None
        next_contract_year = current_year
        
        for month in contract_months:
            if month > current_month:
                next_contract_month = month
                break
        
        if next_contract_month is None:
            next_contract_month = contract_months[0]  # March
            next_contract_year += 1

        # Create the contract
        contract = Contract()
        contract.symbol = ticker
        contract.secType = "FUT"
        contract.exchange = exchange
        contract.currency = ccy
        contract.lastTradeDateOrContractMonth = f"{next_contract_year}{next_contract_month:02d}"

        # Request contract details
        req_id = self.get_next_req_id()
        self.contract_details.clear()
        self.reqContractDetails(req_id, contract)

        # Wait for contract details
        timeout = 10
        while req_id not in self.contract_details and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        if req_id not in self.contract_details:
            raise Exception("Failed to get contract details")

        return contract

    def contractDetails(self, reqId: int, contractDetails):
        """Callback for contract details"""
        self.contract_details[reqId] = contractDetails

    def should_rollover(self, days_before_expiry):
        """Check if it's time to roll over to the next contract"""
        if not self.current_contract:
            return True

        req_id = self.get_next_req_id()
        self.contract_details.clear()
        self.reqContractDetails(req_id, self.current_contract)

        # Wait for contract details
        timeout = 10
        while req_id not in self.contract_details and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        if req_id not in self.contract_details:
            return True

        details = self.contract_details[req_id]
        expiry = datetime.datetime.strptime(details.contract.lastTradeDateOrContractMonth, '%Y%m%d')
        expiry = pytz.timezone('US/Eastern').localize(expiry)
        
        now = datetime.datetime.now(pytz.timezone('US/Eastern'))
        days_to_expiry = (expiry - now).days
        
        return days_to_expiry <= days_before_expiry

    def rollover_contract(self, ticker, exchange, ccy):
        """Roll over to the next contract"""
        self.current_contract = None
        return self.get_current_contract(ticker, exchange, ccy)

    def get_historical_data(self, ticker, exchange, ccy, duration='1 D', bar_size='1 min'):
        """Get historical data for the current contract"""
        if not self.current_contract:
            self.get_current_contract(ticker, exchange, ccy)

        req_id = self.get_next_req_id()
        self.historical_data[req_id] = []
        
        self.reqHistoricalData(
            req_id,
            self.current_contract,
            "",  # empty string for current time
            duration,
            bar_size,
            "TRADES",
            1,  # useRTH
            1,  # formatDate
            False,  # keepUpToDate
            []  # chartOptions
        )

        # Wait for historical data
        timeout = 10
        while not self.historical_data[req_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        return self.historical_data.pop(req_id, [])

    def historicalData(self, reqId: int, bar: BarData):
        """Callback for historical data"""
        if reqId in self.historical_data:
            self.historical_data[reqId].append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback for end of historical data"""
        pass

    def place_market_order(self, action, quantity):
        """Place a market order"""
        if not self.current_contract:
            self.get_current_contract()

        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "MKT"
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.placeOrder(order_id, self.current_contract, order)
        return order_id

    def place_stop_loss_order(self, parent_order_id, quantity, stop_price):
        """Place a stop-loss order"""
        if not self.current_contract:
            self.get_current_contract()

        order = Order()
        order.action = "SELL"
        order.totalQuantity = quantity
        order.orderType = "STP"
        order.auxPrice = stop_price
        order.parentId = parent_order_id
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.placeOrder(order_id, self.current_contract, order)
        return order_id

    def place_profit_taker_order(self, parent_order_id, quantity, profit_price):
        """Place a profit-taking limit order"""
        if not self.current_contract:
            self.get_current_contract()

        order = Order()
        order.action = "SELL"
        order.totalQuantity = quantity
        order.orderType = "LMT"
        order.lmtPrice = profit_price
        order.parentId = parent_order_id
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.placeOrder(order_id, self.current_contract, order)
        return order_id

    def error(self, req_id, error_code, error_string, misc=None):
        if error_code in [2103, 2104, 2105, 2106, 2119, 2158]:
            logging.info(f"({error_code}) {error_string}{' ' + str(misc) if misc is not None else ''}")
        else:
            logging.error(f"Error {error_code}: {error_string}{' ' + str(misc) if misc is not None else ''}") 