(() => {
  "use strict";

  const CHANNEL = "ycet-editor";
  const token = new URLSearchParams(location.search).get("token") || "";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = {
    workspace: null,
    currentFileId: null,
    selection: null,
    drafts: new Map(),
    selectMode: true,
    zoom: 100,
    pan: { x: 0, y: 0 },
    sidebarCollapsed: false,
    temporarySidebar: false,
    colorTarget: null,
    editingAnnotation: null,
    latestResultId: null,
    lastSha: new Map(),
    staleDrafts: new Set(),
    remotePanPoint: null,
    previewMetrics: null,
    transform: { rotation: 0, flipX: 1, flipY: 1 },
    effects: [],
    effectBase: { boxShadow: "", filter: "", backdropFilter: "" },
    activeEffectId: null,
    effectDraft: null,
    color: { h: 0, s: 0, v: 100 },
  };

  const els = {
    layout: $("#layout"), sidebar: $("#sidebar"), tree: $("#file-tree"), search: $("#file-search"),
    frame: $("#preview-frame"), shell: $("#preview-shell"), viewport: $("#canvas-viewport"), empty: $("#empty-state"),
    path: $("#current-path"), project: $("#project-name"), selectMode: $("#select-mode"), sync: $("#sync-pages"),
    selectedPath: $("#selected-path"), selectedName: $("#selected-name"), zoomValue: $("#zoom-value"), zoomInput: $("#zoom-input"),
    toast: $("#toast"), tooltip: $("#tooltip"), connectionDot: $("#connection-dot"), connectionCopy: $("#connection-copy"),
  };

  async function api(path, payload) {
    const response = await fetch(path, {
      method: payload === undefined ? "GET" : "POST",
      headers: { "X-YCET-Token": token, "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      cache: "no-store",
    });
    const body = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
  }

  function toast(copy, kind = "") {
    els.toast.textContent = copy;
    els.toast.className = `toast ${kind}`.trim();
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => els.toast.classList.add("hidden"), 3600);
  }

  function fileById(identifier) {
    return state.workspace?.files.find((item) => item.id === identifier) || null;
  }

  function draftFor(identifier, create = true) {
    if (!identifier) return null;
    if (!state.drafts.has(identifier) && create) state.drafts.set(identifier, { operations: [], annotations: [] });
    return state.drafts.get(identifier) || null;
  }

  function hasDraft(identifier) {
    const draft = draftFor(identifier, false);
    return Boolean(draft && (draft.operations.length || draft.annotations.length));
  }

  function dirtyIds() {
    return [...state.drafts.keys()].filter(hasDraft);
  }

  async function syncDirtyState() {
    try {
      await api("/api/session/drafts", { dirtyFileIds: dirtyIds() });
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function fingerprintKey(fingerprint) {
    return `${(fingerprint?.framePath || []).join(".")}|${fingerprint?.selector || ""}`;
  }

  function upsertOperation(identifier, operation, key) {
    const file = fileById(identifier);
    if (!file) {
      toast("该嵌套页面未登记到工作区，当前只能查看。", "warn");
      return;
    }
    const draft = draftFor(identifier);
    const index = draft.operations.findIndex((item) => item._key === key);
    operation.fileId = identifier;
    operation._key = key;
    if (index >= 0) draft.operations[index] = operation; else draft.operations.push(operation);
    renderTree();
    applyDrafts();
    updateCssSummary();
    syncDirtyState();
  }

  function postPreview(type, payload = {}) {
    els.frame.contentWindow?.postMessage({ channel: CHANNEL, version: 1, type, ...payload }, location.origin);
  }

  function operationsForPreview() {
    return [...state.drafts.values()].flatMap((draft) => draft.operations.filter((item) => !["sync-pages", "annotation"].includes(item.type)));
  }

  function annotationsForPreview() {
    return [...state.drafts.values()].flatMap((draft) => draft.annotations);
  }

  function applyDrafts() {
    postPreview("apply", { operations: operationsForPreview(), annotations: annotationsForPreview() });
  }

  function persistPreferences() {
    if (!state.workspace) return;
    const groups = state.workspace.groups || [];
    const assignments = Object.fromEntries(state.workspace.files.map((file) => [file.id, file.manualGroup || null]));
    const order = state.workspace.files.map((file) => file.id);
    const zoomByFile = { ...(state.workspace.zoomByFile || {}) };
    if (state.currentFileId) zoomByFile[state.currentFileId] = state.zoom;
    api("/api/workspace/preferences", { groups, assignments, order, currentFileId: state.currentFileId, zoomByFile })
      .then((workspace) => { state.workspace = workspace; })
      .catch((error) => toast(error.message, "error"));
  }

  function groupBuckets(files) {
    const manual = new Map((state.workspace.groups || []).map((group) => [group.id, { ...group, files: [], manual: true }]));
    const automatic = new Map();
    const root = [];
    for (const file of files) {
      if (file.manualGroup && manual.has(file.manualGroup)) manual.get(file.manualGroup).files.push(file);
      else if (file.automaticGroup) {
        if (!automatic.has(file.automaticGroup)) automatic.set(file.automaticGroup, { id: `auto:${file.automaticGroup}`, name: file.automaticGroup, files: [], manual: false });
        automatic.get(file.automaticGroup).files.push(file);
      } else root.push(file);
    }
    const groups = [...manual.values()].sort((a, b) => a.order - b.order);
    groups.push(...[...automatic.values()].sort((a, b) => a.name.localeCompare(b.name)));
    return { root, groups };
  }

  function iconButton(symbol, label, className = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `icon-button ${className}`.trim();
    button.setAttribute("aria-label", label);
    button.innerHTML = `<svg><use href="/assets/icons.svg#${symbol}" /></svg>`;
    return button;
  }

  function fileRow(file) {
    const row = document.createElement("div");
    row.className = `file-row${file.id === state.currentFileId ? " active" : ""}${hasDraft(file.id) ? " pending" : ""}`;
    row.dataset.fileId = file.id;
    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = file.name;
    const source = document.createElement("span");
    source.className = "source-badge";
    source.textContent = file.missing ? "缺失" : file.source === "external" ? "外部" : file.kind === "offline" ? "离线" : "";
    if (!source.textContent) source.classList.add("hidden");
    row.innerHTML = '<span class="file-icon" aria-hidden="true"></span>';
    row.append(name, source);
    row.addEventListener("click", () => selectFile(file.id));
    return row;
  }

  function groupNode(group) {
    const section = document.createElement("section");
    section.className = "file-group";
    section.dataset.groupId = group.id;
    const row = document.createElement("div");
    row.className = "group-row";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "group-toggle";
    toggle.innerHTML = `<span>${group.name}</span><span>${group.files.length}</span>`;
    toggle.addEventListener("click", () => section.classList.toggle("collapsed"));
    row.append(toggle);
    const files = document.createElement("div");
    files.className = "group-files";
    group.files.forEach((file) => files.append(fileRow(file)));
    section.append(row, files);
    return section;
  }

  function renderTree() {
    if (!state.workspace) return;
    const query = els.search.value.trim().toLocaleLowerCase();
    const files = state.workspace.files.filter((file) => `${file.name} ${file.path}`.toLocaleLowerCase().includes(query));
    const { root, groups } = groupBuckets(files);
    els.tree.replaceChildren(...root.map(fileRow), ...groups.map(groupNode));
  }

  function confirmAction(title, copy, action) {
    $("#confirm-title").textContent = title;
    $("#confirm-copy").textContent = copy;
    const button = $("#confirm-action");
    button.onclick = () => Promise.resolve(action()).catch((error) => toast(error.message, "error"));
    $("#confirm-dialog").showModal();
  }

  function selectFile(identifier, force = false) {
    const file = fileById(identifier);
    if (!file) {
      state.currentFileId = null;
      els.empty.classList.remove("hidden");
      els.shell.classList.add("hidden");
      return;
    }
    if (!force && state.currentFileId === identifier) return;
    state.currentFileId = identifier;
    state.selection = null;
    state.pan = { x: 0, y: 0 };
    state.previewMetrics = null;
    els.shell.style.removeProperty("width");
    state.zoom = Number(state.workspace.zoomByFile?.[identifier] || 100);
    els.path.textContent = file.path;
    els.empty.classList.toggle("hidden", !file.missing);
    els.shell.classList.toggle("hidden", file.missing);
    els.sync.classList.toggle("hidden", file.kind !== "runtime");
    const synced = draftFor(identifier, false)?.operations.some((item) => item.type === "sync-pages");
    els.sync.textContent = synced ? "已同步" : "同步 pages";
    els.sync.classList.toggle("synced", Boolean(synced));
    clearSelectionPanel();
    resizePreviewShell();
    updateZoom(false);
    if (!file.missing) els.frame.src = `/preview/${encodeURIComponent(identifier)}/?token=${encodeURIComponent(token)}&v=${Date.now()}`;
    renderTree();
    persistPreferences();
  }

  function clearSelectionPanel() {
    closeAnchoredPopovers();
    state.transform = { rotation: 0, flipX: 1, flipY: 1 };
    state.effects = [];
    state.effectBase = { boxShadow: "", filter: "", backdropFilter: "" };
    els.selectedPath.textContent = "尚未选择元素";
    els.selectedName.textContent = "选择预览中的组件";
    $("#text-fields").innerHTML = '<p class="muted">选择包含文本的元素后显示。</p>';
    $("#image-preview").removeAttribute("src");
    $("#image-preview").classList.add("hidden");
    $("#image-status").textContent = "选择本地图片作为待替换资源；发送前仅用于预览。";
    $("#css-property").value = "";
    $("#css-value").value = "";
    setValue("rotation", 0);
    $("#flip-x").classList.remove("pressed");
    $("#flip-y").classList.remove("pressed");
    renderEffects();
    updateCssSummary();
  }

  function number(value, fallback = 0) {
    const parsed = Number.parseFloat(String(value ?? "").replace(/[a-z%]+$/i, ""));
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function fontFamilyName(value) {
    return String(value || "").split(",", 1)[0].trim().replace(/^['"]|['"]$/g, "");
  }

  function fontCssValue(family) {
    return `"${String(family).replace(/["\\]/g, "\\$&")}", sans-serif`;
  }

  function mergeFontOptions(families) {
    const select = $("#font-family");
    const selectedName = fontFamilyName(select.value);
    const names = new Map();
    $$("option", select).forEach((option) => names.set(fontFamilyName(option.value).toLocaleLowerCase(), option.textContent));
    for (const family of families || []) {
      const name = String(family).trim();
      if (name) names.set(name.toLocaleLowerCase(), name);
    }
    const ordered = [...names.values()].sort((left, right) => left.localeCompare(right, undefined, { sensitivity: "base" }));
    select.replaceChildren();
    const system = new Option("System UI", "system-ui, sans-serif");
    select.add(system);
    ordered.filter((name) => name !== "System UI" && name.toLocaleLowerCase() !== "system-ui").forEach((name) => select.add(new Option(name, fontCssValue(name))));
    const match = [...select.options].find((option) => fontFamilyName(option.value).toLocaleLowerCase() === selectedName.toLocaleLowerCase());
    select.value = match?.value || system.value;
  }

  async function loadSystemFonts(includeBrowserFonts = false) {
    const result = await api("/api/fonts");
    const families = [...(result.families || [])];
    if (includeBrowserFonts && window.queryLocalFonts) {
      try {
        const localFonts = await window.queryLocalFonts();
        families.push(...localFonts.map((font) => font.family).filter(Boolean));
      } catch (_error) {
        toast("未获得浏览器本机字体权限，已保留系统字体清单。", "warn");
      }
    }
    mergeFontOptions([...new Set(families)]);
  }

  function setValue(id, value) {
    const input = $(`#${id}`);
    if (!input) return;
    const option = input.tagName === "SELECT" ? [...input.options].find((item) => (
      item.value === value || (id === "font-family" && fontFamilyName(item.value).toLocaleLowerCase() === fontFamilyName(value).toLocaleLowerCase())
    )) : null;
    input.value = option ? option.value : input.tagName === "SELECT" ? input.options[0]?.value || "" : value;
  }

  function parseTransform(value) {
    if (!value || value === "none") return { rotation: 0, flipX: 1, flipY: 1 };
    const direct = value.match(/rotate\((-?[\d.]+)deg\)\s*scale\((-?[\d.]+)\s*,\s*(-?[\d.]+)\)/);
    if (direct) return { rotation: number(direct[1]), flipX: Math.sign(number(direct[2], 1)) || 1, flipY: Math.sign(number(direct[3], 1)) || 1 };
    try {
      const matrix = new DOMMatrix(value);
      const scaleX = Math.hypot(matrix.a, matrix.b) || 1;
      return {
        rotation: Math.round(Math.atan2(matrix.b, matrix.a) * 180 / Math.PI * 100) / 100,
        flipX: 1,
        flipY: Math.sign((matrix.a * matrix.d - matrix.b * matrix.c) / scaleX) || 1,
      };
    } catch (_error) {
      return { rotation: 0, flipX: 1, flipY: 1 };
    }
  }

  function populateSelection(selection) {
    closeAnchoredPopovers();
    state.selection = selection;
    const style = selection.element.styles;
    const rect = selection.element.rect;
    els.selectedPath.textContent = selection.path || selection.fingerprint.selector;
    els.selectedName.textContent = selection.element.name;
    setValue("position-x", rect.x); setValue("position-y", rect.y);
    setValue("width", number(style.width, rect.width)); setValue("height", number(style.height, rect.height));
    const transformOperation = draftFor(selection.fileId, false)?.operations.find((item) => item.property === "transform" && fingerprintKey(item.fingerprint) === fingerprintKey(selection.fingerprint));
    state.transform = parseTransform(transformOperation?.value || style.transform);
    setValue("rotation", state.transform.rotation);
    $("#flip-x").classList.toggle("pressed", state.transform.flipX < 0);
    $("#flip-y").classList.toggle("pressed", state.transform.flipY < 0);
    setValue("opacity", Math.round(number(style.opacity, 1) * 100));
    setValue("radius-tl", number(style.borderTopLeftRadius)); setValue("radius-tr", number(style.borderTopRightRadius));
    setValue("radius-bl", number(style.borderBottomLeftRadius)); setValue("radius-br", number(style.borderBottomRightRadius));
    setValue("radius-all", number(style.borderTopLeftRadius)); setValue("font-family", style.fontFamily);
    setValue("font-weight", style.fontWeight); setValue("font-size", number(style.fontSize));
    setValue("line-height", style.lineHeight === "normal" ? 1.2 : number(style.lineHeight) / Math.max(1, number(style.fontSize)));
    setValue("letter-spacing", style.letterSpacing === "normal" ? 0 : number(style.letterSpacing));
    setValue("border-width", number(style.borderWidth)); setValue("border-style", style.borderStyle);
    setValue("flex-direction", style.flexDirection); setValue("justify-content", style.justifyContent); setValue("align-items", style.alignItems); setValue("gap", number(style.gap));
    $("#layout-context").classList.toggle("hidden", !["flex", "grid"].includes(style.display));
    $$(".alignment button").forEach((button) => button.classList.toggle("active", button.dataset.align === style.textAlign));
    updateColorButtons(style);
    setValue("fill-opacity", Math.round(parseColor(style.backgroundColor).a * 100));
    const parsedEffects = parseEffects(style);
    state.effects = parsedEffects.items;
    state.effectBase = parsedEffects.base;
    renderEffects();
    renderTextFields(selection.element.textFields || []);
    const imageOperation = draftFor(selection.fileId, false)?.operations.find((item) => item.type === "image-replace" && fingerprintKey(item.fingerprint) === fingerprintKey(selection.fingerprint));
    $("#image-preview").classList.toggle("hidden", !imageOperation);
    if (imageOperation) $("#image-preview").src = imageOperation.previewUrl;
    else $("#image-preview").removeAttribute("src");
    $("#image-status").textContent = selection.element.tag === "img" ? (imageOperation ? `待替换：${imageOperation.name}` : `当前图片：${selection.element.imageSource || "未设置"}`) : "当前元素不是图片；选择图片元素后可替换。";
    $("#css-property").value = "";
    $("#css-value").value = "";
  }

  function updateColorButtons(styles) {
    $$("[data-color-property]").forEach((button) => {
      const property = button.dataset.colorProperty;
      const key = property.replace(/-([a-z])/g, (_match, char) => char.toUpperCase());
      const color = styles[key] || (property === "background-color" ? styles.backgroundColor : "#ffffff");
      button.dataset.color = color;
      $("span", button).style.background = color;
      $("em", button).textContent = color;
    });
  }

  function renderTextFields(fields) {
    const root = $("#text-fields");
    root.replaceChildren();
    if (!fields.length) {
      root.innerHTML = '<p class="muted">当前元素不包含可编辑文本。</p>';
      return;
    }
    fields.forEach((field, index) => {
      const label = document.createElement("label");
      label.textContent = `文本 ${index + 1}`;
      const input = document.createElement("textarea");
      input.rows = 2;
      input.value = field.value;
      input.addEventListener("input", () => {
        if (!state.selection) return;
        const key = `text:${fingerprintKey(state.selection.fingerprint)}:${field.index}`;
        upsertOperation(state.selection.fileId, { type: "text", fingerprint: state.selection.fingerprint, index: field.index, value: input.value, original: field.value }, key);
      });
      label.append(input);
      root.append(label);
    });
  }

  function styleOperation(property, value) {
    if (!state.selection) return;
    const key = `style:${fingerprintKey(state.selection.fingerprint)}:${property}`;
    upsertOperation(state.selection.fileId, { type: "style", fingerprint: state.selection.fingerprint, property, value: String(value) }, key);
  }

  function bindPropertyInputs() {
    $$('[data-css]').forEach((input) => {
      input.addEventListener("input", () => {
        let value = input.value;
        if (["position-x", "position-y"].includes(input.id) && state.selection) {
          const axis = input.id === "position-x" ? "x" : "y";
          const position = state.selection.element.styles.position;
          if (position === "static" || position === "relative") {
            if (position === "static") styleOperation("position", "relative");
            value = `${number(input.value) - state.selection.element.rect[axis]}px`;
          } else {
            value = `${input.value}px`;
          }
          styleOperation(input.dataset.css, value);
          return;
        }
        if (input.type === "number") {
          if (input.id === "opacity") value = String(number(value) / 100);
          else if (input.id === "line-height") value = String(value);
          else value = `${value}px`;
        }
        styleOperation(input.dataset.css, value);
      });
    });
    $("#radius-all").addEventListener("input", (event) => {
      ["border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius", "border-bottom-right-radius"].forEach((property) => styleOperation(property, `${event.target.value}px`));
      ["radius-tl", "radius-tr", "radius-bl", "radius-br"].forEach((id) => setValue(id, event.target.value));
    });
    $("#link-radius").addEventListener("click", (event) => {
      const active = event.currentTarget.getAttribute("aria-pressed") !== "true";
      event.currentTarget.setAttribute("aria-pressed", String(active));
      event.currentTarget.classList.toggle("pressed", active);
    });
    $$(".corner-grid input").forEach((input) => input.addEventListener("input", () => {
      if ($("#link-radius").getAttribute("aria-pressed") !== "true") return;
      ["radius-tl", "radius-tr", "radius-bl", "radius-br"].forEach((id) => { if (id !== input.id) setValue(id, input.value); });
      ["border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius", "border-bottom-right-radius"].forEach((property) => styleOperation(property, `${input.value}px`));
    }));
    $$(".alignment button").forEach((button) => button.addEventListener("click", () => {
      $$(".alignment button").forEach((item) => item.classList.toggle("active", item === button));
      styleOperation("text-align", button.dataset.align);
    }));
    const applyTransform = () => styleOperation("transform", `rotate(${state.transform.rotation}deg) scale(${state.transform.flipX}, ${state.transform.flipY})`);
    $("#rotation").addEventListener("input", (event) => { state.transform.rotation = number(event.target.value); applyTransform(); });
    $("#rotate-90").addEventListener("click", () => { state.transform.rotation = (state.transform.rotation + 90) % 360; setValue("rotation", state.transform.rotation); applyTransform(); });
    $("#flip-x").addEventListener("click", () => { state.transform.flipX *= -1; $("#flip-x").classList.toggle("pressed", state.transform.flipX < 0); applyTransform(); });
    $("#flip-y").addEventListener("click", () => { state.transform.flipY *= -1; $("#flip-y").classList.toggle("pressed", state.transform.flipY < 0); applyTransform(); });
    $("#fill-opacity").addEventListener("input", (event) => {
      const color = $('[data-color-property="background-color"]').dataset.color || "rgb(255,255,255)";
      const rgb = parseColor(color);
      styleOperation("background-color", `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${number(event.target.value) / 100})`);
    });
  }

  function setZoom(value, anchor) {
    const previous = state.zoom / 100;
    const next = Math.max(25, Math.min(200, Math.round(value))) / 100;
    if (anchor) {
      const rect = els.shell.getBoundingClientRect();
      const dx = anchor.x - rect.left;
      const dy = anchor.y - rect.top;
      const ratio = next / previous;
      state.pan.x += dx * (1 - ratio);
      state.pan.y += dy * (1 - ratio);
    }
    state.zoom = Math.round(next * 100);
    updateZoom();
  }

  function updateZoom(persist = true) {
    els.zoomValue.textContent = `${state.zoom}%`;
    els.zoomInput.value = state.zoom;
    els.shell.style.transform = `translate(${state.pan.x}px, ${state.pan.y}px) scale(${state.zoom / 100})`;
    if (persist) persistPreferences();
  }

  function resizePreviewShell(metrics = state.previewMetrics) {
    const availableHeight = Math.max(360, els.viewport.clientHeight - 68);
    els.shell.style.height = `${availableHeight}px`;
    if (metrics?.contentWidth) {
      const targetWidth = Math.max(320, Math.min(2400, Math.ceil(metrics.contentWidth) + 2));
      els.shell.style.width = `${targetWidth}px`;
    }
  }

  function bindCanvas() {
    $("#zoom-out").addEventListener("click", () => setZoom(state.zoom - 10));
    $("#zoom-in").addEventListener("click", () => setZoom(state.zoom + 10));
    els.zoomValue.addEventListener("click", () => { els.zoomValue.classList.add("hidden"); els.zoomInput.classList.remove("hidden"); els.zoomInput.select(); });
    const finishZoom = () => { setZoom(number(els.zoomInput.value, state.zoom)); els.zoomInput.classList.add("hidden"); els.zoomValue.classList.remove("hidden"); };
    els.zoomInput.addEventListener("change", finishZoom);
    els.zoomInput.addEventListener("keydown", (event) => { if (event.key === "Enter") finishZoom(); if (event.key === "Escape") { els.zoomInput.classList.add("hidden"); els.zoomValue.classList.remove("hidden"); } });
    els.viewport.addEventListener("wheel", (event) => {
      event.preventDefault();
      if (event.ctrlKey) {
        setZoom(state.zoom + (event.deltaY < 0 ? 5 : -5), { x: event.clientX, y: event.clientY });
      } else {
        postPreview("scroll-page", { deltaX: event.deltaX, deltaY: event.deltaY });
      }
    }, { passive: false });
    let panning = false; let last = null;
    els.viewport.addEventListener("mousedown", (event) => {
      if (event.button !== 1) return;
      event.preventDefault(); panning = true; last = { x: event.clientX, y: event.clientY }; els.viewport.classList.add("panning");
    });
    window.addEventListener("mousemove", (event) => {
      if (!panning) return;
      state.pan.x += event.clientX - last.x; state.pan.y += event.clientY - last.y; last = { x: event.clientX, y: event.clientY }; updateZoom(false);
    });
    window.addEventListener("mouseup", (event) => { if (event.button === 1) { panning = false; els.viewport.classList.remove("panning"); } });
    els.viewport.addEventListener("auxclick", (event) => { if (event.button === 1) event.preventDefault(); });
  }

  function previewPointToPage(point) {
    const rect = els.frame.getBoundingClientRect();
    const scaleX = rect.width / Math.max(1, els.frame.offsetWidth);
    const scaleY = rect.height / Math.max(1, els.frame.offsetHeight);
    return { x: rect.left + point.x * scaleX, y: rect.top + point.y * scaleY };
  }

  function parseColor(value) {
    const canvas = parseColor.canvas ||= document.createElement("canvas");
    const context = canvas.getContext("2d");
    context.fillStyle = "#000000"; context.fillStyle = value || "#000000";
    const normalized = context.fillStyle;
    if (normalized.startsWith("#")) {
      const hex = normalized.slice(1); const full = hex.length === 3 ? [...hex].map((char) => char + char).join("") : hex.slice(0, 6);
      return { r: parseInt(full.slice(0, 2), 16), g: parseInt(full.slice(2, 4), 16), b: parseInt(full.slice(4, 6), 16), a: hex.length >= 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1 };
    }
    const values = normalized.match(/[\d.]+/g)?.map(Number) || [0, 0, 0];
    return { r: values[0], g: values[1], b: values[2], a: values[3] ?? 1 };
  }

  function rgbToHsv({ r, g, b }) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b); const min = Math.min(r, g, b); const delta = max - min;
    let h = 0;
    if (delta) h = max === r ? ((g - b) / delta) % 6 : max === g ? (b - r) / delta + 2 : (r - g) / delta + 4;
    return { h: Math.round((h * 60 + 360) % 360), s: Math.round(max ? delta / max * 100 : 0), v: Math.round(max * 100) };
  }

  function hsvToRgb(h, s, v) {
    s /= 100; v /= 100; const c = v * s; const x = c * (1 - Math.abs((h / 60) % 2 - 1)); const m = v - c;
    const parts = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return { r: Math.round((parts[0] + m) * 255), g: Math.round((parts[1] + m) * 255), b: Math.round((parts[2] + m) * 255) };
  }

  function rgbHex({ r, g, b }) { return `#${[r, g, b].map((item) => Math.max(0, Math.min(255, item)).toString(16).padStart(2, "0")).join("")}`; }

  function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, number(value, minimum)));
  }

  function closeAnchoredPopovers() {
    [$("#color-dialog"), $("#effect-dialog")].forEach((dialog) => { if (dialog?.open) dialog.close(); });
    state.colorTarget = null;
    state.activeEffectId = null;
    state.effectDraft = null;
  }

  function showAnchored(dialog, anchor) {
    if (dialog.open) dialog.close();
    dialog.show();
    requestAnimationFrame(() => {
      const anchorRect = anchor.getBoundingClientRect();
      const popupRect = dialog.getBoundingClientRect();
      const gap = 8;
      const candidates = [
        { left: anchorRect.right + gap, top: anchorRect.top },
        { left: anchorRect.left - popupRect.width - gap, top: anchorRect.top },
        { left: anchorRect.left, top: anchorRect.bottom + gap },
        { left: anchorRect.left, top: anchorRect.top - popupRect.height - gap },
      ];
      const position = candidates.find((item) => item.left >= gap && item.top >= gap && item.left + popupRect.width <= innerWidth - gap && item.top + popupRect.height <= innerHeight - gap) || candidates[1];
      dialog.style.left = `${Math.max(gap, Math.min(innerWidth - popupRect.width - gap, position.left))}px`;
      dialog.style.top = `${Math.max(gap, Math.min(innerHeight - popupRect.height - gap, position.top))}px`;
    });
  }

  function updateColorField(button, value) {
    button.dataset.color = value;
    $("span", button).style.background = value;
    $("em", button).textContent = value;
  }

  function renderColorDialog() {
    const rgb = hsvToRgb(state.color.h, state.color.s, state.color.v);
    const hex = rgbHex(rgb);
    $("#color-r").value = rgb.r; $("#color-g").value = rgb.g; $("#color-b").value = rgb.b;
    $("#color-h").value = Math.round(state.color.h); $("#color-s").value = Math.round(state.color.s); $("#color-v").value = Math.round(state.color.v);
    $("#color-hex").value = hex; $("#color-preview").style.background = hex; $("#color-hue").value = state.color.h;
    $("#color-sv").style.backgroundColor = `hsl(${state.color.h} 100% 50%)`;
    $("#color-sv-handle").style.left = `${state.color.s}%`;
    $("#color-sv-handle").style.top = `${100 - state.color.v}%`;
  }

  function setColorDialog(color) {
    state.color = rgbToHsv(parseColor(color));
    renderColorDialog();
  }

  function openColor(button) {
    state.colorTarget = button;
    setColorDialog(button.dataset.color || "#ffffff");
    showAnchored($("#color-dialog"), button);
  }

  function bindColors() {
    [...$$("[data-color-property]"), $("#shadow-color")].forEach((button) => button.addEventListener("click", () => openColor(button)));
    const updateSv = (event) => {
      const rect = $("#color-sv").getBoundingClientRect();
      state.color.s = clamp((event.clientX - rect.left) / rect.width * 100, 0, 100);
      state.color.v = clamp(100 - (event.clientY - rect.top) / rect.height * 100, 0, 100);
      renderColorDialog();
    };
    $("#color-sv").addEventListener("pointerdown", (event) => { event.currentTarget.setPointerCapture(event.pointerId); updateSv(event); });
    $("#color-sv").addEventListener("pointermove", (event) => { if (event.currentTarget.hasPointerCapture(event.pointerId)) updateSv(event); });
    $("#color-sv").addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      if (event.key === "ArrowLeft") state.color.s = clamp(state.color.s - 1, 0, 100);
      if (event.key === "ArrowRight") state.color.s = clamp(state.color.s + 1, 0, 100);
      if (event.key === "ArrowUp") state.color.v = clamp(state.color.v + 1, 0, 100);
      if (event.key === "ArrowDown") state.color.v = clamp(state.color.v - 1, 0, 100);
      renderColorDialog();
    });
    $("#color-hue").addEventListener("input", (event) => { state.color.h = clamp(event.target.value, 0, 360); renderColorDialog(); });
    ["color-r", "color-g", "color-b"].forEach((id) => $(`#${id}`).addEventListener("input", () => {
      state.color = rgbToHsv({ r: clamp($("#color-r").value, 0, 255), g: clamp($("#color-g").value, 0, 255), b: clamp($("#color-b").value, 0, 255) });
      renderColorDialog();
    }));
    ["color-h", "color-s", "color-v"].forEach((id) => $(`#${id}`).addEventListener("input", () => {
      state.color = { h: clamp($("#color-h").value, 0, 360), s: clamp($("#color-s").value, 0, 100), v: clamp($("#color-v").value, 0, 100) };
      renderColorDialog();
    }));
    $("#color-hex").addEventListener("change", (event) => setColorDialog(event.target.value));
    $("#apply-color").addEventListener("click", () => {
      if (!state.colorTarget) return;
      const value = rgbHex(hsvToRgb(state.color.h, state.color.s, state.color.v));
      updateColorField(state.colorTarget, value);
      if (state.colorTarget.id === "shadow-color") {
        if (state.effectDraft) state.effectDraft.color = value;
      } else {
        styleOperation(state.colorTarget.dataset.colorProperty, value);
      }
    });
    $("#eyedropper").addEventListener("click", async () => {
      if (!window.EyeDropper) return toast("当前浏览器不支持吸管取色。", "warn");
      try { const result = await new EyeDropper().open(); setColorDialog(result.sRGBHex); } catch (_error) { /* 用户取消取色，不改变当前值。 */ }
    });
  }

  const effectLabels = { drop: "外部投影", inset: "内部投影", layer: "图层模糊", backdrop: "背景模糊" };

  function effectDefaults(type = "drop") {
    return { id: crypto.randomUUID(), type, x: 0, y: 4, blur: 8, spread: 0, color: "rgba(15, 23, 42, .25)" };
  }

  function splitCssList(value) {
    const items = [];
    let depth = 0; let start = 0;
    [...String(value || "")].forEach((character, index) => {
      if (character === "(") depth += 1;
      if (character === ")") depth = Math.max(0, depth - 1);
      if (character === "," && depth === 0) { items.push(value.slice(start, index).trim()); start = index + 1; }
    });
    items.push(String(value || "").slice(start).trim());
    return items.filter(Boolean);
  }

  function parseEffects(styles) {
    const items = [];
    const unparsedShadows = [];
    if (styles.boxShadow && styles.boxShadow !== "none") {
      splitCssList(styles.boxShadow).forEach((shadow) => {
        const color = shadow.match(/rgba?\([^)]+\)|#[\da-f]{3,8}/i)?.[0] || "rgba(15, 23, 42, .25)";
        const lengths = shadow.replace(color, "").match(/-?[\d.]+px/g)?.map(number) || [];
        if (lengths.length < 3) { unparsedShadows.push(shadow); return; }
        items.push({ ...effectDefaults(shadow.includes("inset") ? "inset" : "drop"), x: lengths[0], y: lengths[1], blur: lengths[2], spread: lengths[3] || 0, color });
      });
    }
    const readBlurs = (value, type) => {
      if (!value || value === "none") return "";
      for (const match of value.matchAll(/blur\((-?[\d.]+)px\)/g)) items.push({ ...effectDefaults(type), blur: number(match[1], 8) });
      return value.replace(/blur\((-?[\d.]+)px\)/g, "").trim();
    };
    return {
      items,
      base: {
        boxShadow: unparsedShadows.join(", "),
        filter: readBlurs(styles.filter, "layer"),
        backdropFilter: readBlurs(styles.backdropFilter, "backdrop"),
      },
    };
  }

  function renderEffects() {
    const root = $("#effect-list");
    if (!root) return;
    root.replaceChildren();
    state.effects.forEach((effect) => {
      const row = document.createElement("div");
      row.className = "effect-row";
      row.dataset.effectId = effect.id;
      const select = document.createElement("select");
      select.setAttribute("aria-label", "效果类型");
      Object.entries(effectLabels).forEach(([value, label]) => select.add(new Option(label, value)));
      select.value = effect.type;
      const settings = iconButton("settings", "效果设置", "effect-settings");
      const remove = iconButton("trash", "删除效果", "danger remove-effect");
      select.addEventListener("change", () => { effect.type = select.value; updateEffectStyles(); });
      settings.addEventListener("click", () => openEffectSettings(effect, settings));
      remove.addEventListener("click", () => {
        state.effects = state.effects.filter((item) => item.id !== effect.id);
        renderEffects();
        updateEffectStyles();
      });
      row.append(select, settings, remove);
      root.append(row);
    });
  }

  function updateEffectStyles() {
    const shadows = state.effects.filter((item) => ["drop", "inset"].includes(item.type)).map((item) => `${item.type === "inset" ? "inset " : ""}${item.x}px ${item.y}px ${item.blur}px ${item.spread}px ${item.color}`);
    const layerBlurs = state.effects.filter((item) => item.type === "layer").map((item) => `blur(${item.blur}px)`);
    const backdropBlurs = state.effects.filter((item) => item.type === "backdrop").map((item) => `blur(${item.blur}px)`);
    styleOperation("box-shadow", [state.effectBase.boxShadow, ...shadows].filter(Boolean).join(", ") || "none");
    styleOperation("filter", [state.effectBase.filter, ...layerBlurs].filter(Boolean).join(" ") || "none");
    styleOperation("backdrop-filter", [state.effectBase.backdropFilter, ...backdropBlurs].filter(Boolean).join(" ") || "none");
  }

  function openEffectSettings(effect, anchor) {
    state.activeEffectId = effect.id;
    state.effectDraft = { ...effect };
    const simple = ["layer", "backdrop"].includes(effect.type);
    $("#effect-title").textContent = effectLabels[effect.type];
    $("#shadow-controls").classList.toggle("hidden", simple);
    $("#simple-blur-control").classList.toggle("hidden", !simple);
    setValue("shadow-x", effect.x); setValue("shadow-y", effect.y); setValue("shadow-blur", effect.blur); setValue("shadow-spread", effect.spread);
    setValue("simple-blur", effect.blur);
    updateColorField($("#shadow-color"), effect.color);
    showAnchored($("#effect-dialog"), anchor);
  }

  function bindEffects() {
    $("#add-effect").addEventListener("click", () => {
      state.effects.push(effectDefaults("drop"));
      renderEffects();
      updateEffectStyles();
    });
    $("#apply-effect").addEventListener("click", () => {
      const effect = state.effects.find((item) => item.id === state.activeEffectId);
      if (!effect) return;
      if (["layer", "backdrop"].includes(effect.type)) effect.blur = number($("#simple-blur").value, 8);
      else Object.assign(effect, {
        x: number($("#shadow-x").value), y: number($("#shadow-y").value),
        blur: number($("#shadow-blur").value, 8), spread: number($("#shadow-spread").value),
        color: state.effectDraft?.color || effect.color,
      });
      renderEffects();
      updateEffectStyles();
    });
  }

  function openAnnotation(selection, annotation = null) {
    state.selection = selection || state.selection;
    state.editingAnnotation = annotation;
    $("#annotation-title").textContent = annotation ? "编辑批注" : "添加批注";
    $("#annotation-copy").value = annotation?.text || "";
    $("#annotation-dialog").showModal();
    setTimeout(() => $("#annotation-copy").focus(), 0);
  }

  function saveAnnotation() {
    if (!state.selection) return;
    const text = $("#annotation-copy").value.trim();
    if (!text) return;
    const identifier = state.editingAnnotation?.fileId || state.selection.fileId;
    const draft = draftFor(identifier);
    if (state.editingAnnotation) {
      const index = draft.annotations.findIndex((item) => item.id === state.editingAnnotation.id);
      if (index >= 0) draft.annotations[index].text = text;
    } else {
      draft.annotations.push({ type: "annotation", id: crypto.randomUUID(), fileId: identifier, fingerprint: state.selection.fingerprint, text });
    }
    state.editingAnnotation = null; renderTree(); applyDrafts(); syncDirtyState();
  }

  function deleteAnnotation(annotation) {
    const draft = draftFor(annotation.fileId, false);
    if (!draft) return;
    draft.annotations = draft.annotations.filter((item) => item.id !== annotation.id);
    renderTree(); applyDrafts(); syncDirtyState();
  }

  async function chooseImage() {
    if (!state.selection || state.selection.element.tag !== "img") return toast("请先选择图片元素。", "warn");
    try {
      const result = await api("/api/dialog", { kind: "image" });
      if (result.cancelled) return;
      const previewUrl = `/api/selected/${result.assetId}?token=${encodeURIComponent(token)}`;
      $("#image-preview").src = previewUrl; $("#image-preview").classList.remove("hidden");
      $("#image-status").textContent = `待替换：${result.name}`;
      const key = `image:${fingerprintKey(state.selection.fingerprint)}`;
      upsertOperation(state.selection.fileId, { type: "image-replace", fingerprint: state.selection.fingerprint, assetId: result.assetId, path: result.path, name: result.name, previewUrl }, key);
    } catch (error) { toast(error.message, "error"); }
  }

  function updateCssSummary() {
    const draft = draftFor(state.selection?.fileId, false);
    const selectedKey = fingerprintKey(state.selection?.fingerprint);
    const css = draft?.operations.filter((item) => item.type === "css" && fingerprintKey(item.fingerprint) === selectedKey) || [];
    $("#css-summary").textContent = css.length ? css.map((item) => `${item.property}: ${item.value}`).join("\n") : "尚未添加 CSS 覆盖。";
  }

  function applyCustomCss() {
    if (!state.selection) return toast("请先选择元素。", "warn");
    const property = $("#css-property").value.trim(); const value = $("#css-value").value.trim();
    if (!property || !value) return toast("请填写 CSS 属性和值。", "warn");
    const key = `css:${fingerprintKey(state.selection.fingerprint)}:${property}`;
    upsertOperation(state.selection.fileId, { type: "css", fingerprint: state.selection.fingerprint, property, value }, key);
  }

  function syncPages() {
    const runtime = fileById(state.currentFileId);
    if (!runtime || runtime.kind !== "runtime") return;
    const normalized = runtime.name.replace(/--[^.]+(?=\.html$)/, "");
    const source = state.workspace.files.find((file) => file.automaticGroup === "pages" && file.name === normalized);
    if (!source) return toast(`未找到对应静态页 pages/${normalized}。`, "warn");
    const operation = {
      type: "sync-pages", fileId: runtime.id, sourceFileId: source.id, sourcePath: source.path, runtimePath: runtime.path,
      sourceSha256: source.sha256, runtimeSha256: runtime.sha256, dependencyGroup: `sync:${runtime.id}`,
    };
    upsertOperation(runtime.id, operation, `sync:${runtime.id}`);
    els.sync.textContent = "已同步"; els.sync.classList.add("synced");
  }

  function clearCurrent() {
    const draft = draftFor(state.currentFileId, false);
    if (!draft) return;
    draft.operations = [];
    state.staleDrafts.delete(state.currentFileId);
    els.sync.textContent = "同步 pages"; els.sync.classList.remove("synced");
    renderTree(); applyDrafts(); updateCssSummary(); syncDirtyState();
    postPreview("refresh-selection");
    toast("已清空当前 HTML 的样式、内容、图片、CSS 和同步草稿；批注已保留。" );
  }

  function requestFiles() {
    const dependencyByFile = new Map();
    for (const [identifier, draft] of state.drafts) {
      for (const operation of draft.operations) {
        if (operation.type === "sync-pages") {
          dependencyByFile.set(identifier, operation.dependencyGroup);
          dependencyByFile.set(operation.sourceFileId, operation.dependencyGroup);
        }
      }
    }
    return [...state.drafts.entries()].map(([identifier, draft]) => {
      const file = fileById(identifier);
      if (!file) return null;
      const operations = [...draft.annotations, ...draft.operations].map(({ _key, previewUrl, ...operation }) => operation);
      if (!operations.length) return null;
      return { fileId: identifier, sha256: file.sha256, operations, dependencyGroup: dependencyByFile.get(identifier) || null };
    }).filter(Boolean);
  }

  async function sendRequest() {
    if (state.staleDrafts.size) return toast("源文件已在外部变化，请刷新后重新编辑再发送。", "error");
    const files = requestFiles();
    if (!files.length) return toast("当前会话没有待发送修改。", "warn");
    const button = $("#send-ai"); button.disabled = true;
    try {
      const result = await api("/api/requests", { schemaVersion: 1, files });
      state.drafts.clear(); state.staleDrafts.clear(); renderTree(); applyDrafts(); syncDirtyState();
      selectFile(state.currentFileId, true);
      $("#request-instruction").value = result.instruction;
      $("#request-dialog").showModal();
      navigator.clipboard?.writeText(result.instruction).catch(() => {});
      toast("变更包已生成，执行指令已复制。" );
    } catch (error) { toast(error.message, "error"); }
    finally { button.disabled = false; }
  }

  async function requestUndo() {
    try {
      const result = await api("/api/undo/request", {});
      $("#request-instruction").value = result.instruction; $("#request-dialog").showModal();
      navigator.clipboard?.writeText(result.instruction).catch(() => {});
    } catch (error) { toast(error.message, "error"); }
  }

  function showResults(results) {
    const latest = results[0];
    if (!latest) return;
    const root = $("#result-list"); root.replaceChildren();
    for (const item of latest.items || []) {
      const row = document.createElement("div"); row.className = "result-item";
      const status = document.createElement("b"); status.className = item.status || "failed"; status.textContent = ({ success: "成功", failed: "失败", conflict: "冲突" })[item.status] || item.status;
      const copy = document.createElement("span"); copy.textContent = `${item.path || item.fileId || "未知文件"}${item.reason ? `：${item.reason}` : ""}`;
      row.append(status, copy); root.append(row);
    }
    if (!latest.items?.length) root.textContent = latest.reason || "该批次没有文件结果。";
    $("#result-dialog").showModal();
  }

  async function poll() {
    try {
      const [workspace, serviceState, results] = await Promise.all([api("/api/workspace"), api("/api/state"), api("/api/results")]);
      els.connectionDot.classList.remove("offline"); els.connectionCopy.textContent = serviceState.locked ? "功能五打包中" : "本地工作区";
      const currentBefore = fileById(state.currentFileId);
      const previousSha = currentBefore?.sha256;
      for (const file of workspace.files) {
        const old = state.lastSha.get(file.id);
        if (old && old !== file.sha256) {
          if (hasDraft(file.id)) { state.staleDrafts.add(file.id); toast(`“${file.name}”已在外部变化，旧草稿不能发送。`, "warn"); }
          else if (file.id === state.currentFileId) setTimeout(() => selectFile(file.id, true), 0);
        }
        state.lastSha.set(file.id, file.sha256);
      }
      state.workspace = workspace;
      if (!previousSha && state.currentFileId && !fileById(state.currentFileId)) selectFile(workspace.currentFileId, true);
      renderTree();
      $("#undo-ai").disabled = !results.undoAvailable;
      const latest = results.results?.[0];
      if (latest?.requestId && latest.requestId !== state.latestResultId) { state.latestResultId = latest.requestId; showResults(results.results); }
    } catch (_error) {
      els.connectionDot.classList.add("offline"); els.connectionCopy.textContent = "服务已关闭";
    }
  }

  async function refreshProjectFiles(event) {
    const button = event.currentTarget;
    const known = new Set(state.workspace.files.map((file) => file.id));
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    try {
      const workspace = await api("/api/workspace/sync", { paths: [] });
      const added = workspace.files.filter((file) => file.source === "project" && !known.has(file.id));
      state.workspace = workspace;
      if (!fileById(state.currentFileId)) selectFile(workspace.currentFileId, true);
      else renderTree();
      toast(added.length ? `已添加 ${added.length} 个新 HTML 文件。` : "项目 HTML 文件已是最新。" );
    } catch (error) { toast(error.message, "error"); }
    finally { button.disabled = false; button.removeAttribute("aria-busy"); }
  }

  function bindChrome() {
    $("#refresh-files").addEventListener("click", refreshProjectFiles);
    $("#refresh-fonts").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try { await loadSystemFonts(true); toast("本机字体清单已刷新。" ); }
      catch (error) { toast(error.message, "error"); }
      finally { button.disabled = false; }
    });
    els.search.addEventListener("input", renderTree);
    $("#collapse-sidebar").addEventListener("click", () => {
      state.sidebarCollapsed = !state.sidebarCollapsed; state.temporarySidebar = false; els.layout.classList.toggle("sidebar-collapsed", state.sidebarCollapsed);
    });
    $("#edge-reveal").addEventListener("mouseenter", () => { if (state.sidebarCollapsed) { state.temporarySidebar = true; els.layout.classList.remove("sidebar-collapsed"); } });
    let sidebarTimer;
    els.sidebar.addEventListener("mouseenter", () => clearTimeout(sidebarTimer));
    els.sidebar.addEventListener("mouseleave", () => {
      if (!state.sidebarCollapsed || !state.temporarySidebar) return;
      sidebarTimer = setTimeout(() => { state.temporarySidebar = false; els.layout.classList.add("sidebar-collapsed"); }, 1000);
    });
    $("#refresh-preview").addEventListener("click", () => {
      if (state.staleDrafts.has(state.currentFileId)) {
        state.drafts.delete(state.currentFileId);
        state.staleDrafts.delete(state.currentFileId);
        renderTree();
        syncDirtyState();
        toast("源文件已刷新；该文件基于旧摘要的草稿已丢弃，请重新编辑。", "warn");
      }
      selectFile(state.currentFileId, true);
    });
    els.selectMode.addEventListener("click", () => { state.selectMode = !state.selectMode; els.selectMode.classList.toggle("active", state.selectMode); postPreview("select-mode", { active: state.selectMode }); });
    $$(".tab").forEach((button) => button.addEventListener("click", () => {
      $$(".tab").forEach((item) => item.classList.toggle("active", item === button));
      $$(".tab-panel").forEach((panel) => panel.classList.toggle("hidden", panel.dataset.panel !== button.dataset.tab));
    }));
    $("#sync-pages").addEventListener("click", syncPages); $("#clear-current").addEventListener("click", clearCurrent);
    $("#send-ai").addEventListener("click", sendRequest); $("#undo-ai").addEventListener("click", requestUndo);
    $("#copy-instruction").addEventListener("click", () => navigator.clipboard?.writeText($("#request-instruction").value));
    $("#save-annotation").addEventListener("click", saveAnnotation); $("#choose-image").addEventListener("click", chooseImage); $("#apply-css").addEventListener("click", applyCustomCss);
    let tooltipTimer;
    document.addEventListener("mousemove", (event) => {
      const target = event.target.closest?.("[data-tooltip]");
      clearTimeout(tooltipTimer);
      if (!target) return els.tooltip.classList.add("hidden");
      tooltipTimer = setTimeout(() => { els.tooltip.textContent = target.dataset.tooltip; els.tooltip.style.left = `${event.clientX + 10}px`; els.tooltip.style.top = `${event.clientY + 10}px`; els.tooltip.classList.remove("hidden"); }, 500);
    });
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== location.origin || event.source !== els.frame.contentWindow) return;
    const message = event.data || {};
    if (message.channel !== CHANNEL) return;
    if (message.type === "ready") {
      postPreview("select-mode", { active: state.selectMode }); applyDrafts();
    } else if (message.type === "metrics") {
      state.previewMetrics = message.metrics;
      resizePreviewShell(message.metrics);
    } else if (message.type === "selection") {
      populateSelection(message.selection); updateCssSummary();
    } else if (message.type === "annotation-request") openAnnotation(message.selection);
    else if (message.type === "annotation-edit") openAnnotation(null, message.annotation);
    else if (message.type === "annotation-delete") confirmAction("删除批注", "删除当前批注内容？该操作只影响会话草稿。", () => deleteAnnotation(message.annotation));
    else if (message.type === "canvas-wheel") {
      const point = previewPointToPage(message.point);
      setZoom(state.zoom + (message.deltaY < 0 ? 5 : -5), point);
    } else if (message.type === "canvas-pan-start") {
      state.remotePanPoint = previewPointToPage(message.point);
      els.viewport.classList.add("panning");
    } else if (message.type === "canvas-pan-move" && state.remotePanPoint) {
      const point = previewPointToPage(message.point);
      state.pan.x += point.x - state.remotePanPoint.x;
      state.pan.y += point.y - state.remotePanPoint.y;
      state.remotePanPoint = point;
      updateZoom(false);
    } else if (message.type === "canvas-pan-end") {
      state.remotePanPoint = null;
      els.viewport.classList.remove("panning");
    }
  });

  async function init() {
    if (!token) return toast("缺少工作台实例令牌，请通过 ensure 命令重新打开。", "error");
    bindChrome(); bindCanvas(); bindPropertyInputs(); bindColors(); bindEffects();
    new ResizeObserver(() => resizePreviewShell()).observe(els.viewport);
    try {
      state.workspace = await api("/api/workspace");
      await loadSystemFonts(false);
      state.currentFileId = state.workspace.currentFileId;
      state.workspace.files.forEach((file) => state.lastSha.set(file.id, file.sha256));
      els.project.textContent = state.workspace.projectName; renderTree(); selectFile(state.currentFileId, true);
      const results = await api("/api/results"); $("#undo-ai").disabled = !results.undoAvailable;
      setInterval(poll, 2000);
    } catch (error) { toast(error.message, "error"); els.connectionDot.classList.add("offline"); }
  }

  init();
})();
