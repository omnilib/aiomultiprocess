aiomultiprocess
===============

Take a modern Python codebase to the next level of performance.

[![version](https://img.shields.io/pypi/v/aiomultiprocess.svg)](https://pypi.org/project/aiomultiprocess)
[![documentation](https://readthedocs.org/projects/aiosqlite/badge/?version=latest)](https://aiomultiprocess.omnilib.dev)
[![changelog](https://img.shields.io/badge/change-log-blue)](https://aiomultiprocess.omnilib.dev/en/latest/changelog.html)
[![license](https://img.shields.io/pypi/l/aiomultiprocess.svg)](https://github.com/omnilib/aiomultiprocess/blob/master/LICENSE)
[![build status](https://github.com/omnilib/aiomultiprocess/workflows/Build/badge.svg)](https://github.com/omnilib/aiomultiprocess/actions)
[![code coverage](https://img.shields.io/codecov/c/gh/omnilib/aiomultiprocess)](https://codecov.io/gh/omnilib/aiomultiprocess)
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
    results = await pool.map(<coroutine function>, <items>)
```

Install
-------

aiomultiprocess requires Python 3.6 or newer.
You can install it from PyPI:

```bash
$ pip3 install aiomultiprocess
```


Usage
-----

Most of aiomultiprocess mimics the standard multiprocessing module whenever
possible, while accounting for places that benefit from async functionality.

Running your asynchronous jobs on a pool of worker processes is easy:

```python
from aiohttp import request
from aiomultiprocess import Pool

async def get(url):
    async with request("GET", url) as response:
        return await response.text("utf-8")

async def main():
    urls = ["https://jreese.sh", ...]
    async with Pool() as pool:
        async for result in pool.map(get, urls):
            ...  # process result
```

Take a look at the [User Guide][] for more details and examples.

For further context, watch the PyCon US 2018 talk about aiomultiprocess,
["Thinking Outside the GIL"][pycon-2018]:

> [![IMAGE ALT TEXT](http://img.youtube.com/vi/0kXaLh8Fz3k/0.jpg)](http://www.youtube.com/watch?v=0kXaLh8Fz3k "PyCon 2018 - John Reese - Thinking Outside the GIL with AsyncIO and Multiprocessing")

Slides available at [Speaker Deck](https://speakerdeck.com/jreese/thinking-outside-the-gil-2).


License
-------

aiomultiprocess is copyright [John Reese](https://jreese.sh), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.


[User Guide]: https://aiomultiprocess.omnilib.dev/en/latest/guide.html
[pycon-2018]: https://www.youtube.com/watch?v=0kXaLh8Fz3k

