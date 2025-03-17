from ibapi.client import EClient, Order
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

from src.ibkr_api import IBConnection
from src.utilities.logger import Logger
from src.configuration import Configuration

from dotenv import load_dotenv
from src.trading_system import TradingSystem


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    trading_system = TradingSystem(cfg)
    trading_system.start()

    # api = IBConnection(cfg.ib_host, cfg.ib_port, cfg.ib_client_id)
    # api.connect()

    # contract = Contract()
    # contract.symbol = "AAPL"
    # contract.secType = "STK"
    # contract.exchange = "SMART"
    # contract.currency = "USD"
    # # what_to_show = "TRADES"
    # what_to_show = "MIDPOINT"

    # api.reqHistoricalData(1, contract, "", "1 D", "1 min", what_to_show, True, 2, False, [])
    # time.sleep(10)
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

    # api.disconnect()


