# Copyright 2018 John Reese
# Licensed under the MIT license

import logging
import sys

from .core import CoreTest
from .perf import PerfTest

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
