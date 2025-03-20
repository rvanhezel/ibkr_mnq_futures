import sqlite3
import os
import logging
from datetime import datetime


class Database:
    def __init__(self, db_path="trading.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS contracts (
                        contract_id INTEGER PRIMARY KEY
                    )
                ''')
                conn.commit()
                logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

    def add_contract(self, contract):
        """Add a contract to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO contracts (contract_id) VALUES (?)', (contract.conId,))
                conn.commit()
                logging.info(f"Added contract {contract.conId} to database")
                return True
        except Exception as e:
            logging.error(f"Error adding contract to database: {str(e)}")
            return False

    def get_contracts(self):
        """Get all contract IDs from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT contract_id FROM contracts')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Error getting contracts from database: {str(e)}")
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
            logging.error(f"Error removing contract from database: {str(e)}")
            return False 