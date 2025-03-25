from typing import List, Dict, Optional
from src.portfolio.position import Position
from src.portfolio.trading_order import TradingOrder
from src.ibkr_api import IBConnection
from src.configuration import Configuration
import logging
import time
from src.db.database import Database


class PortfolioManager:
    def __init__(self, config: Configuration, api: IBConnection):
        self.config = config
        self.api = api

        self.db = Database()

        self.positions: List[Position] = []
        self.orders: List[TradingOrder] = []

    def has_pending_orders(self):
        return any(order.status not in ['Filled', 'ReSubmitted'] for order in self.orders)

    def open_contract_number(self):
        return sum(position.quantity for position in self.positions if position.status == "OPEN")

    def populate_from_db(self):
        """Populate the portfolio from the database"""
        self.positions = self.db.get_positions()
        self.orders = self.db.get_orders()

    def check_order_statuses(self):
        """Check the status of all orders and positions"""
        for order in self.orders:
            if order.status != 'Filled' and order.status != 'Cancelled' and order.status != 'ReSubmitted':
                logging.warning(f"Order type: {order.order_type}, id:{order.order_id}, not filled. Checking status...")
                self.api.update_order_status(order)

                if order.status == 'Filled':

                    if order.order_type == 'MKT':
                        """We have a previously unfilled market order.
                        We need to place a bracket order for risk mgmt.
                        The order must be updated in the bd as well"""
                        logging.info(f"Order type: {order.order_type}, id:{order.order_id}, filled. Placing bracket order...")

                        position, stop_loss_order, take_profit_order = self._place_bracket_order(order)
                        self.db.add_position(position)
                        self.positions.append(position)

                        self.db.add_order(stop_loss_order)
                        self.db.add_order(take_profit_order)

                        self.orders.append(stop_loss_order)
                        self.orders.append(take_profit_order)

                        self.db.update_order(order)

                    elif order.order_type == 'LMT' or order.order_type == 'STP':
                        """We have a previously unfilled limit or stop order. The stop loss and take
                        profit details in the positions are still correct so no changes are needed, just update the DB"""
                        logging.info(f"Order type: {order.order_type}, id:{order.order_id}, now filled, updating DB")
                        self.db.update_order(order)

                    else:
                        raise TypeError("Unsupported order type. Please check.")
                    
            elif order.status == 'Cancelled':

                if order.order_type == 'MKT':
                    # A market order was cancelled also meaning it was never filled and so no position was entered.
                    logging.warning(f"Order type: {order.order_type}, id:{order.order_id}, was cancelled.")

                    if self.config.resubmit_cancelled_market_orders:
                        logging.info(f"Resubmitting order type: {order.order_type}, id:{order.order_id}.")
                        order.status = 'ReSubmitted'
                        self.db.update_order(order)

                        self.enter_position(order.get_contract())

                elif order.order_type == 'LMT' or order.order_type == 'STP':
                    # A limit or stop order was cancelled. This means a long order was entered, a position taken but
                    # and the bracket order was never filled. We need to try filling the bracket order again and update the DB 
                    # and position
                    logging.warning(f"Order type: {order.order_type}, id:{order.order_id}, was cancelled.")

                    if self.config.resubmit_cancelled_bracket_orders:
                        logging.warning(f"Resubmitting order type: {order.order_type}, id:{order.order_id}...")
                        
                        order.status = 'ReSubmitted'
                        self.db.update_order(order)

                        self.api.place_trading_order(order)
                        self.orders.append(order)
                        self.db.add_order(order)

                else:
                    raise TypeError("Unsupported order type. Please check.")
                
            elif order.status == 'ReSubmitted':
                logging.debug(f"Resubmitted order.")

            else:
                raise TypeError("Unsupported order status. Please check.")


    def enter_position(self, contract):
        """Enter a new long position"""
        order = TradingOrder(
            order_type='MKT',
            action='BUY',
            quantity=self.config.number_of_contracts,
            contract=contract,
            order_id=None,
            status=None,
            timezone=self.config.timezone
        )
        self.api.place_trading_order(order)

        if order.status != 'Filled':
            logging.warning(f"Entry order status: {order.status}. Waiting 10s for fill...")
            time.sleep(10)
            self.api.update_order_status(order)

        if order.status != 'Filled':
            logging.warning(f"Order still not filled. Waiting 30 seconds...")
            time.sleep(30)  
            self.api.update_order_status(order)

        self.orders.append(order)
        self.db.add_order(order)

        if order.status == 'Filled':
            fill_price = self.api.get_order_status(order.order_id)['avg_fill_price']
            logging.info(f"Entered long position: {self.config.number_of_contracts} contracts at {fill_price}")

            position, stop_loss_order, take_profit_order = self._place_bracket_order(order)
            self.db.add_position(position)
            self.positions.append(position)

            self.db.add_order(stop_loss_order)
            self.db.add_order(take_profit_order)

            self.orders.append(stop_loss_order)
            self.orders.append(take_profit_order)

    def _place_bracket_order(self, order):
        """Place a bracket order"""
        ibkr_position = self._get_position_from_order(order)
        full_order_status = self.api.get_order_status(order.order_id)
        fill_price = full_order_status['avg_fill_price']

        stop_loss_order, take_profit_order = self._fill_bracket_order(order, fill_price)

        position = Position(
        ticker=order.ticker,
        security=order.security,
        currency=order.currency,
        expiry=order.expiry,
        contract_id=ibkr_position['contract']['conId'],
        quantity=order.quantity,
        avg_price=fill_price,
        timezone=self.config.timezone,
        stop_loss_price=stop_loss_order.aux_price,
        take_profit_price=take_profit_order.aux_price
        )
        
        return position, stop_loss_order, take_profit_order

    def _fill_bracket_order(self, order, fill_price):
        """Adds stop loss and take profit orders for a given order"""
        # Calculate stop loss and take profit prices
        order_id = order.order_id
        contract = order.get_contract()

        stop_price = fill_price - (self.config.stop_loss_ticks * self.config.mnq_tick_size)
        profit_price = fill_price + (self.config.take_profit_ticks * self.config.mnq_tick_size)

        stop_loss_order = TradingOrder(
            order_type='STP',
            action='SELL',
            quantity=self.config.number_of_contracts,
            contract=contract,
            order_id=None,
            status=None,
            timezone=self.config.timezone,
            parent_order_id=order_id,
            aux_price=stop_price
        )

        take_profit_order = TradingOrder(
            order_type='LMT',
            action='SELL',
            quantity=self.config.number_of_contracts,
            contract=contract,
            order_id=None,
            status=None,
            timezone=self.config.timezone,
            parent_order_id=order_id,
            aux_price=profit_price
        )
        
        # Place stop loss and take profit orders
        stop_order_id, stop_order_status = self.api.place_stop_loss_order(
            stop_loss_order.get_contract(),
            stop_loss_order.order_id, 
            stop_loss_order.quantity, 
            stop_price)
        
        profit_order_id, profit_order_status = self.api.place_profit_taker_order(
            take_profit_order.get_contract(),
            take_profit_order.order_id, 
            take_profit_order.quantity, 
            profit_price)

        stop_loss_order.update_post_fill(order_id=stop_order_id, status=stop_order_status['status'])
        take_profit_order.update_post_fill(order_id=profit_order_id, status=profit_order_status['status'])
        
        time.sleep(self.config.timeout)
        logging.info(f"Stop loss order status: {stop_order_status}")
        logging.info(f"Profit taker order status: {profit_order_status}")        
        logging.info(f"Entered Stop loss: {stop_price}, Take profit: {profit_price}")

        return stop_loss_order, take_profit_order

    def _get_position_from_order(self, trading_order: TradingOrder):
        """Find the position that corresponds to the passed order by matching contract attributes.
        
        Args:
            trading_order (TradingOrder): The order to find a matching position for
            
        Returns:
            dict: The matching position from the API, or None if no match is found
            
        Raises:
            Exception: If no matching position is found
        """
        positions = self.api.get_positions()
        
        matching_positions = []
        for position in positions:
            pos_contract = position['contract']
            
            # Match all relevant contract attributes
            if (pos_contract.symbol == trading_order.ticker and
                pos_contract.secType == trading_order.security and
                pos_contract.exchange == trading_order.exchange and
                pos_contract.currency == trading_order.currency and
                pos_contract.lastTradeDateOrContractMonth == trading_order.expiry):
                
                matching_positions.append(position)
        
        if len(matching_positions) > 1:
            logging.warning(f"Found multiple matching positions for order {trading_order.order_id}")
            return matching_positions[0]
        
        else:
            msg = f"No matching position found for order {trading_order.order_id}"
            logging.error(msg)
            raise Exception(msg)
