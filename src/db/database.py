import sqlite3
import os
import logging
import pandas as pd


class Database:

    def __init__(self, db_path="trading.db"):
        self.db_path = db_path

        if not os.path.exists(self.db_path):
            self._init_db()
        else:
            logging.info(f"Using existing database at {self.db_path}")

    def _init_db(self):  
        """Initialize the database and create tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Create orders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INTEGER PRIMARY KEY,
                        order_type TEXT NOT NULL,
                        action TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        ticker TEXT NOT NULL,
                        security TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        currency TEXT NOT NULL,
                        expiry TEXT NOT NULL,
                        status TEXT NOT NULL,
                        time_sent TIMESTAMP NOT NULL,
                        time_filled TIMESTAMP
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
                        time_closed TIMESTAMP,
                        stop_loss_price REAL,
                        take_profit_price REAL,
                        market_value REAL,
                        unrealized_pnl REAL
                    )
                ''')
                # Create trading_pause table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_pause (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP NOT NULL
                    )
                ''')
                conn.commit()
                logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

    def add_order(self, order):
        """Add a trading order to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO orders (
                        order_id, order_type, action, quantity, ticker, security,
                        exchange, currency, expiry, status, time_sent, time_filled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order.order_id,
                    order.order_type,
                    order.action,
                    order.quantity,
                    order.ticker,
                    order.security,
                    order.exchange,
                    order.currency,
                    order.expiry,
                    order.status,
                    order.time_sent.isoformat(),
                    order.time_filled.isoformat() if order.time_filled else None
                ))
                conn.commit()
                logging.info(f"Added order {order.order_id} to database")
                return True
        except Exception as e:
            logging.error(f"DB: Error adding order to database: {str(e)}")
            return False

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
                        'order_type': row[1],
                        'action': row[2],
                        'quantity': row[3],
                        'ticker': row[4],
                        'security': row[5],
                        'exchange': row[6],
                        'currency': row[7],
                        'expiry': row[8],
                        'status': row[9],
                        'time_sent': pd.Timestamp(row[10]),
                        'time_filled': pd.Timestamp(row[11]) if row[11] else None
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting order from database: {str(e)}")
            return None

    def remove_order(self, order_id: int):
        """Remove an order from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
                conn.commit()
                logging.info(f"DB: Removed order {order_id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error removing order from database: {str(e)}")
            return False

    def add_position(self, position):
        """Add a position to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO positions (
                        contract_id, ticker, security, currency, expiry, quantity,
                        avg_price, status, time_opened, time_closed,
                        stop_loss_price, take_profit_price, market_value, unrealized_pnl
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    position.time_closed.isoformat() if position.time_closed else None,
                    position.stop_loss_price,
                    position.take_profit_price,
                    position.market_value,
                    position.unrealized_pnl
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
                        'time_closed': pd.Timestamp(row[9]) if row[9] else None,
                        'stop_loss_price': row[10],
                        'take_profit_price': row[11],
                        'market_value': row[12],
                        'unrealized_pnl': row[13]
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting position from database: {str(e)}")
            return None

    def remove_position(self, contract_id: int):
        """Remove a position from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM positions WHERE contract_id = ?', (contract_id,))
                conn.commit()
                logging.info(f"DB: Removed position {contract_id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error removing position from database: {str(e)}")
            return False

    def add_trading_pause(self, start_time: pd.Timestamp, end_time: pd.Timestamp):
        """Add a trading pause period to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trading_pause (start_time, end_time)
                    VALUES (?, ?)
                ''', (start_time.isoformat(), end_time.isoformat()))
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
                    SELECT start_time, end_time 
                    FROM trading_pause 
                    ORDER BY start_time DESC 
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    return {
                        'start_time': pd.Timestamp(row[0]).tz_localize(timezone),
                        'end_time': pd.Timestamp(row[1]).tz_localize(timezone)
                    }
                return None
        except Exception as e:
            logging.error(f"DB: Error getting trading pause from database: {str(e)}")
            return None

    def remove_trading_pause(self, start_time: pd.Timestamp):
        """Remove a trading pause from the database by start time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM trading_pause 
                    WHERE start_time = ?
                ''', (start_time.isoformat(),))
                conn.commit()
                logging.info(f"DB: Removed trading pause starting at {start_time}")
                return True
        except Exception as e:
            logging.error(f"DB: Error removing trading pause from database: {str(e)}")
            return False

    def update_order(self, order):
        """Update an existing order in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE orders SET
                        order_type = ?,
                        action = ?,
                        quantity = ?,
                        ticker = ?,
                        security = ?,
                        exchange = ?,
                        currency = ?,
                        expiry = ?,
                        status = ?,
                        time_sent = ?,
                        time_filled = ?
                    WHERE order_id = ?
                ''', (
                    order.order_type,
                    order.action,
                    order.quantity,
                    order.ticker,
                    order.security,
                    order.exchange,
                    order.currency,
                    order.expiry,
                    order.status,
                    order.time_sent.isoformat(),
                    order.time_filled.isoformat() if order.time_filled else None,
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
                        time_opened = ?,
                        time_closed = ?,
                        stop_loss_price = ?,
                        take_profit_price = ?,
                        market_value = ?,
                        unrealized_pnl = ?
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
                    position.time_closed.isoformat() if position.time_closed else None,
                    position.stop_loss_price,
                    position.take_profit_price,
                    position.market_value,
                    position.unrealized_pnl,
                    position.contract_id
                ))
                conn.commit()
                logging.info(f"DB: Updated position {position.contract_id}")
                return True
        except Exception as e:
            logging.error(f"DB: Error updating position in database: {str(e)}")
            return False
        