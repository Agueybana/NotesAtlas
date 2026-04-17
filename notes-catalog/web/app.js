const state = {
  search: "",
  category: "",
  subcategory: "",
  page: 1,
  pageSize: 120,
  hasMore: false,
  categories: [],
  notes: [],
  syncStatus: {},
  moveTarget: null,
  suggestTarget: null,
  activeMenuNoteId: null,
};

const els = {
  searchInput: document.getElementById("searchInput"),
  syncButton: document.getElementById("syncButton"),
  addCategoryButton: document.getElementById("addCategoryButton"),
  clearFiltersButton: document.getElementById("clearFiltersButton"),
  categoryTree: document.getElementById("categoryTree"),
  notesList: document.getElementById("notesList"),
  loadMoreButton: document.getElementById("loadMoreButton"),
  syncPhase: document.getElementById("syncPhase"),
  syncMessage: document.getElementById("syncMessage"),
  syncProgress: document.getElementById("syncProgress"),
  resultsTitle: document.getElementById("resultsTitle"),
  resultsSummary: document.getElementById("resultsSummary"),
  statTotal: document.getElementById("statTotal"),
  statVisible: document.getElementById("statVisible"),
  statFilter: document.getElementById("statFilter"),
  categoryDialog: document.getElementById("categoryDialog"),
  categoryForm: document.getElementById("categoryForm"),
  categoryNameInput: document.getElementById("categoryNameInput"),
  subcategoryNameInput: document.getElementById("subcategoryNameInput"),
  cancelCategoryButton: document.getElementById("cancelCategoryButton"),
  moveDialog: document.getElementById("moveDialog"),
  moveForm: document.getElementById("moveForm"),
  moveDialogTitle: document.getElementById("moveDialogTitle"),
  moveCategorySelect: document.getElementById("moveCategorySelect"),
  moveSubcategorySelect: document.getElementById("moveSubcategorySelect"),
  cancelMoveButton: document.getElementById("cancelMoveButton"),
  suggestDialog: document.getElementById("suggestDialog"),
  suggestDialogTitle: document.getElementById("suggestDialogTitle"),
  suggestionsList: document.getElementById("suggestionsList"),
  closeSuggestButton: document.getElementById("closeSuggestButton"),
  toast: document.getElementById("toast"),
};


async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}


function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    els.toast.classList.remove("is-visible");
  }, 3200);
}


function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}


function updateSyncCard(syncStatus) {
  state.syncStatus = syncStatus || {};
  const phase = syncStatus.phase || "idle";
  els.syncPhase.textContent = phase === "done" ? "Done" : phase.charAt(0).toUpperCase() + phase.slice(1);
  els.syncMessage.textContent = syncStatus.error || syncStatus.message || "Waiting to sync.";

  const total = Number(syncStatus.total || 0);
  const current = Number(syncStatus.current || 0);
  const percent = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : syncStatus.running ? 20 : 0;
  els.syncProgress.style.width = `${percent}%`;
  els.syncButton.disabled = Boolean(syncStatus.running);
  els.syncButton.textContent = syncStatus.running ? "Syncing…" : "Sync notes";
}


function renderCategoryTree(categories) {
  els.categoryTree.innerHTML = "";
  categories.forEach((category) => {
    const wrapper = document.createElement("div");
    wrapper.className = "category-item";

    const topButton = document.createElement("button");
    topButton.type = "button";
    topButton.className = state.category === category.name && !state.subcategory ? "is-active" : "";
    topButton.innerHTML = `
      <div class="note-header">
        <div>
          <strong>${category.name}</strong>
          <small>All subcategories</small>
        </div>
        <span class="count">${category.count}</span>
      </div>
    `;
    topButton.addEventListener("click", () => {
      state.category = category.name;
      state.subcategory = "";
      state.page = 1;
      loadState();
    });
    wrapper.appendChild(topButton);

    const subList = document.createElement("div");
    subList.className = "subcategory-list";
    category.subcategories
      .filter((sub) => sub.count > 0 || sub.name === "General")
      .forEach((sub) => {
        const subButton = document.createElement("button");
        subButton.type = "button";
        if (state.category === category.name && state.subcategory === sub.name) {
          subButton.classList.add("is-active");
        }
        subButton.innerHTML = `<span>${sub.name}</span><span class="count">${sub.count}</span>`;
        subButton.addEventListener("click", () => {
          state.category = category.name;
          state.subcategory = sub.name;
          state.page = 1;
          loadState();
        });
        subList.appendChild(subButton);
      });
    wrapper.appendChild(subList);
    els.categoryTree.appendChild(wrapper);
  });
}


function filterLabel() {
  if (state.category && state.subcategory) return `${state.category} / ${state.subcategory}`;
  if (state.category) return state.category;
  return "All";
}


function renderStats(payload) {
  els.resultsTitle.textContent = state.search ? `Results for “${state.search}”` : "All notes";
  els.resultsSummary.textContent =
    "Search, filter, and refine the catalog locally. Clicking any note reopens it in Apple Notes.";
  els.statTotal.textContent = payload.total_notes.toLocaleString();
  els.statVisible.textContent = state.notes.length.toLocaleString();
  els.statFilter.textContent = filterLabel();
}


