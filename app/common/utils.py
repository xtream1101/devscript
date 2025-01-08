import asyncio
import threading
from typing import Any, Awaitable, Optional, TypeVar

from app.common.constants import SUPPORTED_LANGUAGES

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


def find_matching_language(str: str | None) -> Optional[str]:
    str = str.strip().lower() if str else None
    print(str)
    if not str:
        return None

    lang_keys = SUPPORTED_LANGUAGES.__members__
    lang_labels = {lang.value[0].lower(): lang.name for lang in SUPPORTED_LANGUAGES}
    lang_filenames = {lang.value[1].lower(): lang.name for lang in SUPPORTED_LANGUAGES}
    print(lang_labels)

    if str.upper() in lang_keys:
        return str.upper()

    if str.lower() in lang_labels:
        return lang_labels[str]

    if str.lower() in lang_filenames:
        return lang_filenames[str]

    return None
