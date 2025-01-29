export default function useCopyToClipboard() {
  function setup() {
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

  return {
    setup,
  };
}
