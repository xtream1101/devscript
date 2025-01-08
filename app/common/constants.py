from enum import Enum


class SUPPORTED_LANGUAGES(Enum):
    # VALUE (stored in db), Display Label (display only), Filename (used for loading hljs file)
    # https://highlightjs.readthedocs.io/en/latest/supported-languages.html

    BASH = "Bash", "bash"
    C = "C", "c"
    CPP = "C++", "cpp"
    CSHARP = "C#", "csharp"
    CSS = "CSS", "css"
    DIFF = "Diff", "diff"
    DJANGO = "Django", "django"
    DOCKERFILE = "Dockerfile", "dockerfile"
    GO = "Go", "go"
    GRAPHQL = "GraphQL", "graphql"
    INI = "INI", "ini"
    JAVA = "Java", "java"
    JAVASCRIPT = "JavaScript", "javascript"
    JINJA = "Jinja", "django"
    JSON = "JSON", "json"
    KOTLIN = "Kotlin", "kotlin"
    LESS = "Less", "less"
    LUA = "Lua", "lua"
    MAKEFILE = "Makefile", "makefile"
    MARKDOWN = "Markdown", "markdown"
    OBJECTIVEC = "Objective-C", "objectivec"
    PERL = "Perl", "perl"
    PHP = "PHP", "php"
    PHP_TEMPLATE = "PHP Template", "php-template"
    PLAINTEXT = "Plain Text", "plaintext"
    PGSQL = "PostgreSQL", "pgsql"
    PYTHON = "Python", "python"
    PYTHON_REPL = "Python REPL", "python-repl"
    R = "R", "r"
    RUBY = "Ruby", "ruby"
    RUST = "Rust", "rust"
    SCSS = "SCSS", "scss"
    SHELL = "Shell", "shell"
    SQL = "SQL", "sql"
    SWIFT = "Swift", "swift"
    TYPESCRIPT = "TypeScript", "typescript"
    VBNET = "VB.NET", "vbnet"
    WASM = "WebAssembly", "wasm"
    XML = "XML", "xml"
    YAML = "YAML", "yaml"


SUPPORTED_LANG_FILENAMES = set([lang.value[1] for lang in SUPPORTED_LANGUAGES])
