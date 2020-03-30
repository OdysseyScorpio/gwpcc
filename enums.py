from enum import Enum, unique


@unique
class TradeDirection(Enum):
    ToGWP = 'Bought'
    ToPlayer = 'Sold'


class PriceType(Enum):
    Buy = 'Buy'
    Sell = 'Sell'
