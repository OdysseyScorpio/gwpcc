from collections import Counter, OrderedDict

from lib.gwpcc import consts
from lib.gwpcc.consts import KEY_TRENDS_HISTORICAL_THING_PRICE_BY_DAY
from lib.gwpcc.date_utils import get_date_string_by_delta, get_today_date_string, get_unix_time_range_for_hour, \
    utc_epoch_to_string
from lib.gwpcc.enums import PriceType, TradeDirection
from lib.gwpcc.things.base_thing import BaseThing, preserve_last_value, value_lookup


class Thing(BaseThing):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self._current_value['CurrentSellPrice'] = float(kwargs.get('CurrentSellPrice', -1))
        self._current_value['UseServerPrice'] = kwargs.get('UseServerPrice', False)
        self._current_value['BuyPriceOverride'] = float(kwargs.get('BuyPriceOverride', 0))
        self._current_value['SellPriceOverride'] = float(kwargs.get('SellPriceOverride', 0))
        self._current_value['LocalizedName'] = kwargs.get('LocalizedName', '')
        self._from_database = False

        # Initialise to zeroes.
        self._bmv_votes = Counter()
        if 'BMVVotes' in kwargs:
            # The incoming price history is a list of tuples.
            for price, score in kwargs['BMVVotes']:
                self._bmv_votes.update({float(price): score})

        # Initialise to zeroes.
        if 'TradeHistory' in kwargs:
            self._trade_history = {
                TradeDirection.ToPlayer: kwargs['TradeHistory'].get(TradeDirection.ToPlayer.value, 0),
                TradeDirection.ToGWP   : kwargs['TradeHistory'].get(TradeDirection.ToGWP.value, 0)}
        else:
            self._trade_history = {TradeDirection.ToGWP: 0, TradeDirection.ToPlayer: 0}

    @property
    @value_lookup
    def CurrentSellPrice(self):
        pass

    @CurrentSellPrice.setter
    @preserve_last_value
    def CurrentSellPrice(self, value):
        pass

    @property
    @value_lookup
    def BuyPriceOverride(self):
        pass

    @BuyPriceOverride.setter
    @preserve_last_value
    def BuyPriceOverride(self, value):
        pass

    @property
    @value_lookup
    def SellPriceOverride(self):
        pass

    @SellPriceOverride.setter
    @preserve_last_value
    def SellPriceOverride(self, value):
        pass

    @property
    @value_lookup
    def UseServerPrice(self):
        pass

    @UseServerPrice.setter
    @preserve_last_value
    def UseServerPrice(self, value):
        pass

    @property
    def FromDatabase(self):
        return self._from_database

    @property
    @value_lookup
    def LocalizedName(self):
        pass

    @LocalizedName.setter
    @preserve_last_value
    def LocalizedName(self, value):
        pass

    @property
    def BMVVotes(self):
        return self._bmv_votes

    @property
    def TradeHistory(self):
        return self._trade_history

    def to_dict(self, delta=False):
        to_save = {}

        if self.FromDatabase and delta:
            for key in self._changes.keys():
                to_save[key] = getattr(self, key)
        else:
            for prop in self.get_props():
                to_save[prop] = getattr(self, prop)

        # Remove these, we don't need to store them.
        if 'FromDatabase' in to_save:
            del to_save['FromDatabase']

        if 'LocalizedName' in to_save:
            del to_save['LocalizedName']

        if 'UseServerPrice' in to_save:
            to_save['UseServerPrice'] = 'true' if to_save['UseServerPrice'] else 'false'

        if 'MinifiedContainer' in to_save:
            to_save['MinifiedContainer'] = 'true' if to_save['MinifiedContainer'] else 'false'

        if 'BMVVotes' in to_save:
            del to_save['BMVVotes']

        if 'TradeHistory' in to_save:
            del to_save['TradeHistory']

        return to_save

    def save_to_database(self, connection):
        """
        Save this Thing to the database using the provided connection.
        The connection can be direct or a pipeline object.
        If None is provided, a connection will be created.
        :param connection: Can be a None, a Redis connection or a pipeline.
        :return:
        """

        if not self.FromDatabase:
            # We need to add the hash to the Thing Index
            connection.sadd(consts.KEY_THING_INDEX, self.Hash)

        changes = self.to_dict(delta=True)

        # Only save if there actually changes.
        if len(changes):
            # Do a Delta update if we can (Only if FromDatabase is True)
            connection.hmset(consts.KEY_THING_META.format(self.Hash), changes)
            start_hour = str(get_unix_time_range_for_hour()[0])
            if self.has_changed('CurrentBuyPrice'):
                connection.zadd(KEY_TRENDS_HISTORICAL_THING_PRICE_BY_DAY.format(self.Hash, PriceType.Buy.value),
                                {start_hour: self.CurrentBuyPrice})

            if self.has_changed('CurrentSellPrice'):
                connection.zadd(KEY_TRENDS_HISTORICAL_THING_PRICE_BY_DAY.format(self.Hash, PriceType.Sell.value),
                                {start_hour: self.CurrentSellPrice})

    @classmethod
    def get_many_from_database_by_hash(cls, list_of_thing_hash, connection, date):
        pipe = connection.pipeline()

        # Iterate of the list of Thing data structures and build hash keys
        for thing_hash in list_of_thing_hash:
            pipe.hgetall(consts.KEY_THING_META.format(thing_hash))
            pipe.hgetall(consts.KEY_COUNTERS_HISTORICAL_THINGS_TRADED_BY_DATE.format(thing_hash,
                                                                                     date))
            pipe.zrange(consts.KEY_THING_BASE_MARKET_VALUE_DATA.format(thing_hash), 0, -1, withscores=True)

        db_data = pipe.execute()

        return cls.__parse_get_many_results(db_data, list_of_thing_hash)

    @classmethod
    def __parse_get_many_results(cls, db_data, things_to_find, substitute=None):
        # Lets see if you can wrap your head around this after 1 AM and 9 coffees...
        results = {}
        for index in range(0, len(db_data) - 1, 3):
            if len(db_data[index]) > 0:
                if len(db_data[index + 1]) > 0:
                    db_data[index]['TradeHistory'] = db_data[index + 1]
                if len(db_data[index + 2]) > 0:
                    db_data[index]['BMVVotes'] = db_data[index + 2]
                results[db_data[index]['Hash']] = db_data[index]

        for hash_key in things_to_find:
            thing_to_check = results.get(hash_key, {})
            if len(thing_to_check) and 'Name' in thing_to_check:
                data = results[hash_key]
                new_thing = cls.from_dict(data)
                new_thing._from_database = True
                results[hash_key] = new_thing
            else:
                # Use the generated object, Caller should test FromDatabase
                if substitute:
                    results[hash_key] = substitute[hash_key]

        return results

    @classmethod
    def get_many_from_database(cls, list_of_thing_dict, connection, date=None):

        if date:
            return cls.__get_many_from_database_with_history(list_of_thing_dict, connection, date)

        pipe = connection.pipeline()

        things_to_find = OrderedDict()

        # Iterate of the list of Thing data structures and build hash keys
        for thing_data in list_of_thing_dict:
            thing_obj = cls.from_dict(thing_data)
            things_to_find[thing_obj.Hash] = thing_obj
            pipe.hgetall(consts.KEY_THING_META.format(thing_obj.Hash))

        # Combine the list of hashes and list of results into a dictionary of Key(Hash), Value(Data)
        results = pipe.execute()

        return cls._parse_many_no_history(things_to_find, results)

    @classmethod
    def get_many_from_database_by_hash_without_history(cls, list_of_thing_hash, connection):
        pipe = connection.pipeline()

        things_to_find = OrderedDict()

        # Iterate of the list of Thing data structures and build hash keys
        for thing_hash in list_of_thing_hash:
            things_to_find[thing_hash] = None
            pipe.hgetall(consts.KEY_THING_META.format(thing_hash))

        # Combine the list of hashes and list of results into a dictionary of Key(Hash), Value(Data)
        results = pipe.execute()

        return cls._parse_many_no_history(things_to_find, results)

    @classmethod
    def _parse_many_no_history(cls, things_to_find, results):
        # Combine the list of hashes and list of results into a dictionary of Key(Hash), Value(Data)
        results = dict(zip(things_to_find.keys(), results))

        for hash_key, data in results.items():
            if len(data) and 'Name' in data:
                new_thing = cls.from_dict(data)
                new_thing._from_database = True
                results[hash_key] = new_thing
            else:
                # Use the generated object, Caller should test FromDatabase
                results[hash_key] = things_to_find[hash_key]

        return results

    @classmethod
    def __get_many_from_database_with_history(cls, list_of_thing_dict, connection, date):
        pipe = connection.pipeline()

        things_to_find = OrderedDict()

        # Iterate of the list of Thing data structures and build hash keys
        for thing_data in list_of_thing_dict:
            thing_obj = cls.from_dict(thing_data)
            things_to_find[thing_obj.Hash] = thing_obj
            pipe.hgetall(consts.KEY_THING_META.format(thing_obj.Hash))
            pipe.hgetall(consts.KEY_COUNTERS_HISTORICAL_THINGS_TRADED_BY_DATE.format(thing_obj.Hash,
                                                                                     date))
            pipe.zrange(consts.KEY_THING_BASE_MARKET_VALUE_DATA.format(thing_obj.Hash), 0, -1, withscores=True)

        db_data = pipe.execute()

        return cls.__parse_get_many_results(db_data, things_to_find.keys(), things_to_find)

    @classmethod
    def get_from_database(cls, thing_dict, connection, date=None):
        if date:
            return cls.__get_single_from_database(thing_dict, connection, date)

        thing_obj = cls.from_dict(thing_dict)

        data = connection.hgetall(consts.KEY_THING_META.format(thing_obj.Hash))

        if len(data) and 'Name' in data:
            new_thing = cls.from_dict(data)
            new_thing._from_database = True
            return new_thing

        # Caller should test FromDatabase
        return thing_obj

    @classmethod
    def __get_single_from_database(cls, thing_dict, connection, date):
        pipe = connection.pipeline()

        thing_obj = cls.from_dict(thing_dict)

        pipe.hgetall(consts.KEY_THING_META.format(thing_obj.Hash))
        pipe.hgetall(consts.KEY_COUNTERS_HISTORICAL_THINGS_TRADED_BY_DATE.format(thing_obj.Hash, date))
        pipe.zrange(consts.KEY_THING_BASE_MARKET_VALUE_DATA.format(thing_obj.Hash), 0, -1, withscores=True)

        data, trade_data, bmv_price_data = pipe.execute()

        if len(trade_data) > 0:
            data['TradeHistory'] = trade_data

        if len(bmv_price_data) > 0:
            data['BMVVotes'] = bmv_price_data

        if len(data) and 'Name' in data:
            new_thing = cls.from_dict(data)
            new_thing._from_database = True
            return new_thing

        # Caller should test FromDatabase
        return thing_obj

    @classmethod
    def get_from_database_by_hash(cls, connection, thing_hash, date=get_today_date_string()):
        return cls.get_many_from_database_by_hash([thing_hash], connection, date)[thing_hash]

    def get_trade_history(self, connection, number_of_days: int = 31):
        pipe = connection.pipeline()

        dates = []

        for day in range(0, -(number_of_days + 1), -1):
            date = get_date_string_by_delta(day)
            dates.append(date)
            pipe.hgetall(consts.KEY_COUNTERS_HISTORICAL_THINGS_TRADED_BY_DATE.format(self.Hash, date))

        results = dict(zip(dates, pipe.execute()))

        return results

    def get_price_history(self, connection):
        pipe = connection.pipeline()

        pipe.zrange(KEY_TRENDS_HISTORICAL_THING_PRICE_BY_DAY.format(self.Hash, PriceType.Buy.value), 0, -1,
                    withscores=True)
        pipe.zrange(KEY_TRENDS_HISTORICAL_THING_PRICE_BY_DAY.format(self.Hash, PriceType.Sell.value), 0, -1,
                    withscores=True)

        # Two lists of Tuples [(date,qty),(date,qty)], [(date,qty),(date,qty)]
        buy_data, sell_data = pipe.execute()

        total_data = {}

        if buy_data:
            for date, qty in buy_data:
                total_data[utc_epoch_to_string(int(date))] = {'buy': qty}

        if sell_data:
            for date, qty in sell_data:
                date = utc_epoch_to_string(int(date))
                if date in total_data:
                    total_data[date]['sell'] = qty
                else:
                    total_data[date] = {'sell': qty}

        return dict(sorted(total_data.items(), key=lambda kv: kv[0], reverse=True))
