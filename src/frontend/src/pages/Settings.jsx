import { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../services/settingsService';
import { reinitializeDatabase } from '../services/tradingService';

const Settings = ({ setSystemError, setSystemSuccess }) => {
  const [settings, setSettings] = useState({
    run: { log_level: '' },
    trading: {
      ticker: '',
      exchange: '',
      number_of_contracts: '',
      currency: '',
      trading_start_time: '',
      trading_end_time: '',
      eod_exit_time: '',
      timezone: '',
      roll_contract_days_before: '',
      resubmit_cancelled_order: '',
      strategy: ''
    },
    risk_management: {
      stop_loss_ticks: '',
      take_profit_ticks: '',
      max_24h_loss_per_contract: '',
      trading_pause_hours: '',
      no_endofday_risk: ''
    },
    market_data: {
      mnq_tick_size: '',
      mnq_point_value: '',
      bar_size: '',
      horizon: ''
    },
    api: {
      api: '',
      ib_host: '',
      ib_client_id: '',
      paper_trading: '',
      timeout: ''
    },
    technical_indicators: {
      bollinger_period: '',
      bollinger_std: '',
      rsi_period: '',
      rsi_threshold: ''
    }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await getSettings();
        setSettings(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleChange = (section, field, value) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError(null);
      console.log('Submitting settings...');
      const message = await updateSettings(settings);
      console.log('Received message from API:', message);
      setSuccessMessage(message);
      console.log('Success message set to:', message);
      setTimeout(() => {
        console.log('Clearing success message');
        setSuccessMessage('');
      }, 10000);
    } catch (err) {
      console.error('Error in handleSubmit:', err);
      setError(err.message);
    }
  };

  const handleReinitializeDB = async () => {
    if (window.confirm('Are you sure you want to reinitialize the database? This will delete all existing data.')) {
      try {
        setIsLoading(true);
        await reinitializeDatabase();

        setSuccessMessage('Database reinitialized successfully');
        setTimeout(() => {
          setSuccessMessage('');
        }, 3000);

        setSystemSuccess('Database reinitialized successfully');
        setTimeout(() => setSystemSuccess(null), 6000);
        setSystemError(null);
      } catch (err) {
        setSystemError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {successMessage}
          </div>
        )}

        {loading ? (
          <p>Loading settings...</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">

            {/* Trading Settings */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Trading Settings</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Ticker</label>
                  <input
                    type="text"
                    value={settings.trading.ticker}
                    onChange={(e) => handleChange('trading', 'ticker', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Exchange</label>
                  <input
                    type="text"
                    value={settings.trading.exchange}
                    onChange={(e) => handleChange('trading', 'exchange', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Number of Contracts</label>
                  <input
                    type="number"
                    value={settings.trading.number_of_contracts}
                    onChange={(e) => handleChange('trading', 'number_of_contracts', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Currency</label>
                  <input
                    type="text"
                    value={settings.trading.currency}
                    onChange={(e) => handleChange('trading', 'currency', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Trading Start Time</label>
                  <input
                    type="text"
                    value={settings.trading.trading_start_time}
                    onChange={(e) => handleChange('trading', 'trading_start_time', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Trading End Time</label>
                  <input
                    type="text"
                    value={settings.trading.trading_end_time}
                    onChange={(e) => handleChange('trading', 'trading_end_time', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">EOD Exit Time</label>
                  <input
                    type="text"
                    value={settings.trading.eod_exit_time}
                    onChange={(e) => handleChange('trading', 'eod_exit_time', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Timezone</label>
                  <input
                    type="text"
                    value={settings.trading.timezone}
                    onChange={(e) => handleChange('trading', 'timezone', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Roll Contract Days Before</label>
                  <input
                    type="number"
                    value={settings.trading.roll_contract_days_before}
                    onChange={(e) => handleChange('trading', 'roll_contract_days_before', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Strategy</label>
                  <select
                    value={settings.trading.strategy}
                    onChange={(e) => handleChange('trading', 'strategy', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  >
                    <option value="buy">Buy</option>
                    <option value="bollinger_rsi">Bollinger RSI</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Risk Management Settings */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Risk Management</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Stop Loss Ticks</label>
                  <input
                    type="number"
                    value={settings.risk_management.stop_loss_ticks}
                    onChange={(e) => handleChange('risk_management', 'stop_loss_ticks', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Take Profit Ticks</label>
                  <input
                    type="number"
                    value={settings.risk_management.take_profit_ticks}
                    onChange={(e) => handleChange('risk_management', 'take_profit_ticks', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Max 24h Loss per Contract</label>
                  <input
                    type="number"
                    value={settings.risk_management.max_24h_loss_per_contract}
                    onChange={(e) => handleChange('risk_management', 'max_24h_loss_per_contract', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Trading Pause Hours</label>
                  <input
                    type="number"
                    value={settings.risk_management.trading_pause_hours}
                    onChange={(e) => handleChange('risk_management', 'trading_pause_hours', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Market Data Settings */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Market Data</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">MNQ Tick Size</label>
                  <input
                    type="number"
                    step="0.01"
                    value={settings.market_data.mnq_tick_size}
                    onChange={(e) => handleChange('market_data', 'mnq_tick_size', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">MNQ Point Value</label>
                  <input
                    type="number"
                    value={settings.market_data.mnq_point_value}
                    onChange={(e) => handleChange('market_data', 'mnq_point_value', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Bar Size</label>
                  <input
                    type="text"
                    value={settings.market_data.bar_size}
                    onChange={(e) => handleChange('market_data', 'bar_size', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Horizon</label>
                  <input
                    type="text"
                    value={settings.market_data.horizon}
                    onChange={(e) => handleChange('market_data', 'horizon', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* API Settings */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">API Settings</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">IB Host</label>
                  <input
                    type="text"
                    value={settings.api.ib_host}
                    onChange={(e) => handleChange('api', 'ib_host', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">IB Client ID</label>
                  <input
                    type="number"
                    value={settings.api.ib_client_id}
                    onChange={(e) => handleChange('api', 'ib_client_id', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Paper Trading</label>
                  <select
                    value={settings.api.paper_trading}
                    onChange={(e) => handleChange('api', 'paper_trading', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  >
                    <option value="True">True</option>
                    <option value="False">False</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Timeout</label>
                  <input
                    type="number"
                    value={settings.api.timeout}
                    onChange={(e) => handleChange('api', 'timeout', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Technical Indicators Settings */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Technical Indicators</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Bollinger Bands Period</label>
                  <input
                    type="number"
                    value={settings.technical_indicators.bollinger_period}
                    onChange={(e) => handleChange('technical_indicators', 'bollinger_period', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Bollinger Bands Std Dev</label>
                  <input
                    type="number"
                    value={settings.technical_indicators.bollinger_std}
                    onChange={(e) => handleChange('technical_indicators', 'bollinger_std', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">RSI Period</label>
                  <input
                    type="number"
                    value={settings.technical_indicators.rsi_period}
                    onChange={(e) => handleChange('technical_indicators', 'rsi_period', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">RSI Threshold</label>
                  <input
                    type="number"
                    value={settings.technical_indicators.rsi_threshold}
                    onChange={(e) => handleChange('technical_indicators', 'rsi_threshold', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Run Settings */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Run Settings</h2>
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Log Level</label>
                  <select
                    value={settings.run.log_level}
                    onChange={(e) => handleChange('run', 'log_level', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                  >
                    <option value="Debug">Debug</option>
                    <option value="Info">Info</option>
                    <option value="Warning">Warning</option>
                    <option value="Error">Error</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end items-center space-x-4">
              <button
                type="submit"
                className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Save Settings
              </button>
            </div>
          </form>
        )}

        {/* Database Reinitialization Section */}
        <div className="mt-8 p-6 bg-white rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Database Management</h2>
          <div className="space-y-4">
            <p className="text-gray-600">
              Reinitialize the database to start fresh. This will delete all existing data and reset PnL
            </p>
            <button
              onClick={handleReinitializeDB}
              disabled={isLoading}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Reinitializing...' : 'Reinitialize Database'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings; 