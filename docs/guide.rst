User Guide
==========


aiomultiprocess provides an interface similar to, but more flexible than, the
standard :py:mod:`multiprocessing` module. In the most common use case, the
:class:`~aiomultiprocess.Pool` class provides a simple mechanism for running
coroutines on multiple worker processes::

    from aiohttp import request
    from aiomultiprocess import Pool

    async def get(url):
        async with request("GET", url) as response:
            return await response.text("utf-8")

    async def main():
        urls = ["https://noswap.com", ...]
        async with Pool() as pool:
            async for result in pool.map(get, urls):
                ...  # process result


Workers
-------

For asynchronous jobs needing a dedicated process per job, the
:class:`~aiomultiprocess.Worker` class will run the desired coroutine on
a fresh child process and and return the final result back to the main process::

    from aiohttp import request
    from aiomultiprocess import Worker

    async def get(url, method="GET"):
        async with request(method, url) as response:
            return await response.text("utf-8")

    async def main():
        result = await Worker(
            target=get,
            args=("https://noswap.com",),
            kwargs={"method": "GET"}
        )

The worker process can also be started by manually calling the ``start()``
method, and the results can then be retrieved by awaiting the ``join()``
method::

    async def main():
        worker = Worker(
            target=get,
            args=("https://noswap.com",),
            kwargs={"method": "GET"}
        )
        worker.start()
        result = await worker.join()


Process Pools
-------------

The :class:`~aiomultiprocess.Pool` class provides an easier method of managing
multiple workers, such as spreading jobs across a fixed number of worker
processes and running multiple jobs concurrently on each worker.

Individual jobs can be queued using the ``apply()`` method::  

    from asyncio import gather
    from aiomultiprocess import Pool

    async def get(url):
        async with request("GET", url) as response:
            return await response.text("utf-8")

    async with Pool() as pool:
        a, b, c = gather(
            pool.apply(get, "https://github.com"),
            pool.apply(get, "https://noswap.com"),
            pool.apply(get, "https://omnilib.dev"),
        )

Multiple jobs sharing the same coroutine can be queued using the ``map()``
and ``starmap()`` methods, which will automatically queue one job for each
element in the iterable passed to it. The method can be awaited to get all
results as a list in the same order as the inputs::

    async with Pool() as pool:
        data = [1, 4, 9, 16, 25]
        results = await pool.map(math.sqrt, data)
        # [1, 2, 3, 4, 5]

The ``map()`` and ``starmap()`` methods can also be iterated over to get
results as soon as they are completed, while still maintaining the original
order as the inputs::

    async with Pool() as pool:
        data = [1, 4, 9, 16, 25]
        async for value in pool.map(math.sqrt, data):
            ...


Advanced Usage
--------------

The default configuration of aiomultiprocess should be sufficient for most
use cases, but it does offer the ability to change performance options
for different workloads, and to better integrate with other frameworks.

Spawned vs Forked Processes
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the standard :py:mod:`multiprocessing` module, child processes default to
"forked" processes on Linux (and macOS for Python 3.7 or older), and "spawn"
processes on Windows (and macOS for Python 3.8 and newer). 

