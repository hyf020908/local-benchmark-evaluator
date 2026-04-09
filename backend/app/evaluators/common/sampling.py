from __future__ import annotations

import random
from typing import TypeVar


T = TypeVar("T")


def choose_random_samples(items: list[T], max_samples: int, seed: int) -> list[T]:
    if max_samples <= 0:
        return []
    if len(items) <= max_samples:
        return list(items)
    return random.Random(seed).sample(items, max_samples)
