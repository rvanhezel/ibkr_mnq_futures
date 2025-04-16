import sqlite3
import os
import logging
import pandas as pd
from typing import Union
from ibapi.order import Order
import time


class Database:

    def __init__(self, timezone, db_path="trading.db"):
        self.timezone = timezone
        self.db_path = db_path

        if not os.path.exists(self.db_path):
            self._init_db()
        else:
            logging.info(f"Using existing database at {self.db_path}")

    def reinitialize(self):
        """Delete the existing database file and reinitialize it.
        
        This function will:
        1. Close any existing connections
        2. Delete the database file if it exists
        3. Create a new database with fresh tables
        
        Returns:
            bool: True if reinitialization was successful, False otherwise
        """
        try:
            # Force close any existing connections
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA optimize")
                    conn.close()
            except:
                pass
            
            if os.path.exists(self.db_path):
                max_attempts = 3

                for attempt in range(max_attempts):
                    time.sleep(2)

                    try:
                        os.remove(self.db_path)
                        logging.info(f"Deleted existing database at {self.db_path}")
                        break
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.1)  # Wait 100ms before retrying
                        else:
                            raise
            
            # Initialize new database
            self._init_db()
            logging.info("Database reinitialized successfully")
            return True
            
        except Exception as e:
            msg = f"Error reinitializing database: {str(e)}"
            msg += f". Please retry or manually delete the database file and restart the program."
            logging.error(msg)
            raise Exception(msg)

    def _init_db(self):  
        """Initialize the database and create tables if they don't exist"""
        logging.info("Initializing database")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Create orders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INTEGER PRIMARY KEY,
                        action TEXT NOT NULL,
                        order_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        aux_price REAL,
                        lmt_price REAL,
                        parent_id INTEGER,
                        transmit BOOLEAN NOT NULL,
                        created_timestamp TIMESTAMP NOT NULL
                    )
                ''')
                # Create positions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_id INTEGER NOT NULL,
                        ticker TEXT NOT NULL,
                        security TEXT NOT NULL,
                        currency TEXT NOT NULL,
                        expiry TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        avg_price REAL NOT NULL,
                        time_opened TIMESTAMP NOT NULL,
                        created_timestamp TIMESTAMP NOT NULL
                    )
                ''')
                # Create trading_pause table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_pause (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP NOT NULL,
                        created_timestamp TIMESTAMP NOT NULL
                    )
                ''')
                # Create order_status table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS order_status (
                        order_id INTEGER PRIMARY KEY,
                        status TEXT NOT NULL,
                        filled INTEGER NOT NULL,
                        remaining INTEGER NOT NULL,
                        avg_fill_price REAL,
                        last_fill_price REAL,
                        parent_id INTEGER,
                        why_held TEXT,
                        mkt_cap_price REAL,
                        perm_id INTEGER,
                        client_id INTEGER,
                        last_modified TIMESTAMP NOT NULL,
                        FOREIGN KEY (order_id) REFERENCES orders(order_id)
                    )
                ''')
                conn.commit()
                logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

    def add_order(self, order: Union[Order, list[Order]]):
        """Add a trading order to the database"""
        if not isinstance(order, list):
            order = [order]

        success = True
        current_time = pd.Timestamp.now(tz=self.timezone)
        
        for cur_order in order:
            logging.debug(f"Adding order to database: {cur_order}")

            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO orders (
                            order_id, action, order_type, quantity, aux_price,
                            lmt_price, parent_id, transmit, created_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        cur_order.orderId,
                        cur_order.action,
                        cur_order.orderType,
                        cur_order.totalQuantity,
                        cur_order.auxPrice,
                        cur_order.lmtPrice,
                        cur_order.parentId,
                        cur_order.transmit,
                        current_time.isoformat()
                    ))
                    conn.commit()
                    logging.debug(f"Added order {cur_order.orderId} to database")

            except Exception as e:
                logging.error(f"DB: Error adding order to database: {str(e)}")
                success = False

        return success

    def get_order(self, order_id: int):
        """Get an order from the database by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'order_id': row[0],
                        'action': row[1],
                        'order_type': row[2],
                        'quantity': row[3],
                        'aux_price': row[4],
                        'lmt_price': row[5],
                        'parent_id': row[6],
                        'transmit': row[7],
                        'created_timestamp': row[8]
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting order from database: {str(e)}")
            return None

    def add_position(self, position):
        """Add a position to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = pd.Timestamp.now(tz=self.timezone)
                cursor.execute('''
                    INSERT INTO positions (
                        contract_id, ticker, security, currency, expiry,
                        quantity, avg_price, time_opened, created_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.contract_id,
                    position.ticker,
                    position.security,
                    position.currency,
                    position.expiry,
                    position.quantity,
                    position.avg_price,
                    position.time_opened.isoformat(),
                    current_time.isoformat()
                ))
                conn.commit()
                position_id = cursor.lastrowid
                logging.info(f"Added position {position_id} to database")
                return position_id
        except Exception as e:
            logging.error(f"DB: Error adding position to database: {str(e)}")
            return None

    def get_position(self, position_id: int):
        """Get a position from the database by position ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM positions WHERE id = ?', (position_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'contract_id': row[1],
                        'ticker': row[2],
                        'security': row[3],
                        'currency': row[4],
                        'expiry': row[5],
                        'quantity': row[6],
                        'avg_price': row[7],
                        'time_opened': pd.Timestamp(row[8]),
                        'created_timestamp': pd.Timestamp(row[9])
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting position from database: {str(e)}")
            return None

    def get_position_by_contract_id(self, contract_id: int):
        """Get a position from the database by contract ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM positions WHERE contract_id = ?', (contract_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'contract_id': row[1],
                        'ticker': row[2],
                        'security': row[3],
                        'currency': row[4],
                        'expiry': row[5],
                        'quantity': row[6],
                        'avg_price': row[7],
                        'time_opened': pd.Timestamp(row[8]),
                        'created_timestamp': pd.Timestamp(row[9])
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting position from database: {str(e)}")
            return None

    def update_position(self, position):
        """Update an existing position in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE positions SET
                        contract_id = ?,
                        ticker = ?,
                        security = ?,
                        currency = ?,
                        expiry = ?,
                        quantity = ?,
                        avg_price = ?,
                        time_opened = ?
                    WHERE id = ?
                ''', (
                    position.contract_id,
                    position.ticker,
                    position.security,
                    position.currency,
                    position.expiry,
                    position.quantity,
                    position.avg_price,
                    position.time_opened.isoformat(),
                    position.id
                ))
                conn.commit()
                logging.info(f"DB: Updated position {position.id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error updating position in database: {str(e)}")
            return False

    def add_trading_pause(self, start_time: pd.Timestamp, end_time: pd.Timestamp):
        """Add a trading pause period to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = pd.Timestamp.now(tz=self.timezone)
                cursor.execute('''
                    INSERT INTO trading_pause (start_time, end_time, created_timestamp)
                    VALUES (?, ?, ?)
                ''', (start_time.isoformat(), end_time.isoformat(), current_time.isoformat()))
                conn.commit()
                logging.info(f"Added trading pause to DB from {start_time} to {end_time}")
                return True
        except Exception as e:
            logging.error(f"DB: Error adding trading pause to database: {str(e)}")
            return False

    def get_trading_pause(self, timezone):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT start_time, end_time, created_timestamp
                    FROM trading_pause 
                    ORDER BY start_time DESC 
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    return {
                        'start_time': pd.Timestamp(row[0]).tz_localize(timezone),
                        'end_time': pd.Timestamp(row[1]).tz_localize(timezone),
                        'created_timestamp': pd.Timestamp(row[2]).tz_localize(timezone)
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting trading pause from database: {str(e)}")
            return None

    def update_order(self, order):
        """Update an existing order in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE orders SET
                        action = ?,
                        order_type = ?,
                        quantity = ?,
                        aux_price = ?,
                        lmt_price = ?,
                        parent_id = ?,
                        transmit = ?
                    WHERE order_id = ?
                ''', (
                    order.action,
                    order.order_type,
                    order.quantity,
                    order.aux_price,
                    order.lmt_price,
                    order.parent_id,
                    order.transmit,
                    order.order_id
                ))
                conn.commit()
                logging.info(f"DB: Updated order {order.order_id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error updating order in database: {str(e)}")
            return False

    def print_all_entries(self):
        """Print all entries from all tables in a readable format"""
        logging.debug("=== DATABASE ENTRIES ===")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Print Orders
                logging.debug("=== ORDERS ===")
                cursor.execute("PRAGMA table_info(orders)")
                order_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM orders')
                orders = cursor.fetchall()
                if orders:
                    # Create header with column names
                    header = " | ".join(f"{col:<8}" for col in order_columns)
                    logging.debug(header)
                    logging.debug("-" * len(header))
                    # Print data rows
                    for order in orders:
                        row = " | ".join(f"{str(val):<8}" for val in order)
                        logging.debug(row)
                else:
                    logging.debug("No orders found")

                # Print Positions
                logging.debug("=== POSITIONS ===")
                cursor.execute("PRAGMA table_info(positions)")
                position_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM positions')
                positions = cursor.fetchall()
                if positions:
                    # Create header with column names
                    header = " | ".join(f"{col:<10}" for col in position_columns)
                    logging.debug(header)
                    logging.debug("-" * len(header))
                    # Print data rows
                    for pos in positions:
                        row = " | ".join(f"{str(val):<10}" for val in pos)
                        logging.debug(row)
                else:
                    logging.debug("No positions found")

                # Print Trading Pauses
                logging.debug("=== TRADING PAUSES ===")
                cursor.execute("PRAGMA table_info(trading_pause)")
                pause_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM trading_pause')
                pauses = cursor.fetchall()
                if pauses:
                    # Create header with column names
                    header = " | ".join(f"{col:<15}" for col in pause_columns)
                    logging.debug(header)
                    logging.debug("-" * len(header))
                    # Print data rows
                    for pause in pauses:
                        row = " | ".join(f"{str(val):<15}" for val in pause)
                        logging.debug(row)
                else:
                    logging.debug("No trading pauses found")

                # Print Order Statuses
                logging.debug("=== ORDER STATUSES ===")
                cursor.execute("PRAGMA table_info(order_status)")
                status_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM order_status')
                statuses = cursor.fetchall()
                if statuses:
                    # Create header with column names
                    header = " | ".join(f"{col:<12}" for col in status_columns)
                    logging.debug(header)
                    logging.debug("-" * len(header))
                    # Print data rows
                    for status in statuses:
                        row = " | ".join(f"{str(val):<12}" for val in status)
                        logging.debug(row)
                else:
                    logging.debug("No order statuses found")

                return True
        except Exception as e:
            logging.error(f"DB: Error printing database entries: {str(e)}")
            return False

    def get_all_orders_and_positions(self):
        """Get all orders and positions from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all order IDs
                cursor.execute('SELECT order_id FROM orders ORDER BY created_timestamp DESC')
                order_ids = [row[0] for row in cursor.fetchall()]
                
                # Get all position IDs
                cursor.execute('SELECT id FROM positions ORDER BY created_timestamp ASC')
                position_ids = [row[0] for row in cursor.fetchall()]
                
                # Get orders and positions using existing methods
                orders = [self.get_order(order_id) for order_id in order_ids]
                positions = [self.get_position(position_id) for position_id in position_ids]
                
                return {
                    'orders': orders,
                    'positions': positions
                }
        except Exception as e:
            logging.error(f"DB: Error getting all orders and positions: {str(e)}")
            return {
                'orders': [],
                'positions': []
            }

    def get_trading_pauses(self):
        """Get all trading pauses from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT start_time, end_time, created_timestamp
                    FROM trading_pause 
                    ORDER BY start_time DESC
                ''')
                rows = cursor.fetchall()
                if rows:
                    return [{
                        'start_time': pd.Timestamp(row[0]).tz_convert(self.timezone),
                        'end_time': pd.Timestamp(row[1]).tz_convert(self.timezone),
                        'created_timestamp': pd.Timestamp(row[2]).tz_convert(self.timezone)
                    } for row in rows]
                return []
        except Exception as e:
            logging.error(f"DB: Error getting trading pauses from database: {str(e)}")
            return []

    def add_order_status(self, order_id: int, status_dict: dict):
        """Add a new order status to the database
        
        Args:
            order_id (int): The order ID
            status_dict (dict): Dictionary containing order status fields
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = pd.Timestamp.now(tz=self.timezone)
                
                cursor.execute('''
                    INSERT INTO order_status (
                        order_id, status, filled, remaining, avg_fill_price,
                        last_fill_price, parent_id, why_held, mkt_cap_price,
                        perm_id, client_id, last_modified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_id,
                    status_dict['status'],
                    int(status_dict['filled']),
                    int(status_dict['remaining']),
                    status_dict['avg_fill_price'],
                    status_dict['last_fill_price'],
                    status_dict['parent_id'],
                    status_dict['why_held'],
                    status_dict['mkt_cap_price'],
                    status_dict['perm_id'],
                    status_dict['client_id'],
                    current_time.isoformat()
                ))
                
                conn.commit()
                logging.debug(f"Added status for order {order_id} to DB")
                return True
        except Exception as e:
            logging.error(f"DB: Error adding order status: {str(e)}")
            return False

    def update_order_status(self, order_id: int, status_dict: dict):
        """Update an existing order status in the database
        
        Args:
            order_id (int): The order ID
            status_dict (dict): Dictionary containing order status fields
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = pd.Timestamp.now(tz=self.timezone)
                
                cursor.execute('''
                    UPDATE order_status SET
                        status = ?,
                        filled = ?,
                        remaining = ?,
                        avg_fill_price = ?,
                        last_fill_price = ?,
                        parent_id = ?,
                        why_held = ?,
                        mkt_cap_price = ?,
                        perm_id = ?,
                        client_id = ?,
                        last_modified = ?
                    WHERE order_id = ?
                ''', (
                    status_dict['status'],
                    int(status_dict['filled']),
                    int(status_dict['remaining']),
                    status_dict['avg_fill_price'],
                    status_dict['last_fill_price'],
                    status_dict['parent_id'],
                    status_dict['why_held'],
                    status_dict['mkt_cap_price'],
                    status_dict['perm_id'],
                    status_dict['client_id'],
                    current_time.isoformat(),
                    order_id
                ))
                
                conn.commit()
                logging.info(f"DB: Updated status for order {order_id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error updating order status: {str(e)}")
            return False

    def get_order_status(self, order_id: int):
        """Get the status of an order from the database
        
        Args:
            order_id (int): The order ID
            
        Returns:
            dict: Dictionary containing order status fields, or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM order_status WHERE order_id = ?', (order_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'order_id': row[0],
                        'status': row[1],
                        'filled': row[2],
                        'remaining': row[3],
                        'avg_fill_price': row[4],
                        'last_fill_price': row[5],
                        'parent_id': row[6],
                        'why_held': row[7],
                        'mkt_cap_price': row[8],
                        'perm_id': row[9],
                        'client_id': row[10],
                        'last_modified': pd.Timestamp(row[11])
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting order status: {str(e)}")
            return None

    def get_all_order_statuses(self):
        """Get all order statuses from the database
        
        Returns:
            dict: Dictionary mapping order IDs to their status dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT order_id FROM order_status')
                order_ids = [row[0] for row in cursor.fetchall()]
                
                return {
                    order_id: self.get_order_status(order_id)
                    for order_id in order_ids
                    if self.get_order_status(order_id) is not None
                }
                
        except Exception as e:
            logging.error(f"DB: Error getting all order statuses: {str(e)}")
            return {}