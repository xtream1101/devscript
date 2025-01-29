export default function useTheme() {
  const toggleBtnSelector = "#theme-toggle";
  const $toggleBtn = document.querySelector(toggleBtnSelector);

  function setup() {
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

    $toggleBtn.addEventListener("click", toggleTheme);
  }

  function toggleTheme() {
    const isLightMode = document.documentElement.classList.contains("dark");
    const theme = isLightMode ? "light" : "dark";

    // Toggle theme
    document.documentElement.classList.toggle("dark");
    localStorage.setItem("color-theme", theme);
    window.location.reload();
  }

  return {
    setup,
  };
}
