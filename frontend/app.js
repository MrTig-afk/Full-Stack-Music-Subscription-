/**
 * Music Subscription Frontend Application
 *
 * Single-page application (SPA) for user authentication, music search, and subscription management.
 * Uses browser sessionStorage for session management and fetch API for cross-origin API calls.
 *
 * Architecture:
 * - IIFE scope isolation: All code within anonymous function to avoid global pollution
 * - State management: Centralized state object for session, subscriptions, results, and UI state
 * - Event binding: All listeners attached at initialization (not inline)
 * - DOM caching: DOM elements pre-cached to avoid repeated querySelector calls
 *
 * API Integration:
 * - Base URL resolved from: query param → localStorage → config.js default
 * - CORS mode enabled for cross-origin requests from S3 or other static hosts
 * - Session credentials stored in browser sessionStorage (for demo; use JWT in production)
 *
 * Features:
 * - User registration and login with email/password
 * - Music search by title, artist, album, year (AND matching)
 * - Subscribe/unsubscribe to songs (stored in DynamoDB via backend)
 * - View user subscriptions persisted across sessions
 * - Logout clears local session and browser state
 *
 * @requires config.js - Must be loaded before this script
 */
(() => {
  const config = window.APP_CONFIG || {};
  const apiBase = resolveApiBase(config.apiBaseUrl || "");

  const dom = {
    apiBaseLabel: document.getElementById("api-base-label"),
    authView: document.getElementById("auth-view"),
    appView: document.getElementById("app-view"),
    loginTab: document.getElementById("login-tab"),
    registerTab: document.getElementById("register-tab"),
    switchToRegister: document.getElementById("switch-to-register"),
    switchToLogin: document.getElementById("switch-to-login"),
    loginForm: document.getElementById("login-form"),
    registerForm: document.getElementById("register-form"),
    loginEmail: document.getElementById("login-email"),
    loginPassword: document.getElementById("login-password"),
    loginMessage: document.getElementById("login-message"),
    loginSubmit: document.getElementById("login-submit"),
    registerEmail: document.getElementById("register-email"),
    registerUsername: document.getElementById("register-username"),
    registerPassword: document.getElementById("register-password"),
    registerMessage: document.getElementById("register-message"),
    registerSuccess: document.getElementById("register-success"),
    registerSubmit: document.getElementById("register-submit"),
    userName: document.getElementById("user-name"),
    logoutButton: document.getElementById("logout-button"),
    refreshSubscriptions: document.getElementById("refresh-subscriptions"),
    subscriptionsEmpty: document.getElementById("subscriptions-empty"),
    subscriptionsList: document.getElementById("subscriptions-list"),
    queryForm: document.getElementById("query-form"),
    queryTitle: document.getElementById("query-title"),
    queryArtist: document.getElementById("query-artist"),
    queryAlbum: document.getElementById("query-album"),
    queryYear: document.getElementById("query-year"),
    queryMessage: document.getElementById("query-message"),
    querySubmit: document.getElementById("query-submit"),
    resultsEmpty: document.getElementById("results-empty"),
    resultsList: document.getElementById("results-list"),
  };

  const state = {
    session: loadSession(),
    subscriptions: [],
    results: [],
    activeAuthView: "login",
  };

  dom.apiBaseLabel.textContent = apiBase || "same-origin";
  bindEvents();
  showAuth(state.activeAuthView);

  if (state.session) {
    enterApp(state.session, { loadSubscriptions: true });
  }

  /**
   * Attach event listeners to all form inputs, buttons, and controls.
   * Called once at initialization to set up the entire event system.
   * Uses event delegation where appropriate to reduce listener count.
   */
  function bindEvents() {
    // Tab/view switching (login vs register)
    dom.loginTab.addEventListener("click", () => showAuth("login"));
    dom.registerTab.addEventListener("click", () => showAuth("register"));
    dom.switchToRegister.addEventListener("click", () => showAuth("register"));
    dom.switchToLogin.addEventListener("click", () => showAuth("login"));

    // Form submissions (login, register, query)
    dom.loginForm.addEventListener("submit", handleLogin);
    dom.registerForm.addEventListener("submit", handleRegister);
    dom.queryForm.addEventListener("submit", handleQuery);

    // App actions (logout, refresh subscriptions)
    dom.logoutButton.addEventListener("click", handleLogout);
    dom.refreshSubscriptions.addEventListener("click", refreshSubscriptions);

    // Auto-clear query message on input (improved UX)
    [
      dom.loginEmail,
      dom.loginPassword,
      dom.registerEmail,
      dom.registerUsername,
      dom.registerPassword,
      dom.queryTitle,
      dom.queryArtist,
      dom.queryAlbum,
      dom.queryYear,
    ].forEach((input) => {
      input.addEventListener("input", () => {
        if (input.closest("form") === dom.queryForm) {
          clearMessage(dom.queryMessage);
        }
      });
    });
  }

  /**
   * Resolve the API base URL using this priority order:
   * 1. URL query parameter: ?apiBase=... or ?api-base=...
   * 2. Browser localStorage: music-subscription-api-base
   * 3. config.js default: fallback parameter
   *
   * Query param override is persisted to localStorage for subsequent page loads.
   * Trailing slashes are removed to prevent double slashes in API calls.
   *
   * @param {string} fallback - Default URL from config.js
   * @returns {string} Resolved API base URL, or empty string for same-origin
   *
   * @example
   * // User loads: ?apiBase=https://api.example.com/prod
   * // Result: "https://api.example.com/prod" (stored to localStorage)
   */
  function resolveApiBase(fallback) {
    const params = new URLSearchParams(window.location.search);
    const queryOverride = params.get("apiBase") || params.get("api-base");
    const storedOverride = window.localStorage.getItem(
      "music-subscription-api-base",
    );
    const selected = queryOverride || storedOverride || fallback || "";
    return selected.replace(/\/+$/, "");
  }

  /**
   * Build full API URL by prepending base URL to path if base is set.
   * Enables testing multiple backends by changing apiBase.
   *
   * @param {string} path - API endpoint path (e.g., "/login", "/songs/search")
   * @returns {string} Full API URL or relative path if no base
   */
  function apiPath(path) {
    return apiBase ? `${apiBase}${path}` : path;
  }

  /**
   * Load user session from browser sessionStorage if it exists.
   * Session includes email and user_name, persists across page refreshes within same tab.
   * Cleared when user logs out or closes the browser/tab.
   *
   * @returns {object|null} Session object {email, userName} or null if no session
   */
  function loadSession() {
    const email = window.sessionStorage.getItem("music-subscription-email");
    const userName = window.sessionStorage.getItem(
      "music-subscription-user-name",
    );
    if (!email || !userName) {
      return null;
    }

    return { email, userName };
  }

  /**
   * Save user session to browser sessionStorage.
   * Session data persists across page refreshes within the same tab/window.
   * Also updates the local state.session object.
   *
   * @param {object} session - Session object {email, userName}
   */
  function saveSession(session) {
    window.sessionStorage.setItem("music-subscription-email", session.email);
    window.sessionStorage.setItem(
      "music-subscription-user-name",
      session.userName,
    );
    state.session = session;
  }

  /**
   * Clear user session from browser sessionStorage and local state.
   * Called on logout or when session expires.
   */
  function clearSession() {
    window.sessionStorage.removeItem("music-subscription-email");
    window.sessionStorage.removeItem("music-subscription-user-name");
    state.session = null;
  }

  /**
   * Switch between auth views (login or register).
   * Hides app view and shows auth forms with selected tab active.
   * Clears all messages to provide clean UX when switching modes.
   *
   * @param {string} view - "login" or "register"
   */
  function showAuth(view) {
    state.activeAuthView = view;
    const isLogin = view === "login";
    dom.loginTab.classList.toggle("active", isLogin);
    dom.registerTab.classList.toggle("active", !isLogin);
    dom.loginForm.hidden = !isLogin;
    dom.registerForm.hidden = isLogin;
    dom.authView.hidden = false;
    dom.appView.hidden = true;
    clearMessage(dom.loginMessage);
    clearMessage(dom.registerMessage);
    clearMessage(dom.registerSuccess);
  }

  /**
   * Switch from auth view to main app view.
   * Shows search, subscriptions, and query UI.
   */
  function showApp() {
    dom.authView.hidden = true;
    dom.appView.hidden = false;
  }

  /**
   * Transition user into authenticated app experience.
   * Saves session, displays username, shows app view, and optionally loads subscriptions.
   * Called after successful login or register, and on page load if session exists.
   *
   * @param {object} session - Session object {email, userName}
   * @param {object} options - {loadSubscriptions: boolean} - Fetch subscriptions from backend
   */
  function enterApp(session, options = {}) {
    saveSession(session);
    dom.userName.textContent = session.userName;
    showApp();
    clearMessage(dom.queryMessage);
    dom.resultsEmpty.classList.add("hidden");
    dom.resultsList.innerHTML = "";
    if (options.loadSubscriptions) {
      refreshSubscriptions().catch(() => {
        state.subscriptions = [];
        renderSubscriptions();
      });
    } else {
      renderSubscriptions();
    }
  }

  /**
   * Handle login form submission.
   * Sends email and password to backend /login endpoint.
   * On success: saves session and enters app.
   * On error: displays error message (e.g., invalid credentials).
   *
   * @param {Event} event - Form submission event
   */
  async function handleLogin(event) {
    event.preventDefault();
    clearMessage(dom.loginMessage);
    setBusy(dom.loginSubmit, true);

    try {
      const payload = {
        email: dom.loginEmail.value.trim(),
        password: dom.loginPassword.value,
      };

      const data = await request("/login", {
        method: "POST",
        body: payload,
      });

      enterApp(
        {
          email: data.email || payload.email,
          userName: data.user_name || data.userName || payload.email,
        },
        { loadSubscriptions: true },
      );
      dom.loginForm.reset();
    } catch (error) {
      setMessage(
        dom.loginMessage,
        error.message || "email or password is invalid",
        "error",
      );
    } finally {
      setBusy(dom.loginSubmit, false);
    }
  }

  /**
   * Handle registration form submission.
   * Sends email, username, and password to backend /register endpoint.
   * On success: shows success message and redirects to login after 1 second.
   * On error: displays error message (e.g., email already exists).
   *
   * @param {Event} event - Form submission event
   */
  async function handleRegister(event) {
    event.preventDefault();
    clearMessage(dom.registerMessage);
    clearMessage(dom.registerSuccess);
    setBusy(dom.registerSubmit, true);

    try {
      const payload = {
        email: dom.registerEmail.value.trim(),
        user_name: dom.registerUsername.value.trim(),
        password: dom.registerPassword.value,
      };

      await request("/register", {
        method: "POST",
        body: payload,
      });

      setMessage(
        dom.registerSuccess,
        "Account created successfully. Redirecting to login.",
        "success",
      );
      dom.registerForm.reset();
      window.setTimeout(() => {
        showAuth("login");
        clearMessage(dom.registerSuccess);
      }, 1000);
    } catch (error) {
      setMessage(
        dom.registerMessage,
        error.message || "The email already exists",
        "error",
      );
    } finally {
      setBusy(dom.registerSubmit, false);
    }
  }

  /**
   * Handle music search form submission.
   * Collects query criteria (title, artist, album, year) from form inputs.
   * Sends GET request to /songs/search endpoint.
   * On success: renders results as song cards with Subscribe button.
   * On error: displays error message.
   * Requires at least one field to be filled.
   *
   * @param {Event} event - Form submission event
   */
  async function handleQuery(event) {
    event.preventDefault();
    clearMessage(dom.queryMessage);
    dom.resultsEmpty.classList.add("hidden");
    dom.resultsList.innerHTML = "";

    const criteria = collectQueryCriteria();
    if (!Object.values(criteria).some(Boolean)) {
      setMessage(
        dom.queryMessage,
        "At least one field must be completed",
        "error",
      );
      return;
    }

    setBusy(dom.querySubmit, true);

    try {
      const response = await request(
        `/songs/search?${serializeQuery(criteria)}`,
        { method: "GET" },
      );
      state.results = normalizeItems(response.items || response.songs || []);
      renderResults();
    } catch (error) {
      state.results = [];
      renderResults();
      setMessage(
        dom.queryMessage,
        error.message || "No result is retrieved. Please query again",
        "error",
      );
    } finally {
      setBusy(dom.querySubmit, false);
    }
  }

  /**
   * Collect query criteria from form inputs.
   * Trims whitespace from each field.
   *
   * @returns {object} {title, artist, album, year} - Query parameters (empty string if not filled)
   */
  function collectQueryCriteria() {
    return {
      title: dom.queryTitle.value.trim(),
      artist: dom.queryArtist.value.trim(),
      album: dom.queryAlbum.value.trim(),
      year: dom.queryYear.value.trim(),
    };
  }

  /**
   * Serialize query criteria to URL search string.
   * Only includes non-empty fields.
   * Used for GET /songs/search requests.
   *
   * @param {object} criteria - Query criteria object
   * @returns {string} URL search string (e.g., "artist=Taylor+Swift&year=2008")
   */
  function serializeQuery(criteria) {
    const params = new URLSearchParams();
    Object.entries(criteria).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      }
    });
    return params.toString();
  }

  /**
   * Fetch user subscriptions from backend /subscriptions/{email} endpoint.
   * Updates state.subscriptions and re-renders subscription list.
   * Called on app entry and when user adds/removes subscriptions.
   *
   * @throws {Error} If backend request fails or user not authenticated
   */
  async function refreshSubscriptions() {
    if (!state.session) {
      state.subscriptions = [];
      renderSubscriptions();
      return;
    }

    const response = await request(
      `/subscriptions/${encodeURIComponent(state.session.email)}`,
      {
        method: "GET",
      },
    );

    state.subscriptions = normalizeItems(
      response.items || response.subscriptions || [],
    );
    renderSubscriptions();
  }

  /**
   * Handle subscribe button click on a song result.
   * Adds subscription to backend via POST /subscriptions.
   * Prevents duplicate subscriptions.
   * Refreshes both subscription and result lists.
   *
   * @param {object} song - Song object {title, artist, album, year, image_url}
   */
  async function handleSubscribe(song) {
    if (!state.session) {
      return;
    }

    const key = songKey(song);
    if (state.subscriptions.some((item) => songKey(item) === key)) {
      return;
    }

    await request("/subscriptions", {
      method: "POST",
      body: {
        user_email: state.session.email,
        title: song.title,
        artist: song.artist,
        year: song.year,
        album: song.album,
        img_url: song.image_url || song.img_url || "",
      },
    });

    await refreshSubscriptions();
    renderResults();
  }

  /**
   * Handle remove button click on a subscription.
   * Removes subscription from backend via DELETE /subscriptions.
   * Refreshes both subscription and result lists.
   *
   * @param {object} song - Song object with at least {title, album}
   */
  async function handleRemove(song) {
    if (!state.session) {
      return;
    }

    await request("/subscriptions", {
      method: "DELETE",
      body: {
        user_email: state.session.email,
        title: song.title,
        album: song.album,
      },
    });

    await refreshSubscriptions();
    renderResults();
  }

  /**
   * Handle logout button click.
   * Sends DELETE /logout request to backend (tolerates errors).
   * Clears local session, subscriptions, results, and all form inputs.
   * Resets UI to auth view (login).
   */
  async function handleLogout() {
    try {
      await request("/logout", { method: "DELETE" });
    } catch {
      // Clear the browser session even if the server logout request fails.
    }

    clearSession();
    state.subscriptions = [];
    state.results = [];
    dom.loginForm.reset();
    dom.registerForm.reset();
    dom.queryForm.reset();
    dom.subscriptionsList.innerHTML = "";
    dom.resultsList.innerHTML = "";
    dom.resultsEmpty.classList.add("hidden");
    dom.subscriptionsEmpty.classList.remove("hidden");
    showAuth("login");
  }

  /**
   * Render the user's subscription list.
   * Displays songs user is subscribed to with Remove button.
   * Called after login, subscribe, or remove actions.
   */
  function renderSubscriptions() {
    renderSongList({
      items: state.subscriptions,
      container: dom.subscriptionsList,
      emptyState: dom.subscriptionsEmpty,
      actionLabel: "Remove",
      actionVariant: "ghost danger",
      onAction: handleRemove,
    });
  }

  /**
   * Render query results.
   * Displays search results with Subscribe button.
   * Disables Subscribe button if song already subscribed.
   * Called after search or after subscribe/remove actions.
   */
  function renderResults() {
    const hasResults = state.results.length > 0;
    dom.resultsEmpty.classList.toggle("hidden", hasResults);
    renderSongList({
      items: state.results,
      container: dom.resultsList,
      emptyState: dom.resultsEmpty,
      actionLabel: "Subscribe",
      actionVariant: "primary",
      onAction: handleSubscribe,
      shouldDisable: (song) =>
        state.subscriptions.some((item) => songKey(item) === songKey(song)),
      disabledLabel: "Subscribed",
    });
  }

  /**
   * Generic song list renderer (subscriptions, search results, etc).
   * Creates HTML for each song with image, metadata, and action button.
   * Manages empty state display and button event listeners.
   * Supports conditional disabling of action buttons.
   *
   * @param {object} config - Renderer configuration
   * @param {Array} config.items - Array of song objects to render
   * @param {Element} config.container - DOM element to render into
   * @param {Element} config.emptyState - Element to show when items empty
   * @param {string} config.actionLabel - Button text (e.g., \"Subscribe\")
   * @param {string} config.actionVariant - CSS class for button styling
   * @param {Function} config.onAction - Callback when action button clicked
   * @param {Function} [config.shouldDisable] - Return true to disable button for item
   * @param {string} [config.disabledLabel] - Button text when disabled (default: \"Subscribed\")\n   */
  function renderSongList({
    items,
    container,
    emptyState,
    actionLabel,
    actionVariant,
    onAction,
    shouldDisable = () => false,
    disabledLabel = "Subscribed",
  }) {
    if (!items.length) {
      container.innerHTML = "";
      if (emptyState) {
        emptyState.classList.remove("hidden");
      }
      return;
    }

    if (emptyState) {
      emptyState.classList.add("hidden");
    }

    container.innerHTML = items
      .map((item) => {
        const disabled = shouldDisable(item);
        const image = item.image_url || item.img_url || "";
        const art = image
          ? `<div class="song-art"><img src="${escapeHtml(image)}" alt="${escapeHtml(item.artist || item.title || "Artist image")}" onerror="this.parentElement.textContent='ART';this.parentElement.classList.add('fallback');"></div>`
          : `<div class="song-art">ART</div>`;

        const badges = [
          item.artist
            ? `<span class="badge info">Artist: ${escapeHtml(item.artist)}</span>`
            : "",
          item.album
            ? `<span class="badge">Album: ${escapeHtml(item.album)}</span>`
            : "",
          item.year
            ? `<span class="badge">Year: ${escapeHtml(item.year)}</span>`
            : "",
        ]
          .filter(Boolean)
          .join("");

        return `
          <article class="song-card">
            ${art}
            <div class="song-meta">
              <p class="song-title">${escapeHtml(item.title || "Untitled")}</p>
              <p class="song-subtitle">${escapeHtml(item.artist || "Unknown artist")} · ${escapeHtml(item.album || "Unknown album")}</p>
              <div class="song-badges">${badges}</div>
            </div>
            <button
              class="button ${actionVariant} song-action"
              type="button"
              data-key="${escapeHtml(songKey(item))}"
              ${disabled ? "disabled" : ""}
            >${disabled ? disabledLabel : actionLabel}</button>
          </article>
        `;
      })
      .join("");

    // Attach event listeners to action buttons after rendering.
    container.querySelectorAll("button[data-key]").forEach((button) => {
      const song = items.find((item) => songKey(item) === button.dataset.key);
      if (!song) {
        return;
      }

      button.addEventListener("click", async () => {
        setBusy(button, true);
        try {
          await onAction(song);
        } catch (error) {
          window.alert(
            error.message || "The operation could not be completed.",
          );
        } finally {
          setBusy(button, false);
        }
      });
    });
  }

  /**
   * Normalize song items from backend response.
   * Ensures all expected properties exist (defaulting to empty string).
   * Handles variations in property names (image_url vs img_url).
   *
   * @param {Array} items - Raw items from backend
   * @returns {Array} Normalized items with consistent properties
   */
  function normalizeItems(items) {
    return items.map((item) => ({
      title: item.title || "",
      artist: item.artist || "",
      album: item.album || "",
      year: item.year != null ? String(item.year) : "",
      image_url: item.image_url || item.img_url || "",
      img_url: item.img_url || item.image_url || "",
      music_id: item.music_id || "",
    }));
  }

  /**
   * Generate unique key for a song based on title and album.
   * Used to detect duplicate subscriptions and match songs across requests.
   *
   * @param {object} song - Song object with {title, album}
   * @returns {string} Key in format \"title#album\"\n   */
  function songKey(song) {
    return `${song.title || ""}#${song.album || ""}`;
  }

  /**
   * Fetch wrapper for API requests.
   * Adds CORS mode for cross-origin calls from S3-hosted frontend.
   * Parses JSON response and extracts error details from backend.
   * Throws on HTTP errors or parsing failures.
   *
   * @param {string} path - API endpoint path (relative or absolute via apiPath)\n   * @param {object} [options] - Fetch options\n   * @param {string} [options.method] - HTTP method (default: \"GET\")\n   * @param {object} [options.body] - Request body (auto-JSON stringified)\n   * @returns {Promise<object>} Parsed JSON response\n   * @throws {Error} With detail from backend or generic message\n   */
  async function request(path, options = {}) {
    const response = await fetch(apiPath(path), {
      method: options.method || "GET",
      mode: "cors",
      credentials: "omit",
      headers: options.body ? { "Content-Type": "application/json" } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(data?.detail || data?.message || "Request failed");
    }

    return data || {};
  }

  /**
   * Display a message (error, success, or info) in a container.
   * Sets visibility, text, and CSS class for styling.
   *
   * @param {Element} element - Message container element\n   * @param {string} message - Message text to display\n   * @param {string} variant - CSS class variant (\"error\", \"success\", etc)\n   */
  function setMessage(element, message, variant) {
    element.textContent = message;
    element.hidden = false;
    element.classList.remove("error", "success");
    element.classList.add(variant);
  }

  /**
   * Clear a message container.
   * Hides element and removes styling classes.
   *
   * @param {Element} element - Message container element\n   */
  function clearMessage(element) {
    element.textContent = "";
    element.hidden = true;
    element.classList.remove("error", "success");
  }

  /**
   * Set busy state on a button (typically disables during async operations).
   * Disables button while operation is in progress to prevent double-clicks.
   *
   * @param {Element} target - Button or form element\n   * @param {boolean} busy - true to disable, false to enable\n   */
  function setBusy(target, busy) {
    if (!target) {
      return;
    }

    if (target instanceof HTMLButtonElement) {
      target.disabled = busy;
    }
  }

  /**
   * Escape HTML special characters in a string.
   * Prevents XSS attacks when rendering user data or backend responses.
   * Escapes: & < > \" '\n   * @param {*} value - Value to escape (coerced to string)\n   * @returns {string} Escaped HTML-safe string\n   */
  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
})();
