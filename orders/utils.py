import lib.gwpcc.things.stock
from lib.gwpcc import consts
from lib.gwpcc.colonies.colony import Colony
from lib.gwpcc.consts import KEY_CONFIGURATION_ORDERS, HASH_KEY_ORDER_TICK_DELAY
from lib.gwpcc.orders.order import Order
from lib.gwpcc.things.order_thing import OrderThing
import logging


def get_ticks_needed_for_delivery(connection):
    value = int(connection.hget(KEY_CONFIGURATION_ORDERS, HASH_KEY_ORDER_TICK_DELAY))

    return value


def anti_time_warp_check(colony, current_game_tick, connection):
    # Test to see if the current tick is EARLIER than the last time we received a game tick.
    # This usually means they warped back in time due to an earlier game save.  
    if current_game_tick < colony.LastGameTick:
        # We need to undo any orders pending or delivered since the "new" game tick.
        colony.Timewarps += 1

        # Undo all the items added to the market by transactions made after this tick.
        rollback_orders_since_tick(colony, current_game_tick, connection)

    colony.LastGameTick = current_game_tick


def rollback_orders_since_tick(colony: Colony, tick, connection):
    pipe = connection.pipeline()

    # Get all orders in the list.
    orders_hashes = connection.lrange(consts.KEY_COLONY_ALL_ORDERS.format(colony.Hash), 0, -1)

    orders = Order.get_many_from_database(orders_hashes, connection)

    for order_key, order in orders.items():

        # If there is order data
        if order:

            # Check if the order was placed AFTER the current tick, it never happened so undo it.
            if order.OrderedTick > tick:
                # Always re-add stock that was bought since we decremented the stock when the order was placed.
                things_bought_from_gwp = [OrderThing.from_dict(saved_thing) for saved_thing in
                                          order.ThingsBoughtFromGwp]
                lib.gwpcc.things.stock.receive_things_from_colony(colony.Hash, things_bought_from_gwp, pipe)

                # We don't remove things from GWP anymore if they time warp, we'll just keep hold of them.
                # for thing in things_to_remove_from_gwp:
                #     # Add namespace to item name to form Key

                things_sold_to_gwp = [OrderThing.from_dict(saved_thing) for saved_thing in
                                      order.ThingsSoldToGwp]

                lib.gwpcc.things.stock.give_things_to_colony(colony.Hash, things_sold_to_gwp, pipe)

                # Mark it reversed
                order.Status = consts.ORDER_STATUS_REVERSE

                # Remove it from the colonies processing list.
                pipe.lrem(consts.KEY_COLONY_NEW_ORDERS.format(colony.Hash), 0, order.Hash)

                order.save_to_database(pipe)

        else:
            logging.warning("Tried to enumerate a non-existent order ({}) for colony {}".format(order_key, colony.Hash))

    pipe.execute()
