from ibapi.client import EClient, Order
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

from src.ibkr_api import IBConnection
from src.utilities.logger import Logger
from src.configuration import Configuration

from dotenv import load_dotenv
from src.trading_system import TradingSystem
import time
import logging
import os


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    # trading_system = TradingSystem(cfg)
    # trading_system.start()

    api = IBConnection(cfg.ib_host, cfg.ib_port, cfg.ib_client_id)
    api.connect()

    # contract = api.get_current_contract(cfg.ticker, cfg.exchange, cfg.currency)

    # a = 5
    # print(contract)
    # print(api.get_historical_data(contract))

    # # order_id = api.place_market_order(contract, 'BUY', 2)

    # # time.sleep(10)

    # # print(api.req_position_pnl(contract, 1))

    # api.disconnect()

    # contract = Contract()
    # contract.symbol = "AAPL"
    # contract.secType = "STK"
    # contract.exchange = "SMART"            
    # contract.currency = "USD"
    # what_to_show = "TRADES"
    # # what_to_show = "MIDPOINT"

    contract = Contract()  
    contract.symbol = "MNQ"
    contract.secType = "FUT"
    contract.exchange = "CME"            
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "202506"
    
    # data = api.get_historical_data(contract, "1 D", "1 min")
    # contract_details = api.get_contract_details(contract)
    # print(contract_details)

    # entry_order_id = api.place_market_order(contract, 'BUY', 2)

    # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])
    account_id = os.getenv('IBKR_ACCOUNT_ID')

    positions = api.get_positions()
    print(f"Positions: {positions}")
    
    mnq_contracts = []
    for contract_obj in positions[account_id]:
        contract = contract_obj['contract']
        if contract.symbol == 'MNQ' and contract.secType == 'FUT':
            mnq_contracts.append(contract)

    print(f"MNQ Contracts: {mnq_contracts}")

    account_summary = api.get_account_summary()
    print(f"Account Summary: {account_summary}")

    pnl_details = api.req_position_pnl(mnq_contracts[0].conId, account_id)
    print(pnl_details)

    time.sleep(2)
    # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])

    # order_id = api.next_order_id

    # time.sleep(70)

    # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])

    # order = Order()
    # order.action = "BUY"
    # order.totalQuantity = 1
    # order.orderType = "MKT"
    
    # logging.info(f"Placing order: {order}")
    # api.placeOrder(order_id, contract, order)
    # logging.info(f"Order placed with id: {order_id}")

    api.disconnect()


