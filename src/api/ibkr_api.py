import datetime
import threading
import time
import pytz
from ibapi.client import EClient
from ibapi.wrapper import EWrapper, OrderState
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_cancel import OrderCancel
from ibapi.common import BarData
import logging
import socket
import pandas as pd
import os
from src.portfolio.trading_order import TradingOrder
from src.utilities.utils import get_third_friday


class IBConnection(EWrapper, EClient):
    
    def __init__(self, host, port, client_id, timeout):
        # Suppress IBKR API's internal debug messages
        logging.getLogger('ibapi').setLevel(logging.WARNING)
        logging.getLogger('ibapi.wrapper').setLevel(logging.WARNING)
        logging.getLogger('ibapi.client').setLevel(logging.WARNING)
        
        EClient.__init__(self, self)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self.account_id = os.getenv('IBKR_ACCOUNT_ID')

        # Order ID and Request ID needed for the IBKR API
        self.next_order_id = None
        self.next_req_id = 0

        self.contract_details = {}
        self.positions = {}
        self.historical_data = {}
        self.pnl_data = {}
        self.account_summary = {}
        self.position_data = {}
        self.order_statuses = {}
        self.open_orders = {}

        # self.current_contract = None
        self.connected = False
        self.open_orders_requested = False

        # Lock to ensure thread-safe operations for tracking request ids
        self.lock = threading.Lock()


    def connect(self):
        """Connect to Interactive Brokers TWS/Gateway"""
        try:
            super().connect(self.host, self.port, self.client_id)
            thread = threading.Thread(target=self.run)
            thread.start()
            
            # Wait for nextValidId to ensure connection is established
            timeout = self.timeout
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
    
    def get_contract_details(self, contract):
        """Get contract details for a specific contract"""
        req_id = self.get_next_req_id()
        self.contract_details.clear()
        self.reqContractDetails(req_id, contract)

        # Wait for contract details
        timeout = self.timeout
        while req_id not in self.contract_details and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        if req_id not in self.contract_details:
            raise Exception("Failed to get contract details")

        return self.contract_details[req_id]

    def contractDetails(self, reqId: int, contractDetails):
        """Callback for contract details"""
        self.contract_details[reqId] = contractDetails

    # def should_rollover(self, days_before_expiry):
    #     """Check if it's time to roll over to the next contract"""
    #     if not self.current_contract:
    #         return True

    #     req_id = self.get_next_req_id()
    #     self.contract_details.clear()
    #     self.reqContractDetails(req_id, self.current_contract)

    #     # Wait for contract details
    #     timeout = self.timeout
    #     while req_id not in self.contract_details and timeout > 0:
    #         time.sleep(0.1)
    #         timeout -= 0.1

    #     if req_id not in self.contract_details:
    #         return True

    #     details = self.contract_details[req_id]
    #     expiry = datetime.datetime.strptime(details.contract.lastTradeDateOrContractMonth, '%Y%m%d')
    #     expiry = pytz.timezone('US/Eastern').localize(expiry)
        
    #     now = datetime.datetime.now(pytz.timezone('US/Eastern'))
    #     days_to_expiry = (expiry - now).days
        
    #     return days_to_expiry <= days_before_expiry

    # def rollover_contract(self, ticker, exchange, ccy):
    #     """Roll over to the next contract"""
    #     self.current_contract = None
    #     return self.get_current_contract(ticker, exchange, ccy)

    def get_historical_data(self, contract, duration='1 D', bar_size='1 min', timezone='US/Eastern', RTH=False):
        """Get historical data for the current contract"""
        req_id = self.get_next_req_id()
        self.historical_data[req_id] = []
        
        self.reqHistoricalData(
            req_id,
            contract,
            "",  # empty string for current time
            duration,
            bar_size,
            "TRADES",  # Use actual trade prices
            False,  # useRTH
            1,  # formatDate
            False,  # keepUpToDate
            []  # chartOptions
        )

        # Wait for historical data
        timeout = self.timeout
        while not self.historical_data[req_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
    
        if self.historical_data[req_id]:
            new_bars = self.historical_data[req_id]
            
            new_bars_df = pd.DataFrame({
                'datetime': [pd.to_datetime(bar.date, format='%Y%m%d %H:%M:%S %Z') for bar in new_bars],
                'open': [bar.open for bar in new_bars],
                'high': [bar.high for bar in new_bars],
                'low': [bar.low for bar in new_bars],
                'close': [bar.close for bar in new_bars],
                'volume': [bar.volume for bar in new_bars]
            })
            new_bars_df.set_index('datetime', inplace=True)
            new_bars_df.index = new_bars_df.index.tz_convert(timezone)

            self.historical_data[req_id] = new_bars_df

        return self.historical_data.pop(req_id, [])


    def historicalData(self, reqId: int, bar: BarData):
        """Callback for historical data"""
        if reqId in self.historical_data:
            self.historical_data[reqId].append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback for end of historical data"""
        # logging.info(f"Historical data end: {reqId}, {start}, {end}")
        pass

    def place_trading_order(self, trading_order: TradingOrder):
        """Place a trading order"""
        logging.info(f"Placing trading order: {trading_order}")
        
        order = Order()
        order.action = trading_order.action
        order.totalQuantity = trading_order.quantity
        order.orderType = trading_order.order_type
        order.transmit = trading_order.transmit


        if order.orderType == "LMT":
            order.lmtPrice = trading_order.aux_price
            
        elif order.orderType == "STP":
            order.auxPrice = trading_order.aux_price
            order.outsideRth = True

        elif order.orderType == "MKT":
            pass
        else:
            raise TypeError(f"Invalid order type: {order.orderType}")

        contract = Contract()
        contract.symbol = trading_order.symbol
        contract.secType = trading_order.security
        contract.exchange = trading_order.exchange
        contract.currency = trading_order.currency
        contract.lastTradeDateOrContractMonth = trading_order.expiry
        
        order_id = self.next_order_id
        self.next_order_id += 1

        order.orderId = order_id
        
        self.order_statuses[order_id] = {}
        self.placeOrder(order_id, contract, order)

        timeout = self.timeout
        while not self.order_statuses[order_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        trading_order.update_post_fill(status=self.order_statuses[order_id].get('status', None), order_id=order_id)


    def place_market_order(self, contract, action, quantity):
        """Place a market order"""
        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "MKT"
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.order_statuses[order_id] = {}
        self.placeOrder(order_id, contract, order)

        timeout = self.timeout
        while not self.order_statuses[order_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        return order_id, self.order_statuses[order_id]

    def orderStatus(self, orderId: int, status: str, filled: float,
                   remaining: float, avgFillPrice: float, permId: int,
                   parentId: int, lastFillPrice: float, clientId: int,
                   whyHeld: str, mktCapPrice: float):
        """Callback for order status updates"""
        self.order_statuses[orderId] = {
                'status': status,
                'filled': filled,
                'remaining': remaining,
                'avg_fill_price': avgFillPrice,
                'last_fill_price': lastFillPrice,
                'parent_id': parentId,
                'why_held': whyHeld,
                'mkt_cap_price': mktCapPrice,
                'perm_id': permId,
                'client_id': clientId
        }

    def get_order_status(self, order_id: int) -> dict:
        """Get the current status of an order"""
        return self.order_statuses.get(order_id, None)
    
    def update_order_status(self, order: TradingOrder):
        """Update the status of an order"""
        order.status = self.get_order_status(order.order_id).get('status', None)

    def place_stop_loss_order(self, contract, parent_order_id, quantity, stop_price):
        """Place a stop-loss order"""
        order = Order()
        order.action = "SELL"
        order.totalQuantity = quantity
        order.orderType = "STP"
        order.auxPrice = stop_price
        order.parentId = parent_order_id
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.order_statuses[order_id] = {}
        self.placeOrder(order_id, contract, order)

        timeout = self.timeout
        while not self.order_statuses[order_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        return order_id, self.order_statuses[order_id]

    def place_profit_taker_order(self, contract, parent_order_id, quantity, profit_price):
        """Place a profit-taking limit order"""
        order = Order()
        order.action = "SELL"
        order.totalQuantity = quantity
        order.orderType = "LMT"
        order.lmtPrice = profit_price
        order.parentId = parent_order_id
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.order_statuses[order_id] = {}
        self.placeOrder(order_id, contract, order)

        timeout = self.timeout
        while not self.order_statuses[order_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        return order_id, self.order_statuses[order_id]

    def error(self, req_id, error_code, error_string, misc=None):

        if error_code in [2103, 2104, 2105, 2106, 2119, 2158]:
            logging.info(f"({error_code}) {error_string}{' ' + str(misc) if misc is not None else ''}")

        elif error_code == 110:
            msg = f"Error {error_code}: Submitted prices must be rounded to 2 decimal places."
            msg += f"\n Please check TWS and Discard/Delete any related orders with a 'Transmit' status."
            logging.error(msg)

        else:
            logging.error(f"Error {error_code}: {error_string}{' ' + str(misc) if misc is not None else ''}")

    def get_positions(self):
        """Get current portfolio positions"""
        self.positions[self.account_id] = []
        self.reqPositions() 

        timeout = self.timeout
        while not self.positions[self.account_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        return self.positions.pop(self.account_id, [])
    
    def position(self, account: str, contract: Contract, pos: float, avg_cost: float):
        """Callback for position updates"""
        if account in self.positions:
            self.positions[account].append({
                'contract': contract,
                'position': pos,
                'avg_cost': avg_cost
            })

    def get_account_summary(self):
        """Get all account summary information using the $LEDGER tag"""
        req_id = self.get_next_req_id()
        self.account_summary[req_id] = {}
        
        self.reqAccountSummary(req_id, "All", "$LEDGER")

        timeout = self.timeout
        while timeout > 0 and not self.account_summary[req_id]:
            time.sleep(0.1)
            timeout -= 0.1

        return self.account_summary[req_id]

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary updates"""
        if reqId in self.account_summary:
            self.account_summary[reqId][tag] = {
                'account': account,
                'value': value,
                'currency': currency
            }

    def req_position_pnl(self, contract_id):
        """Request PnL for a specific position"""
        req_id = self.get_next_req_id()
        self.pnl_data[req_id] = None
        self.reqPnLSingle(req_id, self.account_id, "", contract_id)

        # Wait for response
        timeout = self.timeout
        while not self.pnl_data[req_id] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1

        return self.pnl_data.pop(req_id, None)

    def pnlSingle(
            self, 
            reqId: int, 
            pos: float, 
            dailyPnL: float, 
            unrealizedPnL: float, 
            realizedPnL: float, 
            value: float):
        """Callback for PnL single position"""
        if reqId in self.pnl_data:
            self.pnl_data[reqId] = {
                'position': pos,
                'daily_pnl': dailyPnL,
                'unrealized_pnl': unrealizedPnL,
                'realized_pnl': realizedPnL,
                'marketvalue': value
            }

    def cancel_pnl_request(self, req_id):
        """Cancel a PnL request"""
        if req_id in self.pnl_data:
            self.cancelPnLSingle(req_id)
            del self.pnl_data[req_id] 
            
    def cancel_all_pnl_requests(self):
        """Cancel all active PnL requests"""
        for req_id in self.pnl_data:
            self.cancelPnLSingle(req_id)
            del self.pnl_data[req_id]

    def get_latest_mid_price(self, contract, delayed=False):
        """Get the latest mid price for a contract
        
        Args:
            contract (Contract): The contract to get the mid price for
            delayed (bool): Whether to use delayed market data
            
        Returns:
            float: The latest mid price, or None if not available
        """
        req_id = self.get_next_req_id()
        self.market_data = {}
        
        # Request market data with appropriate generic tick list
        if delayed:
            # For futures, use tick type 587 for delayed price
            self.reqMktData(req_id, contract, "587", False, False, [])
        else:
            self.reqMktData(req_id, contract, "", False, False, [])
        
        # Wait for market data
        timeout = self.timeout
        while req_id not in self.market_data and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
            
        if req_id in self.market_data:
            data = self.market_data[req_id]
            # Calculate mid price from bid and ask
            if data.get('bid') is not None and data.get('ask') is not None:
                mid_price = (data['bid'] + data['ask']) / 2
                # Cancel market data subscription
                self.cancelMktData(req_id)
                return mid_price
            # If no bid/ask, try to use last price
            elif data.get('last') is not None:
                self.cancelMktData(req_id)
                return data['last']
                
        # Cancel market data subscription if we haven't already
        self.cancelMktData(req_id)
        return None

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for price updates"""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
            
        if tickType == 1:  # Bid
            self.market_data[reqId]['bid'] = price
        elif tickType == 2:  # Ask
            self.market_data[reqId]['ask'] = price
        elif tickType == 4:  # Last
            self.market_data[reqId]['last'] = price


    def place_orders(self, orders:list[Order], contract:Contract):
        """Place multiple orders"""
        for order in orders:
            self.order_statuses[order.orderId] = {}
            self.placeOrder(order.orderId, contract, order)

            timeout = self.timeout
            while not self.order_statuses[order.orderId] and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1


    def create_bracket_order(self,
                             action:str,
                             quantity:float, 
                             take_profit_limit_price:float, 
                             stop_loss_price:float):
        """Create a bracket order"""
        parent_order_id = self.next_order_id
        self.next_order_id += 1

        parent = Order()
        parent.orderId = parent_order_id
        parent.action = action
        parent.orderType = "MKT"
        parent.totalQuantity = quantity
        parent.transmit = False

        takeProfit = Order()
        takeProfit.orderId = self.next_order_id
        takeProfit.action = "SELL" if action == "BUY" else "BUY"
        takeProfit.orderType = "LMT"
        takeProfit.totalQuantity = quantity
        takeProfit.lmtPrice = take_profit_limit_price
        takeProfit.parentId = parent_order_id
        takeProfit.transmit = False

        self.next_order_id += 1

        stopLoss = Order()
        stopLoss.orderId = self.next_order_id
        stopLoss.action = "SELL" if action == "BUY" else "BUY" 
        stopLoss.orderType = "STP"
        stopLoss.auxPrice = stop_loss_price
        stopLoss.totalQuantity = quantity
        stopLoss.parentId = parent_order_id
        stopLoss.transmit = True

        self.next_order_id += 1

        bracketOrder = [parent, takeProfit, stopLoss]
        return bracketOrder

    # def get_contract_from_order_id(self, order_id: int) -> Contract:
    #     req_id = self.get_next_req_id()
    #     self.open_orders[req_id] = None
        
    #     # Request all open orders
    #     self.reqOpenOrders()
        
    #     # Wait for response
    #     timeout = self.timeout
    #     while self.order_contracts[req_id] is None and timeout > 0:
    #         time.sleep(0.1)
    #         timeout -= 0.1
            
    #     return self.order_contracts.get(req_id, {}).get('contract')

    def request_open_orders(self):
        if not self.open_orders_requested:
            self.reqOpenOrders()
            self.open_orders_requested = True

    def get_open_order(self, order_id: int) -> Order:
        """Get the open order for a specific order ID"""
        return self.open_orders.get(order_id, None)

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState: OrderState):
        """Callback for open orders"""
        self.open_orders[orderId] = {
            'contract': contract,
            'order': order,
            'order_state': orderState
            }

    def openOrderEnd(self):
        """Callback for end of open orders"""
        pass

    def cancel_order(self, order_id: int):
        """Cancel a specific order by its ID. OrderStatus callback is used"""
        self.cancelOrder(order_id, OrderCancel())
  

    def realtimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        # Convert Unix timestamp to pandas Timestamp
        timestamp = pd.Timestamp.fromtimestamp(time)
        print(
            f"ReqId: {reqId}, "
            f"Time: {timestamp}, "
            f"Open: {open_}, "
            f"High: {high}, "
            f"Low: {low}, "
            f"Close: {close}, "
            f"Volume: {volume}, "
            f"Wap: {wap}, "
            f"Count: {count}"
        )
