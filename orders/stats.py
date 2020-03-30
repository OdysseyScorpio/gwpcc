from lib.gwpcc import consts, date_utils


def increment_order_counter(connection):
    pipe = connection.pipeline()
    pipe.incrby(consts.KEY_COUNTERS_HISTORICAL_ORDERS.format(date_utils.get_today_date_string()), 1)
    pipe.incrby(consts.KEY_TOTAL_ORDERS, 1)
    pipe.execute()


def update_orders_placed_by_hour(connection):
    pipe = connection.pipeline()
    pipe.incrby(consts.KEY_TRENDS_ORDERS_BY_HOUR.format(date_utils.get_current_hour()), 1)
    pipe.incrby(consts.KEY_COUNTERS_HOURLY_ORDERS.format(date_utils.get_current_hour()), 1)
    pipe.execute()
