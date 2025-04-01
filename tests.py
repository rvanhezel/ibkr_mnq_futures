from ibapi.client import EClient, Order
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

from src.api.ibkr_api import IBConnection
from src.utilities.logger import Logger
from src.configuration import Configuration

from dotenv import load_dotenv
from src.trading_system import TradingSystem
import time
import logging
import os
from src.portfolio.trading_order import TradingOrder


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    api = IBConnection(cfg.ib_host, cfg.ib_port, cfg.ib_client_id, cfg.timeout, cfg.timezone)
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
    # contract.exchange = "CME"            
    contract.exchange = "SMART"            
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "202506"

    positions = api.get_positions()
    
    mnq_contracts = []
    for contract_obj in positions:
        position_number = int(contract_obj['position'])
        contract = contract_obj['contract']
        if contract.symbol == 'MNQ' and contract.secType == 'FUT':
            mnq_contracts.append((contract, position_number))

    print(f"We have {len(mnq_contracts)} MNQ contracts")
    print(f"MNQ Contracts: {mnq_contracts}")
    
    data = api.get_historical_data(contract, "1 D", "1 min")

    print(data)


    contract_details = api.get_contract_details(contract)
    print(contract_details)

    # order_id, order_status = api.place_market_order(contract, 'BUY', 2)
    # print(f"Order ID: {order_id}, Order Status: {order_status}")

    # order_status = api.get_order_status(order_id)
    # print(f"Order Status: {order_status}")  

    # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])

    # fill_price = api.get_latest_mid_price(contract)
    # upper_buy_price = fill_price + 0.75*(cfg.take_profit_ticks * cfg.mnq_tick_size)
    # upper_sell_price = fill_price + (cfg.take_profit_ticks * cfg.mnq_tick_size)
    # stop_loss_price = fill_price - (cfg.stop_loss_ticks * cfg.mnq_tick_size)

    # mkt_order = TradingOrder(
    #     order_type='MKT',
    #     # order_type='LMT',
    #     action='BUY',
    #     quantity=2,
    #     contract=contract,
    #     order_id=None,
    #     status=None,
    #     timezone=cfg.timezone,
    #     parent_order_id=None,
    #     # aux_price=upper_buy_price,
    #     transmit=False
    # )

    # api.place_trading_order(mkt_order)
    # time.sleep(3)

    # lmt_order = TradingOrder(
    #     order_type='LMT',
    #     action='SELL',
    #     quantity=2,
    #     contract=contract,
    #     order_id=None,
    #     status=None,
    #     timezone=cfg.timezone,
    #     parent_order_id=mkt_order.order_id,
    #     # aux_price=upper_sell_price,
    #     aux_price=20475,
    #     transmit=False
    # )

    # api.place_trading_order(lmt_order)
    # lmt_order_status = api.order_statuses[lmt_order.order_id]

    # time.sleep(3)


    # stp_order = TradingOrder(
    #     order_type='STP',
    #     action='SELL',
    #     quantity=2,
    #     contract=contract,
    #     order_id=None,
    #     status=None,
    #     timezone=cfg.timezone,
    #     parent_order_id=mkt_order.order_id,
    #     # aux_price=stop_loss_price,
    #     aux_price=20472,
    #     transmit=True
    # )

    # api.place_trading_order(stp_order)
    # stp_order_status = api.order_statuses[stp_order.order_id]



    # api.update_order_status(mkt_order)
    # api.update_order_status(stp_order)
    # api.update_order_status(lmt_order)

    # time.sleep(3)


    # # positions = api.get_positions()
    
    # # mnq_contracts = []
    # # for contract_obj in positions:
    # #     position_number = int(contract_obj['position'])
    # #     contract = contract_obj['contract']
    # #     if contract.symbol == 'MNQ' and contract.secType == 'FUT':
    # #         mnq_contracts.append((contract, position_number))

    # # print(f"We have {len(mnq_contracts)} MNQ contracts")
    # # print(f"MNQ Contracts: {mnq_contracts}")

    # # pnl_details = api.req_position_pnl(mnq_contracts[0][0].conId)
    # # print(pnl_details)


    # # contract, position_number = mnq_contracts[-1]
    # # if contract.exchange == '':
    # #     contract.exchange = 'CME'
    # #     print(f"Updated Contract exchange")

    # # sell_order_id, order_status = api.place_market_order(contract, 'SELL', position_number)
    # # print(f"SELL Order ID: {sell_order_id}, Order Status: {order_status}")

    # # time.sleep(3)

    # # order_status = api.get_order_status(sell_order_id)
    # # print(f"SELL Order Status: {order_status}")  

    # # updated_positions = api.get_positions()
    # # print(f"Updated Positions: {updated_positions}")


    # # pnl_details = api.req_position_pnl(mnq_contracts[0][0].conId)
    # # print(pnl_details)

    # # time.sleep(2)

    # # api.update_order_status(mkt_order)
    # # api.update_order_status(stp_order)
    # # api.update_order_status(lmt_order)

    # # # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])

    # # # order_id = api.next_order_id

    # # # time.sleep(70)

    # # # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])

    # # # order = Order()
    # # # order.action = "BUY"
    # # # order.totalQuantity = 1
    # # # order.orderType = "MKT"
    
    # # # logging.info(f"Placing order: {order}")
    # # # api.placeOrder(order_id, contract, order)
    # # # logging.info(f"Order placed with id: {order_id}")

    api.disconnect()


