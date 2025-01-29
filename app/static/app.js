import useTheme from './modules/useTheme.js';
import useDateFormatter from './modules/useDateFormatter.js';
import useCodeHighlighter from './modules/useCodeHighlighter.js';
import useCopyToClipboard from './modules/useCopyToClipboard.js';
import useKeyboardShortcuts from './modules/useKeyboardShortcuts.js';
import useMarkdownEditor from './modules/useMarkdownEditor.js';
import useTagsInput from './modules/useTagsInput.js';
import useSelectDropdown from './modules/useSelectDropdown.js';
import useFavoriteBtn from './modules/useFavoriteBtn.js';

document.addEventListener("DOMContentLoaded", (event) => {
    // Immediately scroll to the selected snippet if the URL has a selected_id query parameter
    scrollToSelectedSnippet();

    // Setup the base theme -- this must be done before any other setup functions
    const theme = useTheme();
    theme.setup();

    // Setup the rest of the modules
    const codeHighlighter = useCodeHighlighter();
    const copyToClipboard = useCopyToClipboard();
    const dateFormatter = useDateFormatter();
    const favoriteBtn = useFavoriteBtn();
    const keyboardShortcuts = useKeyboardShortcuts();
    const markdownEditor = useMarkdownEditor();
    const selectDropdown = useSelectDropdown();
    const tagsInput = useTagsInput();

    // Buttons and Actions
    copyToClipboard.setup();
    favoriteBtn.setup();
    keyboardShortcuts.setup();

    // Display Elements
    dateFormatter.format()
    codeHighlighter.highlightAll();

    // Forms and Inputs
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
