export default function useMarkdownEditor() {
  function setup() {
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

  return {
    setup,
  };
}
