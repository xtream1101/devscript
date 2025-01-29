export default function useSelectDropdown() {
  function setup() {
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

  return {
    setup,
  };
}
