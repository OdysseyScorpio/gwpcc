from lib.gwpcc import consts, date_utils
from lib.gwpcc.things.thing import BaseThing


def update_stats_for_sold_thing(thing: BaseThing, quantity, pipe):
    __update_stats_for_thing(False, thing, quantity, pipe)


def update_stats_for_bought_thing(thing: BaseThing, quantity, pipe):
    __update_stats_for_thing(True, thing, quantity, pipe)


def reset_thing_traded_stats_bucket(connection):
    actions = ['Bought', 'Sold']

    hour = date_utils.get_unix_time_range_for_hour()

    for action in actions:
        time = connection.get(consts.KEY_BUCKET_MOST_TRADED_CURRENT_LAST_UPDATED.format(action))
        if time and hour[0] != time:
            connection.delete(consts.KEY_BUCKET_MOST_TRADED_CURRENT_HOUR.format(action))
            connection.set(consts.KEY_BUCKET_MOST_TRADED_CURRENT_LAST_UPDATED.format(action), hour[0])
        if not time:
            connection.set(consts.KEY_BUCKET_MOST_TRADED_CURRENT_LAST_UPDATED.format(action), hour[0])


def __update_stats_for_thing(buy, thing, quantity, pipe):
    current_hour = date_utils.get_current_hour()
    current_day = date_utils.get_today_date_string()

    action = 'Bought' if buy else 'Sold'

    if not pipe:
        raise ValueError('Pipe parameter must be set!')

    # Update Base Market Value
    pipe.zincrby(consts.KEY_THING_BASE_MARKET_VALUE_DATA.format(thing.Hash), 1, thing.BaseMarketValue)

    # Hourly over time e.g. best hours to buy/sell trend
    pipe.hincrby(consts.KEY_COUNTERS_HOURLY_VOLUME_TRADED.format(current_hour), action, quantity)
    pipe.hincrby(consts.KEY_COUNTERS_HOURLY_THINGS.format(thing.Hash, current_hour), action, quantity)

    # Hourly, as in this has been traded in this hour or not.
    pipe.zincrby(consts.KEY_BUCKET_MOST_TRADED_CURRENT_HOUR.format(action), quantity, thing.Hash)

    # Daily
    pipe.hincrby(consts.KEY_COUNTERS_HISTORICAL_VOLUME_TRADED.format(current_day), action, quantity)

    # Per day by action by hash
    pipe.zincrby(
        consts.KEY_COUNTERS_HISTORICAL_THING_VOLUME_TRADED_BY_DATE_AND_ACTION.format(current_day, action),
        quantity, thing.Hash)

    # Per hash by day by action
    pipe.hincrby(consts.KEY_COUNTERS_HISTORICAL_THINGS_TRADED_BY_DATE.format(thing.Hash, current_day), action,
                 quantity)

    # Trends
    pipe.hincrby(consts.KEY_TRENDS_VOLUME_TRADED_BY_HOUR.format(current_hour), action, quantity)

    # Totals
    pipe.incrby(consts.KEY_TOTAL_BUY_OR_SELL.format(action), quantity)
