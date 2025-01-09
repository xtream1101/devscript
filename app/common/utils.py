import asyncio
import threading
from typing import Any, Awaitable, Optional, TypeVar

T = TypeVar("T")


class sync_await:
    def __enter__(self) -> "sync_await":
        self._loop = asyncio.new_event_loop()
        self._looper = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._looper.start()
        return self

    def __call__(self, coro: Awaitable[T], timeout: Optional[float] = None) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    def __exit__(self, *exc_info: Any) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._looper.join()
        self._loop.close()
