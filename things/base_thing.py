import functools
import hashlib
from abc import ABC


def preserve_last_value(func):
    # noinspection PyProtectedMember
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        attribute = func.__name__
        args[0]._changes[attribute] = True
        args[0]._previous_value[attribute] = args[0]._current_value[attribute]
        args[0]._current_value[attribute] = args[1]

    return wrapper


def value_lookup(func):
    # noinspection PyProtectedMember
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        attribute = func.__name__
        return args[0]._current_value[attribute]

    return wrapper


class BaseThing(ABC):
    __properties = None

    def __init__(self, name: str, **kwargs):
        if name is None or name == '':
            raise ValueError('Must specify a name!')
        self._name = name
        self._quality = kwargs.get('Quality', "")
        self._stuff_type = kwargs.get('StuffType', "")

        self._current_value = {'BaseMarketValue': float(kwargs.get('BaseMarketValue', 0)),
                               'CurrentBuyPrice': float(kwargs.get('CurrentBuyPrice', -1)),
                               'Quantity': int(kwargs.get('Quantity', 0)),
                               'MinifiedContainer': bool(kwargs.get('MinifiedContainer', False))}

        self._hash = kwargs.get('Hash', self.calculate_hash(self.Name, self.Quality, self.StuffType))

        # Dicts for tracking changes
        self._changes = {}
        self._previous_value = {}

    @classmethod
    def get_props(cls):
        if not cls.__properties:
            cls.__properties = [prop for prop in cls._iter_properties()]
        return cls.__properties

    @property
    def Name(self):
        return self._name

    @Name.setter
    def Name(self, value):
        self._changes['Name'] = True
        self._name = value

    @property
    def Quality(self):
        return self._quality

    @Quality.setter
    def Quality(self, value):
        self._changes['Quality'] = True
        self._quality = value

    @property
    def StuffType(self):
        return self._stuff_type

    @StuffType.setter
    def StuffType(self, value):
        self._changes['StuffType'] = True
        self._stuff_type = value

    @property
    @value_lookup
    def CurrentBuyPrice(self):
        pass

    @CurrentBuyPrice.setter
    @preserve_last_value
    def CurrentBuyPrice(self, value):
        pass

    @property
    @value_lookup
    def BaseMarketValue(self):
        pass

    @BaseMarketValue.setter
    @preserve_last_value
    def BaseMarketValue(self, value):
        pass

    @property
    @value_lookup
    def Quantity(self):
        pass

    @Quantity.setter
    @preserve_last_value
    def Quantity(self, value):
        pass

    @property
    @value_lookup
    def MinifiedContainer(self):
        pass

    @MinifiedContainer.setter
    @preserve_last_value
    def MinifiedContainer(self, value):
        pass

    @property
    def Hash(self):
        return self._hash

    @Hash.setter
    @preserve_last_value
    def Hash(self, value):
        self._changes['Hash'] = True
        self._hash = value

    @classmethod
    def _iter_properties(cls):
        for var_name in dir(cls):
            value = getattr(cls, var_name)
            if isinstance(value, property):
                yield var_name

    @classmethod
    def from_dict(cls, thing: dict):
        if 'Name' not in thing:
            raise ValueError('Thing Name must be provided.')
        return cls(thing['Name'], **thing)

    @classmethod
    def calculate_hash(cls, name: str, quality=None, stuff_type=None) -> str:
        if not quality:
            quality = ''
        if not stuff_type:
            stuff_type = ''
        return hashlib.sha1('{}{}{}'.format(name, stuff_type, quality).encode('UTF8')).hexdigest()

    @classmethod
    def calculate_hash_from_dict(cls, dict_of_thing: dict) -> str:
        return cls.calculate_hash(dict_of_thing['Name'], dict_of_thing.get('Quality'), dict_of_thing.get('StuffType'))

    @property
    def FullName(self):
        full_name = self._name
        if self._quality:
            full_name += ':{}'.format(self._quality)
        if self._stuff_type:
            full_name += ':{}'.format(self._stuff_type)
        return full_name

    def __str__(self):
        return '{} ({})'.format(self.FullName, self.Hash)

    def has_changed(self, attribute):
        return True if self._changes.get(attribute) else False

    def get_change(self, attribute):
        return self._previous_value.get(attribute, None)
