import re
from typing import ClassVar, List, Optional

from pydantic import BaseModel

from app.common.constants import SUPPORTED_LANGUAGES

SEARCH_KEY_MAP = {
    "languages": "languages",
    "language": "languages",
    "lang": "languages",
    "tags": "tags",
    "tag": "tags",
    "is": "is_",
}


class SnippetsSearchParser(BaseModel):
    q: str | None = None
    search_terms: List[str] = []
    languages: List[str] = []
    tags: List[str] = []
    is_: List[str] = []

    IS_PUBLIC_TERM: ClassVar[str] = "public"
    IS_MINE_TERM: ClassVar[str] = "mine"
    IS_FORK_TERM: ClassVar[str] = "fork"
    IS_FAVORITE_TERM: ClassVar[str] = "favorite"

    @property
    def is_fork(self):
        return self.IS_FORK_TERM in self.is_

    @property
    def is_mine(self):
        return self.IS_MINE_TERM in self.is_

    @property
    def is_public(self):
        return self.IS_PUBLIC_TERM in self.is_

    @property
    def is_favorite(self):
        return self.IS_FAVORITE_TERM in self.is_

    def __init__(self, **data):
        super().__init__(**data)

        if self.q:
            self.parse_query()

    def parse_query(self):
        if not self.q:
            return

        is_pattern = rf"(?:(?<=\s)|(?<=^))(is):\s?\"?({self.IS_FORK_TERM}|{self.IS_MINE_TERM}|{self.IS_PUBLIC_TERM}|{self.IS_FAVORITE_TERM})\"?(?:(?=\s)|(?=$))"
        keywords_pattern = (
            r"(?:(?<=\s)|(?<=^))(languages?|tags?|lang?):\s?(?:\"([^\"]*)\"|([^\"\s]+))"
        )

        key_value_pattern = rf"{is_pattern}|{keywords_pattern}"
        key_value_matches = re.findall(key_value_pattern, self.q)

        # Process the matches
        for match in key_value_matches:
            pairs = [
                pair for pair in match if pair
            ]  # Remove empty strings from the match

            key = pairs[0]
            key = SEARCH_KEY_MAP.get(key, key)
            value = pairs[1]

            match key:
                case "languages":
                    self.add_language(value)
                case "tags":
                    self.add_tag(value)
                case "is_":
                    self.add_is(value)

        # Remove the key-value pairs from the query to leave only free-text
        query_without_keys = re.sub(key_value_pattern, "", self.q)

        # Regular expression pattern to match everything else as search terms, including invalid keywords
        search_pattern = r'[a-zA-Z0-9-_]+:"[^"]*"|"[^"]*"|[^":\s][^"]*'

        # Find all search terms
        search_matches = re.findall(search_pattern, query_without_keys)

        # Append the matched search terms (including invalid keywords) to the "search" list
        if search_matches:
            for match in search_matches:
                match = match.strip()
                if match:
                    self.add_search_term(match)

    def add_language(self, input_lang: str):
        language = self._lookup_language(input_lang) or input_lang

        if language in self.languages:
            return

        self.languages.append(language)

    def add_tag(self, tag: str):
        tag = tag.lower()

        if tag in self.tags:
            return

        self.tags.append(tag)

    def add_is(self, is_: str):
        is_ = is_.lower()

        if is_ in self.is_:
            return

        self.is_.append(is_)

    def add_search_term(self, term: str):
        self.search_terms.append(term)

    def _lookup_language(self, str: str | None) -> Optional[str]:
        str = str.strip().lower() if str else None

        if not str:
            return None

        lang_keys = SUPPORTED_LANGUAGES.__members__
        lang_labels = {lang.value[0].lower(): lang.name for lang in SUPPORTED_LANGUAGES}
        lang_filenames = {
            lang.value[1].lower(): lang.name for lang in SUPPORTED_LANGUAGES
        }

        if str.upper() in lang_keys:
            return str.upper()

        if str.lower() in lang_labels:
            return lang_labels[str]

        if str.lower() in lang_filenames:
            return lang_filenames[str]

        return None


# Test the function with various inputs
test_inputs = [
    'user:"john" language:"python" language:c++ foo bar tags:"zsh" tags:public "bat cat" is:"public" is:"owner"',
    'language:"python"',
    'language:"python" language:c++',
    '"run script"',
    'language:"python" language:c++ foo bar tags:"zsh" tags:public "bat cat"',
    'is:"owner" language:"python" "foo bar"',
    'is:owner language:"python" "foo bar"',
    'is:"public" language:"python" "foo bar"',
    'is:public language:"python" "foo bar"',
    'is:mine language:"python" "foo bar"',  # Should be treated as a search term
    'is:"invalid" language:"python" "foo bar"',
    'language: "python \'foo\' bar" bat cat "foo bar"',
    'language: "python" "foo bar" is: public',
]
