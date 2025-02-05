# Advanced Search Guide

Snippet Manager provides powerful search capabilities to help you find exactly what you're looking for.
You can combine multiple search terms and filters to narrow down results.


## Basic Search

Simply type words or phrases to search through snippet titles, descriptions, and content:

```plaintext
hello world python
```

Use quotes for exact phrase matching:

```plaintext
"hello world"
```


## Language Filtering

Filter snippets by programming language using any of these equivalent keywords:

- `language:`
- `languages:`
- `lang:`

Examples:

```plaintext
language:python                # Find Python snippets
languages:"c++"                # Find C++ snippets (use quotes for languages with special characters)
lang:javascript hello world    # Find JavaScript snippets containing "hello world"
```

The language name is case-insensitive and matches both the language name and common file extensions.


## Tag Filtering

Filter snippets by tags using:

- `tag:`
- `tags:`

Examples:

```plaintext
tag:algorithm                 # Find snippets tagged with "algorithm"
tags:"data structure"         # Find snippets with "data structure" tag (use quotes for tags with spaces)
tag:utils tag:helper          # Find snippets with both "utils" and "helper" tags
```

Tags are case-insensitive.


## Special Filters

Use the `is:` keyword to filter snippets by special attributes:

- `is:public` - Show only public snippets
- `is:mine` - Show only your snippets
- `is:fork` - Show only forked snippets
- `is:favorite` - Show only favorited snippets

Examples:

```plaintext
is:mine language:python      # Find your Python snippets
is:public tag:algorithm      # Find public algorithm snippets
is:favorite tag:utils        # Find your favorited utility snippets
```


## Combining Filters

You can combine any number of search terms and filters:

```plaintext
is:public language:javascript tag:react "api call"
```

This would search for:

- Public snippets
- Written in JavaScript
- Tagged with "react"
- Containing the exact phrase "api call"


## Search Tips

1. Filters are case-insensitive
2. Use quotes for terms containing spaces
3. Multiple filters of the same type combine with AND logic
4. Free text terms combine with AND logic
5. Order of filters doesn't matter
