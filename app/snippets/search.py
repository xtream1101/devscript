import re

from app.common.utils import find_matching_language


def parse_query(query):
    result = {
        "search": [],
        "languages": [],
        "tags": [],
        "is": [],
    }

    if not query:
        return result

    # Initialize dictionary to store the parsed results
    result = {
        "search": [],
        "languages": [],
        "tags": [],
        "is": [],
    }

    key_value_pattern = r'(language|tag|languages|tags):\s?"([^"]*)"|(language|tag|languages|tags):\s?([^"\s]+)|(is):\s?(public|owner|forked)|(is):\s?"(public|owner|forked)"'

    # Find all valid key-value pairs (like language:"python", tags:"zsh", is:"public", or is:public)
    key_value_matches = re.findall(key_value_pattern, query)

    # Process the matches
    for match in key_value_matches:
        pairs = [pair for pair in match if pair]  # Remove empty strings from the match
        key = pairs[0]
        value = pairs[1]

        if key == "tag":
            key = "tags"

        if key == "language":
            key = "languages"

        if key == "languages":
            value = find_matching_language(value) or value

        result[key].append(value.strip())

    # Remove the key-value pairs from the query to leave only free-text
    query_without_keys = re.sub(key_value_pattern, "", query)

    # Regular expression pattern to match everything else as search terms, including invalid keywords
    search_pattern = r'[a-zA-Z0-9-_]+:"[^"]*"|"[^"]*"|[^":\s][^"]*'  # Matches invalid keywords and free text

    # Find all search terms
    search_matches = re.findall(search_pattern, query_without_keys)

    if search_matches:
        # Append the matched search terms (including invalid keywords) to the "search" list
        result["search"].extend(
            [match.strip() for match in search_matches if match.strip()]
        )

    # Convert defaultdict to regular dictionary for easier readability
    return dict(result)


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
