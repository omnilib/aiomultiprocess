# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import os

from unittest import TestCase

import aiomultiprocess as amp
from aiomultiprocess.core import context, PoolWorker

from .base import async_test


async def mapper(value):
    return value * 2


async def starmapper(*values):
    return [value * 2 for value in values]


class CoreTest(TestCase):

    @async_test
    async def test_process(self):

        async def sleepy():
            await asyncio.sleep(0.1)

        p = amp.Process(target=sleepy, name="test_process")
        p.start()

        self.assertEqual(p.name, "test_process")
        self.assertTrue(p.pid)
        self.assertTrue(p.is_alive())

        await p.join()
        self.assertFalse(p.is_alive())

    @async_test
    async def test_worker(self):

        async def sleepypid():
            await asyncio.sleep(0.1)
            return os.getpid()

        p = amp.Worker(target=sleepypid)
        p.start()
        await p.join()

        self.assertFalse(p.is_alive())
        self.assertEqual(p.result, p.pid)

        # test results from join
        p = amp.Worker(target=sleepypid)
        p.start()
        self.assertEqual(await p.join(), p.pid)

        # test awaiting p directly
        p = amp.Worker(target=sleepypid)
        p.start()
        self.assertEqual(await p, p.pid)

    @async_test
    async def test_pool_worker(self):
        tx = context.Queue()
        rx = context.Queue()
        worker = PoolWorker(tx, rx, 1)
        worker.start()

        self.assertTrue(worker.is_alive())
        tx.put_nowait((1, mapper, (5,), {}))
        await asyncio.sleep(0.5)
        result = rx.get_nowait()

        self.assertEqual(result, (1, 10))
        self.assertFalse(worker.is_alive())  # maxtasks == 1

    @async_test
    async def test_pool(self):
        values = list(range(10))
        results = [await mapper(i) for i in values]

        async with amp.Pool(2) as pool:
            await asyncio.sleep(0.5)
            self.assertEqual(pool.process_count, 2)
            self.assertEqual(len(pool.processes), 2)

            self.assertEqual(await pool.apply(mapper, (values[0],)), results[0])
            self.assertEqual(await pool.map(mapper, values), results)
            self.assertEqual(
                await pool.starmap(starmapper, [values[:4], values[4:]]),
                [results[:4], results[4:]],
            )
