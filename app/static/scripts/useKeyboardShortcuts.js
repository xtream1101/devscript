export default function useKeyboardShortcuts() {
  const SEARCH_KEY = "/";
  const ADD_KEY = "a";
  const SUPPORTED_SHORTCUTS = [SEARCH_KEY, ADD_KEY];

  function setup() {
    document.body.addEventListener("keyup", handleKeyUp);
  }

  function handleKeyUp(event) {
    if (event.target !== document.body) {
      return;
    }

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
      const $addSnippetBtn = document.getElementById("global-add-snippet-btn");
      if (!$addSnippetBtn) {
        return;
      }
      $addSnippetBtn.click();
    }
  }

  return {
    setup,
  };
}
