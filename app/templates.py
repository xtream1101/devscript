import uuid
from typing import Any, Dict

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.constants import SUPPORTED_LANG_FILENAMES, SUPPORTED_LANGUAGES


def app_context(request: Request) -> Dict[str, Any]:
    return {
        "request": request,
        "supported_languages": {
            "options": SUPPORTED_LANGUAGES,
            "filenames": SUPPORTED_LANG_FILENAMES,
        },
    }


@pass_context
def dashboard_snippet_view_url(context: dict, snippet_id: uuid.UUID) -> str:
    request = context["request"]
    curr_query_params = {
        k: v
        for k, v in request.query_params.items()
        if k not in ["selected_snippet_id"]
    }
    return request.url_for("dashboard").include_query_params(
        selected_snippet_id=snippet_id, **curr_query_params
    )


templates = Jinja2Templates(
    directory="app/templates", context_processors=[app_context], auto_reload=True
)
templates.env.globals["dashboard_snippet_view_url"] = dashboard_snippet_view_url
