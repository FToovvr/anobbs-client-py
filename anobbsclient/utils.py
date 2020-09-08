from typing import Tuple

import time

import requests


def current_timestamp_ms_offset_to_utc8() -> int:
    return int((time.time() + 60*60*8)*1000)
