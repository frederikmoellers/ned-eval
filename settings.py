#!/usr/bin/env python3

# Licensed under the EUPL

from decimal import Decimal
import os
from typing import Dict, Union

lambdas = [
    (-1.0, "No dummy traffic"),
    (0.001, "~1 packet per 20 minutes, very low overhead"),
    (0.01, "~1 packet per 100 seconds, low overhead"),
    (1/60, "~1 packet per minute"),
    (0.1, "~1 packet per 10 seconds, higher than usual present IA times"),
    (0.5, "~1 packet per 2 seconds"),
    (1.0, "~1 packet per second"),
]

# NOTE: the actual threshold in seconds needs to be divided by TIMESTAMP_PRECISION
INTERARRIVAL_THRESHOLDS = {
    1: 10000,
    "2.1": 100000,
    "2.2": 100000,
    3: 100000000,
}

# the number of user interactions to analyse when estimating epsilon and delta
# NOTE: the same number of non-user-interactions will be tested as well (if available)
SAMPLE_COUNT = 1000
# how long does the attacker sample data (in seconds)?
SAMPLE_DURATION = 10
# timeout for generating samples (in seconds)
SAMPLE_TIMEOUT = 900

# timestamp precision of the different systems
TIMESTAMP_PRECISION: Dict[Union[int, str], float] = {
    1: 1.0,
    "2.1": 1.0,
    "2.2": 1.0,
    3: 0.001,
}
