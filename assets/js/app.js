/*
 * Copyright 2026 Julien Bombled
 * Licensed under the Apache License, Version 2.0. See LICENSE / NOTICE.
 *
 * SoundBoard — a static, GitHub-Pages-ready soundboard with a multi-pack
 * content model and runtime ThemeForge theming. No build step, no framework.
 */

(() => {
  "use strict";

  const STORE = {
    theme: "soundboard.theme",
    volume: "soundboard.volume",
    fav: (packId) => `soundboard.fav.${packId}`,
  };

  // --- Tiny structured logger (console-backed). -------------------------
  const log = {
    info: (...a) => console.info("[soundboard]", ...a),
    warn: (...a) => console.warn("[soundboard]", ...a),
    error: (...a) => console.error("[soundboard]", ...a),
  };

  // --- DOM references. --------------------------------------------------
  const el = {
    packTitle: document.getElementById("pack-title"),
    packSubtitle: document.getElementById("pack-subtitle"),
    search: document.getElementById("search"),
    packSelect: document.getElementById("pack-select"),
    themeSelect: document.getElementById("theme-select"),
    favToggle: document.getElementById("fav-toggle"),
    volume: document.getElementById("volume"),
    stopAll: document.getElementById("stop-all"),
    charFilter: document.getElementById("char-filter"),
    board: document.getElementById("board"),
    emptyState: document.getElementById("empty-state"),
    resultCount: document.getElementById("result-count"),
  };

  // --- Application state. ------------------------------------------------
  const state = {
    themes: [],
    themeById: new Map(),
    packsIndex: [],
    pack: null,
    favorites: new Set(),
    filters: { query: "", character: null, favOnly: false },
    audio: new Audio(),
    playingFile: null,
    rafId: 0,
  };

  // ---------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------
  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return res.json();
  }

  async function boot() {
    try {
      const [themesDoc, packsDoc] = await Promise.all([
        fetchJson("assets/data/themes.json"),
        fetchJson("assets/data/packs.json"),
      ]);

      state.themes = themesDoc.themes || [];
      state.themes.forEach((t) => state.themeById.set(t.id, t));
      applyTokens(themesDoc.tokens);
      populateThemeSelect();

      state.packsIndex = packsDoc.packs || [];
      populatePackSelect();

      wireControls();
      restoreVolume();

      const firstPack = state.packsIndex[0];
      if (!firstPack) throw new Error("No packs declared in packs.json");
      await loadPack(firstPack.id);
    } catch (err) {
      log.error("boot failed:", err);
      el.board.innerHTML =
        `<p class="empty-state">Erreur de chargement : ${escapeHtml(String(err.message))}</p>`;
    }
  }

  async function loadPack(packId) {
    const entry = state.packsIndex.find((p) => p.id === packId);
    if (!entry) { log.warn("unknown pack", packId); return; }

    stopPlayback();
    state.pack = await fetchJson(entry.manifest);
    state.favorites = loadFavorites(state.pack.id);
    state.filters = { query: "", character: null, favOnly: false };
    el.search.value = "";
    el.favToggle.setAttribute("aria-pressed", "false");

    el.packTitle.textContent = state.pack.name;
    el.packSubtitle.textContent = `${state.pack.count} répliques`;
    el.packSelect.value = state.pack.id;

    // Theme: stored preference wins, else the pack default.
    const stored = localStorage.getItem(STORE.theme);
    const themeId = state.themeById.has(stored) ? stored : entry.defaultTheme;
    applyTheme(themeId);
    el.themeSelect.value = themeId;

    renderCharFilter();
    render();
    log.info("pack loaded:", state.pack.id, state.pack.count, "sounds");
  }

  // ---------------------------------------------------------------------
  // Theming
  // ---------------------------------------------------------------------
  function applyTokens(tokens) {
    if (!tokens) return;
    const root = document.documentElement.style;
    const map = {
      radius: (k) => `--radius-${k}`,
      spacing: (k) => `--space-${k}`,
    };
    for (const group of ["radius", "spacing"]) {
      Object.entries(tokens[group] || {}).forEach(([k, v]) => {
        root.setProperty(map[group](k), v);
      });
    }
  }

  function applyTheme(themeId) {
    const theme = state.themeById.get(themeId);
    if (!theme) { log.warn("unknown theme", themeId); return; }
    const root = document.documentElement.style;
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.setProperty(`--${camelToKebab(key)}`, value);
    });
    document.documentElement.dataset.themeFamily = (theme.family || "").toLowerCase();
    localStorage.setItem(STORE.theme, themeId);
  }

  function populateThemeSelect() {
    el.themeSelect.innerHTML = "";
    const groups = { Dark: [], Light: [], Other: [] };
    state.themes.forEach((t) => {
      const fam = (t.family === "Dark" || t.family === "Light") ? t.family : "Other";
      groups[fam].push(t);
    });
    for (const [label, items] of Object.entries(groups)) {
      if (!items.length) continue;
      const og = document.createElement("optgroup");
      og.label = label === "Other" ? "Autres" : (label === "Dark" ? "Sombres" : "Clairs");
      items.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.name;
        og.appendChild(opt);
      });
      el.themeSelect.appendChild(og);
    }
  }

  function populatePackSelect() {
    el.packSelect.innerHTML = "";
    state.packsIndex.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      el.packSelect.appendChild(opt);
    });
    el.packSelect.disabled = state.packsIndex.length <= 1;
  }

  // ---------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------
  function renderCharFilter() {
    el.charFilter.innerHTML = "";
    const counts = new Map();
    state.pack.sounds.forEach((s) => {
      if (!s.character) return;
      counts.set(s.character, (counts.get(s.character) || 0) + 1);
    });

    const makeChip = (label, value, count) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.setAttribute("aria-pressed", String(state.filters.character === value));
      chip.innerHTML = `${escapeHtml(label)}` +
        (count != null ? `<span class="chip-count">${count}</span>` : "");
      chip.addEventListener("click", () => {
        state.filters.character = state.filters.character === value ? null : value;
        renderCharFilter();
        render();
      });
      return chip;
    };

    el.charFilter.appendChild(makeChip("Tous", null, state.pack.count));
    [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .forEach(([name, n]) => el.charFilter.appendChild(makeChip(name, name, n)));
  }

  function matchesFilters(sound) {
    const f = state.filters;
    if (f.favOnly && !state.favorites.has(sound.file)) return false;
    if (f.character && sound.character !== f.character) return false;
    if (f.query) {
      const hay = `${sound.title} ${sound.character} ${sound.episode}`.toLowerCase();
      if (!hay.includes(f.query)) return false;
    }
    return true;
  }

  function render() {
    const list = state.pack.sounds.filter(matchesFilters);
    el.board.innerHTML = "";
    const frag = document.createDocumentFragment();
    list.forEach((sound) => frag.appendChild(buildCard(sound)));
    el.board.appendChild(frag);

    el.emptyState.hidden = list.length !== 0;
    el.resultCount.textContent = `${list.length} / ${state.pack.count} répliques`;
  }

  function buildCard(sound) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "sound" + (sound.file === state.playingFile ? " playing" : "");
    card.dataset.file = sound.file;
    card.title = sound.episode || "";

    const isFav = state.favorites.has(sound.file);
    card.innerHTML = `
      <span class="fav-btn" role="button" aria-pressed="${isFav}"
            aria-label="Favori" title="Favori">${isFav ? "&#9733;" : "&#9734;"}</span>
      <span class="sound-title">${escapeHtml(sound.title)}</span>
      <span class="sound-meta">
        <span class="sound-char">${escapeHtml(sound.character || "")}</span>
      </span>
      <span class="progress"></span>`;

    card.addEventListener("click", (ev) => {
      if (ev.target.closest(".fav-btn")) { toggleFavorite(sound.file); return; }
      play(sound);
    });
    return card;
  }

  // ---------------------------------------------------------------------
  // Playback
  // ---------------------------------------------------------------------
  function play(sound) {
    if (state.playingFile === sound.file) { stopPlayback(); return; }
    stopPlayback();

    state.audio.src = `${state.pack.soundsBase}${encodeURIComponent(sound.file)}`;
    state.audio.volume = Number(el.volume.value);
    state.playingFile = sound.file;
    markPlaying(sound.file, true);

    state.audio.play().catch((err) => {
      log.error("playback error:", err);
      stopPlayback();
    });
    trackProgress();
  }

  function stopPlayback() {
    cancelAnimationFrame(state.rafId);
    if (!state.audio.paused) state.audio.pause();
    state.audio.currentTime = 0;
    if (state.playingFile) markPlaying(state.playingFile, false);
    state.playingFile = null;
  }

  function markPlaying(file, on) {
    const card = el.board.querySelector(`.sound[data-file="${cssEscape(file)}"]`);
    if (!card) return;
    card.classList.toggle("playing", on);
    if (!on) { const p = card.querySelector(".progress"); if (p) p.style.width = "0"; }
  }

  function trackProgress() {
    const step = () => {
      const card = el.board.querySelector(`.sound[data-file="${cssEscape(state.playingFile)}"]`);
      if (card && state.audio.duration) {
        const pct = (state.audio.currentTime / state.audio.duration) * 100;
        const bar = card.querySelector(".progress");
        if (bar) bar.style.width = `${pct}%`;
      }
      if (!state.audio.paused) state.rafId = requestAnimationFrame(step);
    };
    state.rafId = requestAnimationFrame(step);
  }

  // ---------------------------------------------------------------------
  // Favorites
  // ---------------------------------------------------------------------
  function loadFavorites(packId) {
    try {
      const raw = localStorage.getItem(STORE.fav(packId));
      return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
  }

  function persistFavorites() {
    localStorage.setItem(STORE.fav(state.pack.id), JSON.stringify([...state.favorites]));
  }

  function toggleFavorite(file) {
    if (state.favorites.has(file)) state.favorites.delete(file);
    else state.favorites.add(file);
    persistFavorites();
    if (state.filters.favOnly) render();
    else {
      const card = el.board.querySelector(`.sound[data-file="${cssEscape(file)}"]`);
      const btn = card && card.querySelector(".fav-btn");
      if (btn) {
        const on = state.favorites.has(file);
        btn.setAttribute("aria-pressed", String(on));
        btn.innerHTML = on ? "&#9733;" : "&#9734;";
      }
    }
  }

  // ---------------------------------------------------------------------
  // Controls wiring
  // ---------------------------------------------------------------------
  function wireControls() {
    el.search.addEventListener("input", () => {
      state.filters.query = el.search.value.trim().toLowerCase();
      render();
    });
    el.themeSelect.addEventListener("change", () => applyTheme(el.themeSelect.value));
    el.packSelect.addEventListener("change", () => loadPack(el.packSelect.value));
    el.favToggle.addEventListener("click", () => {
      state.filters.favOnly = !state.filters.favOnly;
      el.favToggle.setAttribute("aria-pressed", String(state.filters.favOnly));
      render();
    });
    el.stopAll.addEventListener("click", stopPlayback);
    el.volume.addEventListener("input", () => {
      state.audio.volume = Number(el.volume.value);
      localStorage.setItem(STORE.volume, el.volume.value);
    });
    state.audio.addEventListener("ended", stopPlayback);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") stopPlayback();
      if (e.key === "/" && document.activeElement !== el.search) {
        e.preventDefault(); el.search.focus();
      }
    });
  }

  function restoreVolume() {
    const v = localStorage.getItem(STORE.volume);
    if (v !== null) { el.volume.value = v; state.audio.volume = Number(v); }
  }

  // ---------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------
  function camelToKebab(s) { return s.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(); }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function cssEscape(s) {
    return window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&");
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
