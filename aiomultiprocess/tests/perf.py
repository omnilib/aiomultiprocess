# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import time
from unittest import TestCase

import aiomultiprocess as amp
from .base import perf_test

PERF_SETS = [
    # sleep, tasks, processes, concurrency
    ((0,), 400, 4, 8),
    ((0,), 800, 4, 16),
    ((0,), 1600, 4, 32),
    ((0,), 3200, 4, 64),
    ((0.05,), 400, 4, 8),
    ((0.05,), 800, 4, 16),
    ((0.05,), 1600, 4, 32),
    ((0.05,), 3200, 4, 64),
    ((-0.002, 0.20, -0.002), 200, 4, 8),
    ((-0.002, 0.20, -0.002), 400, 4, 16),
    ((-0.002, 0.20, -0.002), 800, 4, 32),
    ((-0.002, 0.20, -0.002), 1600, 4, 64),
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


async def sleepy(durations):
    for duration in durations:
        if duration >= 0:
            await asyncio.sleep(duration)
        else:
            time.sleep(-duration)


class PerfTest(TestCase):
    @perf_test
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
