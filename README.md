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

```python
async with Pool() as pool:
    results = await pool.map(<coroutine>, <items>)
```

For more context, watch the PyCon US 2018 talk about aiomultiprocess,
["Thinking Outside the GIL"][pycon-2018]:

> [![IMAGE ALT TEXT](http://img.youtube.com/vi/0kXaLh8Fz3k/0.jpg)](http://www.youtube.com/watch?v=0kXaLh8Fz3k "PyCon 2018 - John Reese - Thinking Outside the GIL with AsyncIO and Multiprocessing")


Install
-------

aiomultiprocess requires Python 3.6 or newer.
You can install it from PyPI:

```bash session
$ pip3 install aiomultiprocess
```


Usage
-----

Most of aiomultiprocess mimics the standard multiprocessing module whenever
possible, while accounting for places that benefit from async functionality.

Executing a coroutine on a child process is as simple as:

```python
from aiohttp import request
from aiomultiprocess import Process

async def fetch(url):
    return await request("GET", url)

p = Process(target=fetch, args="https://jreese.sh")
await p
```

If you want to get results back from that coroutine, `Worker` makes that available:

```python
from aiohttp import request
from aiomultiprocess import Worker

async def fetch(url):
    return await request("GET", url)

p = Worker(target=fetch, args="https://jreese.sh")
response = await p
```

If you want a managed pool of worker processes, then use `Pool`:

```python
from aiohttp import request
from aiomultiprocess import Pool

async def fetch(url):
    return await request("GET", url)

urls = ["https://jreese.sh", ...]
async with Pool() as pool:
    result = await pool.map(fetch, urls)
```


License
-------

aiomultiprocess is copyright [John Reese](https://jreese.sh), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.


[pycon-2018]: https://www.youtube.com/watch?v=0kXaLh8Fz3k
