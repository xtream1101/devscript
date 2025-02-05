export default function useCodeEditor(codeHighlighter) {
    // Map hljs language names to our supported language values
    const languageMap = {
        arduino: "ARDUINO",
        bash: "BASH",
        c: "C",
        cpp: "CPP",
        csharp: "CSHARP",
        css: "CSS",
        diff: "DIFF",
        django: "DJANGO",
        dockerfile: "DOCKERFILE",
        go: "GO",
        graphql: "GRAPHQL",
        ini: "INI",
        java: "JAVA",
        javascript: "JAVASCRIPT",
        json: "JSON",
        kotlin: "KOTLIN",
        less: "LESS",
        lua: "LUA",
        makefile: "MAKEFILE",
        markdown: "MARKDOWN",
        objectivec: "OBJECTIVEC",
        perl: "PERL",
        php: "PHP",
        plaintext: "PLAINTEXT",
        pgsql: "PGSQL",
        powershell: "POWERSHELL",
        python: "PYTHON",
        r: "R",
        ruby: "RUBY",
        rust: "RUST",
        scss: "SCSS",
        shell: "SHELL",
        sql: "SQL",
        swift: "SWIFT",
        typescript: "TYPESCRIPT",
        xml: "XML",
        yaml: "YAML",
    };

    function setup() {
        const textareas = document.querySelectorAll("[data-textarea-code]");
        textareas.forEach(setupEditorFeatures);
    }

    function setupEditorFeatures(textarea) {
        // Setup language detection
        const langSelect = document.getElementById("language");
        const detectedLangSpan = document.getElementById("detected-language");

        if (langSelect && detectedLangSpan) {
            textarea.addEventListener("input", () => {
                detectedLangSpan.textContent = "";
                if (langSelect.value === "auto") {
                    // Clear language attribute when auto is selected
                    textarea.removeAttribute("language");

                    if (textarea.value.trim()) {
                        const detectedLang = codeHighlighter.detectLanguage(
                            textarea.value
                        );
                        if (detectedLang) {
                            // Map the detected language to our supported language enum
                            const mappedLang =
                                languageMap[detectedLang.toLowerCase()];
                            if (mappedLang) {
                                detectedLangSpan.textContent = `Detected: ${detectedLang}`;
                                // Set the detected language for syntax highlighting
                                textarea.setAttribute(
                                    "language",
                                    detectedLang.toLowerCase()
                                );
                            }
                        }
                    }
                }
            });

            // Set detected language on form submit if auto is selected
            const form = document.getElementById("form--snippet-save");
            if (form) {
                form.addEventListener("submit", () => {
                    if (langSelect.value === "auto") {
                        // Default to PLAINTEXT
                        let selectedLang = "PLAINTEXT";

                        // Try to detect language if there's content
                        if (textarea.value.trim()) {
                            const detectedLang = codeHighlighter.detectLanguage(
                                textarea.value
                            );
                            if (detectedLang) {
                                // Map the detected language to our supported language enum
                                const mappedLang =
                                    languageMap[detectedLang.toLowerCase()];
                                if (mappedLang) {
                                    selectedLang = mappedLang;
                                }
                            }
                        }

                        // Set the selected language
                        const options = Array.from(langSelect.options);
                        const matchingOption = options.find(
                            (opt) => opt.value === selectedLang
                        );
                        if (matchingOption) {
                            langSelect.value = matchingOption.value;
                        }
                    }
                });
            }
        }

        // Handle tab key to insert spaces
        textarea.addEventListener(
            "keydown",
            (e) => {
                if (e.key === "Tab") {
                    // Prevent both the default tab behavior and event bubbling
                    e.preventDefault();
                    e.stopPropagation();

                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    const spaces = "    "; // 4 spaces

                    // Insert 4 spaces at cursor position
                    textarea.value =
                        textarea.value.substring(0, start) +
                        spaces +
                        textarea.value.substring(end);

                    // Move cursor after the inserted spaces
                    textarea.selectionStart = textarea.selectionEnd =
                        start + spaces.length;

                    // Trigger input event for syntax highlighting
                    textarea.dispatchEvent(new Event("input"));

                    // Return false to ensure the event is completely cancelled
                    return false;
                }
            },
            { capture: true }
        ); // Use capture phase to handle event before other listeners

        // Handle enter key for auto-indentation
        textarea.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();

                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const text = textarea.value;

                // Get the current line before the cursor
                const lineStart = text.lastIndexOf("\n", start - 1) + 1;
                const currentLine = text.substring(lineStart, start);

                // Extract leading whitespace from the current line
                const indentation = currentLine.match(/^\s*/)[0];

                // Insert newline with the same indentation
                textarea.value =
                    text.substring(0, start) +
                    "\n" +
                    indentation +
                    text.substring(end);

                // Move cursor after the indentation
                const newCursorPos = start + 1 + indentation.length;
                textarea.selectionStart = textarea.selectionEnd = newCursorPos;

                // Trigger input event for syntax highlighting
                textarea.dispatchEvent(new Event("input"));
            }
        });
    }

    return {
        setup,
    };
}
