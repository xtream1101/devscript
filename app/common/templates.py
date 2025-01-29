import time
from typing import Any, Dict

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.auth.utils import AUTH_COOKIE, optional_current_user
from app.common import utils
from app.common.constants import SUPPORTED_LANG_FILENAMES, SUPPORTED_LANGUAGES
from app.settings import settings


def app_context(request: Request) -> Dict[str, Any]:
    active_route = request.scope["route"].name if request.scope.get("route") else None

    user = None
    with utils.sync_await() as await_:
        try:
            session_token = await_(AUTH_COOKIE(request))
            if session_token:
                user = await_(optional_current_user(session_token))
        except Exception:
            pass

    selected_code_theme_light = (
        user.code_theme_light
        if user and user.code_theme_light
        else settings.DEFAULT_CODE_THEME_LIGHT
    )
    selected_code_theme_dark = (
        user.code_theme_dark
        if user and user.code_theme_dark
        else settings.DEFAULT_CODE_THEME_DARK
    )

    return {
        # Used on all pages
        "request": request,
        "user": user,
        "settings": settings,
        "active_route_name": active_route,
        "supported_languages": {
            "options": SUPPORTED_LANGUAGES,
            "filenames": SUPPORTED_LANG_FILENAMES,
        },
        "selected_code_themes": {
            "light": selected_code_theme_light,
            "dark": selected_code_theme_dark,
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
def static_url(context: dict, path: str) -> str:
    params = {"v": settings.VERSION}

    if not settings.is_prod:
        params["t"] = str(time.time())

    return (
        context["request"].url_for("static", path=path).include_query_params(**params)
    )


@jinja_global_function
@pass_context
def snippet_view_url(context: dict, snippet_id) -> str:
    return context["request"].url_for("snippet.view", id=snippet_id)


@jinja_global_function
@pass_context
def snippets_index_url(
    context: dict,
    snippet_id=None,
    q=None,
    lang=None,
    tag=None,
    is_public=None,
) -> str:
    request = context["request"]
    params = {}

    curr_tab = request.query_params.get("tab")
    curr_query = request.query_params.get("q")

    if curr_tab:
        params["tab"] = curr_tab

    if snippet_id:
        params["selected_id"] = snippet_id

    if q or isinstance(q, str):
        params["q"] = q
    elif lang:
        params["q"] = f"lang:{lang.lower()}"
    elif tag:
        params["q"] = f'tag:"{tag}"'
    elif is_public:
        params["q"] = "is:public"
    elif curr_query:
        params["q"] = curr_query

    return request.url_for("snippets.index").include_query_params(**params)


@jinja_global_function
@pass_context
def get_flashed_messages(context: dict) -> list:
    return utils.get_flashed_messages(context["request"])


@jinja_global_function
@pass_context
def snippet_language_display(context: dict, language: str) -> str:
    if language not in SUPPORTED_LANGUAGES.__members__:
        return language

    return SUPPORTED_LANGUAGES[language].value[0]
