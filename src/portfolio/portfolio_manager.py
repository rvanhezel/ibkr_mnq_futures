import copy
from src.portfolio.position import Position
import pandas as pd
from typing import List, Dict, Optional
from ibapi.order import Order
from ibapi.contract import Contract
import os
from src.portfolio.position import Position
from src.api.ibkr_api import IBConnection
from src.configuration import Configuration
import logging
import time
from src.db.database import Database
from src.api.api_utils import get_current_contract, order_from_dict
from src.utilities.utils import trading_day_start_time_ts


class PortfolioManager:

    def __init__(self, config: Configuration, api: IBConnection, db: Database):
        self.config = config
        self.api = api
        self.db = db

        self.positions: List[Position] = []
        self.orders: List[List[(Order, bool)]] = []       #list of bracket orders (list of 3 orders). bool is for whether an order has been resubmitted when cancelled
        self.order_statuses: Dict[int, Dict] = {}          #order id -> order status

    def _get_order_status(self, order_id: int):
        """Get the order status for a given order id. Required to persist order
        statuses after the API or app disconnects. Check the API first, then check the local status. 
        Filled orders are not stored in the API after restart but unfilled are."""
        if order_id in self.api.order_statuses:
            return self.api.order_statuses[order_id]
        elif order_id in self.order_statuses:
            return self.order_statuses[order_id]
        else:
            logging.error(f"Order {order_id} not found in API or local order statuses")
            return None
        
    def update_positions(self):
        """Update the positions from the API."""
        logging.info(f"{self.__class__.__name__}: Updating positions from orders.")
        logging.debug(f"{self.__class__.__name__}: There are {self._total_orders()} orders")

        for bracket_order in self.orders:
            for order, _ in bracket_order:
                logging.info(f"Order: {str(order)}")
        
        self.api.request_open_orders()

        if len(self.orders) > 0:
            filled_count, cancelled_count, pending_count = self._get_order_status_count()
            logging.debug(f"Order statuses: {filled_count} filled, {cancelled_count} cancelled, {pending_count} pending")

        for bracket_idx, bracket_order in enumerate(self.orders):
            
            for order_idx, (order, already_handled) in enumerate(bracket_order):
                
                order_status = self._get_order_status(order.orderId)
                
                if order_status['status'] == 'Filled' and not already_handled:

                    order_details = self.api.get_open_order(order.orderId)
                    contract = order_details['contract']
                    
                    if order.orderType == 'MKT' and order.action == 'BUY':

                        if len(self.positions) == 0:
                            logging.info(f"Buy order filled, creating new position.")

                            position = Position(
                            ticker=contract.symbol,
                            security=contract.secType,
                            currency=contract.currency,
                            expiry=contract.lastTradeDateOrContractMonth,
                            contract_id=contract.conId,
                            quantity=int(order.totalQuantity),
                            avg_price=order_status['avg_fill_price'],
                            timezone=self.config.timezone,
                            )

                            self.positions.append(position)
                            self.db.add_position(position)

                            self.db.update_order_status(order.orderId, order_status)

                            self.orders[bracket_idx][order_idx] = (order, True)

                        else:
                            logging.info(f"Buy order filled, updating position.")

                            position = copy.deepcopy(self.positions[-1])

                            total_quantity = position.quantity + int(order.totalQuantity)
                            avg_price = position.quantity * position.avg_price
                            avg_price += int(order.totalQuantity) * order_status['avg_fill_price'] 
                            avg_price /= total_quantity

                            position.quantity = total_quantity
                            position.avg_price = avg_price

                            self.orders[bracket_idx][order_idx] = (order, True)
                            
                            self.positions.append(position)
                            self.db.add_position(position)

                            self.db.update_order_status(order.orderId, order_status)

                    elif order.orderType == 'MKT' and order.action == 'SELL':

                        logging.info(f"Market sell order filled, updating position.")

                        position = copy.deepcopy(self.positions[-1])

                        total_quantity = position.quantity - int(order.totalQuantity)
                        avg_price = position.quantity * position.avg_price
                        avg_price += int(order.totalQuantity) * order_status['avg_fill_price'] 
                        avg_price /= (position.quantity + int(order.totalQuantity))

                        position.quantity = total_quantity
                        position.avg_price = avg_price
                        
                        self.orders[bracket_idx][order_idx] = (order, True)

                        self.positions.append(position)
                        self.db.add_position(position)

                        self.db.update_order_status(order.orderId, order_status)
                    
                    elif order.orderType == 'STP' or order.orderType == 'LMT' and order.action == 'SELL':

                        logging.info(f"{order.orderType} order filled, updating position.")

                        position = copy.deepcopy(self.positions[-1])

                        total_quantity = position.quantity - int(order.totalQuantity)
                        avg_price = position.quantity * position.avg_price
                        avg_price += int(order.totalQuantity) * order_status['avg_fill_price'] 
                        avg_price /= (position.quantity + int(order.totalQuantity))

                        position.quantity = total_quantity
                        position.avg_price = avg_price

                        self.orders[bracket_idx][order_idx] = (order, True)

                        self.positions.append(position)
                        self.db.add_position(position)

                        self.db.update_order_status(order.orderId, order_status)

                    else:

                        raise TypeError(f"Order type {order.orderType} with action {order.action} is not supported.")
        
        msg = f"{self.__class__.__name__}: Finished updating positions from orders."
        msg += f" Currently {len(self.positions)} position(s)."

        logging.info(msg)
        if len(self.positions) > 0:
            for position in self.positions:
                logging.info(str(position))

        self.db.print_all_entries()

    def daily_pnl(self):
        """Update the daily PnL. The daily pnl is made up from the PnL of all filled orders."""
        index_pnl = 0

        for bracket_order in self.orders:
            # a backet order only hits realized pnl if 2 out of 3 orders are filled
            # We need to check the status of each order and then sum the pnl of the filled orders

            filled_count = 0
            current_order_pnl = 0

            for order, _ in bracket_order:

                order_status = self._get_order_status(order.orderId)

                if order_status['status'] == 'Filled':
                    
                    if order.orderType == 'STP' or order.orderType == 'LMT' and order.action == 'SELL':

                        current_order_pnl += order_status['avg_fill_price'] * int(order_status['filled'])

                    elif order.orderType == 'MKT' and order.action == 'BUY':

                        current_order_pnl -= order_status['avg_fill_price'] * int(order_status['filled'])

                    elif order.orderType == 'MKT' and order.action == 'SELL':

                        current_order_pnl += order_status['avg_fill_price'] * int(order_status['filled'])

                    else:

                        raise TypeError(f"Order type {order.orderType} with action {order.action} is not supported.")
                    
                    filled_count += 1
                
            if filled_count >= 2:
                index_pnl += current_order_pnl

        return index_pnl * self.config.mnq_point_value

    def place_bracket_order(self, contract: Contract = None):
        """Place a bracket order"""
        logging.debug("Placing bracket order.")
        contract = self.get_current_contract() if contract is None else contract

        mid_price = self.api.get_latest_mid_price(contract)

        if mid_price is None:
            logging.error(f"No mid price found for contract {contract.symbol}. Cannot place bracket order.")
            return
        
        stop_loss_price = mid_price - (self.config.stop_loss_ticks * self.config.mnq_tick_size)
        take_profit_limit_price = mid_price + (self.config.take_profit_ticks * self.config.mnq_tick_size)

        stop_loss_price = round(stop_loss_price/self.config.mnq_tick_size) * self.config.mnq_tick_size
        take_profit_limit_price = round(take_profit_limit_price/self.config.mnq_tick_size) * self.config.mnq_tick_size

        logging.debug(f"STP price: {stop_loss_price}, LMT price: {take_profit_limit_price}")

        bracket = self.api.create_bracket_order(
            "BUY", 
            self.config.number_of_contracts, 
            take_profit_limit_price, 
            stop_loss_price)
        
        self.api.place_orders(bracket, contract)

        if all(self._get_order_status(order.orderId) for order in bracket):
            # This means all orders were accepted by the API
            self._handle_successful_bracket_order(bracket)
        else:
            self._handle_failed_bracket_order(bracket)

    def _handle_successful_bracket_order(self, bracket: List[Order]):
        """Handle a successful bracket order. This is called when all orders were accepted by the API."""
        logging.info("All orders were accepted by the API.")
        self.orders.append(list(zip(bracket, [False] * len(bracket))))
        self.db.add_order(bracket)

        for order in bracket:
            order_id = order.orderId
            status = self._get_order_status(order_id)
            self.db.add_order_status(order_id, status)

        self.update_positions()

    def _handle_failed_bracket_order(self, bracket: List[Order]):
        """Handle a failed bracket order. This is called when the order is not in the order status dictionary."""
        logging.error("Order callbacks not received for all orders.")
        logging.warning(f"Pausing for {self.config.timeout} seconds before rechecking order statuses.")

        time.sleep(self.config.timeout)

        logging.warning("Checking order statuses again after pause.")

        for order in bracket:
            logging.info(f"Order {order.orderId} status - {self.api.order_statuses[order.orderId]}")

        # If order statuses are now received, then we can process positions
        if all(self._get_order_status(order.orderId) for order in bracket):

            self._handle_successful_bracket_order(bracket)

        else:

            logging.error("Order callbacks still not received for all orders. Handling cancellations")
            
            try:

                mkt_order, lmt_order, stp_order = bracket[0], bracket[1], bracket[2]
                for left_order, order_type in zip([mkt_order, lmt_order, stp_order], ['MKT', 'LMT', 'STP']):
                    if left_order.orderType != order_type:
                        logging.error(f"Bracket order not in expected order. Please check.")

                if not self.api.order_statuses[mkt_order.orderId]:
                    logging.error(f"MKT order {mkt_order.orderId} is not in the order status dictionary.")
                    logging.warning(f"Cancelling MKT order {mkt_order.orderId}")
                    self.api.cancel_order(mkt_order.orderId)

                    if self.api.order_statuses[mkt_order.orderId]['status'] == "Cancelled":
                        logging.info(f"MKT order {mkt_order.orderId} was cancelled successfully.")
                        logging.info(f"Now cancelling LMT and STP orders")

                        self.api.cancel_order(lmt_order.orderId)
                        self.api.cancel_order(stp_order.orderId)

                        logging.info(f"LMT order {lmt_order.orderId} status: {self.api.order_statuses[lmt_order.orderId]['status']}")
                        logging.info(f"STP order {stp_order.orderId} status: {self.api.order_statuses[stp_order.orderId]['status']}")

                        if (self.api.order_statuses[lmt_order.orderId]['status'] != "Cancelled" or
                            self.api.order_statuses[stp_order.orderId]['status'] != "Cancelled"):
                            logging.error(f"LMT or STP order was not cancelled. Please check.")
                            return

                else:
                    logging.info(f"MKT order {mkt_order.orderId} status received: {self.api.order_statuses[mkt_order.orderId]['status']}")

                if not self.api.order_statuses[lmt_order.orderId] or not self.api.order_statuses[stp_order.orderId]:
                    # If we're here it means that the MKT order was accepted by the API but not the brackets.
                    logging.error(f"LMT order status: {self.api.order_statuses[lmt_order.orderId]}")
                    logging.error(f"STP order status: {self.api.order_statuses[stp_order.orderId]}")
                    
                    #Try to cancel the brackets
                    self.api.cancel_order(lmt_order.orderId)
                    self.api.cancel_order(stp_order.orderId)

                    if self.api.order_statuses[lmt_order.orderId]['status'] == "Cancelled":
                        logging.info(f"LMT order {lmt_order.orderId} was cancelled successfully.")
                    else:
                        logging.error(f"Could not cancel LMT order. Status: {self.api.order_statuses[lmt_order.orderId]['status']}")

                    if self.api.order_statuses[stp_order.orderId]['status'] == "Cancelled":
                        logging.info(f"STP order {stp_order.orderId} was cancelled successfully.")
                    else:
                        logging.error(f"Could not cancel STP order. Status: {self.api.order_statuses[stp_order.orderId]['status']}")

                    # Handle case where brackets are cancelled but the market order is filled
                    if (self.api.order_statuses[mkt_order.orderId]['status'] == "Filled" and
                        self.api.order_statuses[lmt_order.orderId]['status'] == "Cancelled" and
                        self.api.order_statuses[stp_order.orderId]['status'] == "Cancelled"):

                        logging.warning(f"Market order {mkt_order.orderId} was filled while brackets were cancelled.")
                        logging.warning(f"Closing open position.")

                        #get order details for market order
                        self.api.request_open_orders()
                        
                        order_details = self.api.get_open_order(mkt_order.orderId)
                        contract = order_details['contract']

                        # Place the order
                        new_order_id, _ = self.api.place_market_order(contract, "SELL", mkt_order.totalQuantity)
                        new_order_details = self.api.get_open_order(new_order_id)
                        
                        self.orders.append([(new_order_details['order'], False)])
                        self.db.add_order(new_order_details['order'])
                        self.db.add_order_status(new_order_id, self._get_order_status(new_order_id))

                        self.update_positions()

                    else:
                        logging.error(f"Order statuses not received for all orders. Undefined behavior.")

                else:
                    
                    logging.error(f"Should not be here. Order statuses received for all orders but not handled.")
                    for order in bracket:
                        logging.info(f"Order {order.orderId} status - {self.api.order_statuses[order.orderId]}")

            except Exception as e:
                logging.error(f"Error handling cancellations for failed bracket order: {e}")

                for order in bracket:
                    logging.warning(f"Order {order.orderId} status - {self.api.order_statuses[order.orderId]}")

    def has_pending_orders(self):
        for bracket_order in self.orders:

            for order, _ in bracket_order:

                order_status = self._get_order_status(order.orderId)['status']

                if (order.orderType == 'MKT' and 
                    order_status != 'Filled' and
                    order_status != 'Cancelled'):

                    return True
                
        return False

    def current_position_quantity(self):
        return self.positions[-1].quantity if len(self.positions) > 0 else 0

    def check_cancelled_market_order(self):
        """Check for cancelled market orders and resubmit them if required."""
        logging.debug("Checking for cancelled market orders.")

        found_cancelled_order = False

        for bracket_order in self.orders:

            for order, already_resubmitted in bracket_order:

                order_status = self._get_order_status(order.orderId)['status']

                if (not already_resubmitted and 
                    order.orderType == 'MKT' and
                    order_status == "Cancelled"):

                    logging.warning(f"Order type: {order.orderType}, id:{order.orderId}, was cancelled.")
                    found_cancelled_order = True

                    if self.config.resubmit_cancelled_order:

                        logging.info(f"Resubmitting order type: {order.orderType}, id:{order.orderId}.")
                        already_resubmitted = True

                        order_details = self.api.get_open_order(order.orderId)

                        self.place_bracket_order(order_details['contract'])

                    else:
                        logging.info(f"Not resubmitting cancelled order type: {order.orderType}, id:{order.orderId}.")

        if not found_cancelled_order:
            logging.debug("No cancelled orders found.")
        
    def get_current_contract(self): 
        """Get the current contract"""
        return get_current_contract(
            self.config.ticker,
            self.config.exchange,
            self.config.currency,
            self.config.roll_contract_days_before,
            self.config.timezone)
    
    def _get_order_status_count(self):
        filled_count = 0
        cancelled_count = 0
        total_orders = 0
        
        for bracket_order in self.orders:

            total_orders += len(bracket_order)

            for order, _ in bracket_order:

                status = self._get_order_status(order.orderId)['status']
                if status == 'Filled':
                    filled_count += 1
                elif status == 'Cancelled':
                    cancelled_count += 1

        pending_count = total_orders - filled_count - cancelled_count
        return filled_count, cancelled_count, pending_count

    def cancel_all_orders(self):
        """Cancel all unfilled and non-cancelled orders."""
        logging.info("Cancelling all active orders.")
        
        for bracket_order in self.orders:

            for order, _ in bracket_order:
            
                order_status = self._get_order_status(order.orderId)
                
                if order_status['status'] not in ['Filled', 'Cancelled']:
                    logging.info(f"Cancelling order {order.orderId} of type {order.orderType}")
                    self.api.cancel_order(order.orderId)

    def close_all_positions(self):
        """Close all open positions by issuing market sell orders."""
        logging.info("Closing all open positions.")

        if len(self.positions) == 0:
            logging.info("No positions to close.")
            return
        
        # The last position entry is the current position
        position = self.positions[-1]

        if position.quantity > 0:
            logging.info(f"Closing position for {position.ticker} with quantity {position.quantity}")
            matching_position = self.api.get_matching_position(position)

            if matching_position is None:
                msg = f"Position {position.ticker} with quantity {position.quantity} not found in IBKR. Cannot close."
                logging.error(msg)
                return

            native_contract_quantity = int(matching_position['position'])
            if position.quantity > native_contract_quantity:
                msg = f"Trying to close position {position.ticker} with quantity {position.quantity}."
                msg += f" Only {native_contract_quantity} contracts are found on IBKR. Cannot close local position."
                logging.error(msg)
                return
            
            contract = Contract()
            contract.symbol = position.ticker
            contract.secType = position.security
            contract.currency = position.currency
            contract.exchange = self.config.exchange
            contract.lastTradeDateOrContractMonth = position.expiry

            # Place the order
            order_id, _ = self.api.place_market_order(contract, "SELL", position.quantity)
            order_details = self.api.get_open_order(order_id)
            self.orders.append([(order_details['order'], False)])

            self.db.add_order(order_details['order'])

            order_id = order_details['order'].orderId
            self.db.add_order_status(order_id, self._get_order_status(order_id))

            self.update_positions()

        elif position.quantity == 0:
            msg = f"Position {position.ticker} with quantity {position.quantity}. No positions to close"
            logging.info(msg)
        else:
            msg = f"Trying to close position {position.ticker} with quantity {position.quantity}. None handled scenario."
            logging.error(msg)
            raise NotImplementedError(msg)
    
    def _total_orders(self):
        return sum(len(bracket_order) for bracket_order in self.orders)
    
    def clear_orders_statuses_positions(self):
        """Clear all orders and positions. This is called when the trading day
        has ended and we need to clear the orders and positions for the next day.
        """
        logging.debug("Clearing orders, order statuses and positions.")
        self.orders = []
        self.positions = []
        self.order_statuses = {}

    def populate_from_db(self, check_state: bool = True):
        """Populate the orders from the database. Only orders created after the 
        trading day start time are loaded. By loading orders and setting 
        already_handled to False, we can ensure that the orders are processed 
        again and dont have to load the positions from the database.
        """
        logging.info("PortfolioManager: Populating orders from database.")
        self.db.print_all_entries()

        raw_orders_and_positions = self.db.get_all_orders_and_positions()
        raw_orders = raw_orders_and_positions['orders']
        raw_positions = raw_orders_and_positions['positions']

        trading_day_start = trading_day_start_time_ts(self.config.trading_start_time, self.config.timezone)

        logging.debug(f"PortfolioManager: Raw orders found: {len(raw_orders_and_positions['orders'])}")
        loaded_orders = []
        for order in raw_orders:
            time_created = pd.to_datetime(order['created_timestamp'])
            if time_created > trading_day_start:
                loaded_orders.append(order_from_dict(order))

        logging.debug(f"Loaded {len(loaded_orders)} orders from database.")


        logging.info("PortfolioManager: Populating order statuses from database.")

        raw_order_statuses = self.db.get_all_order_statuses()
        logging.debug(f"PortfolioManager: Raw order statuses found: {len(raw_order_statuses)}")

        for order_id, status in raw_order_statuses.items():
            time_last_modified = pd.to_datetime(status['last_modified'])

            if time_last_modified > trading_day_start:
                self.order_statuses[order_id] = status

        logging.debug(f"Loaded {len(self.order_statuses)} order statuses from database.")

        # Set whether a position has been logged from filled orders
        filled_flags = []
        for order in loaded_orders:
            order_status = self._get_order_status(order.orderId)
            if order_status['status'] == 'Filled':
                filled_flags.append(True)
            else:
                filled_flags.append(False)

        # Group orders into brackets of 3 orders each
        bracket_orders = []
        for i in range(0, len(loaded_orders), 3):
            bracket = loaded_orders[i:i+3]
            bracket_filled_flags = filled_flags[i:i+3]
            bracket_orders.append(list(zip(bracket, bracket_filled_flags)))

        self.orders = bracket_orders

        logging.info("PortfolioManager: Populating positions from database.")
        logging.debug(f"PortfolioManager: Raw positions found: {len(raw_positions)}")

        for position in raw_positions:
            time_created = pd.to_datetime(position['created_timestamp'])

            if time_created > trading_day_start:
                self.positions.append(Position.from_dict(position))

        logging.debug(f"Loaded {len(self.positions)} positions from database.")

        # Check that the latest position from the DB actually still exists in IBKR
        if check_state:
            if len(self.positions) > 0:
                latest_db_position = self.positions[-1]
                matching_position = self.api.get_matching_position(latest_db_position)

                if matching_position is None:
                    msg = f"Inconsistent DB state: Position {latest_db_position.ticker} with quantity {latest_db_position.quantity}"
                    msg += f" from DB not found in IBKR. Reinitializing database and portfolio state."
                    logging.error(msg)

                    self.cancel_all_orders()
                    self.clear_orders_statuses_positions()
                    self.db.reinitialize()
                    self.db.print_all_entries()

                elif latest_db_position.quantity > int(matching_position['position']):
                    msg = f"Inconsistent DB state: Position {latest_db_position.ticker} has {latest_db_position.quantity} contracts."
                    msg += f" Only {int(matching_position['position'])} contracts are found on IBKR."
                    msg += f" Reinitializing database and portfolio state."
                    logging.error(msg)
                    
                    self.cancel_all_orders()
                    self.clear_orders_statuses_positions()
                    self.db.reinitialize()
                    self.db.print_all_entries()
                else:
                    logging.info("DB state consistent with IBKR.")

        return len(loaded_orders), len(self.order_statuses), len(self.positions)



