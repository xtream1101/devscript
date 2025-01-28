document.addEventListener("DOMContentLoaded", (event) => {
    initTheme();

    scrollToSelectedSnippet();
    initDateFormatter();
    initHLJS();
    initMarkdownEditor();
    initTags();
    initDropdowns();
    initCopyToClipboard();
    initToggleSnippetFavorite();
    initKeyboardShortcuts();
});

function scrollToSelectedSnippet() {
    const locationQueryParams = new URLSearchParams(window.location.search);
    const selectedSnippetId = locationQueryParams.get("selected_id");

    setTimeout(() => {
        if (selectedSnippetId && !document.location.hash) {
            document
                .getElementById(`snippet-${selectedSnippetId}`)
                .scrollIntoView({
                    behavior: "instant",
                    block: "center",
                    inline: "center",
                });
        }
    }, 0);
}

function initHLJS() {
    hljs.addPlugin(
        new CopyButtonPlugin({
            autohide: false, // Always show the copy button
        })
    );

    document.querySelectorAll("pre code").forEach((block) => {
        hljs.highlightElement(block);
    });
}

function initCopyToClipboard() {
    document.querySelectorAll("[data-copy-to-cliboard]").forEach((element) => {
        element.addEventListener("click", (e) => {
            copyToClipboard(e, element.getAttribute("data-copy-to-cliboard"));
        });
    });
}

function copyToClipboard(e, copyElementId) {
    e.preventDefault();
    e.stopPropagation();

    const $btn = e.currentTarget || e.target;
    const $copyElement = document.getElementById(copyElementId);

    if (typeof $copyElement === "undefined" || $copyElement === null) {
        return;
    }

    const content = $copyElement.value;

    navigator.clipboard.writeText(content).then(() => {
        const originalBtnContents = $btn.innerHTML;
        $btn.classList.add("!bg-green-400");
        $btn.innerText = "Copied!";

        setTimeout(() => {
            $btn.classList.remove("!bg-green-400");
            $btn.innerHTML = originalBtnContents;
        }, 1000);
    });
}

function initToggleSnippetFavorite() {
    document.querySelectorAll("[data-favorite-btn]").forEach((element) => {
        element.addEventListener("click", (e) => {
            const $btn = e.currentTarget;
            const snippetId = $btn.getAttribute("data-favorite-btn");
            toggleSnippetFavorite(e, snippetId);
        });
    });
}

function toggleSnippetFavorite(e, snippet_id) {
    e.stopPropagation();
    e.preventDefault();

    const $btns = document.querySelectorAll(
        `[data-favorite-btn="${snippet_id}"]`
    );

    $btns.forEach(($btn) => {
        $btn.classList.toggle("is-favorite");
        const hasClass = $btn.classList.contains("is-favorite");
        $btn.title = hasClass ? "Remove from favorites" : "Add to favorites";
        $btn.blur();
    });

    const url = `/snippets/${snippet_id}/toggle-favorite/`;
    fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    })
        .then((response) => response.json())
        .catch((error) => {
            $btns.forEach(($btn) => {
                $btn.classList.toggle("is-favorite");
                const hasClass = $btn.classList.contains("is-favorite");
                $btn.title = hasClass
                    ? "Remove from favorites"
                    : "Add to favorites";
            });
        });
}

function initKeyboardShortcuts() {
    document.body.addEventListener("keyup", function (event) {
        if (event.target !== document.body) {
            return;
        }

        const SEARCH_KEY = "/";
        const ADD_KEY = "a";
        const SUPPORTED_SHORTCUTS = [SEARCH_KEY, ADD_KEY];
        if (!SUPPORTED_SHORTCUTS.includes(event.key)) {
            return;
        }

        if (event.key === SEARCH_KEY) {
            const $searchInput = document.getElementById("global-search-input");
            if (!$searchInput) {
                return;
            }
            $searchInput.focus();
        } else if (event.key === ADD_KEY) {
            const $addSnippetBtn = document.getElementById(
                "global-add-snippet-btn"
            );
            if (!$addSnippetBtn) {
                return;
            }
            $addSnippetBtn.click();
        }
    });
}

