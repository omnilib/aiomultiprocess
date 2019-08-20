# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import os
import time
from unittest import TestCase

import aiomultiprocess as amp
from aiomultiprocess.core import PoolWorker, ProxyException, context

from .base import async_test


async def two():
    return 2


async def mapper(value):
    return value * 2


async def starmapper(*values):
    return [value * 2 for value in values]


DUMMY_CONSTANT = None


def initializer(value):
    global DUMMY_CONSTANT

    DUMMY_CONSTANT = value


async def get_dummy_constant():
    return DUMMY_CONSTANT


async def raise_fn():
    raise RuntimeError("raising")


class CoreTest(TestCase):
    def setUp(self):
        amp.set_context("fork")

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
    async def test_process_timeout(self):
        async def sleepy():
            await asyncio.sleep(1)

        p = amp.Process(target=sleepy)
        p.start()

        with self.assertRaises(asyncio.TimeoutError):
            await p.join(timeout=0.01)

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

    @async_test
    async def test_worker_join(self):
        async def sleepypid():
            await asyncio.sleep(0.1)
            return os.getpid()

        # test results from join
        p = amp.Worker(target=sleepypid)
        p.start()
        self.assertEqual(await p.join(), p.pid)

        # test awaiting p directly, no need to start
        p = amp.Worker(target=sleepypid)
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

        self.assertEqual(result, (1, 10, None))
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

    @async_test
    async def test_spawn_context(self):
        with self.assertRaises(ValueError):
            amp.set_context("foo")

        async def inline(x):
            return x

        amp.set_context("spawn")

        with self.assertRaises(AttributeError):
            p = amp.Worker(target=inline, args=(1,), name="test_inline")
            p.start()
            await p.join()

        p = amp.Worker(target=two, name="test_global")
        p.start()
        await p.join()

        values = list(range(10))
        results = [await mapper(i) for i in values]
        async with amp.Pool(2) as pool:
            self.assertEqual(await pool.map(mapper, values), results)

        self.assertEqual(p.result, 2)

    @async_test
    async def test_initializer(self):
        result = 10
        async with amp.Pool(2, initializer=initializer, initargs=(result,)) as pool:
            self.assertEqual(await pool.apply(get_dummy_constant, args=()), result)

    @async_test
    async def test_async_initializer(self):
        async def sleepy():
            await asyncio.sleep(0)

        with self.assertRaises(ValueError) as _:
            p = amp.Process(target=sleepy, name="test_process", initializer=sleepy)
            p.start()

    @async_test
    async def test_raise(self):
        async with amp.Pool(2) as pool:
            with self.assertRaises(ProxyException) as _:
                await pool.apply(raise_fn, args=())

    @async_test
    async def test_none(self):
        async with amp.Pool(2) as pool:
            self.assertIsNone(await pool.apply(asyncio.sleep, args=(0,)))

    @async_test
    async def test_sync_target(self):
        def dummy():
            pass

        with self.assertRaises(ValueError) as _:
            p = amp.Process(target=dummy, name="test_process", initializer=dummy)
            p.start()

    @async_test
    async def test_process_terminate(self):
        start = time.time()

        async def terminate(process):
            await asyncio.sleep(0.5)
            process.terminate()

        p = amp.Process(target=asyncio.sleep, args=(1,), name="test_process")
        await asyncio.gather(*[terminate(p), p])
        self.assertLess(time.time() - start, 0.6)
