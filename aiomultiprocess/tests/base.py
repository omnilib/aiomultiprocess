# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
from functools import wraps


def async_test(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fn(*args, **kwargs))

    return wrapper
