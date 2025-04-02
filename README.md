# MNQ Futures Trading Bot

This automated trading system trades Micro E-Mini Nasdaq 100 (MNQ) futures contracts using Interactive Brokers TWS API. The system implements a specific strategy based on Bollinger Bands and RSI indicators.

![Python Version](https://img.shields.io/badge/Python-3.12%2B-green)
<!-- ![License](https://img.shields.io/badge/License-MIT-yellow) -->

## 🚀 Features

- Trades MNQ futures contracts during specified market hours (9 PM CT to 4 PM CT)
- Uses 1-minute chart data for trading decisions
- Implements Bollinger Bands and RSI-based entry strategy
- Manages stop-loss and take-profit orders
- Handles contract rollovers automatically
- Implements trading pauses based on loss limits

## 📦 Requirements

- Python 3.12+
- Interactive Brokers account with TWS or IB Gateway
- Required Python packages (see requirements.txt)
- TWS/IB Gateway API

## 🔧 Setup

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Configure your Interactive Brokers connection:
   - Ensure TWS or IB Gateway is running and you're logged in
   - Configure the port number in config.py
   - Enable activeX and socket clients in TWS
   - Disable read-only API in TWS
   - Configure Windows to not 'sleep'

3. Update the configuration in config.py with your specific parameters

## 🎬 Usage

Run the main trading script:
```bash
python main.py
```

## Trading Logic

### Entry Conditions
- Price must be below the middle Bollinger Band
- RSI must cross above 31 (move from below 31 to above 31)

### Exit Conditions
- Stop Loss: 120 ticks per contract
- Take Profit: 300 ticks per contract

### Risk Management
- Trading pause if cumulative losses exceed $360 per contract in a 24-hour period
- Trading resumes after a 24-hour cooling period

### Trading Hours
- Trading occurs from 9 PM CT to 4 PM CT
- Sunday night through Friday evening
- Contract rollover occurs 7 days before quarterly expiration 