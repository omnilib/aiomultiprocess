# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import logging
import multiprocessing as mp
import os

from typing import Any, Awaitable, Callable, Tuple, TypeVar, Dict

R = TypeVar("R")

log = logging.getLogger(__name__)


_manager = None


def get_manager():
    """Return a singleton shared manager."""
    global _manager
    if _manager is None:
        _manager = mp.Manager()

    return _manager


class Process:
    """Execute a coroutine on a separate process."""

    def __init__(
        self,
        group: None = None,
        target: Callable[..., Awaitable[R]] = None,  # pylint: disable=bad-whitespace
        name: str = None,
        args: Tuple[Any, ...] = None,  # pylint: disable=bad-whitespace
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
        self.aio_target = target
        self.aio_args = args or ()
        self.aio_kwargs = kwargs or {}
        self.aio_process = mp.Process(
            group=group, target=self.run_async, name=name, daemon=daemon
        )

    async def run(self) -> Any:
        raise NotImplementedError()

    def run_async(self) -> R:
        try:
            if self.aio_init:
                self.aio_init()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if self.aio_target:
                log.debug(
                    f"running {self.aio_target}(*{self.aio_args}, **{self.aio_kwargs}))"
                )
                result = loop.run_until_complete(
                    self.aio_target(*self.aio_args, **self.aio_kwargs)
                )

            else:
                result = loop.run_until_complete(
                    self.run(*self.aio_args, **self.aio_kwargs)
                )

            return result

        except BaseException:
            log.exception(f"aio process {os.getpid()} failed")
            raise

    async def join(self, timeout=None) -> None:
        if timeout is not None:
            try:
                return await asyncio.wait_for(self.join(), timeout)

            except asyncio.TimeoutError:
                return

        while self.exitcode is None:
            await asyncio.sleep(0.005)

    def __getattr__(self, name):
        return getattr(self.aio_process, name)


class Worker(Process):
    """Execute a coroutine on a separate process and return the result."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.aio_namespace = get_manager().Namespace()

    async def run(self) -> Any:
        raise NotImplementedError()

    def run_async(self) -> R:
        try:
            result: R = super().run_async()
            self.aio_namespace.result = result
            return result

        except BaseException as e:
            self.aio_namespace.result = e
            raise

    @property
    def result(self) -> R:
        if self.exitcode is not None:
            return self.aio_namespace.result

        return None
