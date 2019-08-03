# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import logging
import multiprocessing
import multiprocessing.managers
import os
import queue
import sys
import traceback
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

T = TypeVar("T")
R = TypeVar("R")

TaskID = NewType("TaskID", int)
PoolTask = Optional[Tuple[TaskID, Callable[..., R], Sequence[T], Dict[str, T]]]
TracebackStr = str
PoolResult = Tuple[TaskID, Optional[R], Optional[TracebackStr]]

# shared context for all multiprocessing primitives
# "fork" is unix default and flexible, but uses more memory (ref counting breaks CoW)
# "spawn" is windows default (and only option), but can't execute non-global functions
# see https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
context = multiprocessing.get_context()
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


def set_context(method: Optional[str] = None) -> None:
    """Set the context type for future process/pool objects."""
    global context
    context = multiprocessing.get_context(method)


async def not_implemented(*args: Any, **kwargs: Any) -> None:
    """Default function to call when none given."""
    raise NotImplementedError()


class Unit(NamedTuple):
    """Container for what to call on the child process."""

    target: Callable
    args: Sequence[Any]
    kwargs: Dict[str, Any]
    namespace: Any
    initializer: Optional[Callable] = None
    initargs: Sequence[Any] = ()
    runner: Optional[Callable] = None


class ProxyException(Exception):
    pass


class Process:
    """Execute a coroutine on a separate process."""

    def __init__(
        self,
        group: None = None,
        target: Callable = None,
        name: str = None,
        args: Sequence[Any] = None,
        kwargs: Dict[str, Any] = None,
        *,
        daemon: bool = None,
        initializer: Optional[Callable] = None,
        initargs: Sequence[Any] = (),
        process_target: Optional[Callable] = None,
    ) -> None:
        if target is not None and not asyncio.iscoroutinefunction(target):
            raise ValueError(f"target must be coroutine function")

        if initializer is not None and asyncio.iscoroutinefunction(initializer):
            raise ValueError(f"initializer must be synchronous function")

        self.unit = Unit(
            target=target or not_implemented,
            args=args or (),
            kwargs=kwargs or {},
            namespace=get_manager().Namespace(),
            initializer=initializer,
            initargs=initargs,
        )
        self.aio_process = context.Process(
            group=group,
            target=process_target or Process.run_async,
            args=(self.unit,),
            name=name,
            daemon=daemon,
        )

    def __await__(self) -> Any:
        """Enable awaiting of the process result by chaining to `start()` & `join()`."""
        if not self.is_alive() and self.exitcode is None:
            self.start()

        return self.join().__await__()

    @staticmethod
    def run_async(unit: Unit) -> R:
        """Initialize the child process and event loop, then execute the coroutine."""
        try:
            if unit.initializer:
                unit.initializer(*unit.initargs)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result: R = loop.run_until_complete(unit.target(*unit.args, **unit.kwargs))

            return result

        except BaseException:
            log.exception(f"aio process {os.getpid()} failed")
            raise

    def start(self) -> None:
        """Start the child process."""
        return self.aio_process.start()

    async def join(self, timeout: int = None) -> None:
        """Wait for the process to finish execution without blocking the main thread."""
        if not self.is_alive() and self.exitcode is None:
            raise ValueError("must start process before joining it")

        if timeout is not None:
            return await asyncio.wait_for(self.join(), timeout)

        while self.exitcode is None:
            await asyncio.sleep(0.005)

    @property
    def name(self) -> str:
        """Child process name."""
        return self.aio_process.name

    def is_alive(self) -> bool:
        """Is child process running."""
        return self.aio_process.is_alive()

    @property
    def daemon(self) -> bool:
        """Should child process be daemon."""
        return self.aio_process.daemon

    @daemon.setter
    def daemon(self, value: bool) -> None:
        """Should child process be daemon."""
        self.aio_process.daemon = value

    @property
    def pid(self) -> Optional[int]:
        """Process ID of child, or None if not started."""
        return self.aio_process.pid

    @property
    def exitcode(self) -> Optional[int]:
        """Exit code from child process, or None if still running."""
        return self.aio_process.exitcode

    def terminate(self) -> None:
        """Send SIGTERM to child process."""
        return self.aio_process.terminate()

    # multiprocessing.Process methods added in 3.7
    if sys.version_info >= (3, 7):

        def kill(self) -> None:
            """Send SIGKILL to child process."""
            return self.aio_process.kill()

        def close(self) -> None:
            """Clean up child process once finished."""
            return self.aio_process.close()


class Worker(Process):
    """Execute a coroutine on a separate process and return the result."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, process_target=Worker.run_async, **kwargs)
        self.unit.namespace.result = None

    @staticmethod
    def run_async(unit: Unit) -> R:
        """Initialize the child process and event loop, then execute the coroutine."""
        try:
            result: R = Process.run_async(unit)
            unit.namespace.result = result
            return result

        except BaseException as e:
            unit.namespace.result = e
            raise

    async def join(self, timeout: int = None) -> Any:
        """Wait for the worker to finish, and return the final result."""
        await super().join(timeout)
        return self.result

    @property
    def result(self) -> R:
        """Easy access to the resulting value from the coroutine."""
        if self.exitcode is None:
            raise ValueError("coroutine not completed")

        return self.unit.namespace.result


class PoolWorker(Process):
    """Individual worker process for the async pool."""

    def __init__(
        self,
        tx: multiprocessing.Queue,
        rx: multiprocessing.Queue,
        ttl: int = MAX_TASKS_PER_CHILD,
        concurrency: int = CHILD_CONCURRENCY,
        *,
        initializer: Optional[Callable] = None,
        initargs: Sequence[Any] = (),
    ) -> None:
        super().__init__(target=self.run, initializer=initializer, initargs=initargs)
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
                    break

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

                result = None
                tb = None
                try:
                    result = future.result()
                except BaseException:
                    tb = traceback.format_exc()

                log.debug(f"{self.name} completed {tid}: {result}")
                self.rx.put_nowait((tid, result, tb))
                completed += 1


class Pool:
    """Execute coroutines on a pool of child processes."""

    def __init__(
        self,
        processes: int = None,
        initializer: Callable[..., None] = None,
        initargs: Sequence[Any] = (),
        maxtasksperchild: int = MAX_TASKS_PER_CHILD,
        childconcurrency: int = CHILD_CONCURRENCY,
    ) -> None:
        self.process_count = max(1, processes or os.cpu_count() or 2)
        self.initializer = initializer
        self.initargs = initargs
        self.maxtasksperchild = max(0, maxtasksperchild)
        self.childconcurrency = max(1, childconcurrency)

        self.processes: List[Process] = []
        self.tx_queue = context.Queue()
        self.rx_queue = context.Queue()

        self.running = True
        self.last_id = 0
        self._results: Dict[TaskID, Tuple[Any, Optional[TracebackStr]]] = {}
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
                    initializer=self.initializer,
                    initargs=self.initargs,
                )
                process.start()
                self.processes.append(process)

            # pull results into a shared dictionary for later retrieval
            while True:
                try:
                    task_id, value, tb = self.rx_queue.get_nowait()
                    self._results[task_id] = value, tb

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
                    result, tb = self._results.pop(tid)
                    if tb is not None:
                        raise ProxyException(tb)
                    ready[tid] = result
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
