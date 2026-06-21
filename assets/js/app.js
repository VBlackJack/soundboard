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

  // Decorative palette used to color-code characters. Each entry is a CSS
  // custom property defined by the active theme, so dots stay themable.
  const CHAR_PALETTE = [
    "--cyan", "--green", "--orange", "--pink",
    "--purple", "--red", "--yellow", "--blue",
  ];

  const log = {
    info: (...a) => console.info("[soundboard]", ...a),
    warn: (...a) => console.warn("[soundboard]", ...a),
    error: (...a) => console.error("[soundboard]", ...a),
  };

  const el = {
    packTitle: document.getElementById("pack-title"),
    packSubtitle: document.getElementById("pack-subtitle"),
    search: document.getElementById("search"),
    packSelect: document.getElementById("pack-select"),
    themeSelect: document.getElementById("theme-select"),
    favToggle: document.getElementById("fav-toggle"),
    volume: document.getElementById("volume"),
    stopAll: document.getElementById("stop-all"),
    charCombo: document.getElementById("char-combo"),
    board: document.getElementById("board"),
    emptyState: document.getElementById("empty-state"),
    resultCount: document.getElementById("result-count"),
  };

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
    combo: null, // { trigger, panel, search, list, label }
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

    const stored = localStorage.getItem(STORE.theme);
    const themeId = state.themeById.has(stored) ? stored : entry.defaultTheme;
    applyTheme(themeId);
    el.themeSelect.value = themeId;

    buildCharCombo();
    render();
    log.info("pack loaded:", state.pack.id, state.pack.count, "sounds");
  }

  // ---------------------------------------------------------------------
  // Theming
  // ---------------------------------------------------------------------
  function applyTokens(tokens) {
    if (!tokens) return;
    const root = document.documentElement.style;
    const map = { radius: (k) => `--radius-${k}`, spacing: (k) => `--space-${k}` };
    for (const group of ["radius", "spacing"]) {
      Object.entries(tokens[group] || {}).forEach(([k, v]) => root.setProperty(map[group](k), v));
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
    const labels = { Dark: "Sombres", Light: "Clairs", Other: "Autres" };
    for (const [key, items] of Object.entries(groups)) {
      if (!items.length) continue;
      const og = document.createElement("optgroup");
      og.label = labels[key];
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
  // Character combobox (searchable)
  // ---------------------------------------------------------------------
  function characterCounts() {
    const counts = new Map();
    state.pack.sounds.forEach((s) => {
      if (!s.character) return;
      counts.set(s.character, (counts.get(s.character) || 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }

  function buildCharCombo() {
    el.charCombo.innerHTML = "";

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "combo-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.innerHTML =
      `<span class="combo-trigger-label">Tous les personnages</span>` +
      `<span class="caret" aria-hidden="true">&#9662;</span>`;

    const panel = document.createElement("div");
    panel.className = "combo-panel";
    panel.hidden = true;

    const search = document.createElement("input");
    search.type = "search";
    search.className = "combo-search";
    search.placeholder = "Filtrer un personnage…";
    search.setAttribute("aria-label", "Filtrer un personnage");

    const list = document.createElement("div");
    list.className = "combo-list";
    list.setAttribute("role", "listbox");

    panel.append(search, list);
    el.charCombo.append(trigger, panel);
    state.combo = { trigger, panel, search, list, label: trigger.firstElementChild };

    const makeOption = (name, value, count, colorVar) => {
      const opt = document.createElement("button");
      opt.type = "button";
      opt.className = "combo-option";
      opt.setAttribute("role", "option");
      opt.dataset.value = value == null ? "" : value;
      opt.dataset.name = name.toLowerCase();
      opt.innerHTML =
        `<span class="opt-dot" style="background:var(${colorVar})"></span>` +
        `<span class="opt-name">${escapeHtml(name)}</span>` +
        `<span class="opt-count">${count}</span>`;
      opt.addEventListener("click", () => selectCharacter(value, name));
      return opt;
    };

    list.appendChild(makeOption("Tous les personnages", null, state.pack.count, "--text-secondary"));
    characterCounts().forEach(([name, n]) =>
      list.appendChild(makeOption(name, name, n, charColorVar(name))));

    updateComboSelection();

    trigger.addEventListener("click", () => toggleCombo());
    search.addEventListener("input", () => filterComboOptions(search.value.trim().toLowerCase()));
  }

  function filterComboOptions(query) {
    state.combo.list.querySelectorAll(".combo-option").forEach((opt) => {
      const keep = !query || opt.dataset.value === "" || opt.dataset.name.includes(query);
      opt.style.display = keep ? "" : "none";
    });
  }

  function toggleCombo(forceOpen) {
    const open = forceOpen != null ? forceOpen : state.combo.panel.hidden;
    state.combo.panel.hidden = !open;
    state.combo.trigger.setAttribute("aria-expanded", String(open));
    if (open) {
      state.combo.search.value = "";
      filterComboOptions("");
      state.combo.search.focus();
    }
  }

  function selectCharacter(value, name) {
    state.filters.character = value;
    updateComboSelection();
    toggleCombo(false);
    state.combo.trigger.focus();
    render();
  }

  function updateComboSelection() {
    const current = state.filters.character;
    state.combo.label.textContent = current || "Tous les personnages";
    state.combo.list.querySelectorAll(".combo-option").forEach((opt) => {
      const val = opt.dataset.value || null;
      opt.setAttribute("aria-selected", String(val === current));
    });
  }

  // ---------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------
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
    el.resultCount.textContent = `${list.length} / ${state.pack.count}`;
  }

  function buildCard(sound) {
    const card = document.createElement("div");
    card.className = "sound" + (sound.file === state.playingFile ? " playing" : "");
    card.setAttribute("role", "button");
    card.tabIndex = 0;
    card.dataset.file = sound.file;
    card.title = sound.episode ? `${sound.title}\n${sound.episode}` : sound.title;
    if (sound.character) {
      card.style.setProperty("--char-color", `var(${charColorVar(sound.character)})`);
    }

    const isFav = state.favorites.has(sound.file);
    const playing = sound.file === state.playingFile;
    card.innerHTML = `
      <button type="button" class="fav-btn" aria-pressed="${isFav}"
              aria-label="Favori" title="Favori">${isFav ? "&#9733;" : "&#9734;"}</button>
      <span class="sound-title">${escapeHtml(sound.title)}</span>
      <span class="sound-meta">
        <span class="char-dot" aria-hidden="true"></span>
        <span class="sound-char">${escapeHtml(sound.character || "—")}</span>
        <span class="play-icon" aria-hidden="true">${playing ? "&#10074;&#10074;" : "&#9654;"}</span>
      </span>
      <span class="progress"></span>`;

    card.addEventListener("click", (ev) => {
      if (ev.target.closest(".fav-btn")) { toggleFavorite(sound.file); return; }
      play(sound);
    });
    card.addEventListener("keydown", (ev) => {
      if (ev.target !== card) return; // let the favorite button handle its own keys
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); play(sound); }
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

    state.audio.play().catch((err) => { log.error("playback error:", err); stopPlayback(); });
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
    const icon = card.querySelector(".play-icon");
    if (icon) icon.innerHTML = on ? "&#10074;&#10074;" : "&#9654;";
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
    if (state.filters.favOnly) { render(); return; }
    const card = el.board.querySelector(`.sound[data-file="${cssEscape(file)}"]`);
    const btn = card && card.querySelector(".fav-btn");
    if (btn) {
      const on = state.favorites.has(file);
      btn.setAttribute("aria-pressed", String(on));
      btn.innerHTML = on ? "&#9733;" : "&#9734;";
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

    document.addEventListener("click", (e) => {
      if (state.combo && !state.combo.panel.hidden && !el.charCombo.contains(e.target)) {
        toggleCombo(false);
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (state.combo && !state.combo.panel.hidden) { toggleCombo(false); state.combo.trigger.focus(); }
        else stopPlayback();
      }
      if (e.key === "/" && document.activeElement !== el.search) {
        e.preventDefault();
        el.search.focus();
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
  function charColorVar(name) {
    let h = 0;
    for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
    return CHAR_PALETTE[h % CHAR_PALETTE.length];
  }
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
