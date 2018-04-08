# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import logging
import os
import sys

from functools import wraps
from unittest import TestCase

import aiomultiprocess as amp


def async_test(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fn(*args, **kwargs))

    return wrapper


def init():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)


class CoreTest(TestCase):

    @async_test
    async def test_process(self):

        async def sleepy():
            await asyncio.sleep(1)

        p = amp.Process(target=sleepy, name="test_process", initializer=init)
        p.start()

        self.assertEqual(p.name, "test_process")
        self.assertTrue(p.pid)
        self.assertTrue(p.is_alive())

        await p.join()
        self.assertFalse(p.is_alive())

    @async_test
    async def test_worker(self):

        async def sleepypid():
            await asyncio.sleep(1)
            return os.getpid()

        p = amp.Worker(target=sleepypid, initializer=init)
        p.start()
        await p.join()

        self.assertFalse(p.is_alive())
        self.assertEqual(p.result, p.pid)
