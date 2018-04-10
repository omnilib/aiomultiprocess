# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import logging
import multiprocessing
import multiprocessing.managers
import os
import queue

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    NewType,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")
R = TypeVar("R")

TaskID = NewType("TaskID", int)
PoolTask = Optional[Tuple[TaskID, Callable[..., R], Sequence[T], Dict[str, T]]]
PoolResult = Tuple[TaskID, Union[R, BaseException]]

# shared context for all multiprocessing primitives
# fork is unix default and most flexible, but uses more memory (ref counting breaks CoW)
# see https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
context = multiprocessing.get_context("fork")
_manager = None

log = logging.getLogger(__name__)

MAX_TASKS_PER_CHILD = 0  # number of tasks to execute before recycling a child process
CHILD_CONCURRENCY = 16  # number of tasks to execute simultaneously per child process


def get_manager() -> multiprocessing.managers.SyncManager:
    """Return a singleton shared manager."""
    global _manager
    if _manager is None:
        _manager = context.Manager()

    return _manager


class Process:
    """Execute a coroutine on a separate process."""

    def __init__(
        self,
        group: None = None,
        target: Callable[..., Awaitable[R]] = None,  # pylint: disable=bad-whitespace
        name: str = None,
        args: Sequence[Any] = None,
        kwargs: Dict[str, Any] = None,
        *,
        daemon: bool = None,
        initializer: Callable = None,
    ) -> None:
        if target is not None and not asyncio.iscoroutinefunction(target):
            raise ValueError(f"target must be coroutine function")

        if initializer is not None and asyncio.iscoroutinefunction(initializer):
            raise ValueError(f"initializer must be synchronous function")

        self.aio_init = initializer
        self.aio_target = target or self.run
        self.aio_args = args or ()
        self.aio_kwargs = kwargs or {}
        self.aio_manager = get_manager()
        self.aio_process = context.Process(
            group=group, target=self.run_async, name=name, daemon=daemon
        )

    async def run(self) -> R:
        """Override this method to add default behavior when `target` isn't given."""
        raise NotImplementedError()

    def run_async(self) -> R:
        """Initialize the child process and event loop, then execute the coroutine."""
        try:
            if self.aio_init:
                self.aio_init()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self.aio_target(*self.aio_args, **self.aio_kwargs)
            )

            return result

        except BaseException:
            log.exception(f"aio process {os.getpid()} failed")
            raise

    async def join(self, timeout: int = None) -> None:
        """Wait for the process to finish execution without blocking the main thread."""
        if timeout is not None:
            try:
                return await asyncio.wait_for(self.join(), timeout)

            except asyncio.TimeoutError:
                return

        while self.exitcode is None:
            await asyncio.sleep(0.005)

    def __getattr__(self, name: str) -> Any:
        """All other properties chain to the proxied Process object."""
        return getattr(self.aio_process, name)


class Worker(Process):
    """Execute a coroutine on a separate process and return the result."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.aio_namespace = get_manager().Namespace()
        self.aio_namespace.result = None

    async def run(self) -> R:
        """Override this method to add default behavior when `target` isn't given."""
        raise NotImplementedError()

    def run_async(self) -> R:
        """Initialize the child process and event loop, then execute the coroutine."""
        try:
            result: R = super().run_async()
            self.aio_namespace.result = result
            return result

        except BaseException as e:
            self.aio_namespace.result = e
            raise

    @property
    def result(self) -> R:
        """Easy access to the resulting value from the coroutine."""
        if self.exitcode is not None:
            return self.aio_namespace.result

        return None


class PoolWorker(Process):
    """Individual worker process for the async pool."""

    def __init__(
        self,
        tx: multiprocessing.Queue,
        rx: multiprocessing.Queue,
        ttl: int = MAX_TASKS_PER_CHILD,
        concurrency: int = CHILD_CONCURRENCY,
    ) -> None:
        super().__init__()
        self.concurrency = max(1, concurrency)
        self.ttl = max(0, ttl)
        self.tx = tx
        self.rx = rx

    async def run(self) -> None:
        """Pick up work, execute work, return results, rinse, repeat."""
        pending: Dict[asyncio.Future, TaskID] = {}
        completed = 0
        running = True
        while running or pending:
            # TTL, Tasks To Live, determines how many tasks to execute before dying
            if self.ttl and completed >= self.ttl:
                running = False

            # pick up new work as long as we're "running" and we have open slots
            while running and len(pending) < self.concurrency:
                try:
                    task: PoolTask = self.tx.get_nowait()
                except queue.Empty:
                    break

                if task is None:
                    running = False

                tid, func, args, kwargs = task
                log.debug(f"{self.name} running {tid}: {func}(*{args}, **{kwargs})")
                future = asyncio.ensure_future(func(*args, **kwargs))
                pending[future] = tid

            if not pending:
                await asyncio.sleep(0.005)
                continue

            # return results and/or exceptions when completed
            done, _ = await asyncio.wait(
                pending.keys(), timeout=0.05, return_when=asyncio.FIRST_COMPLETED
            )
            for future in done:
                tid = pending.pop(future)

                try:
                    result = future.result()
                except BaseException as e:
                    result = e

                log.debug(f"{self.name} completed {tid}: {result}")
                self.rx.put_nowait((tid, result))
                completed += 1


