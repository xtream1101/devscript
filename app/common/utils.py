import asyncio
import threading
from typing import Any, Awaitable, Dict, List, Literal, Optional, TypeVar

from fastapi import Request

T = TypeVar("T")


def flash(
    request: Request,
    message: str,
    level: Literal["info", "warning", "error", "success"] = "info",
    title: str | None = None,
    placement: Literal["inline", "notification"] = "inline",
    is_dismissible: bool = True,
    format: Literal["default", "new_api_key"] = "default",
    **kwargs,
) -> None:
    """
    Add a flash message to the session.

    Args:
        request: The request object
        message: The message to flash
        level: The level of the message (e.g. "info", "warning", "error", "success")
        title: The title of the message
        placement: The placement of the message (e.g. "inline", "notification") - defaults to "inline"
        is_dismissible: Whether the message is dismissible - defaults to True
        format: The format of the message (e.g. "new_api_key") - defaults to "default"
        **kwargs: Additional keyword arguments
    """
    if "_messages" not in request.session:
        request.session["_messages"] = []

    request.session["_messages"].append(
        {
            "message": message,
            "title": title,
            "level": level,
            "placement": placement,
            "is_dismissible": is_dismissible,
            "format": format,
            **kwargs,
        }
    )


def get_flashed_messages(request: Request) -> List[Dict[str, str]]:
    """
    Get and clear all flashed messages.

    Args:
        request: The request object

    Returns:
        A list of flashed messages
    """
    messages = request.session.pop("_messages", [])
    return messages


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


def get_key_from_options(my_dict: dict, key_options: List[str]) -> Any:
    for key in key_options:
        if key in my_dict:
            return my_dict[key]
    return None
