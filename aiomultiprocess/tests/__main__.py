# Copyright 2019 John Reese
# Licensed under the MIT license

import unittest
import os

if __name__ == "__main__":  # pragma: no cover
    unittest.main(module="aiomultiprocess.tests", verbosity=2)
    os.environ['TEST_WITH_UVLOOP'] = "OK"
    unittest.main(module="aiomultiprocess.tests", verbosity=2)
