
API Reference
=============

.. module:: aiomultiprocess

Process Pools
-------------

.. autoclass:: Pool
    :members:
    :special-members: __aenter__, __aexit__

.. autoclass:: PoolResult
    :members:
    :special-members: __aiter__, __await__

.. autoclass:: Scheduler
    :members:

.. autoclass:: RoundRobin
    :members:

Advanced
--------

.. autofunction:: set_start_method

.. autoclass:: Process
    :members:

.. autoclass:: Worker
    :members: