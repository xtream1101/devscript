import re
from collections import defaultdict


def parse_query(query):
    # Initialize dictionary to store the parsed results
    result = defaultdict(list)

    # Regular expression pattern to match only valid 'is' values: is:public, is:"public", is:owner, is:"owner"
    key_value_pattern = r'(language|tags):\s?"([^"]*)"|(language|tags):\s?([^"\s]+)|(is):\s?(public|owner)|(is):\s?"(public|owner)"'  # Matches specific 'is' values

    # Find all valid key-value pairs (like language:"python", tags:"zsh", is:"public", or is:public)
    key_value_matches = re.findall(key_value_pattern, query)

    # Process the matches
    for match in key_value_matches:
        pairs = [pair for pair in match if pair]  # Remove empty strings from the match
        key = pairs[0]
        value = pairs[1]

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

    # Normalize the result dictionary: if 'language' is found, collect them in one list
    if "language" in result:
        result["languages"] = result.pop("language")

    # If 'is' has values like 'public' or 'owner', we could add them to a list
    if "is" in result:
        result["is"] = result["is"]  # Ensure 'is' is stored as a list of values

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

for query in test_inputs:
    print(f"Input: {query}")
    print(f"Output: {parse_query(query)}\n")
