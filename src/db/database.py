import sqlite3
import os
import logging
import pandas as pd
from typing import Union
from ibapi.order import Order


class Database:

    def __init__(self, timezone, db_path="trading.db"):
        self.timezone = timezone
        self.db_path = db_path

        if not os.path.exists(self.db_path):
            self._init_db()
        else:
            logging.info(f"Using existing database at {self.db_path}")

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
                        contract_id INTEGER PRIMARY KEY,
                        ticker TEXT NOT NULL,
                        security TEXT NOT NULL,
                        currency TEXT NOT NULL,
                        expiry TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        avg_price REAL NOT NULL,
                        status TEXT NOT NULL,
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
                    logging.info(f"Added order {cur_order.orderId} to database")

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
                        quantity, avg_price, status, time_opened, created_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.contract_id,
                    position.ticker,
                    position.security,
                    position.currency,
                    position.expiry,
                    position.quantity,
                    position.avg_price,
                    position.status,
                    position.time_opened.isoformat(),
                    current_time.isoformat()
                ))
                conn.commit()
                logging.info(f"Added position {position.contract_id} to database")
                return True
        except Exception as e:
            logging.error(f"DB: Error adding position to database: {str(e)}")
            return False

    def get_position(self, contract_id: int):
        """Get a position from the database by contract ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM positions WHERE contract_id = ?', (contract_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'contract_id': row[0],
                        'ticker': row[1],
                        'security': row[2],
                        'currency': row[3],
                        'expiry': row[4],
                        'quantity': row[5],
                        'avg_price': row[6],
                        'status': row[7],
                        'time_opened': pd.Timestamp(row[8]),
                        'created_timestamp': pd.Timestamp(row[9])
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting position from database: {str(e)}")
            return None

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

    def update_position(self, position):
        """Update an existing position in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE positions SET
                        ticker = ?,
                        security = ?,
                        currency = ?,
                        expiry = ?,
                        quantity = ?,
                        avg_price = ?,
                        status = ?,
                        time_opened = ?
                    WHERE contract_id = ?
                ''', (
                    position.ticker,
                    position.security,
                    position.currency,
                    position.expiry,
                    position.quantity,
                    position.avg_price,
                    position.status,
                    position.time_opened.isoformat(),
                    position.contract_id
                ))
                conn.commit()
                logging.info(f"DB: Updated position {position.contract_id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error updating position in database: {str(e)}")
            return False

    def print_all_entries(self):
        """Print all entries from all tables in a readable format"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Print Orders
                print("\n=== ORDERS ===")
                cursor.execute("PRAGMA table_info(orders)")
                order_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM orders')
                orders = cursor.fetchall()
                if orders:
                    # Create header with column names
                    header = " | ".join(f"{col:<8}" for col in order_columns)
                    print(header)
                    print("-" * len(header))
                    # Print data rows
                    for order in orders:
                        row = " | ".join(f"{str(val):<8}" for val in order)
                        print(row)
                else:
                    print("No orders found")

                # Print Positions
                print("\n=== POSITIONS ===")
                cursor.execute("PRAGMA table_info(positions)")
                position_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM positions')
                positions = cursor.fetchall()
                if positions:
                    # Create header with column names
                    header = " | ".join(f"{col:<10}" for col in position_columns)
                    print(header)
                    print("-" * len(header))
                    # Print data rows
                    for pos in positions:
                        row = " | ".join(f"{str(val):<10}" for val in pos)
                        print(row)
                else:
                    print("No positions found")

                # Print Trading Pauses
                print("\n=== TRADING PAUSES ===")
                cursor.execute("PRAGMA table_info(trading_pause)")
                pause_columns = [col[1] for col in cursor.fetchall()]
                cursor.execute('SELECT * FROM trading_pause')
                pauses = cursor.fetchall()
                if pauses:
                    # Create header with column names
                    header = " | ".join(f"{col:<15}" for col in pause_columns)
                    print(header)
                    print("-" * len(header))
                    # Print data rows
                    for pause in pauses:
                        row = " | ".join(f"{str(val):<15}" for val in pause)
                        print(row)
                else:
                    print("No trading pauses found")

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
                
                # Get all position contract IDs
                cursor.execute('SELECT contract_id FROM positions ORDER BY created_timestamp DESC')
                position_ids = [row[0] for row in cursor.fetchall()]
                
                # Get orders and positions using existing methods
                orders = [self.get_order(order_id) for order_id in order_ids]
                positions = [self.get_position(contract_id) for contract_id in position_ids]
                
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
                        'start_time': pd.Timestamp(row[0]).tz_localize(self.timezone),
                        'end_time': pd.Timestamp(row[1]).tz_localize(self.timezone),
                        'created_timestamp': pd.Timestamp(row[2]).tz_localize(self.timezone)
                    } for row in rows]
                return []
        except Exception as e:
            logging.error(f"DB: Error getting trading pauses from database: {str(e)}")
            return []
        