class Pool:
    """Execute coroutines on a pool of child processes."""

    def __init__(
        self,
        processes: int = None,
        initializer: Callable[..., None] = None,  # pylint: disable=bad-whitespace
        initargs: Sequence[Any] = None,
        maxtasksperchild: int = MAX_TASKS_PER_CHILD,
        childconcurrency: int = CHILD_CONCURRENCY,
    ) -> None:
        self.process_count = max(1, processes or os.cpu_count())
        self.initializer = initializer
        self.initargs = initargs or ()
        self.maxtasksperchild = max(0, maxtasksperchild)
        self.childconcurrency = max(1, childconcurrency)

        self.processes: List[Process] = []
        self.tx_queue = context.Queue()
        self.rx_queue = context.Queue()

        self.running = True
        self.last_id = 0
        self._results: Dict[TaskID, Any] = {}
        self._loop = asyncio.ensure_future(self.loop())

    async def __aenter__(self) -> "Pool":
        """Enable `async with Pool() as pool` usage."""
        return self

    async def __aexit__(self, *args) -> None:
        """Automatically terminate the pool when falling out of scope."""
        self.terminate()
        await self.join()

    async def loop(self) -> None:
        """Maintain the pool of workers while open."""
        while self.processes or self.running:
            # clean up workers that reached TTL
            for process in self.processes:
                if not process.is_alive():
                    self.processes.remove(process)

            # start new workers when slots are unfilled
            while self.running and len(self.processes) < self.process_count:
                process = PoolWorker(
                    self.tx_queue,
                    self.rx_queue,
                    self.maxtasksperchild,
                    self.childconcurrency,
                )
                process.start()
                self.processes.append(process)

            # pull results into a shared dictionary for later retrieval
            while True:
                try:
                    task_id, value = self.rx_queue.get_nowait()
                    self._results[task_id] = value

                except queue.Empty:
                    break

            # let someone else do some work for once
            await asyncio.sleep(0.005)

    def queue_work(
        self,
        func: Callable[..., Awaitable[R]],
        args: Sequence[Any],
        kwargs: Dict[str, Any],
    ) -> TaskID:
        """Add a new work item to the outgoing queue."""
        self.last_id += 1
        task_id = TaskID(self.last_id)

        self.tx_queue.put_nowait((task_id, func, args, kwargs))
        return task_id

    async def results(self, tids: Sequence[TaskID]) -> Sequence[R]:
        """Wait for all tasks to complete, and return results, preserving order."""
        pending = set(tids)
        ready: Dict[TaskID, R] = {}

        while pending:
            for tid in pending.copy():
                if tid in self._results:
                    ready[tid] = self._results.pop(tid)
                    pending.remove(tid)

            await asyncio.sleep(0.005)

        return [ready[tid] for tid in tids]

    async def apply(
        self,
        func: Callable[..., Awaitable[R]],
        args: Sequence[Any] = None,
        kwds: Dict[str, Any] = None,
    ) -> R:
        """Run a single coroutine on the pool."""
        if not self.running:
            raise RuntimeError(f"pool is closed")

        args = args or ()
        kwds = kwds or {}

        tid = self.queue_work(func, args, kwds)
        results: Sequence[R] = await self.results([tid])
        return results[0]

    async def map(
        self,
        func: Callable[[T], Awaitable[R]],
        iterable: Sequence[T],
        # chunksize: int = None,  # todo: implement chunking maybe
    ) -> Sequence[R]:
        """Run a coroutine once for each item in the iterable."""
        if not self.running:
            raise RuntimeError(f"pool is closed")

        tids = [self.queue_work(func, (item,), {}) for item in iterable]
        return await self.results(tids)

    async def starmap(
        self,
        func: Callable[..., Awaitable[R]],
        iterable: Sequence[Sequence[T]],
        # chunksize: int = None,  # todo: implement chunking maybe
    ) -> Sequence[R]:
        """Run a coroutine once for each sequence of items in the iterable."""
        if not self.running:
            raise RuntimeError(f"pool is closed")

        tids = [self.queue_work(func, args, {}) for args in iterable]
        return await self.results(tids)

    def close(self) -> None:
        """Close the pool to new visitors."""
        self.running = False
        for _ in range(self.process_count):
            self.tx_queue.put_nowait(None)

    def terminate(self) -> None:
        """No running by the pool!"""
        if self.running:
            self.close()

        for process in self.processes:
            process.terminate()

    async def join(self) -> None:
        """Wait for the pool to finish gracefully."""
        if self.running:
            raise RuntimeError(f"pool is still open")

        await self._loop