function initMarkdownEditor() {
    const $textareas = document.querySelectorAll("[data-markdown-editor]");
    if ($textareas.length === 0) {
        return;
    }

    for (let i = 0; i < $textareas.length; i++) {
        const $textarea = $textareas[i];
        $textarea.style.display = "none";

        const $editor = document.createElement("div");
        $textarea.parentNode.insertBefore($editor, $textarea);

        const isDarkMode = document.documentElement.classList.contains("dark")

        const editor = new toastui.Editor({
            el: $editor,
            height: "500px",
            initialValue: $textarea.value,
            previewStyle: "tab",
            previewHighlight: false,
            plugins: [],
            hideModeSwitch: true,
            autofocus: false,
            theme: (isDarkMode ? "dark" : "default"),
            events: {
                change: function () {
                    $textarea.value = editor.getMarkdown();
                },
            },
        });
    }
}

function initTags() {
    const $tagInputs = document.querySelectorAll("[data-tags-input]");
    if ($tagInputs.length === 0) {
        return;
    }

    for (let i = 0; i < $tagInputs.length; i++) {
        const $input = $tagInputs[i];
        const $tagify = new Tagify($input, {
            pattern: /^[a-zA-Z0-9\.\-\_\s\\\/]{0,16}$/i,
            keepInvalidTags: true,
            originalInputValueFormat: (valuesArr) =>
                valuesArr.map((item) => item.value).join(","),
        });
        new DragSort($tagify.DOM.scope, {
            selector: '.' + $tagify.settings.classNames.tag,
            callbacks: {
                dragEnd() {
                    $tagify.updateValueByDOMTags();
                }
            }
        })
    }
}

function initDateFormatter() {
    const $datetimeElements = document.querySelectorAll("[data-timestamp]");
    if ($datetimeElements.length === 0) {
        return;
    }

    for (let i = 0; i < $datetimeElements.length; i++) {
        const $element = $datetimeElements[i];
        const datetime = dayjs($element.getAttribute("data-timestamp"));
        const displayFormat =
            $element.getAttribute("data-timestamp-format") || "fromNow";
        const titleFormat =
            $element.getAttribute("data-timestamp-title-format") ||
            "dddd, MMMM D, YYYY h:mm A";

        const formattedDate =
            displayFormat === "fromNow"
                ? datetime.fromNow()
                : datetime.format(displayFormat);
        const formattedTitle = datetime.format(titleFormat);

        $element.innerText = formattedDate;
        $element.title = formattedTitle;
    }
}

function initTheme() {
    const themeToggleBtn = document.getElementById("theme-toggle");

    // Change the icons inside the button based on previous settings
    if (
        localStorage.getItem("color-theme") === "dark" ||
        (!("color-theme" in localStorage) &&
            window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
        document.documentElement.classList.add("dark");
        document.getElementById("highlightjs-dark-theme").disabled = false;
        document.querySelectorAll("[data-dark-mode-only]").forEach((element) => {
            element.classList.remove("hidden");
        });
    } else {
        document.documentElement.classList.remove("dark");
        document.getElementById("highlightjs-light-theme").disabled = false;
        document.querySelectorAll("[data-light-mode-only]").forEach((element) => {
            element.classList.remove("hidden");
        });
    }

    themeToggleBtn.addEventListener("click", function () {
        const isLightMode = document.documentElement.classList.contains("dark");
        const theme = isLightMode ? "light" : "dark";

        // Toggle theme
        document.documentElement.classList.toggle("dark");
        localStorage.setItem("color-theme", theme);
        window.location.reload();
    });
}

function initDropdowns() {
    const $dropdowns = document.querySelectorAll("[data-dropdown]");

    for (let i = 0; i < $dropdowns.length; i++) {
        const $dropdown = $dropdowns[i];
        const searchPlaceholder =
            $dropdown.getAttribute("data-dropdown-search-placeholder") ||
            "Search...";
        new SlimSelect({
            select: $dropdown,
            settings: {
                showSearch: true,
                searchPlaceholder,
                openPosition: "down",
            },
        });
    }
}
