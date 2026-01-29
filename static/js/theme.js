/**
 * Theme Switcher - Supports Light Mode and Dark Mode
 * Automatically persists user preference in localStorage
 */

(function () {
  "use strict";

  const THEME_KEY = "expense-tracker-theme";
  const THEMES = {
    LIGHT: "light-mode",
    DARK: "dark-mode",
  };

  /**
   * Initialize theme on page load
   */
  function initTheme() {
    // Check localStorage first
    let savedTheme = localStorage.getItem(THEME_KEY);

    // If no saved theme, check system preference
    if (!savedTheme) {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;
      savedTheme = prefersDark ? THEMES.DARK : THEMES.LIGHT;
    }

    applyTheme(savedTheme);
    updateThemeButton();
  }

  /**
   * Apply theme to the document
   */
  function applyTheme(theme) {
    const body = document.body;
    const navbar = document.querySelector(".navbar");

    // Remove all theme classes
    body.classList.remove(THEMES.LIGHT, THEMES.DARK);
    if (navbar) navbar.classList.remove(THEMES.LIGHT, THEMES.DARK);

    // Apply new theme
    body.classList.add(theme);
    if (navbar) navbar.classList.add(theme);

    // Save preference
    localStorage.setItem(THEME_KEY, theme);
  }

  /**
   * Toggle between light and dark mode
   */
  function toggleTheme() {
    const currentTheme = localStorage.getItem(THEME_KEY) || THEMES.LIGHT;
    const newTheme = currentTheme === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT;

    applyTheme(newTheme);
    updateThemeButton();
  }

  /**
   * Update theme button icon and text
   */
  function updateThemeButton() {
    const button = document.getElementById("theme-toggle-btn");
    if (!button) return;

    const currentTheme = localStorage.getItem(THEME_KEY) || THEMES.LIGHT;
    const isDark = currentTheme === THEMES.DARK;

    button.innerHTML = isDark
      ? '<i class="fas fa-sun"></i>'
      : '<i class="fas fa-moon"></i>';
    button.title = isDark ? "Switch to Light Mode" : "Switch to Dark Mode";
    button.setAttribute("aria-label", button.title);
  }

  /**
   * Listen for system theme changes
   */
  function watchSystemTheme() {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", (e) => {
        // Only apply if user hasn't set a preference
        if (!localStorage.getItem(THEME_KEY)) {
          const newTheme = e.matches ? THEMES.DARK : THEMES.LIGHT;
          applyTheme(newTheme);
          updateThemeButton();
        }
      });
    }
  }

  /**
   * Attach event listeners
   */
  function attachListeners() {
    const button = document.getElementById("theme-toggle-btn");
    if (button) {
      button.addEventListener("click", toggleTheme);
    }
  }

  /**
   * Initialize on DOM ready
   */
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    attachListeners();
    watchSystemTheme();
  });

  // Export functions for testing/debugging
  window.ThemeSwitcher = {
    toggleTheme,
    applyTheme,
    getCurrentTheme: () => localStorage.getItem(THEME_KEY) || THEMES.LIGHT,
    setTheme: (theme) => applyTheme(theme),
  };
})();
