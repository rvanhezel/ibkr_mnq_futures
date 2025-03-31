from src.portfolio.position import Position
import pandas as pd
from typing import List, Dict, Optional
from ibapi.order import Order
from ibapi.contract import Contract
import os
from src.portfolio.position import Position
from src.portfolio.trading_order import TradingOrder
from src.api.ibkr_api import IBConnection
from src.configuration import Configuration
import logging
import time
from src.db.database import Database
from src.api.api_utils import get_current_contract, order_from_dict
from src.utilities.utils import trading_day_start_time


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

                            self.orders[bracket_idx][order_idx] = (order, True)

                        else:
                            logging.info(f"Buy order filled, updating position.")

                            position = self.positions[0]

                            total_quantity = position.quantity + int(order.totalQuantity)
                            avg_price = position.quantity * position.avg_price
                            avg_price += int(order.totalQuantity) * order_status['avg_fill_price'] 
                            avg_price /= total_quantity

                            position.quantity = total_quantity
                            position.avg_price = avg_price

                            self.orders[bracket_idx][order_idx] = (order, True)
                            
                            self.db.add_position(position) #create a new entry in the db as opposed to updating the existing one

                    elif order.orderType == 'MKT' and order.action == 'SELL':

                        logging.info(f"Market sell order filled, updating position.")

                        position = self.positions[0]

                        total_quantity = position.quantity - int(order.totalQuantity)
                        avg_price = position.quantity * position.avg_price
                        avg_price += int(order.totalQuantity) * order_status['avg_fill_price'] 
                        avg_price /= (position.quantity + int(order.totalQuantity))

                        position.quantity = total_quantity
                        position.avg_price = avg_price
                        
                        self.orders[bracket_idx][order_idx] = (order, True)

                        self.db.add_position(position) 

                    elif order.orderType == 'STP' or order.orderType == 'LMT' and order.action == 'SELL':

                        logging.info(f"{order.orderType} order filled, updating position.")

                        position = self.positions[0]

                        total_quantity = position.quantity - int(order.totalQuantity)
                        avg_price = position.quantity * position.avg_price
                        avg_price += int(order.totalQuantity) * order_status['avg_fill_price'] 
                        avg_price /= (position.quantity + int(order.totalQuantity))

                        position.quantity = total_quantity
                        position.avg_price = avg_price

                        self.orders[bracket_idx][order_idx] = (order, True)

                        self.db.add_position(position)

                    else:

                        raise TypeError(f"Order type {order.orderType} with action {order.action} is not supported.")
        
        msg = f"{self.__class__.__name__}: Finished updating positions from orders."
        msg += f" Currently {len(self.positions)} position(s)."

        logging.info(msg)
        if len(self.positions) > 0:
            for position in self.positions:
                logging.info(str(position))

    def daily_pnl(self):
        """Update the daily PnL. The daily pnl is made up from the PnL of all filled orders."""
        pnl = 0

        for bracket_order in self.orders:
            # a backet order only hits pnl if 2 out of 3 orders are filled
            # so we need to check the status of each order
            # and then sum the pnl of the filled orders

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
                pnl += current_order_pnl

        return pnl

    def place_bracket_order(self):
        """Place a bracket order"""
        logging.debug("Placing bracket order.")
        contract = self.get_current_contract()

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
            logging.info("All orders were accepted by the API.")
            self.orders.append(list(zip(bracket, [False] * len(bracket))))
            self.db.add_order(bracket)

            for order in bracket:
                order_id = order.orderId
                status = self._get_order_status(order_id)
                self.db.add_order_status(order_id, status)

            self.update_positions()

            self.db.print_all_entries()

        else:
            logging.error("Failed to place all orders.")
            for order in bracket:
                logging.info(f"Cancelling order {order.orderId} of type {order.orderType}")
                self.api.cancel_order(order.orderId)

    def has_pending_orders(self):
        for bracket_order in self.orders:

            for order, _ in bracket_order:

                order_status = self._get_order_status(order.orderId)['status']

                if (order.orderType == 'MKT' and 
                    order_status != 'Filled' and
                    order_status != 'Cancelled'):

                    return True
                
        return False

    def contract_count_from_open_positions(self):
        return sum(position.quantity for position in self.positions)

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

                    logging.warning(f"Order type: {order.order_type}, id:{order.order_id}, was cancelled.")
                    found_cancelled_order = True

                    if self.config.resubmit_cancelled_order:

                        logging.info(f"Resubmitting order type: {order.order_type}, id:{order.order_id}.")
                        already_resubmitted = True

                        order_details = self.api.get_open_order(order.orderId)

                        self.place_bracket_order(order_details['contract'])

                    else:
                        logging.info(f"Not resubmitting cancelled order type: {order.order_type}, id:{order.order_id}.")

        if not found_cancelled_order:
            logging.debug("No cancelled orders found.")

    # def _get_ibkr_position_from_contract(self, contract: Contract):
    #     """Find the position that corresponds to the passed order by matching contract attributes.
        
    #     Args:
    #         trading_order (TradingOrder): The order to find a matching position for
            
    #     Returns:
    #         dict: The matching position from the API, or None if no match is found
            
    #     Raises:
    #         Exception: If no matching position is found
    #     """
    #     positions = self.api.get_positions()
        
    #     matching_positions = []
    #     for position in positions:
    #         pos_contract = position['contract']
            
    #         # Match all relevant contract attributes
    #         if (pos_contract.symbol == contract.symbol and
    #             pos_contract.secType == contract.secType and
    #             pos_contract.exchange == contract.exchange and
    #             pos_contract.currency == contract.currency and
    #             pos_contract.lastTradeDateOrContractMonth == contract.lastTradeDateOrContractMonth):
                
    #             matching_positions.append(position)
        
    #     if len(matching_positions) > 1:
    #         logging.warning(f"Found multiple matching positions for contract.")
    #         return matching_positions[0]
        
    #     elif len(matching_positions) == 1:
    #         return matching_positions[0]
        
    #     else:
    #         msg = f"No matching position found for contract."
    #         logging.error(msg)
    #         raise Exception(msg)
        
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
                
        # # Wait a moment for orders to be cancelled
        # time.sleep(3)
        
        # # Update order statuses
        # filled_count, cancelled_count, pending_count = self._get_order_status_count()
        # msg = f"Order status after cancellation: {filled_count} filled,"
        # msg += f" {cancelled_count} cancelled, {pending_count} pending"
        # logging.info(msg)

    def close_all_positions(self):
        """Close all open positions by issuing market sell orders."""
        logging.info("Closing all open positions.")
        
        for position in self.positions:
            if position.quantity > 0:
                logging.info(f"Closing position for {position.ticker} with quantity {position.quantity}")
                
                contract = Contract()
                contract.symbol = position.ticker
                contract.secType = position.security
                contract.exchange = self.config.exchange
                contract.currency = position.currency
                contract.lastTradeDateOrContractMonth = position.expiry
                
                # Place the order
                order_id, _ = self.api.place_market_order(contract, "SELL", position.quantity)
                order_details = self.api.get_open_order(order_id)
                self.orders.append((order_details['order'], False))

            else:
                msg = f"Unsupported position type: {position.ticker} with quantity {position.quantity}."
                msg += " Cannot close."
                logging.error(msg)
                raise AttributeError(msg)
                
        # # Wait a moment for orders to be processed
        # time.sleep(1)
        
        # # Update positions
        # self.update_positions()
        
        # # Log final position status
        # remaining_positions = sum(1 for position in self.positions if position.quantity > 0)
        # logging.info(f"Remaining open positions after closing: {remaining_positions}")
    
    def _total_orders(self):
        return sum(len(bracket_order) for bracket_order in self.orders)
    
    def clear_orders_and_positions(self):
        """Clear all orders and positions. This is called when the trading day
        has ended and we need to clear the orders and positions for the next day.
        """
        self.orders = []
        self.positions = []

    def populate_from_db(self):
        """Populate the orders from the database. Only orders created after the 
        trading day start time are loaded. By loading orders and setting 
        already_handled to False, we can ensure that the orders are processed 
        again and dont have to load the positions from the database.
        """
        logging.info("PortfolioManager: Populating orders from database.")

        raw_orders_and_positions = self.db.get_all_orders_and_positions()
        raw_orders = raw_orders_and_positions['orders']
        raw_positions = raw_orders_and_positions['positions']

        trading_day_start = trading_day_start_time(self.config.trading_start_time, self.config.timezone)

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

        self.orders = [list(zip(loaded_orders, filled_flags))]

        logging.info("PortfolioManager: Populating positions from database.")
        logging.debug(f"PortfolioManager: Raw positions found: {len(raw_positions)}")

        for position in raw_positions:
            time_created = pd.to_datetime(position['created_timestamp'])

            if time_created > trading_day_start:
                self.positions.append(Position.from_dict(position))

        logging.debug(f"Loaded {len(self.positions)} positions from database.")