By default, aiomultiprocess uses spawned worker processes, regardless of the
host operating system. This provides the benefit of consistent behavior
("forked" processes aren't available on Windows and have limitations on macOS)
and also reduces the amount of memory used by the process pool.

However, this also requires that any objects or coroutines used must be
importable from the fresh child processes. Inner functions, lambdas, or object
types defined at runtime, cannot be serialized to these freshly spawned
processes.

If forked processes are required, or if the "forkserver" method is preferred,
the :func:`~aiomultiprocess.set_start_method` function must be called
before creating workers or process pools::

    import aiomultiprocess

    aiomultiprocess.set_start_method("fork")

For more detail, see the :py:mod:`multiprocessing` module documentation for
`Contexts and start methods <https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods>`_


Initializers
^^^^^^^^^^^^

In some cases, there may be a need to run arbitrary code in the child process
before accepting and running jobs. aiomultiprocess supports the use of an
"initializer" function, and if given, will run this function with the given
arguments in each child process, after the async event loop has been created::

    import logging
    from aiomultiprocess import Pool

    def setup_logging(level=logging.WARNING):
        logging.basicConfig(level=level)

    async with Pool(
        initializer=setup_logging, initargs=(logging.DEBUG,)
    ) as pool:
        ...


Exceptions
^^^^^^^^^^^^

Exceptions raised in worker processes are silenced and transferred back to main
process, where they are turned into :class:`~aiomultiprocess.types.ProxyException`
objects.
In some cases, you may want to something exceptions within the worker process itself.
You can use provided "exception_handler" hook, for example::

    import sentry_sdk
    from aiomultiprocess import Pool

    async with Pool(
        exception_handler=sentry_sdk.capture_exception
    ) as pool:
        ...


Using uvloop
^^^^^^^^^^^^

If you wish to use `uvloop <https://uvloop.readthedocs.io/index.html>`_
or some alternative event loop implementation, then you will need to tell
aiomultiprocess which event loop initializer to use in child processes::

    import uvloop
    from aiomultiprocess import Pool

    async with Pool(loop_initializer=uvloop.new_event_loop) as pool:
        ...

This is also available for use with individual :class:`~aiomultiprocess.Process`
and :class:`~aiomultiprocess.Worker` objects::

    import uvloop
    from aiomultiprocess import Process, Worker

    await Process(
        target=some_coro, loop_initializer=uvloop.new_event_loop
    )
    result = await Worker(
        target=other_coro, loop_initializer=uvloop.new_event_loop
    )


Performance Tuning
------------------

Process pools offer five different options to tune the number and behavior
of worker processes in the pool:

* The ``processes`` value controls the number of worker processes the pool
  will create and maintain. With the default value of ``None``, the pool will
  create enough workers for each CPU core available on the host machine. Any
  other positive integer value will instruct the pool to create that number
  of workers instead.

* Setting ``maxtasksperchild`` to a positive integer value will make worker
  processes clean and respawn after the given number of tasks have completed.
  This can be used with long-running services, or memory-leaking libraries,
  to help reduce overall memory usage across the pool. 
  The default value (``0``) will disable this and let worker processes live
  until the pool is explicitly closed.

* The ``queuecount`` value controls the number of queues used by the pool.
  At high levels of throughput, queue contention may become a limiting factor,
  especially with a large number of worker processes. The pool will spread
  jobs across queues according to the scheduler used, and adding more queues
  (up to the number of active processes) reduces the number of workers assigned
  to each queue.

* The ``childconcurrency`` value controls the maximum number of active,
  concurrent jobs each worker process will pick up from its queue at once.
  While the worker has accepted fewer than ``childconcurrency`` jobs, it will
  look for and accept more jobs from its assigned queue. When a job has
  completed, that frees a slot for a new job from the queue.

* The ``scheduler`` for the pool controls how jobs are distributed among queues
  in the pool. The default :class:`~aiomultiprocess.RoundRobin` scheduler
  evenly distributes jobs across all queues in round-robin order. Alternative
  schedulers may assign jobs to queues using arbitrary criteria, but no other
  scheduler implementation is available by default with aiomultiprocess.

Maximum concurrency of a process pool can be calculated as::

    total_concurrency = processes * childconcurrency

The throughput of the process pool can be derived by knowing the average
duration of a job at a given level of concurrency::

    throughput = total_concurrency / job_time

The level of "contention" for an individual queue can be expressed as a
function of the throughput of the pool in jobs per second::

    contention = throughput / queuecount


Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Together, the tuning options above can provide optimum configuration for a wide
variety of latency, throughput, and computation tradeoffs:

* For computation-heavy workloads, it is recommended to lower the
  ``childconcurrency``, keep ``queuecount < (cpu_count / 4)``, and use the
  default worker process count and scheduler. This will reduce latency of
  individual jobs and help prevent incidental timeouts.

* For jobs that involve high-latency, low-bandwidth async operations, increasing
  the ``childconcurrency`` and ``queuecount`` values will increase the total
  concurrency and throughput of the process pool.
  
* For optimal balance of workloads across all child processes, 
  between all child processes, use a ``queuecount`` that is an integer divisor
  of the ``processes`` count, so that each queue has the same number of workers
  assigned to it.

* For jobs with high variability in computation or duration, worker queues may
  become unbalanced. This can be mitigated with a lower ``queuecount``, an
  alternative scheduler aware of queue sizes, or by queueing fewer jobs at
  a time and waiting for results before queueing more jobs.
