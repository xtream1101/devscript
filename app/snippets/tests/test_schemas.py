import datetime
import uuid

from fastapi.testclient import TestClient

import app.snippets.schemas as schemas
from app.app import app
from app.auth.models import User
from app.common.constants import SUPPORTED_LANGUAGES

client = TestClient(app)


def test_snippet_view_schema(mocker):
    user = User(display_name="test-user", email="user@example.com")
    user_to_view_spy = mocker.spy(user, "to_view")

    expects_data = {
        "id": str(uuid.uuid4()),
        "title": "Test Snippet Schema",
        "subtitle": "Test Subtitle",
        "content": "print('Hello, world!')",
        "description": """
# Test Description

This is a test description
    """,
        "language": SUPPORTED_LANGUAGES.PYTHON.name,
        "command_name": "test-command",
        "user_id": str(user.id),
        "user": user,
        "created_at": datetime.datetime(2021, 1, 1, 0, 0, 0),
        "updated_at": datetime.datetime(2021, 1, 1, 0, 0, 0),
        "public": True,
        "tags": [],
    }

    snippet = schemas.SnippetView(**expects_data)

    assert user_to_view_spy.call_count == 1

    assert snippet.model_dump() == {
        **expects_data,
        "forked_from_id": None,
        "is_fork": False,
        "is_favorite": False,
        "user": {
            "display_name": "test-user",
            "email": "user@example.com",
            "registered_at": None,
        },
    }

    assert (
        snippet.html_description
        == "<h1>Test Description</h1>\n<p>This is a test description</p>"
    )
    assert "content_truncated" not in dir(snippet)


def test_snippet_card_view_schema(mocker):
    user = User(display_name="test-user", email="user@example.com")
    user_to_view_spy = mocker.spy(user, "to_view")

    expects_data = {
        "id": str(uuid.uuid4()),
        "title": "Test Snippet Schema",
        "subtitle": "Test Subtitle",
        "content": "abcdefghijklmnopqrstuvwxyz" * 10,
        "language": SUPPORTED_LANGUAGES.PYTHON.name,
        "command_name": "test-command",
        "user_id": str(user.id),
        "user": user,
        "created_at": datetime.datetime(2021, 1, 1, 0, 0, 0),
        "updated_at": datetime.datetime(2021, 1, 1, 0, 0, 0),
        "public": True,
        "tags": [],
    }

    snippet_data = {
        **expects_data,
        "description": """
# Test Description

This is a test description
    """,
    }

    snippet = schemas.SnippetCardView(**snippet_data)

    assert user_to_view_spy.call_count == 1

    assert snippet.model_dump() == {
        **expects_data,
        "forked_from_id": None,
        "is_fork": False,
        "is_favorite": False,
        "user": {
            "display_name": "test-user",
            "email": "user@example.com",
            "registered_at": None,
        },
    }

    assert len(snippet.content_truncated) == 203
    assert (
        snippet.content_truncated
        == "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqr..."
    )
    assert "html_description" not in dir(snippet)
