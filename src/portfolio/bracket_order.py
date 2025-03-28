from ibapi.client import EClient
from ibapi.wrapper import EWrapper, OrderState
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
import pandas as pd
import os
from src.portfolio.trading_order import TradingOrder


def create_bracket_order(
        parent_order_id:int,
        action:str,
        quantity, 
        take_profit_limit_price:float, 
        stop_loss_price:float):
    """Create a bracket order"""
    parent = Order()
    parent.orderId = parent_order_id
    parent.action = action
    parent.orderType = "MKT"
    parent.totalQuantity = quantity
    parent.transmit = False

    takeProfit = Order()
    takeProfit.orderId = parent.orderId + 1
    takeProfit.action = "SELL" if action == "BUY" else "BUY"
    takeProfit.orderType = "LMT"
    takeProfit.totalQuantity = quantity
    takeProfit.lmtPrice = take_profit_limit_price
    takeProfit.parentId = parent_order_id
    takeProfit.transmit = False

    stopLoss = Order()
    stopLoss.orderId = parent.orderId + 2
    stopLoss.action = "SELL" if action == "BUY" else "BUY" 
    stopLoss.orderType = "STP"
    stopLoss.auxPrice = stop_loss_price
    stopLoss.totalQuantity = quantity
    stopLoss.parentId = parent_order_id
    stopLoss.transmit = True

    bracketOrder = [parent, takeProfit, stopLoss]
    return bracketOrder