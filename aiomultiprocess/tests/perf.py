# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import time
from unittest import TestCase, skip

import aiomultiprocess as amp

from .base import async_test

PERF_SETS = [
    # sleep, tasks, processes, concurrency
    (0.01, 100, 1, 1),
    (0.01, 200, 2, 1),
    (0.01, 400, 2, 2),
    (0.01, 800, 2, 4),
    (0.02, 800, 2, 8),
    (0.02, 1600, 4, 8),
    (0.04, 1600, 4, 16),
    (0.08, 1600, 8, 16),
    (0.08, 3200, 8, 32),
]


class Timer:
    def __init__(self):
        self.start = 0
        self.end = 0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()

    @property
    def result(self):
        return self.end - self.start


async def sleepy(duration):
    await asyncio.sleep(duration)


class PerfTest(TestCase):
    @skip
    @async_test
    async def test_pool_concurrency(self):
        results = []
        for sleep, tasks, processes, concurrency in PERF_SETS:
            with Timer() as timer:
                async with amp.Pool(processes, childconcurrency=concurrency) as pool:
                    await pool.map(sleepy, (sleep for _ in range(tasks)))

            results.append((sleep, tasks, processes, concurrency, timer.result))

        print()
        for result in results:
            print(*result)
