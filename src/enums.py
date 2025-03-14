from enum import Enum


class Signal(Enum):
    BUY = 0
    SELL = 1
    HOLD = 2


class OrderType(Enum):
    LIMIT = 0
    MARKET = 1


class Exchange(str, Enum):
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    CRYPTO = "CRYPTO"
    EMPTY = ""
    UNKNOWN = "UNKNOWN"


class PositionDirection(str, Enum):
    SHORT = "short"
    LONG = "long"
