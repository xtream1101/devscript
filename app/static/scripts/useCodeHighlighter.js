export default function useCodeHighlighter() {
  hljs.addPlugin(
    new CopyButtonPlugin({
      autohide: false, // Always show the copy button
    })
  );

  function highlightAll() {
    highlightCodeBlocks();
    highlightTextareas();
  }

  function highlightCodeBlocks() {
    document.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightElement(block);
    });
  }

  async function highlightTextareas() {
    // Highlighted code script automatically runs when the script is loaded
    if (!window.chrome && !window.netscape) {
      await import('https://unpkg.com/@ungap/custom-elements');
    }
    await import('https://unpkg.com/highlighted-code');
  }

  return {
    highlightAll,
  };
}
