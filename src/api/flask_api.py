from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
import sys
import json
import configparser

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.trading_system import TradingSystem
from src.configuration import Configuration

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize trading system
config_path = os.path.join(project_root, 'run.cfg')
cfg = Configuration(config_path)
trading_system = TradingSystem(cfg)

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current trading system status"""
    try:
        status = {
            'is_running': trading_system.is_running,
            'current_position': trading_system.portfolio_manager.get_current_position(),
            'last_signal': trading_system.last_signal,
            'last_trade_time': trading_system.last_trade_time
        }
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error getting status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_trading():
    """Start the trading system"""
    try:
        trading_system.start()
        return jsonify({'message': 'Trading system started'})
    except Exception as e:
        logging.error(f"Error starting trading system: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_trading():
    """Stop the trading system"""
    try:
        trading_system.stop()
        return jsonify({'message': 'Trading system stopped'})
    except Exception as e:
        logging.error(f"Error stopping trading system: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions"""
    try:
        positions = trading_system.portfolio_manager.get_all_positions()
        return jsonify(positions)
    except Exception as e:
        logging.error(f"Error getting positions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get recent orders"""
    try:
        orders = trading_system.portfolio_manager.get_all_orders()
        return jsonify(orders)
    except Exception as e:
        logging.error(f"Error getting orders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update trading settings"""
    try:
        if request.method == 'GET':
            # Convert config to dictionary format
            settings = {
                'trading_hours': {
                    'start_time': cfg.trading_hours.get('start_time'),
                    'end_time': cfg.trading_hours.get('end_time'),
                    'timezone': cfg.trading_hours.get('timezone')
                },
                'risk_parameters': {
                    'max_position_size': cfg.risk_parameters.get('max_position_size'),
                    'stop_loss_points': cfg.risk_parameters.get('stop_loss_points')
                },
                'strategy_parameters': {
                    'rsi_period': cfg.strategy_parameters.get('rsi_period'),
                    'bb_period': cfg.strategy_parameters.get('bb_period'),
                    'bb_std_dev': cfg.strategy_parameters.get('bb_std_dev')
                }
            }
            return jsonify(settings)
        else:  # POST
            new_settings = request.json
            
            # Create a new configparser object
            config = configparser.ConfigParser()
            
            # Update settings in config
            config['trading_hours'] = new_settings['trading_hours']
            config['risk_parameters'] = new_settings['risk_parameters']
            config['strategy_parameters'] = new_settings['strategy_parameters']
            
            # Save updated config
            with open(config_path, 'w') as f:
                config.write(f)
            
            # Reload configuration
            cfg.load_config(config_path)
            
            return jsonify({'message': 'Settings updated successfully'})
    except Exception as e:
        logging.error(f"Error handling settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 