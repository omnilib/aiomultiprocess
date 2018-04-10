aiomultiprocess
===============

Take a modern Python codebase to the next level of performance.

[![build status](https://travis-ci.org/jreese/aiomultiprocess.svg?branch=master)](https://travis-ci.org/jreese/aiomultiprocess)
[![version](https://img.shields.io/pypi/v/aiomultiprocess.svg)](https://pypi.org/project/aiomultiprocess)
[![license](https://img.shields.io/pypi/l/aiomultiprocess.svg)](https://github.com/jreese/aiomultiprocess/blob/master/LICENSE)
[![code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

On their own, AsyncIO and multiprocessing are useful, but limited:
AsyncIO still can't exceed the speed of GIL, and multiprocessing only works on
one task at a time.  But together, they can fully realize their true potential.

aiomultiprocess presents a simple interface, while running a full AsyncIO event
loop on each child process, enabling levels of concurrency never before seen
in a Python application.  Each child process can execute multiple coroutines
at once, limited only by the workload and number of cores available.

Gathering tens of thousands of network requests in seconds is as easy as:

    async with Pool() as pool:
        results = await pool.map(<coroutine>, <items>)


Install
-------

aiomultiprocess requires Python 3.6 or newer.
You can install it from PyPI:

    $ pip3 install aiomultiprocess


Usage
-----

Most of aiomultiprocess mimics the standard multiprocessing module whenever
possible, while accounting for places that benefit from async functionality.

Executing a coroutine on a child process is as simple as:

    from aiomultiprocess import Process

    async def foo(...):
        ...

    p = Process(target=foo, args=..., kwargs=...)
    p.start()
    await p.join()

If you want to get results back from that coroutine, then use `Worker` instead:

    from aiomultiprocess import Worker

    async def foo(...):
        ...

    p = Worker(target=foo, args=..., kwargs=...)
    p.start()
    await p.join()

    print(p.result)

If you want a managed pool of worker processes, then use `Pool`:

    from aiomultiprocess import Pool

    async def foo(value):
        return value * 2

    async with Pool() as pool:
        result = await pool.map(foo, range(10))


License
-------

aiomultiprocess is copyright [John Reese](https://jreese.sh), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.
