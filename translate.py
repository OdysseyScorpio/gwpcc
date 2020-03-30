from lib.db import get_redis_database_connection
from lib.gwpcc.consts import KEY_THING_LOCALE_THING_NAME
from lib.gwpcc.things.thing import Thing


def translate(request, hash_list):
    pipe = get_redis_database_connection(request).pipeline()
    for thing_hash in hash_list:
        pipe.get(KEY_THING_LOCALE_THING_NAME.format(request.session['language'], thing_hash))

    db_results = pipe.execute()
    things_with_names = dict(zip(hash_list, db_results))

    if request.session['language'] != 'english':
        things_with_names = try_fallback_english(request, things_with_names)

    things_with_names = fallback_on_def(request, things_with_names)

    things_with_names = {k: v.title() for k, v in things_with_names.items()}

    return things_with_names


def try_fallback_english(request, translate_items):
    pipe = get_redis_database_connection(request).pipeline()

    need_fallback = []
    for thing_hash, name in translate_items.items():

        if name is None:
            need_fallback.append(thing_hash)
            pipe.get(KEY_THING_LOCALE_THING_NAME.format('english', thing_hash))

    db_results = pipe.execute()

    fallback_names = dict(zip(need_fallback, db_results))

    translate_items = {**translate_items, **fallback_names}

    return translate_items


def fallback_on_def(request, translate_items):
    need_fallback = []
    for thing_hash, name in translate_items.items():

        if name is None:
            need_fallback.append(thing_hash)

    connection = get_redis_database_connection(request)

    things = Thing.get_many_from_database_by_hash_without_history(need_fallback, connection)

    for thing_hash, thing in things.items():
        translate_items[thing_hash] = thing.FullName

    return translate_items
