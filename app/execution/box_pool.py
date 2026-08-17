from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

class BoxPool:
    def __init__(self, size: int, *, offset: int = 0):
        if not isinstance(size, int) or size < 1:
            raise ValueError("BoxPool size must be a positive integer")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("BoxPool offset must be a non-negative integer")
        self.size = size
        self.offset = offset
        self._free: asyncio.Queue[int] = asyncio.Queue(maxsize=size)
        self._leased: set[int] = set()
        self._discarded: set[int] = set()
        for box_id in range(offset, offset + size):
            self._free.put_nowait(box_id)

    @property
    def available(self):
        return self._free.qsize()

    @property
    def leased(self):
        return frozenset(self._leased)

    @property
    def discarded(self):
        return frozenset(self._discarded)

    async def acquire(self):
        box_id = await self._free.get()
        if box_id in self._leased or box_id in self._discarded:
            raise RuntimeError(f"BoxPool internal state is inconsistent for box {box_id}")
        self._leased.add(box_id)
        return box_id

    def release(self, box_id: int):
        if box_id not in self._leased:
            raise ValueError(f"Box {box_id} is not leased by this pool")
        self._leased.remove(box_id)
        self._free.put_nowait(box_id)

    def discard(self, box_id: int):
        if box_id not in self._leased:
            raise ValueError(f"Box {box_id} is not leased by this pool")
        self._leased.remove(box_id)
        self._discarded.add(box_id)

    @asynccontextmanager
    async def lease(self):
        box_id = await self.acquire()
        try:
            yield box_id
        finally:
            if box_id in self._leased:
                self.release(box_id)
