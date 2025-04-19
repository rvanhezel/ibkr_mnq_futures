from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import json
import configparser
import logging

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.trading_system import TradingSystem
from src.configuration import Configuration
from src.utilities.logger import Logger


# Initialize logger
logger = Logger()

app = Flask(__name__)
# Configure CORS to allow requests from the frontend
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize configuration and trading system
try:
    config_path = os.path.join(project_root, 'run.cfg')
    logging.info(f"Loading configuration from: {config_path}")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    # Create configparser instance for Flask API
    config_parser = configparser.ConfigParser()
    config_parser.read(config_path)
    
    # Create Configuration instance for trading system
    cfg = Configuration(config_path)
    trading_system = TradingSystem(cfg)
    
    logging.info("Configuration and trading system initialized successfully")
except Exception as e:
    msg = f"FlaskAPI  - Error initializing configuration: {str(e)}"
    logging.error(msg)
    raise Exception(msg)

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get trading system status"""
    try:
        logging.info("Fetching trading system status")
        
        return jsonify({
            'status': 'running' if trading_system.is_running else 'stopped',
            'last_update': trading_system.last_update_time,
            'positions': trading_system.portfolio_manager.get_all_positions(),
            'orders': trading_system.portfolio_manager.get_all_orders(),
            'daily_pnl': trading_system.portfolio_manager.daily_pnl(),
            'message': trading_system.message_queue.read_message()
        })
    except Exception as e:
        msg = f"FlaskAPI  - Error from endpoint /api/status: {str(e)}"
        logging.error(msg)
        return jsonify({'error': msg}), 500

@app.route('/api/start', methods=['POST'])
def start_trading():
    """Start the trading system"""
    try:
        logging.info("Starting trading system")
        if trading_system.is_running:
            return jsonify({'error': 'Trading system is already running'}), 400
        
        trading_system.start()
        return jsonify({
            'message': 'Trading system started successfully',
            'status': 'running'
        })
    except Exception as e:
        msg = f"FlaskAPI  - Error from endpoint /api/start: {str(e)}"
        logging.error(msg)
        return jsonify({'error': msg}), 500

@app.route('/api/stop', methods=['POST'])
def stop_trading():
    """Stop the trading system"""
    try:
        logging.info("Stopping trading system")
        if not trading_system.is_running:
            return jsonify({'error': 'Trading system is not running'}), 400
        
        trading_system.stop()
        return jsonify({
            'message': 'Trading system stopped successfully',
            'status': 'stopped'
        })
    except Exception as e:
        msg = f"FlaskAPI  - Error from endpoint /api/stop: {str(e)}"
        logging.error(msg)
        return jsonify({'error': msg}), 500

@app.route('/api/settings', methods=['GET', 'POST', 'OPTIONS'])
def handle_settings():
    """Get or update trading settings"""
    try:
        if request.method == 'OPTIONS':
            return '', 200
            
        if request.method == 'GET':
            logging.info("Fetching settings")
            try:
                # Convert config to dictionary format using config_parser
                settings = {
                    'run': {
                        'log_level': config_parser.get('Run', 'log_level')
                    },
                    'trading': {
                        'ticker': config_parser.get('Trading', 'ticker'),
                        'exchange': config_parser.get('Trading', 'exchange'),
                        'number_of_contracts': config_parser.get('Trading', 'number_of_contracts'),
                        'currency': config_parser.get('Trading', 'currency'),
                        'trading_start_time': config_parser.get('Trading', 'trading_start_time'),
                        'trading_end_time': config_parser.get('Trading', 'trading_end_time'),
                        'eod_exit_time': config_parser.get('Trading', 'eod_exit_time'),
                        'timezone': config_parser.get('Trading', 'timezone'),
                        'roll_contract_days_before': config_parser.get('Trading', 'roll_contract_days_before'),
                        'resubmit_cancelled_order': config_parser.get('Trading', 'resubmit_cancelled_order'),
                        'strategy': config_parser.get('Trading', 'strategy')
                    },
                    'risk_management': {
                        'stop_loss_ticks': config_parser.get('Risk_Management', 'stop_loss_ticks'),
                        'take_profit_ticks': config_parser.get('Risk_Management', 'take_profit_ticks'),
                        'max_24h_loss_per_contract': config_parser.get('Risk_Management', 'max_24h_loss_per_contract'),
                        'trading_pause_hours': config_parser.get('Risk_Management', 'trading_pause_hours'),
                        'no_endofday_risk': config_parser.get('Risk_Management', 'no_endofday_risk')
                    },
                    'market_data': {
                        'mnq_tick_size': config_parser.get('Market_Data', 'mnq_tick_size'),
                        'mnq_point_value': config_parser.get('Market_Data', 'mnq_point_value'),
                        'bar_size': config_parser.get('Market_Data', 'bar_size'),
                        'horizon': config_parser.get('Market_Data', 'horizon')
                    },
                    'api': {
                        'api': config_parser.get('API', 'api'),
                        'ib_host': config_parser.get('API', 'ib_host'),
                        'ib_client_id': config_parser.get('API', 'ib_client_id'),
                        'paper_trading': config_parser.get('API', 'paper_trading'),
                        'timeout': config_parser.get('API', 'timeout')
                    },
                    'technical_indicators': {
                        'bollinger_period': config_parser.get('Technical_Indicators', 'bollinger_period'),
                        'bollinger_std': config_parser.get('Technical_Indicators', 'bollinger_std'),
                        'rsi_period': config_parser.get('Technical_Indicators', 'rsi_period'),
                        'rsi_threshold': config_parser.get('Technical_Indicators', 'rsi_threshold')
                    }
                }
                logging.info(f"Returning settings: {settings}")
                return jsonify(settings)
            except Exception as e:
                logging.error(f"Error reading settings: {str(e)}")
                logging.error(f"Config sections: {config_parser.sections()}")
                return jsonify({'error': f'Error reading settings: {str(e)}'}), 500
        else:  # POST
            try:
                logging.info("Updating settings")
                new_settings = request.json
                logging.info(f"Received new settings: {new_settings}")
                
                # Update settings in config_parser
                # Run section
                config_parser.set('Run', 'log_level', str(new_settings['run']['log_level']))
                
                # Trading section
                config_parser.set('Trading', 'ticker', str(new_settings['trading']['ticker']))
                config_parser.set('Trading', 'exchange', str(new_settings['trading']['exchange']))
                config_parser.set('Trading', 'number_of_contracts', str(new_settings['trading']['number_of_contracts']))
                config_parser.set('Trading', 'currency', str(new_settings['trading']['currency']))
                config_parser.set('Trading', 'trading_start_time', str(new_settings['trading']['trading_start_time']))
                config_parser.set('Trading', 'trading_end_time', str(new_settings['trading']['trading_end_time']))
                config_parser.set('Trading', 'eod_exit_time', str(new_settings['trading']['eod_exit_time']))
                config_parser.set('Trading', 'timezone', str(new_settings['trading']['timezone']))
                config_parser.set('Trading', 'roll_contract_days_before', str(new_settings['trading']['roll_contract_days_before']))
                config_parser.set('Trading', 'resubmit_cancelled_order', str(new_settings['trading']['resubmit_cancelled_order']))
                config_parser.set('Trading', 'strategy', str(new_settings['trading']['strategy']))
                
                # Risk Management section
                config_parser.set('Risk_Management', 'stop_loss_ticks', str(new_settings['risk_management']['stop_loss_ticks']))
                config_parser.set('Risk_Management', 'take_profit_ticks', str(new_settings['risk_management']['take_profit_ticks']))
                config_parser.set('Risk_Management', 'max_24h_loss_per_contract', str(new_settings['risk_management']['max_24h_loss_per_contract']))
                config_parser.set('Risk_Management', 'trading_pause_hours', str(new_settings['risk_management']['trading_pause_hours']))
                config_parser.set('Risk_Management', 'no_endofday_risk', str(new_settings['risk_management']['no_endofday_risk']))
                
                # Market Data section
                config_parser.set('Market_Data', 'mnq_tick_size', str(new_settings['market_data']['mnq_tick_size']))
                config_parser.set('Market_Data', 'mnq_point_value', str(new_settings['market_data']['mnq_point_value']))
                config_parser.set('Market_Data', 'bar_size', str(new_settings['market_data']['bar_size']))
                config_parser.set('Market_Data', 'horizon', str(new_settings['market_data']['horizon']))
                
                # API section
                config_parser.set('API', 'api', str(new_settings['api']['api']))
                config_parser.set('API', 'ib_host', str(new_settings['api']['ib_host']))
                config_parser.set('API', 'ib_client_id', str(new_settings['api']['ib_client_id']))
                config_parser.set('API', 'paper_trading', str(new_settings['api']['paper_trading']))
                config_parser.set('API', 'timeout', str(new_settings['api']['timeout']))
                
                # Technical Indicators section
                config_parser.set('Technical_Indicators', 'bollinger_period', str(new_settings['technical_indicators']['bollinger_period']))
                config_parser.set('Technical_Indicators', 'bollinger_std', str(new_settings['technical_indicators']['bollinger_std']))
                config_parser.set('Technical_Indicators', 'rsi_period', str(new_settings['technical_indicators']['rsi_period']))
                config_parser.set('Technical_Indicators', 'rsi_threshold', str(new_settings['technical_indicators']['rsi_threshold']))
                
                # Save updated config
                with open(config_path, 'w') as f:
                    config_parser.write(f)
                
                # Reload Configuration instance with new settings
                cfg = Configuration(config_path)
                trading_system.config = cfg
                
                logging.info("Settings updated successfully")
                return jsonify({'message': 'Settings updated successfully'})
            except Exception as e:
                logging.error(f"Error updating settings: {str(e)}")
                return jsonify({'error': f'Error updating settings: {str(e)}'}), 500
            
    except Exception as e:
        msg = f"FlaskAPI  - Error from endpoint /api/settings: {str(e)}"
        logging.error(msg)
        return jsonify({'error': msg}), 500

@app.route('/api/reinitialize-db', methods=['POST'])
def reinitialize_db():
    """Reinitialize the database by deleting the existing file and creating a new instance. 
    Also clears persisting clear orders, statuses and positions.
    """
    try:
        logging.info("Reinitializing database")
        trading_system.db.reinitialize()
        trading_system.portfolio_manager.clear_orders_statuses_positions()
        return jsonify({'status': 'success', 'message': 'Database reinitialized successfully'})
    
    except Exception as e:
        msg = f"FlaskAPI  - Error from endpoint /api/reinitialize-db: {str(e)}"
        logging.error(msg)
        return jsonify({'error': msg}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 