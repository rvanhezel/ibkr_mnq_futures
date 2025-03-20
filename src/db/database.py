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
                # Create contracts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS contracts (
                        contract_id INTEGER PRIMARY KEY
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

    def add_contract(self, contract_id):
        """Add a contract to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO contracts (contract_id) VALUES (?)', (contract_id,))
                conn.commit()
                logging.info(f"Added contract id {contract_id} to database")
                return True
        except Exception as e:
            logging.error(f"DB: Error adding contract id {contract_id} to database: {str(e)}")
            return False

    def get_contracts(self):
        """Get all contract IDs from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT contract_id FROM contracts')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"DB: Error getting contracts from database: {str(e)}")
            return []

    def remove_contract(self, contract_id):
        """Remove a contract from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM contracts WHERE contract_id = ?', (contract_id,))
                conn.commit()
                logging.info(f"Removed contract {contract_id} from database")
                return True
        except Exception as e:
            logging.error(f"DB: Error removing contract from database: {str(e)}")
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
        