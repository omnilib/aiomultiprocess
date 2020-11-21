# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import sys
import time
from unittest import TestCase
from unittest.mock import patch

import aiomultiprocess as amp
from .base import (
    async_test,
    do_nothing,
    get_dummy_constant,
    initializer,
    raise_fn,
    sleepy,
    two,
)


class CoreTest(TestCase):  # pylint: disable=too-many-public-methods
    def setUp(self):
        # reset to default context before each test
        amp.set_start_method()

    @async_test
    async def test_process(self):
        p = amp.Process(target=sleepy, name="test_process")
        p.start()

        self.assertEqual(p.name, "test_process")
        self.assertTrue(p.pid)
        self.assertTrue(p.is_alive())

        await p.join()
        self.assertFalse(p.is_alive())

    @async_test
    async def test_process_await(self):
        p = amp.Process(target=sleepy, name="test_process")
        await p

        self.assertIsNotNone(p.exitcode)

        p = amp.Process(target=sleepy, name="test_process")
        p.start()
        await p

        self.assertIsNotNone(p.exitcode)

    @async_test
    async def test_process_join(self):
        p = amp.Process(target=sleepy, name="test_process")

        with self.assertRaisesRegex(ValueError, "must start process"):
            await p.join()

        p.start()
        await p.join()
        self.assertIsNotNone(p.exitcode)

    @async_test
    async def test_process_daemon(self):
        p = amp.Process(daemon=False)
        self.assertEqual(p.daemon, False)
        p.daemon = True
        self.assertEqual(p.daemon, True)

        p = amp.Process(daemon=True)
        self.assertEqual(p.daemon, True)
        p.daemon = False
        self.assertEqual(p.daemon, False)

    @async_test
    async def test_process_terminate(self):
        start = time.time()
        p = amp.Process(target=asyncio.sleep, args=(1,), name="test_process")
        p.start()

        p.terminate()
        await p.join()
        self.assertLess(p.exitcode, 0)
        self.assertLess(time.time() - start, 0.6)

    @async_test
    async def test_process_kill(self):
        p = amp.Process(target=sleepy)
        p.start()

        if sys.version_info >= (3, 7):
            p.kill()
            await p.join()
            self.assertLess(p.exitcode, 0)

        else:
            with self.assertRaises(AttributeError):
                p.kill()
            await p.join()

    @async_test
    async def test_process_close(self):
        p = amp.Process(target=sleepy)
        p.start()

        if sys.version_info >= (3, 7):
            with self.assertRaises(ValueError):
                self.assertIsNone(p.exitcode)
                p.close()

            await p.join()
            self.assertIsNotNone(p.exitcode)

            p.close()

            with self.assertRaises(ValueError):
                _ = p.exitcode

        else:
            with self.assertRaises(AttributeError):
                p.close()
            await p.join()

    @async_test
    async def test_process_timeout(self):
        p = amp.Process(target=sleepy)
        p.start()

        with self.assertRaises(asyncio.TimeoutError):
            await p.join(timeout=0.01)

    @async_test
    async def test_worker(self):
        p = amp.Worker(target=sleepy)
        p.start()

        with self.assertRaisesRegex(ValueError, "coroutine not completed"):
            _ = p.result

        await p.join()

        self.assertFalse(p.is_alive())
        self.assertEqual(p.result, p.pid)

    @async_test
    async def test_worker_join(self):
        # test results from join
        p = amp.Worker(target=sleepy)
        p.start()
        self.assertEqual(await p.join(), p.pid)

        # test awaiting p directly, no need to start
        p = amp.Worker(target=sleepy)
        self.assertEqual(await p, p.pid)

    @async_test
    async def test_spawn_method(self):
        self.assertEqual(amp.core.get_context().get_start_method(), "spawn")

        async def inline(x):
            return x

        with self.assertRaisesRegex(AttributeError, "Can't pickle local object"):
            _ = amp.Worker(target=inline, args=(1,), name="test_inline")
            await _

        result = await amp.Worker(target=two, name="test_global")
        self.assertEqual(result, 2)

    @async_test
    async def test_set_start_method(self):
        with self.assertRaises(ValueError):
            amp.set_start_method("foo")

        if sys.platform.startswith("win32"):
            amp.set_start_method(None)
            self.assertEqual(amp.core.get_context().get_start_method(), "spawn")

            with self.assertRaises(ValueError):
                amp.set_start_method("fork")

        elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
            amp.set_start_method("fork")

            async def inline(x):
                return x

            result = await amp.Worker(target=inline, args=(17,), name="test_inline")
            self.assertEqual(result, 17)

    @patch("aiomultiprocess.core.set_start_method")
    @async_test
    async def test_set_context(self, ssm_mock):
        amp.set_context()
        ssm_mock.assert_called_with(None)

        amp.set_context("foo")
        ssm_mock.assert_called_with("foo")

        ssm_mock.side_effect = Exception("fake exception")
        with self.assertRaisesRegex(Exception, "fake exception"):
            amp.set_context("whatever")

    @async_test
    async def test_initializer(self):
        result = await amp.Worker(
            target=get_dummy_constant,
            name="test_process",
            initializer=initializer,
            initargs=(10,),
        )
        self.assertEqual(result, 10)

    @async_test
    async def test_async_initializer(self):
        with self.assertRaises(ValueError) as _:
            p = amp.Process(target=sleepy, name="test_process", initializer=sleepy)
            p.start()

    @async_test
    async def test_raise(self):
        result = await amp.Worker(
            target=raise_fn, name="test_process", initializer=do_nothing
        )
        self.assertIsInstance(result, RuntimeError)

    @async_test
    async def test_sync_target(self):
        with self.assertRaises(ValueError) as _:
            p = amp.Process(
                target=do_nothing, name="test_process", initializer=do_nothing
            )
            p.start()

    @async_test
    async def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            await amp.core.not_implemented()
