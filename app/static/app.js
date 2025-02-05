import useTheme from "./scripts/useTheme.js";
import useDateFormatter from "./scripts/useDateFormatter.js";
import useCodeHighlighter from "./scripts/useCodeHighlighter.js";
import useCodeEditor from "./scripts/useCodeEditor.js";
import useCopyToClipboard from "./scripts/useCopyToClipboard.js";
import useKeyboardShortcuts from "./scripts/useKeyboardShortcuts.js";
import useMarkdownEditor from "./scripts/useMarkdownEditor.js";
import useTagsInput from "./scripts/useTagsInput.js";
import useSelectDropdown from "./scripts/useSelectDropdown.js";
import useFavoriteBtn from "./scripts/useFavoriteBtn.js";

document.addEventListener("DOMContentLoaded", (event) => {
    // Immediately scroll to the selected snippet if the URL has a selected_id query parameter
    scrollToSelectedSnippet();

    // Setup the base theme -- this must be done before any other setup functions
    const theme = useTheme();
    theme.setup();

    // Initialize code highlighter first since code editor depends on it
    const codeHighlighter = useCodeHighlighter();
    codeHighlighter.highlightAll();

    // Initialize code editor with highlighter
    const codeEditor = useCodeEditor(codeHighlighter);
    codeEditor.setup();

    // Initialize remaining modules
    const copyToClipboard = useCopyToClipboard();
    const dateFormatter = useDateFormatter();
    const favoriteBtn = useFavoriteBtn();
    const keyboardShortcuts = useKeyboardShortcuts();
    const markdownEditor = useMarkdownEditor();
    const selectDropdown = useSelectDropdown();
    const tagsInput = useTagsInput();

    // Setup remaining modules
    copyToClipboard.setup();
    favoriteBtn.setup();
    keyboardShortcuts.setup();
    dateFormatter.format();
    markdownEditor.setup();
    tagsInput.setup();
    selectDropdown.setup();
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
