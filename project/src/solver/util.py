from asyncio import Event


class ZeroBarrier:
    _pending: int
    _event: Event

    def __init__(self):
        self._pending = 0
        self._event = Event()
        self._event.set()  # immediately return on never-pushed barriers

    def push(self):
        self._event.clear()
        self._pending += 1

    def pop(self):
        self._pending -= 1
        if self._pending <= 0:
            self._event.set()

    async def wait(self):
        await self._event.wait()
