"""Count-min sketch. An estimate, not a ledger row."""

from __future__ import annotations

import math
import random

WIDTH = math.ceil(math.e / 0.001)
DEPTH = 5
_PRIME = 2_147_483_647


class CountMin:
    def __init__(self, seed: int = 1) -> None:
        rng = random.Random(seed)
        self.a = [rng.randrange(1, _PRIME) for _ in range(DEPTH)]
        self.b = [rng.randrange(0, _PRIME) for _ in range(DEPTH)]
        self.table = [[0 for _ in range(WIDTH)] for _ in range(DEPTH)]

    def _index(self, row: int, key: int) -> int:
        return ((self.a[row] * (key % _PRIME) + self.b[row]) % _PRIME) % WIDTH

    def update(self, key: int, count: int) -> None:
        if count < 0:
            raise ValueError("count")
        for row in range(DEPTH):
            self.table[row][self._index(row, key)] += count

    def query(self, key: int) -> int:
        return min(self.table[row][self._index(row, key)] for row in range(DEPTH))
