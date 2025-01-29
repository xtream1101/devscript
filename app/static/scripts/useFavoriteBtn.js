export default function useFavoriteBtn() {
  function setup() {
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

  return {
    setup,
  };
}