async function openNote(noteId) {
  try {
    await fetchJSON("/api/open", {
      method: "POST",
      body: JSON.stringify({ note_id: noteId }),
    });
  } catch (error) {
    showToast(error.message);
  }
}


function closeMenus() {
  state.activeMenuNoteId = null;
  document.querySelectorAll(".note-card.menu-open").forEach((card) => card.classList.remove("menu-open"));
  document.querySelectorAll(".menu").forEach((menu) => menu.remove());
}


function isSuggestable(note) {
  return note.category === "Uncategorized";
}


function buildMenu(note, anchor) {
  closeMenus();
  state.activeMenuNoteId = note.note_id;
  const card = anchor.closest(".note-card");
  card.classList.add("menu-open");
  const menu = document.createElement("div");
  menu.className = "menu";

  const openButton = document.createElement("button");
  openButton.type = "button";
  openButton.textContent = "Open in Notes";
  openButton.addEventListener("click", () => {
    openNote(note.note_id);
    closeMenus();
  });

  const moveButton = document.createElement("button");
  moveButton.type = "button";
  moveButton.textContent = "Move to category";
  moveButton.addEventListener("click", () => {
    state.moveTarget = note;
    openMoveDialog();
    closeMenus();
  });

  menu.append(openButton, moveButton);
  if (isSuggestable(note)) {
    const suggestButton = document.createElement("button");
    suggestButton.type = "button";
    suggestButton.textContent = "Suggest category";
    suggestButton.addEventListener("click", async () => {
      closeMenus();
      await openSuggestDialog(note);
    });
    menu.appendChild(suggestButton);
  }
  card.appendChild(menu);

  const dismiss = (event) => {
    if (!menu.contains(event.target) && event.target !== anchor) {
      closeMenus();
      document.removeEventListener("click", dismiss);
    }
  };
  window.setTimeout(() => document.addEventListener("click", dismiss), 0);
}


function renderSuggestionList(payload) {
  els.suggestionsList.innerHTML = "";
  const suggestions = payload.suggestions || [];
  if (!suggestions.length) {
    els.suggestionsList.innerHTML = `<div class="suggestion-empty">No category suggestions were available for this note yet.</div>`;
    return;
  }

  suggestions.forEach((suggestion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggestion-option";
    button.innerHTML = `
      <strong>${suggestion.category}</strong>
      <span>${suggestion.subcategory}</span>
      <small>${suggestion.reason}</small>
    `;
    button.addEventListener("click", async () => {
      if (!state.suggestTarget) return;
      const approved = window.confirm(
        `Move "${state.suggestTarget.generated_title}" to ${suggestion.category} / ${suggestion.subcategory}?`,
      );
      if (!approved) return;
      await fetchJSON("/api/assign", {
        method: "POST",
        body: JSON.stringify({
          note_id: state.suggestTarget.note_id,
          category: suggestion.category,
          subcategory: suggestion.subcategory,
        }),
      });
      els.suggestDialog.close();
      showToast("Note moved locally");
      state.page = 1;
      await loadState();
    });
    els.suggestionsList.appendChild(button);
  });
}


async function openSuggestDialog(note) {
  state.suggestTarget = note;
  els.suggestDialogTitle.textContent = note.generated_title;
  els.suggestionsList.innerHTML = `<div class="suggestion-loading">Loading suggestions…</div>`;
  els.suggestDialog.showModal();
  try {
    const payload = await fetchJSON("/api/suggest-category", {
      method: "POST",
      body: JSON.stringify({ note_id: note.note_id }),
    });
    renderSuggestionList(payload);
  } catch (error) {
    els.suggestionsList.innerHTML = `<div class="suggestion-empty">${error.message}</div>`;
  }
}


function renderNotes(notes) {
  els.notesList.innerHTML = "";
  if (!notes.length) {
    els.notesList.innerHTML = `<div class="empty-state">No notes match the current filters yet.</div>`;
    return;
  }

  notes.forEach((note) => {
    const article = document.createElement("article");
    article.className = "note-card";
    article.innerHTML = `
      <div class="note-header">
        <button class="card-link" type="button">
          <h4 class="note-title">${note.generated_title}</h4>
          ${note.original_name && note.original_name !== note.generated_title ? `<div class="note-original">Original: ${note.original_name}</div>` : ""}
          <div class="note-preview">${note.preview_text || "No preview available."}</div>
          <div class="note-meta">
            <div class="note-tags">
              <span class="pill pill-accent">${note.category}</span>
              <span class="pill">${note.subcategory}</span>
            </div>
            <div class="meta-copy">${formatDate(note.modified_at)} · ${note.folder_name}</div>
          </div>
        </button>
        <button class="ellipsis" type="button" aria-label="More actions">...</button>
      </div>
    `;

    article.querySelector(".card-link").addEventListener("click", () => openNote(note.note_id));
    article.querySelector(".ellipsis").addEventListener("click", (event) => {
      event.stopPropagation();
      buildMenu(note, event.currentTarget);
    });
    els.notesList.appendChild(article);
  });
}


