/* Cleanup Center: virtualized, searchable, filterable file browser.
 * Handles two independently virtualized lists:
 *   - Duplicate groups (variable row height - a group's row grows when expanded
 *     to show its extra copies inline).
 *   - Everything else (temp/cache, old downloads, large files, unknown) as one
 *     flat, fixed-row-height list - clicking a row opens the side panel instead
 *     of expanding inline, since individual files don't have children to show.
 * Both stay responsive at 50,000+ records because only the visible slice (plus
 * a small buffer) is ever present in the DOM; everything else is just an
 * offset into an array.
 */
(function () {
  "use strict";

  const ROW_H = 40;
  const GROUP_H = 60;
  const EXTRA_H = 34;
  const BUFFER = 6;

  let RAW = null;          // full payload from /cleanup/data
  let allItems = [];       // flat items: temp_cache/old_download/large_file/unknown
  let allGroups = [];      // duplicate groups
  let filteredItems = [];
  let filteredGroups = [];
  const expandedGroups = new Set();
  const selected = new Set(); // ids of selected items (file ids or "group:extraId")
  let sortKey = "size_desc";

  function humanSize(n) {
    n = Number(n);
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return (i === 0 ? Math.round(n) : n.toFixed(1)) + " " + units[i];
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function shortPath(p, keep) {
    keep = keep || 60;
    if (!p || p.length <= keep) return p || "";
    const head = p.slice(0, Math.floor(keep / 2) - 2);
    const tail = p.slice(-(Math.floor(keep / 2) - 1));
    return head + "..." + tail;
  }

  /* ------------------------------ file-type icons -------------------------- */
  const EXT_ICON_MAP = {
    doc: ["txt", "pdf", "doc", "docx", "rtf", "odt", "md", "csv", "xls", "xlsx", "ppt", "pptx"],
    image: ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "heic", "ico", "tiff"],
    video: ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"],
    audio: ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"],
    archive: ["zip", "rar", "7z", "tar", "gz", "bz2", "iso"],
    code: ["py", "js", "ts", "java", "c", "cpp", "cs", "html", "css", "json", "xml", "sh", "go", "rs"],
    exe: ["exe", "msi", "bat", "cmd", "dll", "sys"],
  };
  const EXT_TO_KIND = {};
  Object.keys(EXT_ICON_MAP).forEach((kind) => EXT_ICON_MAP[kind].forEach((ext) => { EXT_TO_KIND[ext] = kind; }));
  const ICON_BODIES = {
    doc: '<path d="M5 2.5h6l4 4v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1z"/><path d="M11 2.5v4h4"/><line x1="6.5" y1="11" x2="13.5" y2="11"/><line x1="6.5" y1="14" x2="13.5" y2="14"/>',
    image: '<rect x="3" y="4" width="14" height="12" rx="1.2"/><circle cx="7" cy="8" r="1.3"/><path d="M4 14.5l3.5-3.8 2.5 2.5 3.5-4.2 3.5 5"/>',
    video: '<rect x="3" y="4" width="14" height="12" rx="1.2"/><polygon points="8,7.8 8,12.2 12,10"/>',
    audio: '<circle cx="6.5" cy="15" r="2"/><circle cx="14.5" cy="13" r="2"/><path d="M8.5 15V4.5l8-1.5v9"/>',
    archive: '<rect x="4" y="3" width="12" height="14" rx="1.2"/><line x1="10" y1="3" x2="10" y2="17" stroke-dasharray="1.6 1.6"/>',
    code: '<polyline points="7 6 2.5 10 7 14"/><polyline points="13 6 17.5 10 13 14"/>',
    exe: '<rect x="3" y="5" width="14" height="10" rx="2"/><circle cx="10" cy="10" r="2.4"/>',
    unknown: '<path d="M5 2.5h6l4 4v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1z"/><path d="M11 2.5v4h4"/>'
      + '<text x="10" y="15.5" text-anchor="middle" font-size="7" font-weight="700" fill="currentColor" stroke="none">?</text>',
    copies: '<rect x="3" y="5" width="10" height="12" rx="1" fill="var(--card-bg)"/><rect x="7" y="3" width="10" height="12" rx="1"/>',
    openFolder: '<path d="M3 6a1 1 0 0 1 1-1h4l1.5 2H16a1 1 0 0 1 1 1v1H5.5a1 1 0 0 0-1 .8L3 15V6z"/>'
      + '<path d="M3.6 15l1.5-6.2a1 1 0 0 1 1-.8H17a1 1 0 0 1 1 1.2l-1.5 5a1 1 0 0 1-1 .8H4.6a1 1 0 0 1-1-1z"/>',
  };
  function svgIcon(body, size) {
    size = size || 16;
    return `<svg width="${size}" height="${size}" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" `
      + `stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }
  function fileIconHtml(ext, size) {
    const clean = (ext || "").replace(/^\./, "").toLowerCase();
    const kind = EXT_TO_KIND[clean];
    return svgIcon(ICON_BODIES[kind] || ICON_BODIES.unknown, size);
  }
  const CHEVRON = '<polyline points="7 4 13 10 7 16"/>';

  /* ---------------- generic variable-height virtual list ---------------- */
  function makeVirtualList(container, spacer, getHeight, renderRow) {
    let items = [];
    let offsets = [];

    function recompute() {
      let y = 0;
      offsets = new Array(items.length + 1);
      for (let i = 0; i < items.length; i++) {
        offsets[i] = y;
        y += getHeight(items[i], i);
      }
      offsets[items.length] = y;
      spacer.style.height = y + "px";
    }

    function findStart(scrollTop) {
      // binary search for the last offset <= scrollTop
      let lo = 0, hi = items.length - 1, ans = 0;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (offsets[mid] <= scrollTop) { ans = mid; lo = mid + 1; } else { hi = mid - 1; }
      }
      return ans;
    }

    function render() {
      const scrollTop = container.scrollTop;
      const viewH = container.clientHeight || 400;
      spacer.innerHTML = "";
      if (!items.length) return { start: 0, end: 0, total: 0 };
      let start = Math.max(0, findStart(scrollTop) - BUFFER);
      let end = start;
      while (end < items.length && offsets[end] < scrollTop + viewH + BUFFER * ROW_H) end++;
      end = Math.min(items.length, end + BUFFER);
      const frag = document.createDocumentFragment();
      for (let i = start; i < end; i++) {
        const el = renderRow(items[i], i);
        el.style.position = "absolute";
        el.style.top = offsets[i] + "px";
        el.style.left = "0";
        el.style.right = "0";
        frag.appendChild(el);
      }
      spacer.appendChild(frag);
      return { start, end, total: items.length };
    }

    let onRangeChange = null;
    // Deliberately not requestAnimationFrame-gated: rAF only fires while the
    // tab is actively compositing, which stalls scroll updates in minimized/
    // occluded/background-throttled windows. A render here is cheap (it only
    // ever touches ~20-30 DOM nodes), so a plain scroll listener is both
    // simpler and more robust than rAF for this specific case.
    let pending = false;
    container.addEventListener("scroll", () => {
      if (pending) return;
      pending = true;
      setTimeout(() => {
        pending = false;
        const r = render();
        if (onRangeChange) onRangeChange(r);
      }, 16);
    });

    return {
      setItems(newItems) {
        items = newItems;
        recompute();
        const r = render();
        if (onRangeChange) onRangeChange(r);
      },
      refreshHeights() {
        recompute();
        const r = render();
        if (onRangeChange) onRangeChange(r);
      },
      onRange(fn) { onRangeChange = fn; },
    };
  }

  /* ---------------------------- filtering -------------------------------- */
  function readFilters() {
    return {
      q: (document.getElementById("f-search").value || "").toLowerCase().trim(),
      category: document.getElementById("f-category").value,
      risk: document.getElementById("f-risk").value,
      minMb: parseFloat(document.getElementById("f-minsize").value) || 0,
      maxMb: parseFloat(document.getElementById("f-maxsize").value) || Infinity,
      location: (document.getElementById("f-location").value || "").toLowerCase().trim(),
    };
  }

  let tierFilter = "all"; // "all" | "safe" | "review" - the beginner-mode tier tabs

  function itemMatches(it, f) {
    if (tierFilter !== "all" && it.tier !== tierFilter) return false;
    if (f.q && !it._search.includes(f.q)) return false;
    if (f.category !== "all" && f.category !== "duplicate" && it.category !== f.category) return false;
    if (f.category === "duplicate") return false; // items list never contains duplicates
    if (f.risk !== "all" && it.risk_level !== f.risk) return false;
    const mb = it.size / (1024 * 1024);
    if (mb < f.minMb || mb > f.maxMb) return false;
    if (f.location && !it.path.toLowerCase().includes(f.location)) return false;
    return true;
  }

  function groupMatches(g, f) {
    if (tierFilter === "review") return false; // duplicate extras are always "safe" tier
    if (f.category !== "all" && f.category !== "duplicate") return false;
    if (f.risk !== "all" && f.risk !== "low") return false; // duplicate extras are always "low" risk
    const mb = g.size / (1024 * 1024);
    if (mb < f.minMb || mb > f.maxMb) return false;
    if (f.location && !g._search_paths.includes(f.location)) return false;
    if (f.q && !g._search.includes(f.q)) return false;
    return true;
  }

  const SORTERS = {
    size_desc: (a, b) => b.size - a.size,
    size_asc: (a, b) => a.size - b.size,
    filename_asc: (a, b) => (a.filename || "").localeCompare(b.filename || ""),
    risk_desc: (a, b) => riskRank(b.risk_level) - riskRank(a.risk_level),
  };
  const GROUP_SORTERS = {
    size_desc: (a, b) => b.waste_bytes - a.waste_bytes,
    size_asc: (a, b) => a.waste_bytes - b.waste_bytes,
    filename_asc: (a, b) => (a.keeper.filename || "").localeCompare(b.keeper.filename || ""),
    count_desc: (a, b) => b.count - a.count,
    risk_desc: (a, b) => b.count - a.count,
  };
  function riskRank(r) { return r === "high" ? 3 : r === "medium" ? 2 : 1; }

  function applyAll() {
    const f = readFilters();
    filteredItems = allItems.filter((it) => itemMatches(it, f));
    filteredGroups = allGroups.filter((g) => groupMatches(g, f));
    const isort = SORTERS[sortKey] || SORTERS.size_desc;
    const gsort = GROUP_SORTERS[sortKey] || GROUP_SORTERS.size_desc;
    filteredItems.sort(isort);
    filteredGroups.sort(gsort);
    fileVList.setItems(filteredItems);
    groupVList.setItems(filteredGroups);
    updateSectionVisibility();
    updateBulkBar();
  }

  function updateSectionVisibility() {
    document.getElementById("dup-section").style.display = filteredGroups.length ? "" : "none";
    document.getElementById("dup-empty").style.display = (!allGroups.length) ? "" : "none";
    document.getElementById("files-empty").style.display = (filteredItems.length === 0) ? "" : "none";
  }

  let debounceTimer = null;
  window.onFilterChange = function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(applyAll, 120);
  };
  window.onSortChange = function () {
    sortKey = document.getElementById("f-sort").value;
    applyAll();
  };
  window.clearAllFilters = function () {
    document.getElementById("f-search").value = "";
    document.getElementById("f-category").value = "all";
    document.getElementById("f-risk").value = "all";
    document.getElementById("f-minsize").value = "";
    document.getElementById("f-maxsize").value = "";
    document.getElementById("f-location").value = "";
    document.getElementById("f-sort").value = "size_desc";
    sortKey = "size_desc";
    resetTierTabs();
    applyAll();
  };
  function resetTierTabs() {
    tierFilter = "all";
    document.querySelectorAll(".tier-tab").forEach((b) => b.classList.remove("active"));
    const allTab = document.querySelector('.tier-tab[data-tier="all"]');
    if (allTab) allTab.classList.add("active");
  }
  window.setTierFilter = function (tier, btn) {
    tierFilter = tier;
    document.querySelectorAll(".tier-tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    applyAll();
  };
  // Advanced Mode's own controls (category/risk/size/location/sort) and the
  // simple tier tabs are two different filtering vocabularies over the same
  // data - switching modes resets to "no filter" in the vocabulary being
  // hidden, so toggling back and forth never leaves an invisible filter
  // active that the visible controls don't explain.
  window.onAdvancedModeChange = function () {
    resetTierTabs();
    if (fileVList) applyAll();
  };

  /* ---------------------------- row rendering ----------------------------- */
  function isAdvanced() { return document.documentElement.getAttribute("data-advanced") === "true"; }

  function riskBadgeHtml(risk, conf) {
    const color = risk === "high" ? "var(--risk-high)" : risk === "medium" ? "var(--risk-med)" : "var(--risk-low)";
    return `<span class="risk-badge"><span class="risk-dot" style="background:${color}"></span>${esc(risk.toUpperCase())}</span><span class="conf">${conf}%</span>`;
  }
  function tierBadgeHtml(tier) {
    const safe = tier === "safe";
    const color = safe ? "var(--risk-low)" : "var(--risk-med)";
    const label = safe ? "Safe" : "Review";
    return `<span class="risk-badge"><span class="risk-dot" style="background:${color}"></span>${esc(label)}</span>`;
  }
  function statusBadgeHtml(risk, conf, tier) {
    return isAdvanced() ? riskBadgeHtml(risk, conf) : tierBadgeHtml(tier);
  }

  function renderFileRow(it) {
    const row = document.createElement("div");
    row.className = "vrow";
    row.dataset.id = it.id;
    const checked = selected.has(it.id) ? "checked" : "";
    // Checkbox/delete state is wired via addEventListener below, closing over
    // `it` directly - not via inline onclick/onchange with JSON.stringify(...)
    // embedded in an HTML attribute, which breaks the moment the value (a
    // Windows path, or an object containing one) contains a double quote:
    // JSON.stringify's own wrapping quotes collide with the attribute's
    // quotes and silently truncate the handler (this was the actual cause of
    // "selecting a second duplicate deselects the first" - the checkbox's
    // onchange was malformed and never ran, so toggleSelect was never called).
    row.innerHTML = `
      <label class="vcell vcell-check">
        <input type="checkbox" ${checked}>
      </label>
      <div class="vcell vcell-icon">${fileIconHtml(it.ext, 15)}</div>
      <div class="vcell vcell-path" title="${esc(it.path)}">${esc(shortPath(it.path, 64))}</div>
      <div class="vcell vcell-cat">${esc(catLabel(it.category))}</div>
      <div class="vcell vcell-size mono">${humanSize(it.size)}</div>
      <div class="vcell vcell-risk">${statusBadgeHtml(it.risk_level, it.confidence, it.tier)}</div>
      <div class="vcell vcell-actions">
        <button class="btn-del btn-open-file" title="Open in File Explorer">${svgIcon(ICON_BODIES.openFolder, 13)}</button>
        <button class="btn-del">Delete</button>
      </div>`;
    const checkLabel = row.querySelector(".vcell-check");
    const checkbox = row.querySelector('input[type=checkbox]');
    checkLabel.addEventListener("click", (ev) => ev.stopPropagation());
    checkbox.addEventListener("change", () => window.toggleSelect(it.id, checkbox.checked));
    const actionsCell = row.querySelector(".vcell-actions");
    actionsCell.addEventListener("click", (ev) => ev.stopPropagation());
    row.querySelector(".btn-open-file").addEventListener("click", function () { window.openPath(it.path); });
    row.querySelector(".btn-del:not(.btn-open-file)").addEventListener("click", function () { window.deleteOne(this, it); });
    row.addEventListener("click", () => openPanel(it));
    return row;
  }

  function catLabel(c) {
    return { temp_cache: "Temp/Cache", old_download: "Old Download", large_file: "Large File", unknown: "Unknown", duplicate: "Duplicate" }[c] || c;
  }

  function renderGroupRow(g) {
    const wrap = document.createElement("div");
    wrap.className = "vgroup";
    const expanded = expandedGroups.has(g.group_id);
    const header = document.createElement("div");
    header.className = "vgroup-header";
    header.innerHTML = `
      <span class="vgroup-caret${expanded ? " open" : ""}">${svgIcon(CHEVRON, 13)}</span>
      <span class="vcell-icon">${svgIcon(ICON_BODIES.copies, 15)}</span>
      <span class="vgroup-title"><b>${g.count} copies</b> &middot; ${humanSize(g.size)} each &middot; wastes <b>${humanSize(g.waste_bytes)}</b></span>
      <span class="vgroup-keeper" title="${esc(g.keeper.path)}">keeping ${esc(shortPath(g.keeper.path, 46))}</span>`;
    header.addEventListener("click", () => {
      if (expandedGroups.has(g.group_id)) expandedGroups.delete(g.group_id); else expandedGroups.add(g.group_id);
      groupVList.refreshHeights();
    });
    wrap.appendChild(header);
    if (expanded) {
      g.extras.forEach((e) => {
        const row = document.createElement("div");
        row.className = "vrow vrow-extra";
        const checked = selected.has(e.id) ? "checked" : "";
        row.innerHTML = `
          <label class="vcell vcell-check">
            <input type="checkbox" ${checked}>
          </label>
          <div class="vcell vcell-icon">${fileIconHtml(e.path.split(".").pop(), 15)}</div>
          <div class="vcell vcell-path" title="${esc(e.path)}">${esc(shortPath(e.path, 56))}</div>
          <div class="vcell vcell-size mono">${humanSize(e.size)}</div>
          <div class="vcell vcell-risk">${statusBadgeHtml("low", 95, "safe")}</div>
          <div class="vcell vcell-actions">
            <button class="btn-del btn-open-file" title="Open in File Explorer">${svgIcon(ICON_BODIES.openFolder, 13)}</button>
            <button class="btn-del">Delete</button>
          </div>`;
        const checkLabel = row.querySelector(".vcell-check");
        const checkbox = row.querySelector('input[type=checkbox]');
        checkLabel.addEventListener("click", (ev) => ev.stopPropagation());
        checkbox.addEventListener("change", () => window.toggleSelect(e.id, checkbox.checked));
        const actionsCell = row.querySelector(".vcell-actions");
        actionsCell.addEventListener("click", (ev) => ev.stopPropagation());
        row.querySelector(".btn-open-file").addEventListener("click", function () { window.openPath(e.path); });
        row.querySelector(".btn-del:not(.btn-open-file)").addEventListener("click", function () { window.deleteOne(this, e); });
        row.addEventListener("click", () => openPanel(e));
        wrap.appendChild(row);
      });
    }
    return wrap;
  }

  /* ------------------------------ side panel ------------------------------ */
  function openPanel(it) {
    const panel = document.getElementById("side-panel");
    document.getElementById("panel-path").textContent = it.path;
    document.getElementById("panel-filename").textContent = it.filename || it.path.split("\\").pop();
    document.getElementById("panel-size").textContent = humanSize(it.size);
    document.getElementById("panel-cat").textContent = catLabel(it.category || "duplicate");
    document.getElementById("panel-risk").innerHTML = statusBadgeHtml(it.risk_level || "low", it.confidence || 95, it.tier || "safe");
    document.getElementById("panel-reason").textContent = it.simple_label || it.reason || "";
    document.getElementById("panel-reason-technical").textContent = it.reason || "";
    document.getElementById("panel-age").textContent = it.age_label || "";
    const delBtn = document.getElementById("panel-delete-btn");
    delBtn.disabled = false;
    delBtn.textContent = "Delete";
    delBtn.onclick = () => window.deleteOne(delBtn, it, closePanel);
    const openBtn = document.getElementById("panel-open-btn");
    openBtn.onclick = () => window.openPath(it.path);
    panel.classList.add("open");
  }
  window.closePanel = function () { document.getElementById("side-panel").classList.remove("open"); };
  function closePanel() { window.closePanel(); }

  /* -------------------------------- toast ----------------------------------- */
  let toastTimer = null;
  function showToast(message, actionLabel, actionFn, duration) {
    const toast = document.getElementById("toast");
    document.getElementById("toast-msg").textContent = message;
    const btn = document.getElementById("toast-action");
    if (actionLabel && actionFn) {
      btn.style.display = "";
      btn.textContent = actionLabel;
      btn.onclick = () => { hideToast(); actionFn(); };
    } else {
      btn.style.display = "none";
      btn.onclick = null;
    }
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, duration || 6000);
  }
  function hideToast() {
    document.getElementById("toast").classList.remove("show");
  }

  async function restorePath(path) {
    try {
      const res = await fetch(window.CLEANUP_URLS.restoreUrl, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }),
      });
      const data = await res.json();
      if (data.success) showToast("Restored " + (path.split("\\").pop()));
      else showToast("Could not restore: " + data.reason);
    } catch (e) {
      showToast("Restore request failed: " + e);
    }
  }

  /* ------------------------------ selection -------------------------------- */
  window.toggleSelect = function (id, checked) {
    if (checked) selected.add(id); else selected.delete(id);
    updateBulkBar();
  };
  window.selectAllFiltered = function () {
    filteredItems.forEach((it) => selected.add(it.id));
    fileVList.refreshHeights();
    updateBulkBar();
  };
  window.selectAllDuplicates = function () {
    if (!filteredGroups.length) return;
    filteredGroups.forEach((g) => { g.extras.forEach((e) => selected.add(e.id)); });
    groupVList.refreshHeights();
    updateBulkBar();
  };
  window.deleteAllDuplicates = function () {
    if (!filteredGroups.length) return;
    filteredGroups.forEach((g) => { g.extras.forEach((e) => selected.add(e.id)); });
    groupVList.refreshHeights();
    updateBulkBar();
    window.openBulkPreview();
  };
  window.cleanAllSafe = function () {
    let found = false;
    filteredItems.forEach((it) => { if (it.tier === "safe") { selected.add(it.id); found = true; } });
    filteredGroups.forEach((g) => { g.extras.forEach((e) => { selected.add(e.id); found = true; }); });
    if (!found) { showToast("No safe-to-remove items match your current view."); return; }
    fileVList.refreshHeights();
    groupVList.refreshHeights();
    updateBulkBar();
    window.openBulkPreview();
  };
  window.openPath = async function (path) {
    try {
      const res = await fetch(window.CLEANUP_URLS.openUrl, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }),
      });
      const data = await res.json();
      if (!data.success) showToast("Could not open: " + data.reason);
    } catch (e) {
      showToast("Open request failed: " + e);
    }
  };
  function updateBulkBar() {
    const bar = document.getElementById("bulk-bar");
    if (selected.size > 0) {
      bar.style.display = "flex";
      document.getElementById("bulk-count").textContent = selected.size + " selected";
      let total = 0;
      selected.forEach((id) => { const it = findItemById(id); if (it) total += it.size || 0; });
      document.getElementById("bulk-reclaim-amt").textContent = humanSize(total);
    } else {
      bar.style.display = "none";
    }
  }
  window.clearSelection = function () {
    selected.clear();
    fileVList.refreshHeights();
    groupVList.refreshHeights();
    updateBulkBar();
  };

  /* ------------------------------- delete ---------------------------------- */
  // opts.skipConfirm: called from a bulk flow (bulkDelete) that already got
  // ONE confirmation via the Review Selected modal - don't ask again per
  // file, native-dialog or otherwise. Also implies override:true for
  // unknown-type items, since the user already saw the "N unrecognized-type
  // file(s)" note in that same modal before approving the batch.
  // opts.silent: suppress the per-item success toast during a bulk loop -
  // bulkDelete shows one summary toast for the whole batch instead.
  window.deleteOne = async function (btn, item, onDone, opts) {
    opts = opts || {};
    const requireTyped = item.category === "unknown";
    let override = requireTyped;
    if (!opts.skipConfirm) {
      let ok;
      if (requireTyped) {
        ok = await window.dsPrompt(
          item.path + (item.reason ? "\n\n" + item.reason : ""),
          "DELETE",
          { title: "Unrecognized file type - type DELETE to confirm", okLabel: "Delete" }
        );
      } else {
        ok = await window.dsConfirm(
          item.path + (item.reason ? "\n\n" + item.reason : ""),
          { title: "Send this to the Recycle Bin?", okLabel: "Delete", danger: true }
        );
      }
      if (!ok) return;
    } else {
      override = true;
    }
    if (btn) { btn.disabled = true; btn.textContent = "Deleting..."; }
    const payload = {
      path: item.path, category: item.category || "duplicate", reason: item.reason || "",
      risk_level: item.risk_level || "low", confidence: item.confidence || 95, confirm: true, override: override,
    };
    if (item.category === "duplicate" || item.group_id) {
      payload.category = "duplicate";
      payload.duplicate_keeper = item.duplicate_keeper || (findKeeperFor(item.group_id) || "");
    }
    try {
      const res = await fetch(window.CLEANUP_URLS.deleteUrl, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        removeItemEverywhere(item.id || item.path);
        if (onDone) onDone();
        if (!opts.silent) showToast("Sent to Recycle Bin: " + (item.filename || item.path.split("\\").pop()), "Undo", () => restorePath(item.path));
      } else if (data.already_gone) {
        // Nothing to clean up - the file was already off disk (e.g. removed
        // by another delete in the same batch, or by the app's own runtime
        // cleaning up a stale temp folder). Not a failure worth alarming
        // over: drop it from the list quietly instead of a red error.
        if (btn) { btn.disabled = false; btn.textContent = "Delete"; }
        removeItemEverywhere(item.id || item.path);
        if (onDone) onDone();
        if (!opts.silent) window.dsToast("Already removed - it's no longer on disk.", { duration: 5000 });
      } else {
        if (btn) { btn.disabled = false; btn.textContent = "Delete"; }
        if (!opts.silent) window.dsToast("Not deleted: " + data.reason, { type: "error", duration: 9000 });
      }
      return data;
    } catch (e) {
      if (btn) { btn.disabled = false; btn.textContent = "Delete"; }
      window.dsToast("Request failed: " + e, { type: "error", duration: 9000 });
      return { success: false, reason: String(e) };
    }
  };

  function findKeeperFor(groupId) {
    const g = allGroups.find((g) => g.group_id === groupId);
    return g ? g.keeper.path : "";
  }

  function removeItemEverywhere(id) {
    allItems = allItems.filter((it) => it.id !== id);
    allGroups.forEach((g) => { g.extras = g.extras.filter((e) => e.id !== id); });
    allGroups = allGroups.filter((g) => g.extras.length > 0);
    selected.delete(id);
    applyAll();
  }

  /* ------------------------------ bulk preview ------------------------------ */
  const PREVIEW_LIST_CAP = 300;

  window.openBulkPreview = function () {
    if (!selected.size) return;
    const ids = Array.from(selected);
    const items = ids.map(findItemById).filter(Boolean);
    if (!items.length) return;

    let totalSize = 0, unknownCount = 0;
    items.forEach((it) => {
      totalSize += it.size || 0;
      if (it.category === "unknown") unknownCount++;
    });

    document.getElementById("preview-count").textContent = items.length;
    document.getElementById("preview-size").textContent = humanSize(totalSize);

    const noteEl = document.getElementById("preview-unknown-note");
    if (unknownCount > 0) {
      noteEl.style.display = "";
      noteEl.textContent = unknownCount + " of these are unrecognized-type file(s) - review the list above carefully, since confirming here approves them too.";
    } else {
      noteEl.style.display = "none";
    }

    const shown = items.slice(0, PREVIEW_LIST_CAP);
    const rows = shown.map((it) =>
      `<div class="modal-list-row"><span title="${esc(it.path)}">${esc(shortPath(it.path, 70))}</span><span>${humanSize(it.size)}</span></div>`
    ).join("");
    const more = items.length > PREVIEW_LIST_CAP
      ? `<div class="modal-more">+ ${items.length - PREVIEW_LIST_CAP} more not shown</div>` : "";
    document.getElementById("preview-list").innerHTML = rows + more;

    document.getElementById("preview-modal").classList.add("open");
  };

  window.closeBulkPreview = function () {
    document.getElementById("preview-modal").classList.remove("open");
  };

  window.confirmBulkPreview = function () {
    window.closeBulkPreview();
    window.bulkDelete();
  };

  window.bulkDelete = async function () {
    if (!selected.size) return;
    const ids = Array.from(selected);
    // skipped = already gone from disk, or locked by another running program -
    // not really failures, just nothing DriveSense could do. blocked = an
    // actual safety refusal (protected path, exclusion, etc).
    let done = 0, skipped = 0, blocked = 0, freed = 0;
    const deletedPaths = [];
    for (const id of ids) {
      const item = findItemById(id);
      if (!item) continue;
      document.getElementById("bulk-count").textContent = `Deleting ${done + 1} of ${ids.length}...`;
      const r = await window.deleteOne(null, item, undefined, { skipConfirm: true, silent: true });
      if (r && r.success) { done++; freed += item.size || 0; deletedPaths.push(item.path); }
      else if (r && (r.already_gone || r.locked)) { skipped++; }
      else { blocked++; }
    }
    selected.clear();
    updateBulkBar();
    const bits = [];
    if (skipped) bits.push(skipped + " skipped (already gone or in use elsewhere)");
    if (blocked) bits.push(blocked + " blocked");
    const summary = `${done} deleted, ${humanSize(freed)} freed` + (bits.length ? " (" + bits.join(", ") + ")" : "");
    if (done > 0) {
      showToast(summary, "Undo all", () => { deletedPaths.forEach((p) => restorePath(p)); }, 8000);
    } else {
      showToast(summary);
    }
  };

  function findItemById(id) {
    let it = allItems.find((x) => x.id === id);
    if (it) return it;
    for (const g of allGroups) {
      it = g.extras.find((e) => e.id === id);
      if (it) { it.duplicate_keeper = g.keeper.path; it.category = "duplicate"; return it; }
    }
    return null;
  }

  /* -------------------------------- init ----------------------------------- */
  let fileVList, groupVList;

  function buildSearchStrings() {
    allItems.forEach((it) => {
      it._search = [it.filename, it.path, it.ext, it.category].join(" ").toLowerCase();
    });
    allGroups.forEach((g) => {
      const paths = [g.keeper.path].concat(g.extras.map((e) => e.path)).join(" ").toLowerCase();
      g._search_paths = paths;
      g._search = [g.hash, g.group_id, paths].join(" ").toLowerCase();
    });
  }

  async function init() {
    const res = await fetch(window.CLEANUP_URLS.dataUrl);
    if (!res.ok) {
      document.getElementById("cleanup-loading").textContent = "No scan data yet.";
      return;
    }
    RAW = await res.json();
    allItems = RAW.items || [];
    allGroups = (RAW.duplicates && RAW.duplicates.groups) || [];
    buildSearchStrings();

    document.getElementById("cleanup-loading").style.display = "none";
    document.getElementById("cleanup-content").style.display = "";

    const fileContainer = document.getElementById("file-list");
    const fileSpacer = document.getElementById("file-spacer");
    fileVList = makeVirtualList(fileContainer, fileSpacer, () => ROW_H, renderFileRow);
    fileVList.onRange((r) => {
      document.getElementById("files-range").textContent = r.total
        ? `Showing ${r.total ? r.start + 1 : 0}-${r.end} of ${r.total}` : "No files match your filters.";
    });

    const groupContainer = document.getElementById("dup-list");
    const groupSpacer = document.getElementById("dup-spacer");
    groupVList = makeVirtualList(
      groupContainer, groupSpacer,
      (g) => GROUP_H + (expandedGroups.has(g.group_id) ? g.extras.length * EXTRA_H : 0),
      renderGroupRow
    );
    groupVList.onRange((r) => {
      document.getElementById("dup-range").textContent = r.total
        ? `Showing ${r.total ? r.start + 1 : 0}-${r.end} of ${r.total} groups` : "";
    });

    applyAll();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
