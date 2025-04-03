from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
import sys
import json
import configparser

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS to allow requests from the frontend
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize configuration
try:
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'run.cfg')
    logger.info(f"Loading configuration from: {config_path}")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    
    # Verify all required sections exist
    required_sections = ['Run', 'Trading', 'Risk_Management', 'Market_Data', 'API', 'Technical_Indicators']
    missing_sections = [section for section in required_sections if section not in cfg]
    if missing_sections:
        raise ValueError(f"Missing required configuration sections: {missing_sections}")
    
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Error initializing configuration: {str(e)}")
    raise

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get trading system status"""
    try:
        logger.info("Fetching trading system status")
        # For now, return mock data
        return jsonify({
            'status': 'stopped',
            'last_update': '2024-01-01 00:00:00',
            'positions': [
                {
                    'symbol': 'MNQ',
                    'quantity': 0,
                    'avg_price': 0,
                    'unrealized_pnl': 0,
                    'realized_pnl': 0
                }
            ],
            'orders': [
                {
                    'order_id': '123',
                    'symbol': 'MNQ',
                    'action': 'BUY',
                    'quantity': 1,
                    'order_type': 'LIMIT',
                    'limit_price': 17000,
                    'status': 'FILLED',
                    'filled_quantity': 1,
                    'remaining_quantity': 0,
                    'timestamp': '2024-01-01 00:00:00'
                }
            ]
        })
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': f'Error getting status: {str(e)}'}), 500

@app.route('/api/start', methods=['POST'])
def start_trading():
    """Start the trading system"""
    try:
        logger.info("Starting trading system")
        # TODO: Implement actual trading system start
        return jsonify({'message': 'Trading system started successfully'})
    except Exception as e:
        logger.error(f"Error starting trading system: {str(e)}")
        return jsonify({'error': f'Error starting trading system: {str(e)}'}), 500

@app.route('/api/stop', methods=['POST'])
def stop_trading():
    """Stop the trading system"""
    try:
        logger.info("Stopping trading system")
        # TODO: Implement actual trading system stop
        return jsonify({'message': 'Trading system stopped successfully'})
    except Exception as e:
        logger.error(f"Error stopping trading system: {str(e)}")
        return jsonify({'error': f'Error stopping trading system: {str(e)}'}), 500

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

@app.route('/api/settings', methods=['GET', 'POST', 'OPTIONS'])
def handle_settings():
    """Get or update trading settings"""
    try:
        if request.method == 'OPTIONS':
            return '', 200
            
        if request.method == 'GET':
            logger.info("Fetching settings")
            try:
                # Convert config to dictionary format
                settings = {
                    'run': {
                        'log_level': cfg.get('Run', 'log_level')
                    },
                    'trading': {
                        'ticker': cfg.get('Trading', 'ticker'),
                        'exchange': cfg.get('Trading', 'exchange'),
                        'number_of_contracts': cfg.get('Trading', 'number_of_contracts'),
                        'currency': cfg.get('Trading', 'currency'),
                        'trading_start_time': cfg.get('Trading', 'trading_start_time'),
                        'trading_end_time': cfg.get('Trading', 'trading_end_time'),
                        'eod_exit_time': cfg.get('Trading', 'eod_exit_time'),
                        'timezone': cfg.get('Trading', 'timezone'),
                        'roll_contract_days_before': cfg.get('Trading', 'roll_contract_days_before'),
                        'resubmit_cancelled_order': cfg.get('Trading', 'resubmit_cancelled_order'),
                        'strategy': cfg.get('Trading', 'strategy')
                    },
                    'risk_management': {
                        'stop_loss_ticks': cfg.get('Risk_Management', 'stop_loss_ticks'),
                        'take_profit_ticks': cfg.get('Risk_Management', 'take_profit_ticks'),
                        'max_24h_loss_per_contract': cfg.get('Risk_Management', 'max_24h_loss_per_contract'),
                        'trading_pause_hours': cfg.get('Risk_Management', 'trading_pause_hours'),
                        'no_endofday_risk': cfg.get('Risk_Management', 'no_endofday_risk')
                    },
                    'market_data': {
                        'mnq_tick_size': cfg.get('Market_Data', 'mnq_tick_size'),
                        'mnq_point_value': cfg.get('Market_Data', 'mnq_point_value'),
                        'bar_size': cfg.get('Market_Data', 'bar_size'),
                        'horizon': cfg.get('Market_Data', 'horizon')
                    },
                    'api': {
                        'api': cfg.get('API', 'API'),
                        'ib_host': cfg.get('API', 'ib_host'),
                        'ib_client_id': cfg.get('API', 'ib_client_id'),
                        'paper_trading': cfg.get('API', 'paper_trading'),
                        'timeout': cfg.get('API', 'timeout')
                    },
                    'technical_indicators': {
                        'bollinger_period': cfg.get('Technical_Indicators', 'bollinger_period'),
                        'bollinger_std': cfg.get('Technical_Indicators', 'bollinger_std'),
                        'rsi_period': cfg.get('Technical_Indicators', 'rsi_period'),
                        'rsi_threshold': cfg.get('Technical_Indicators', 'rsi_threshold')
                    }
                }
                logger.info(f"Returning settings: {settings}")
                return jsonify(settings)
            except Exception as e:
                logger.error(f"Error reading settings: {str(e)}")
                return jsonify({'error': f'Error reading settings: {str(e)}'}), 500
        else:  # POST
            try:
                logger.info("Updating settings")
                new_settings = request.json
                logger.info(f"Received new settings: {new_settings}")
                
                # Update settings in config
                # Run section
                cfg.set('Run', 'log_level', str(new_settings['run']['log_level']))
                
                # Trading section
                cfg.set('Trading', 'ticker', str(new_settings['trading']['ticker']))
                cfg.set('Trading', 'exchange', str(new_settings['trading']['exchange']))
                cfg.set('Trading', 'number_of_contracts', str(new_settings['trading']['number_of_contracts']))
                cfg.set('Trading', 'currency', str(new_settings['trading']['currency']))
                cfg.set('Trading', 'trading_start_time', str(new_settings['trading']['trading_start_time']))
                cfg.set('Trading', 'trading_end_time', str(new_settings['trading']['trading_end_time']))
                cfg.set('Trading', 'eod_exit_time', str(new_settings['trading']['eod_exit_time']))
                cfg.set('Trading', 'timezone', str(new_settings['trading']['timezone']))
                cfg.set('Trading', 'roll_contract_days_before', str(new_settings['trading']['roll_contract_days_before']))
                cfg.set('Trading', 'resubmit_cancelled_order', str(new_settings['trading']['resubmit_cancelled_order']))
                cfg.set('Trading', 'strategy', str(new_settings['trading']['strategy']))
                
                # Risk Management section
                cfg.set('Risk_Management', 'stop_loss_ticks', str(new_settings['risk_management']['stop_loss_ticks']))
                cfg.set('Risk_Management', 'take_profit_ticks', str(new_settings['risk_management']['take_profit_ticks']))
                cfg.set('Risk_Management', 'max_24h_loss_per_contract', str(new_settings['risk_management']['max_24h_loss_per_contract']))
                cfg.set('Risk_Management', 'trading_pause_hours', str(new_settings['risk_management']['trading_pause_hours']))
                cfg.set('Risk_Management', 'no_endofday_risk', str(new_settings['risk_management']['no_endofday_risk']))
                
                # Market Data section
                cfg.set('Market_Data', 'mnq_tick_size', str(new_settings['market_data']['mnq_tick_size']))
                cfg.set('Market_Data', 'mnq_point_value', str(new_settings['market_data']['mnq_point_value']))
                cfg.set('Market_Data', 'bar_size', str(new_settings['market_data']['bar_size']))
                cfg.set('Market_Data', 'horizon', str(new_settings['market_data']['horizon']))
                
                # API section
                cfg.set('API', 'API', str(new_settings['api']['api']))
                cfg.set('API', 'ib_host', str(new_settings['api']['ib_host']))
                cfg.set('API', 'ib_client_id', str(new_settings['api']['ib_client_id']))
                cfg.set('API', 'paper_trading', str(new_settings['api']['paper_trading']))
                cfg.set('API', 'timeout', str(new_settings['api']['timeout']))
                
                # Technical Indicators section
                cfg.set('Technical_Indicators', 'bollinger_period', str(new_settings['technical_indicators']['bollinger_period']))
                cfg.set('Technical_Indicators', 'bollinger_std', str(new_settings['technical_indicators']['bollinger_std']))
                cfg.set('Technical_Indicators', 'rsi_period', str(new_settings['technical_indicators']['rsi_period']))
                cfg.set('Technical_Indicators', 'rsi_threshold', str(new_settings['technical_indicators']['rsi_threshold']))
                
                # Save updated config
                with open(config_path, 'w') as f:
                    cfg.write(f)
                
                logger.info("Settings updated successfully")
                return jsonify({'message': 'Settings updated successfully'})
            except Exception as e:
                logger.error(f"Error updating settings: {str(e)}")
                return jsonify({'error': f'Error updating settings: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error handling settings request: {str(e)}")
        return jsonify({'error': f'Error handling settings request: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 