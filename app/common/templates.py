import uuid
from typing import Any, Dict

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.common.constants import SUPPORTED_LANG_FILENAMES, SUPPORTED_LANGUAGES


def app_context(request: Request) -> Dict[str, Any]:
    active_route = request.scope["route"].name if request.scope.get("route") else None

    return {
        "request": request,
        "active_route_name": active_route,
        "nav": [
            {
                "label": "Dashboard",
                "route": "snippets.index",
            },
            {
                "label": "API Keys",
                "route": "api_keys.index",
            },
        ],
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
def snippets_search_url(context: dict, snippet_id: uuid.UUID) -> str:
    request = context["request"]
    curr_query_params = {
        k: v for k, v in request.query_params.items() if k not in ["selected_id"]
    }

    url = request.url_for("snippets.index").include_query_params(
        selected_id=snippet_id,
        **curr_query_params,
    )

    return f"{url}#snippet-{snippet_id}"


@jinja_global_function
@pass_context
def snippet_language_display(context: dict, language: str) -> str:
    if language not in SUPPORTED_LANGUAGES.__members__:
        return language

    return SUPPORTED_LANGUAGES[language].value[0]