function renderPayload(payload, append = false) {
  state.categories = payload.categories || [];
  state.hasMore = Boolean(payload.has_more);
  if (append) {
    state.notes = [...state.notes, ...(payload.notes || [])];
  } else {
    state.notes = payload.notes || [];
  }
  renderCategoryTree(state.categories);
  renderStats(payload);
  updateSyncCard(payload.sync_status || {});
  renderNotes(state.notes);
  els.loadMoreButton.style.display = state.hasMore ? "inline-flex" : "none";
}


async function loadState({ append = false } = {}) {
  const params = new URLSearchParams({
    search: state.search,
    category: state.category,
    subcategory: state.subcategory,
    page: String(state.page),
    page_size: String(state.pageSize),
  });
  const payload = await fetchJSON(`/api/state?${params.toString()}`);
  renderPayload(payload, append);
}


function categoryMap() {
  return Object.fromEntries(state.categories.map((entry) => [entry.name, entry.subcategories.map((sub) => sub.name)]));
}


function syncMoveSubcategories() {
  const selectedCategory = els.moveCategorySelect.value;
  const subcategories = categoryMap()[selectedCategory] || ["General"];
  els.moveSubcategorySelect.innerHTML = "";
  subcategories.forEach((subcategory) => {
    const option = document.createElement("option");
    option.value = subcategory;
    option.textContent = subcategory;
    els.moveSubcategorySelect.appendChild(option);
  });
}


function openMoveDialog() {
  if (!state.moveTarget) return;
  els.moveDialogTitle.textContent = state.moveTarget.generated_title;
  els.moveCategorySelect.innerHTML = "";
  state.categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.name;
    option.textContent = category.name;
    els.moveCategorySelect.appendChild(option);
  });
  els.moveCategorySelect.value = state.moveTarget.category;
  syncMoveSubcategories();
  els.moveSubcategorySelect.value = state.moveTarget.subcategory;
  els.moveDialog.showModal();
}


async function createCategory(event) {
  event.preventDefault();
  const category = els.categoryNameInput.value.trim();
  const subcategory = els.subcategoryNameInput.value.trim();
  if (!category) return;
  await fetchJSON("/api/categories", {
    method: "POST",
    body: JSON.stringify({ category, subcategory }),
  });
  els.categoryDialog.close();
  els.categoryForm.reset();
  showToast("Category saved");
  state.page = 1;
  await loadState();
}


async function moveNote(event) {
  event.preventDefault();
  if (!state.moveTarget) return;
  await fetchJSON("/api/assign", {
    method: "POST",
    body: JSON.stringify({
      note_id: state.moveTarget.note_id,
      category: els.moveCategorySelect.value,
      subcategory: els.moveSubcategorySelect.value,
    }),
  });
  els.moveDialog.close();
  showToast("Note moved locally");
  state.page = 1;
  await loadState();
}


async function triggerSync() {
  const payload = await fetchJSON("/api/sync", { method: "POST", body: "{}" });
  updateSyncCard(payload.sync_status || {});
  showToast(payload.started ? "Sync started" : "Sync already running");
}


let syncPollHandle = null;
function startSyncPolling() {
  if (syncPollHandle) return;
  syncPollHandle = window.setInterval(async () => {
    const status = await fetchJSON("/api/status");
    updateSyncCard(status);
    if (!status.running) {
      window.clearInterval(syncPollHandle);
      syncPollHandle = null;
      await loadState();
    }
  }, 2500);
}


function wireEvents() {
  let searchTimer = null;
  els.searchInput.addEventListener("input", (event) => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      state.search = event.target.value.trim();
      state.page = 1;
      loadState();
    }, 220);
  });

  els.syncButton.addEventListener("click", async () => {
    await triggerSync();
    startSyncPolling();
  });

  els.addCategoryButton.addEventListener("click", () => {
    els.categoryDialog.showModal();
  });

  els.clearFiltersButton.addEventListener("click", () => {
    state.search = "";
    state.category = "";
    state.subcategory = "";
    state.page = 1;
    els.searchInput.value = "";
    loadState();
  });

  els.loadMoreButton.addEventListener("click", async () => {
    state.page += 1;
    await loadState({ append: true });
  });

  els.categoryForm.addEventListener("submit", (event) => {
    createCategory(event).catch((error) => showToast(error.message));
  });
  els.cancelCategoryButton.addEventListener("click", () => els.categoryDialog.close());

  els.moveCategorySelect.addEventListener("change", syncMoveSubcategories);
  els.moveForm.addEventListener("submit", (event) => {
    moveNote(event).catch((error) => showToast(error.message));
  });
  els.cancelMoveButton.addEventListener("click", () => els.moveDialog.close());
  els.closeSuggestButton.addEventListener("click", () => els.suggestDialog.close());
  els.suggestDialog.addEventListener("close", () => {
    state.suggestTarget = null;
  });
}


async function init() {
  wireEvents();
  const payload = await fetchJSON("/api/state");
  renderPayload(payload);
  if (payload.sync_status?.running) {
    startSyncPolling();
  }
}


init().catch((error) => {
  showToast(error.message);
});
