aiomultiprocess
===============

v0.7.0
------

Feature release

- Changed to use spawned processes by default on all platforms
- Use sharded work/result queues for Pools, using round robin
  by default, with option to provide a custom scheduler
- Initializers now run after creating the event loop
- Full support for Python 3.8 and Windows
- Major refactoring and splitting of internals
- 100% test coverage

```
$ git shortlog -s v0.6.1...v0.7.0
    12	Daniel Ip
     1	HJK
    15	John Reese
```


v0.6.1
------

Minor release v0.6.1

- Better exception handling/proxying from child process (#27)
- Improved test coverage (#29)

```
$ git shortlog -s v0.6.0...v0.6.1
     9	Daniel Ip
     6	John Reese
```


v0.6.0
------

Feature release v0.6.0

- Enable passing initializer functions/args to process pools (#23)
- `kill()` and `close()` are only available on Python 3.7+
- Added correct Python version requirements to package metadata
- Bundled unit tests inside module for distrtibution

```
$ git shortlog -s v0.5.0...v0.6.0
     1	Daniel Ip
    18	John Reese
```


v0.5.0
------

Feature release v0.5.0:

- Support Windows
- Support "spawn" contexts on all platforms
- Allow changing the multiprocessing context at runtime
- Better support for features in Python 3.7

```
$ git shortlog -s v0.4.0...v0.5.0
    15	John Reese
     1	smheidrich
     1	x1ah
```


v0.4.0
------

Feature release v0.4.0:

- Allow awaiting Process objects directly to start/join child process
- Worker objects return final result from await/join
- Better unit testing, types, and documentation

```
$ git shortlog -s v0.3.0...v0.4.0
    12	John Reese
```


v0.3.0
------

Feature release:

- enable multiple coroutines per child process
- perf testing

```
$ git shortlog -s v0.2.0...v0.3.0
    10	John Reese
```


v0.2.0
------

Feature release:

- Run coroutines on child process or process pool

```
$ git shortlog -s d58104b244a984f37d2f672431b4a2fc7e74931b...v0.2.0
     1	John Reese
```


