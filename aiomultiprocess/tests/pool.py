# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
from unittest import TestCase

import aiomultiprocess as amp
from aiomultiprocess.core import get_context
from aiomultiprocess.pool import PoolWorker, ProxyException

from .base import async_test, mapper, raise_fn, starmapper, two


class PoolTest(TestCase):  # pylint: disable=too-many-public-methods
    @async_test
    async def test_pool_worker_max_tasks(self):
        tx = get_context().Queue()
        rx = get_context().Queue()
        worker = PoolWorker(tx, rx, 1)
        worker.start()

        self.assertTrue(worker.is_alive())
        tx.put_nowait((1, mapper, (5,), {}))
        await asyncio.sleep(0.5)
        result = rx.get_nowait()

        self.assertEqual(result, (1, 10, None))
        self.assertFalse(worker.is_alive())  # maxtasks == 1

    @async_test
    async def test_pool_worker_stop(self):
        tx = get_context().Queue()
        rx = get_context().Queue()
        worker = PoolWorker(tx, rx, 2)
        worker.start()

        self.assertTrue(worker.is_alive())
        tx.put_nowait((1, mapper, (5,), {}))
        await asyncio.sleep(0.5)
        result = rx.get_nowait()

        self.assertEqual(result, (1, 10, None))
        self.assertTrue(worker.is_alive())  # maxtasks == 2

        tx.put(None)
        await worker.join(timeout=0.5)
        self.assertFalse(worker.is_alive())

    @async_test
    async def test_pool_worker_exceptions(self):
        tx = get_context().Queue()
        rx = get_context().Queue()
        worker = PoolWorker(tx, rx)
        worker.start()

        self.assertTrue(worker.is_alive())
        tx.put_nowait((1, raise_fn, (), {}))
        await asyncio.sleep(0.5)
        tid, result, trace = rx.get_nowait()

        self.assertEqual(tid, 1)
        self.assertIsNone(result)
        self.assertIsInstance(trace, str)
        self.assertIn("RuntimeError: raising", trace)

        tx.put(None)
        await worker.join(timeout=0.5)
        self.assertFalse(worker.is_alive())

    @async_test
    async def test_pool(self):
        values = list(range(10))
        results = [await mapper(i) for i in values]

        async with amp.Pool(2, maxtasksperchild=5) as pool:
            self.assertEqual(pool.process_count, 2)
            self.assertEqual(len(pool.processes), 2)

            self.assertEqual(await pool.apply(mapper, (values[0],)), results[0])
            self.assertEqual(await pool.map(mapper, values), results)
            self.assertEqual(
                await pool.starmap(starmapper, [values[:4], values[4:]]),
                [results[:4], results[4:]],
            )

    @async_test
    async def test_pool_exception(self):
        async with amp.Pool(2) as pool:
            with self.assertRaises(ProxyException):
                await pool.apply(raise_fn, args=())

    def test_pool_args(self):
        with self.assertRaisesRegex(ValueError, "queue count must be <= process"):
            amp.Pool(4, queuecount=9)

    @async_test
    async def test_pool_closed(self):
        pool = amp.Pool(2)
        pool.close()

        with self.assertRaisesRegex(RuntimeError, "pool is closed"):
            await pool.apply(two)

        with self.assertRaisesRegex(RuntimeError, "pool is closed"):
            await pool.map(mapper, [1, 2, 3])

        with self.assertRaisesRegex(RuntimeError, "pool is closed"):
            await pool.starmap(starmapper, [[1, 2, 3], [1, 2, 3]])

        pool.terminate()

    @async_test
    async def test_pool_early_join(self):
        async with amp.Pool(2) as pool:
            with self.assertRaisesRegex(RuntimeError, "pool is still open"):
                await pool.join()
