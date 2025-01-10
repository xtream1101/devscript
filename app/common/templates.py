from typing import Any, Dict

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.auth.utils import AUTH_COOKIE, optional_current_user
from app.common import utils
from app.common.constants import SUPPORTED_LANG_FILENAMES, SUPPORTED_LANGUAGES


def app_context(request: Request) -> Dict[str, Any]:
    active_route = request.scope["route"].name if request.scope.get("route") else None

    with utils.sync_await() as await_:
        try:
            session_token = await_(AUTH_COOKIE(request))
            if not session_token:
                user = None
            else:
                user = await_(optional_current_user(session_token))
        except Exception:
            user = None

    return {
        "request": request,
        "user": user,
        "active_route_name": active_route,
        "nav": [],
        "supported_languages": {
            "options": SUPPORTED_LANGUAGES,
            "filenames": SUPPORTED_LANG_FILENAMES,
        },
    }


templates = Jinja2Templates(
    directory="app", context_processors=[app_context], auto_reload=True
)


def jinja_global_function(func):
    templates.env.globals[func.__name__] = func
    return func


@jinja_global_function
@pass_context
def snippet_view_url(context: dict, snippet_id) -> str:
    return context["request"].url_for("snippet.view", id=snippet_id)


@jinja_global_function
@pass_context
def snippet_card_url(context: dict, snippet_id) -> str:
    request = context["request"]

    params = {"selected_id": snippet_id}

    curr_q = request.query_params.get("q")
    if curr_q:
        params["q"] = curr_q

    return request.url_for("snippets.index").include_query_params(**params)


@jinja_global_function
@pass_context
def snippet_language_search_url(context: dict, language_key: str) -> str:
    return (
        context["request"]
        .url_for("snippets.index")
        .include_query_params(q=f"lang:{language_key.lower()}")
    )


@jinja_global_function
@pass_context
def snippet_tag_search_url(context: dict, tag: str) -> str:
    return (
        context["request"]
        .url_for("snippets.index")
        .include_query_params(q=f'tag:"{tag}"')
    )


@jinja_global_function
@pass_context
def snippet_is_public_search_url(context: dict) -> str:
    return (
        context["request"].url_for("snippets.index").include_query_params(q="is:public")
    )


@jinja_global_function
@pass_context
def snippet_language_display(context: dict, language: str) -> str:
    if language not in SUPPORTED_LANGUAGES.__members__:
        return language

    return SUPPORTED_LANGUAGES[language].value[0]
