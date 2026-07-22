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
    selectMode: false,
    zoom: 100,
    pan: { x: 0, y: 0 },
    collapsedGroupIds: new Set(),
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
    requests: [],
    activeRequest: null,
    results: [],
    pollTimer: null,
    serviceClosed: false,
    requestRevision: 0,
    syncPages: [],
    dismissedRequestIds: new Set(),
  };

  const els = {
    layout: $("#layout"), sidebar: $("#sidebar"), tree: $("#file-tree"), search: $("#file-search"),
    frame: $("#preview-frame"), shell: $("#preview-shell"), viewport: $("#canvas-viewport"), empty: $("#empty-state"),
    path: $("#current-path"), project: $("#project-name"), selectMode: $("#select-mode"), clearAnnotations: $("#clear-annotations"), sync: $("#sync-pages"),
    selectedPath: $("#selected-path"), selectedName: $("#selected-name"), zoomValue: $("#zoom-value"), zoomInput: $("#zoom-input"),
    toast: $("#toast"), tooltip: $("#tooltip"), connectionDot: $("#connection-dot"), connectionCopy: $("#connection-copy"),
    inspector: $(".inspector"), requestStatus: $("#request-status"), serviceClosed: $("#service-closed"),
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

  function isActiveRequest(request = state.activeRequest) {
    return Boolean(request && ["pending", "processing"].includes(request.status));
  }

  function isFileLocked(identifier) {
    return Boolean(isActiveRequest() && state.activeRequest.fileIds?.includes(identifier));
  }

  function requireEditable(identifier) {
    if (!isFileLocked(identifier)) return true;
    toast("当前文件正在等待 Agent 处理，暂时不能继续编辑。", "warn");
    return false;
  }

  function draftFor(identifier, create = true) {
    if (!identifier) return null;
    if (!state.drafts.has(identifier) && create) state.drafts.set(identifier, { operations: [], annotations: [], rootFileIds: new Set() });
    return state.drafts.get(identifier) || null;
  }

  function hasDraft(identifier) {
    const draft = draftFor(identifier, false);
    return Boolean(draft && (draft.operations.length || draft.annotations.length));
  }

  function hasRelatedDraft(identifier) {
    return [...state.drafts.values()].some((draft) => (
      (draft.operations.length || draft.annotations.length) && draft.rootFileIds?.has(identifier)
    ));
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
    if (!requireEditable(identifier)) return;
    const file = fileById(identifier);
    if (!file) {
      toast("该嵌套页面未登记到工作区，当前只能查看。", "warn");
      return;
    }
    const draft = draftFor(identifier);
    if (state.selection?.fileId === identifier && state.selection.rootFileId && state.selection.rootFileId !== identifier) {
      draft.rootFileIds.add(state.selection.rootFileId);
    }
    const index = draft.operations.findIndex((item) => item._key === key);
    operation.fileId = identifier;
    operation._key = key;
    if (index >= 0) draft.operations[index] = operation; else draft.operations.push(operation);
    renderTree();
    applyDrafts();
    syncDirtyState();
  }

  function postPreview(type, payload = {}) {
    els.frame.contentWindow?.postMessage({ channel: CHANNEL, version: 1, type, ...payload }, location.origin);
  }

  function operationsForPreview() {
    return [...state.drafts.values()].flatMap((draft) => draft.operations.flatMap((item) => {
      if (item.type === "sync-pages") return item._previewOperations || [];
      return item.type === "annotation" ? [] : [item];
    }));
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
    row.className = `file-row${file.id === state.currentFileId ? " active" : ""}${hasDraft(file.id) || hasRelatedDraft(file.id) ? " pending" : ""}${syncOpportunity(file.id) ? " needs-sync" : ""}`;
    row.dataset.fileId = file.id;
    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = file.name;
    const source = document.createElement("span");
    source.className = "source-badge";
    source.textContent = file.missing ? "缺失" : file.source === "external" ? "外部" : file.kind === "offline" && file.name !== "prototype-mobile.html" ? "离线" : "";
    if (!source.textContent) source.classList.add("hidden");
    row.innerHTML = '<span class="file-icon" aria-hidden="true"></span>';
    row.append(name, source);
    row.addEventListener("click", () => selectFile(file.id));
    return row;
  }

  function syncOpportunity(identifier) {
    return state.syncPages.find((item) => item.runtimeFileId === identifier) || null;
  }

  function renderSyncButton(identifier = state.currentFileId) {
    const file = fileById(identifier);
    const synced = draftFor(identifier, false)?.operations.some((item) => item.type === "sync-pages");
    const visible = Boolean(file?.kind === "runtime" && (synced || syncOpportunity(identifier)));
    els.sync.classList.toggle("hidden", !visible);
    els.sync.textContent = synced ? "已同步" : "同步 pages";
    els.sync.classList.toggle("synced", Boolean(synced));
  }

  function groupNode(group) {
    const section = document.createElement("section");
    section.className = `file-group${state.collapsedGroupIds.has(group.id) ? " collapsed" : ""}`;
    section.dataset.groupId = group.id;
    const row = document.createElement("div");
    row.className = "group-row";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "group-toggle";
    toggle.innerHTML = '<span class="group-label"><svg aria-hidden="true"><use href="/assets/icons.svg#folder"></use></svg><span></span></span><span class="group-count"></span>';
    toggle.querySelector(".group-label span").textContent = group.name;
    toggle.querySelector(".group-count").textContent = group.files.length;
    toggle.addEventListener("click", () => {
      const collapsed = section.classList.toggle("collapsed");
      if (collapsed) state.collapsedGroupIds.add(group.id);
      else state.collapsedGroupIds.delete(group.id);
    });
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
    els.clearAnnotations.disabled = isFileLocked(state.currentFileId) || !(draftFor(state.currentFileId, false)?.annotations.length);
    updateEditingLock();
  }

  function confirmAction(title, copy, action, actionCopy = "确认") {
    $("#confirm-title").textContent = title;
    $("#confirm-copy").textContent = copy;
    const button = $("#confirm-action");
    button.textContent = actionCopy;
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
    renderSyncButton(identifier);
    clearSelectionPanel();
    resizePreviewShell();
    updateZoom(false);
    if (!file.missing) els.frame.src = `/preview/${encodeURIComponent(identifier)}/?token=${encodeURIComponent(token)}&v=${Date.now()}`;
    renderTree();
    updateEditingLock();
    persistPreferences();
  }

  function updateEditingLock() {
    const locked = isFileLocked(state.currentFileId);
    els.inspector.classList.toggle("request-file-locked", locked);
    $$("input, select, textarea, button", $(".inspector-scroll", els.inspector)).forEach((control) => { control.disabled = locked; });
    $("#clear-current").disabled = locked;
    els.sync.disabled = locked;
    els.clearAnnotations.disabled = locked || !(draftFor(state.currentFileId, false)?.annotations.length);
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
    setValue("rotation", 0);
    $("#flip-x").classList.remove("pressed");
    $("#flip-y").classList.remove("pressed");
    renderEffects();
  }

  function clearCurrentSelection() {
    if (!state.selection) return;
    state.selection = null;
    clearSelectionPanel();
    postPreview("clear-selection");
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
    updateEditingLock();
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
    if (!requireEditable(state.selection.fileId)) return;
    const key = `style:${fingerprintKey(state.selection.fingerprint)}:${property}`;
    upsertOperation(state.selection.fileId, { type: "style", fingerprint: state.selection.fingerprint, property, value: String(value) }, key);
  }

  function bindPropertyInputs() {
    $$('[data-css]').forEach((input) => {
      input.addEventListener("input", () => {
        let value = input.value;
        if (["position-x", "position-y"].includes(input.id) && state.selection) {
          const axis = input.id === "position-x" ? "x" : "y";
          const offsetProperty = input.dataset.css;
          const position = state.selection.element.styles.position;
          const delta = number(input.value) - state.selection.element.rect[axis];
          // X/Y 展示的是视口坐标，写回时必须把坐标差量叠加到元素原有偏移，不能把绝对坐标直接当作 left/top。
          if (position === "static") styleOperation("position", "relative");
          value = `${number(state.selection.element.styles[offsetProperty]) + delta}px`;
          styleOperation(offsetProperty, value);
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
    let scrollAdjustment = null;
    if (anchor) {
      const rect = els.shell.getBoundingClientRect();
      const offsetX = Math.max(0, Math.min(rect.width, anchor.x - rect.left));
      const offsetY = Math.max(0, Math.min(rect.height, anchor.y - rect.top));
      if (next > 1) {
        const sourceScale = previous > 1 ? previous : 1;
        state.pan.x = offsetX - (offsetX - state.pan.x) * next / sourceScale;
        state.pan.y = offsetY - (offsetY - state.pan.y) * next / sourceScale;
      } else if (previous <= 1) {
        scrollAdjustment = {
          deltaX: offsetX * (1 / previous - 1 / next),
          deltaY: offsetY * (1 / previous - 1 / next),
        };
      }
    }
    state.zoom = Math.round(next * 100);
    updateZoom();
    if (scrollAdjustment) requestAnimationFrame(() => postPreview("scroll-page", scrollAdjustment));
  }

  function clampPan() {
    if (state.zoom <= 100) {
      state.pan = { x: 0, y: 0 };
      return;
    }
    const scale = state.zoom / 100;
    state.pan.x = Math.max(els.shell.clientWidth * (1 - scale), Math.min(0, state.pan.x));
    state.pan.y = Math.max(els.shell.clientHeight * (1 - scale), Math.min(0, state.pan.y));
  }

  function canPanPreview() {
    if (state.zoom > 100) return true;
    const metrics = state.previewMetrics;
    return Boolean(metrics && (metrics.contentWidth > els.frame.offsetWidth + 1 || metrics.contentHeight > els.frame.offsetHeight + 1));
  }

  function updateZoom(persist = true) {
    const scale = state.zoom / 100;
    clampPan();
    els.zoomValue.textContent = `${state.zoom}%`;
    els.zoomInput.value = state.zoom;
    els.shell.style.removeProperty("transform");
    // 外框始终固定；缩小时扩展逻辑视口，放大时让内部层可在外框内二维平移。
    els.frame.style.width = scale <= 1 ? `${100 / scale}%` : "100%";
    els.frame.style.height = scale <= 1 ? `${100 / scale}%` : "100%";
    els.frame.style.transform = scale <= 1
      ? `scale(${scale})`
      : `translate(${state.pan.x}px, ${state.pan.y}px) scale(${scale})`;
    els.viewport.classList.toggle("can-pan", canPanPreview());
    if (persist) persistPreferences();
  }

  function resizePreviewShell() {
    // 红框区域本身就是浏览器视口，外框始终占满可用区域。
    els.shell.style.removeProperty("width");
    els.shell.style.removeProperty("height");
    updateZoom(false);
  }

  function bindCanvas() {
    $("#zoom-out").addEventListener("click", () => setZoom(state.zoom - 10));
    $("#zoom-reset").addEventListener("click", () => setZoom(100));
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
    els.viewport.addEventListener("click", (event) => {
      if (!state.selectMode || !state.selection || event.target.closest("#preview-shell")) return;
      clearCurrentSelection();
    });
    els.path.addEventListener("click", () => {
      if (state.selectMode && state.selection) clearCurrentSelection();
    });
    let panning = false; let last = null;
    els.viewport.addEventListener("mousedown", (event) => {
      if (event.button !== 1 || !canPanPreview()) return;
      event.preventDefault(); panning = true; last = { x: event.clientX, y: event.clientY }; els.viewport.classList.add("panning");
    });
    window.addEventListener("mousemove", (event) => {
      if (!panning) return;
      if (state.zoom > 100) {
        state.pan.x += event.clientX - last.x;
        state.pan.y += event.clientY - last.y;
      } else {
        postPreview("scroll-page", { deltaX: last.x - event.clientX, deltaY: last.y - event.clientY });
      }
      last = { x: event.clientX, y: event.clientY };
      updateZoom(false);
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
    return { h: (h * 60 + 360) % 360, s: max ? delta / max * 100 : 0, v: max * 100 };
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
    applyColor();
  }

  function setColorDialog(color) {
    state.color = rgbToHsv(parseColor(color));
    renderColorDialog();
  }

  function openColor(button) {
    const property = button.dataset.colorProperty;
    const key = property && state.selection ? `style:${fingerprintKey(state.selection.fingerprint)}:${property}` : null;
    const draft = key ? draftFor(state.selection.fileId, false) : null;
    const operation = key ? draft?.operations.find((item) => item._key === key) : null;
    state.colorSession = {
      button,
      color: button.dataset.color || "#ffffff",
      effectColor: state.effectDraft?.color,
      fileId: state.selection?.fileId,
      key,
      operation: operation ? { ...operation } : null,
    };
    state.colorTarget = button;
    setColorDialog(button.dataset.color || "#ffffff");
    showAnchored($("#color-dialog"), button);
  }

  function applyColor() {
    if (!state.colorTarget) return;
    const value = rgbHex(hsvToRgb(state.color.h, state.color.s, state.color.v));
    updateColorField(state.colorTarget, value);
    if (state.colorTarget.id === "shadow-color") {
      if (state.effectDraft) state.effectDraft.color = value;
    } else {
      styleOperation(state.colorTarget.dataset.colorProperty, value);
    }
  }

  function rollbackColor() {
    const session = state.colorSession;
    if (!session) return;
    state.colorSession = null;
    updateColorField(session.button, session.color);
    if (session.button.id === "shadow-color") {
      if (state.effectDraft) state.effectDraft.color = session.effectColor;
      return;
    }
    const draft = draftFor(session.fileId, false);
    if (!draft || !session.key) return;
    const index = draft.operations.findIndex((item) => item._key === session.key);
    if (session.operation) {
      if (index >= 0) draft.operations[index] = session.operation;
      else draft.operations.push(session.operation);
    } else if (index >= 0) {
      draft.operations.splice(index, 1);
    }
    renderTree();
    applyDrafts();
    syncDirtyState();
  }

  function commitColor(event) {
    event.preventDefault();
    state.colorSession = null;
    $("#color-dialog").close("apply");
  }

  function bindColors() {
    $("#color-dialog").addEventListener("close", () => rollbackColor());
    [...$$("[data-color-property]"), $("#shadow-color")].forEach((button) => button.addEventListener("click", () => openColor(button)));
    let draggingSv = false;
    const updateSv = (event) => {
      const rect = $("#color-sv").getBoundingClientRect();
      state.color.s = clamp((event.clientX - rect.left) / rect.width * 100, 0, 100);
      state.color.v = clamp(100 - (event.clientY - rect.top) / rect.height * 100, 0, 100);
      renderColorDialog();
    };
    const endSvDrag = (event) => {
      draggingSv = false;
      if ($("#color-sv").hasPointerCapture(event.pointerId)) $("#color-sv").releasePointerCapture(event.pointerId);
    };
    $("#color-sv").addEventListener("pointerdown", (event) => {
      event.preventDefault();
      draggingSv = true;
      event.currentTarget.setPointerCapture(event.pointerId);
      updateSv(event);
    });
    $("#color-sv").addEventListener("pointermove", (event) => {
      if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
      event.preventDefault();
      updateSv(event);
    });
    $("#color-sv").addEventListener("pointerup", endSvDrag);
    $("#color-sv").addEventListener("pointercancel", endSvDrag);
    document.addEventListener("selectstart", (event) => { if (draggingSv) event.preventDefault(); }, true);
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
    $("#color-hex").addEventListener("input", (event) => {
      if (/^#[0-9a-f]{6}$/i.test(event.target.value)) setColorDialog(event.target.value);
    });
    $("#apply-color").addEventListener("click", commitColor);
    $("#native-color-fallback").addEventListener("input", (event) => setColorDialog(event.target.value));
    $("#eyedropper").addEventListener("click", async () => {
      if (!window.EyeDropper) {
        const fallback = $("#native-color-fallback");
        fallback.value = rgbHex(hsvToRgb(state.color.h, state.color.s, state.color.v));
        fallback.click();
        return;
      }
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
    if (!state.selection || !requireEditable(annotation?.fileId || state.selection.fileId)) return;
    state.editingAnnotation = annotation;
    $("#annotation-title").textContent = annotation ? "编辑批注" : "添加批注";
    $("#annotation-copy").value = annotation?.text || "";
    $("#annotation-dialog").showModal();
    setTimeout(() => $("#annotation-copy").focus(), 0);
  }

  function saveAnnotation() {
    if (!state.selection) return;
    if (!requireEditable(state.editingAnnotation?.fileId || state.selection.fileId)) return;
    const text = $("#annotation-copy").value.trim();
    if (!text) return;
    const identifier = state.editingAnnotation?.fileId || state.selection.fileId;
    const draft = draftFor(identifier);
    if (state.selection.rootFileId && state.selection.rootFileId !== identifier) draft.rootFileIds.add(state.selection.rootFileId);
    if (state.editingAnnotation) {
      const index = draft.annotations.findIndex((item) => item.id === state.editingAnnotation.id);
      if (index >= 0) draft.annotations[index].text = text;
    } else {
      draft.annotations.push({ type: "annotation", id: crypto.randomUUID(), fileId: identifier, fingerprint: state.selection.fingerprint, text });
    }
    state.editingAnnotation = null; renderTree(); applyDrafts(); syncDirtyState();
  }

  function deleteAnnotation(annotation) {
    if (!requireEditable(annotation.fileId)) return;
    const draft = draftFor(annotation.fileId, false);
    if (!draft) return;
    draft.annotations = draft.annotations.filter((item) => item.id !== annotation.id);
    renderTree(); applyDrafts(); syncDirtyState();
  }

  function clearCurrentAnnotations() {
    if (!requireEditable(state.currentFileId)) return;
    const draft = draftFor(state.currentFileId, false);
    if (!draft?.annotations.length) return;
    draft.annotations = [];
    state.editingAnnotation = null;
    renderTree(); applyDrafts(); syncDirtyState();
    toast("已清空当前 HTML 的全部批注。");
  }

  async function chooseImage() {
    if (!state.selection || state.selection.element.tag !== "img") return toast("请先选择图片元素。", "warn");
    if (!requireEditable(state.selection.fileId)) return;
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

  function syncPages() {
    const runtime = fileById(state.currentFileId);
    if (!runtime || runtime.kind !== "runtime") return;
    if (!requireEditable(runtime.id)) return;
    const opportunity = syncOpportunity(runtime.id);
    if (!opportunity) return toast("对应静态页没有尚未同步的成功样式修改。", "warn");
    const source = fileById(opportunity.sourceFileId);
    if (!source) return toast("对应静态页已不在当前工作区。", "warn");
    const previewOperations = (opportunity.previewOperations || []).map((item) => ({ ...item, fileId: runtime.id }));
    const operation = {
      type: "sync-pages", fileId: runtime.id, sourceFileId: source.id, sourcePath: source.path, runtimePath: runtime.path,
      sourceRequestId: opportunity.sourceRequestId, sourceSha256: opportunity.sourceAfterSha256,
      runtimeSha256: runtime.sha256, dependencyGroup: `sync:${runtime.id}`, _previewOperations: previewOperations,
    };
    upsertOperation(runtime.id, operation, `sync:${runtime.id}`);
    renderSyncButton(runtime.id);
  }

  function clearCurrent() {
    if (!requireEditable(state.currentFileId)) return;
    const affected = [...state.drafts.entries()].filter(([identifier, draft]) => (
      identifier === state.currentFileId || draft.rootFileIds?.has(state.currentFileId)
    ));
    if (!affected.length) return;
    for (const [identifier, draft] of affected) {
      draft.operations = [];
      state.staleDrafts.delete(identifier);
    }
    renderSyncButton(state.currentFileId);
    renderTree(); applyDrafts(); syncDirtyState();
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
      const operations = [...draft.annotations, ...draft.operations].map(({ _key, previewUrl, _previewOperations, ...operation }) => operation);
      if (!operations.length) return null;
      return { fileId: identifier, sha256: file.sha256, operations, dependencyGroup: dependencyByFile.get(identifier) || null };
    }).filter(Boolean);
  }

  const REQUEST_STATUS_LABELS = {
    pending: "待交给 Agent",
    processing: "Agent 处理中",
    success: "处理成功",
    partial: "部分成功",
    failed: "处理失败",
    aborted: "已中止",
  };

  function requestStatusNote(request) {
    if (request.status === "pending") return "请将执行指令粘贴到当前 Agent";
    if (request.status === "processing") return "请求涉及的文件暂时锁定编辑";
    return request.reason || `${request.fileCount} 个文件，${request.operationCount} 项操作`;
  }

  function renderRequestStatus() {
    const request = state.activeRequest || state.requests[0] || null;
    const dismissed = Boolean(request?.status === "success" && state.dismissedRequestIds.has(request.requestId));
    els.requestStatus.classList.toggle("hidden", !request || dismissed);
    if (request) {
      const badge = $("#request-status-badge");
      badge.textContent = REQUEST_STATUS_LABELS[request.status] || request.status;
      badge.className = `request-badge ${request.status}`;
      $("#request-status-id").textContent = request.requestId.slice(0, 8);
      $("#request-status-note").textContent = requestStatusNote(request);
      $("#request-copy").classList.toggle("hidden", request.status !== "pending");
      $("#request-cancel").classList.toggle("hidden", request.status !== "pending");
      $("#request-dismiss").classList.toggle("hidden", request.status !== "success");
    }
    const active = isActiveRequest();
    const send = $("#send-ai");
    send.disabled = active;
    if (active) send.dataset.tooltip = "当前请求完成或中止后才能再次发送";
    else delete send.dataset.tooltip;
    updateEditingLock();
  }

  function applyRequestListing(listing) {
    if (Number(listing.revision || 0) < state.requestRevision) return;
    state.requestRevision = Number(listing.revision || state.requestRevision);
    state.requests = listing.requests || [];
    state.activeRequest = listing.activeRequest || null;
    state.syncPages = listing.syncPages || [];
    renderRequestStatus();
    renderTree();
    renderSyncButton();
  }

  function openRequestDialog(request, title = "变更包已生成", copy = "请将以下执行指令粘贴到当前 Agent。工作台不会直接控制 Agent 会话。") {
    $("#request-dialog-title").textContent = title;
    $("#request-dialog-copy").textContent = copy;
    $("#request-meta").classList.toggle("hidden", !request);
    if (request) {
      $("#request-id").textContent = request.requestId;
      $("#request-dialog-status").textContent = REQUEST_STATUS_LABELS[request.status] || request.status;
      $("#request-file-count").textContent = String(request.fileCount);
      $("#request-operation-count").textContent = String(request.operationCount);
    }
    $("#request-instruction").value = request?.instruction || "";
    $("#clipboard-status").textContent = "";
    $("#clipboard-status").className = "clipboard-status";
    $("#request-dialog").showModal();
  }

  async function copyInstruction(instruction = $("#request-instruction").value) {
    const status = $("#clipboard-status");
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(instruction);
      status.textContent = "执行指令已复制到剪贴板。";
      status.className = "clipboard-status success";
      return true;
    } catch (_error) {
      status.textContent = "浏览器未允许自动复制，请点击“复制指令”重试或手动选择文本。";
      status.className = "clipboard-status warn";
      return false;
    }
  }

  async function refreshRequestListing() {
    applyRequestListing(await api("/api/requests"));
  }

  function cancelActiveRequest() {
    const request = state.activeRequest;
    if (!request || request.status !== "pending") return;
    confirmAction("取消待处理请求", "取消后不会恢复发送时已清空的草稿。确定取消这个请求吗？", async () => {
      await api(`/api/requests/${encodeURIComponent(request.requestId)}/cancel`, {});
      const results = await api("/api/results");
      state.results = results.results || [];
      state.latestResultId = request.requestId;
      await refreshRequestListing();
      toast("待处理请求已取消；已发送草稿不会恢复。", "warn");
    });
  }

  function showRequestDetails() {
    const request = state.activeRequest || state.requests[0];
    if (!request) return;
    const result = state.results.find((item) => item.requestId === request.requestId);
    if (result && !isActiveRequest(request)) showResults([result]);
    else openRequestDialog(request, "Agent 请求详情");
  }

  function dismissRequestStatus() {
    const request = state.activeRequest || state.requests[0];
    if (!request || request.status !== "success") return;
    // 只关闭当前会话中的成功提示，不删除持久化请求和逐文件结果。
    state.dismissedRequestIds.add(request.requestId);
    renderRequestStatus();
  }

  async function sendRequest() {
    if (state.staleDrafts.size) return toast("源文件已在外部变化，请刷新后重新编辑再发送。", "error");
    if (isActiveRequest()) return toast("当前 Agent 请求尚未完成，暂时不能再次发送。", "warn");
    const files = requestFiles();
    if (!files.length) return toast("当前会话没有待发送修改。", "warn");
    const button = $("#send-ai"); button.disabled = true;
    try {
      const result = await api("/api/requests", { schemaVersion: 1, files });
      state.drafts.clear(); state.staleDrafts.clear(); renderTree(); applyDrafts(); syncDirtyState();
      selectFile(state.currentFileId, true);
      state.activeRequest = result.request;
      state.requestRevision = Number(result.revision || state.requestRevision);
      state.requests = [result.request, ...state.requests.filter((item) => item.requestId !== result.requestId)];
      renderRequestStatus();
      openRequestDialog(result.request);
      const copied = await copyInstruction(result.instruction);
      toast(copied ? "变更包已生成，执行指令已复制。" : "变更包已生成，请手动复制执行指令。", copied ? "" : "warn");
    } catch (error) { toast(error.message, "error"); }
    finally { renderRequestStatus(); }
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

  function enterClosedState() {
    state.serviceClosed = true;
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = null;
    state.drafts.clear();
    state.staleDrafts.clear();
    state.selection = null;
    state.editingAnnotation = null;
    clearSelectionPanel();
    els.connectionDot.classList.add("offline");
    els.connectionCopy.textContent = "服务已关闭";
    document.title = "Prototype Studio - 已关闭";
    els.serviceClosed.classList.remove("hidden");
  }

  async function shutdownWorkbench() {
    const button = $("#shutdown-workbench");
    button.disabled = true;
    try {
      await api("/api/shutdown", {});
      enterClosedState();
    } catch (error) {
      button.disabled = false;
      toast(`关闭工作台失败：${error.message}`, "error");
    }
  }

  function confirmShutdown() {
    const dirtyCount = dirtyIds().length;
    const copy = dirtyCount
      ? `当前有 ${dirtyCount} 个 HTML 文件包含未发送修改。关闭进程后，这些批注、样式、内容、图片、CSS 和同步草稿将全部丢失；已生成的 Agent 请求不会被取消。`
      : "关闭后需要通过 Skill 重新启动工作台；已生成或正在执行的 Agent 请求不会被取消。";
    confirmAction("关闭工作台进程", copy, shutdownWorkbench, "关闭进程");
  }

  async function poll() {
    if (state.serviceClosed) return;
    try {
      const [workspace, serviceState, requests, results] = await Promise.all([api("/api/workspace"), api("/api/state"), api("/api/requests"), api("/api/results")]);
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
      if (Number(requests.revision || 0) >= state.requestRevision) {
        state.requestRevision = Number(requests.revision || state.requestRevision);
        state.requests = requests.requests || [];
        state.activeRequest = requests.activeRequest || null;
        state.syncPages = requests.syncPages || [];
      }
      state.results = results.results || [];
      if (!previousSha && state.currentFileId && !fileById(state.currentFileId)) selectFile(workspace.currentFileId, true);
      renderTree();
      renderRequestStatus();
      const latest = state.results[0];
      if (latest?.requestId && latest.requestId !== state.latestResultId) { state.latestResultId = latest.requestId; showResults(state.results); }
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

  async function cleanupMissingFiles(event) {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const workspace = await api("/api/workspace/cleanup-missing", {});
      state.workspace = workspace;
      if (!fileById(state.currentFileId)) selectFile(workspace.currentFileId, true);
      else renderTree();
      toast("已清理缺失 HTML 的工作区记录。" );
    } catch (error) { toast(error.message, "error"); }
    finally { button.disabled = false; }
  }

  function updateSelectMode(active) {
    state.selectMode = active;
    els.selectMode.classList.toggle("active", active);
    $("span", els.selectMode).textContent = active ? "正在选择" : "选择元素";
    postPreview("select-mode", { active });
  }

  function bindChrome() {
    $("#shutdown-workbench").addEventListener("click", confirmShutdown);
    $("#refresh-files").addEventListener("click", refreshProjectFiles);
    $("#cleanup-missing-files").addEventListener("click", cleanupMissingFiles);
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
      sidebarTimer = setTimeout(() => { state.temporarySidebar = false; els.layout.classList.add("sidebar-collapsed"); }, 200);
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
    els.selectMode.addEventListener("click", () => updateSelectMode(!state.selectMode));
    els.clearAnnotations.addEventListener("click", clearCurrentAnnotations);
    $$(".tab").forEach((button) => button.addEventListener("click", () => {
      $$(".tab").forEach((item) => item.classList.toggle("active", item === button));
      $$(".tab-panel").forEach((panel) => panel.classList.toggle("hidden", panel.dataset.panel !== button.dataset.tab));
    }));
    $("#sync-pages").addEventListener("click", syncPages); $("#clear-current").addEventListener("click", clearCurrent);
    $("#send-ai").addEventListener("click", sendRequest);
    $("#copy-instruction").addEventListener("click", async () => {
      const copyTask = copyInstruction();
      $("#request-dialog").close();
      const copied = await copyTask;
      toast(copied ? "执行指令已复制。" : "无法自动复制，请从请求详情中重试。", copied ? "" : "warn");
    });
    $("#request-copy").addEventListener("click", async () => {
      const copied = await copyInstruction(state.activeRequest?.instruction || state.requests[0]?.instruction || "");
      toast(copied ? "执行指令已再次复制。" : "无法自动复制，请在详情中手动选择指令。", copied ? "" : "warn");
    });
    $("#request-cancel").addEventListener("click", cancelActiveRequest);
    $("#request-dismiss").addEventListener("click", dismissRequestStatus);
    $("#request-details").addEventListener("click", showRequestDetails);
    $("#save-annotation").addEventListener("click", saveAnnotation); $("#choose-image").addEventListener("click", chooseImage);
    let tooltipTimer;
    document.addEventListener("mousemove", (event) => {
      const target = event.target.closest?.("[data-tooltip]");
      clearTimeout(tooltipTimer);
      if (!target) return els.tooltip.classList.add("hidden");
      const point = { x: event.clientX, y: event.clientY };
      tooltipTimer = setTimeout(() => {
        els.tooltip.textContent = target.dataset.tooltip;
        els.tooltip.style.left = "0px";
        els.tooltip.style.top = "0px";
        els.tooltip.classList.remove("hidden");
        const rect = els.tooltip.getBoundingClientRect();
        const gap = 10;
        const edge = 8;
        // 靠近视口边缘时反向放置，避免提示被压缩后异常换行。
        const left = point.x + gap + rect.width <= innerWidth - edge ? point.x + gap : point.x - gap - rect.width;
        const top = point.y + gap + rect.height <= innerHeight - edge ? point.y + gap : point.y - gap - rect.height;
        els.tooltip.style.left = `${Math.max(edge, Math.min(innerWidth - edge - rect.width, left))}px`;
        els.tooltip.style.top = `${Math.max(edge, Math.min(innerHeight - edge - rect.height, top))}px`;
      }, 500);
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
      populateSelection(message.selection);
    } else if (message.type === "annotation-request") openAnnotation(message.selection);
    else if (message.type === "annotation-edit") openAnnotation(null, message.annotation);
    else if (message.type === "annotation-delete") confirmAction("删除批注", "删除当前批注内容？该操作只影响会话草稿。", () => deleteAnnotation(message.annotation));
    else if (message.type === "canvas-wheel") {
      const point = previewPointToPage(message.point);
      setZoom(state.zoom + (message.deltaY < 0 ? 5 : -5), point);
    } else if (message.type === "canvas-pan-start" && (state.zoom > 100 || message.scrollable)) {
      state.remotePanPoint = previewPointToPage(message.point);
      state.remotePanMode = state.zoom > 100 ? "zoom" : "scroll";
      els.viewport.classList.add("panning");
    } else if (message.type === "canvas-pan-move" && state.remotePanPoint) {
      const point = previewPointToPage(message.point);
      if (state.remotePanMode === "zoom") {
        state.pan.x += point.x - state.remotePanPoint.x;
        state.pan.y += point.y - state.remotePanPoint.y;
        updateZoom(false);
      } else {
        postPreview("scroll-page", { deltaX: state.remotePanPoint.x - point.x, deltaY: state.remotePanPoint.y - point.y });
      }
      state.remotePanPoint = point;
    } else if (message.type === "canvas-pan-end") {
      state.remotePanPoint = null;
      state.remotePanMode = null;
      els.viewport.classList.remove("panning");
    }
  });

  async function init() {
    if (!token) return toast("缺少工作台实例令牌，请通过 ensure 命令重新打开。", "error");
    bindChrome(); bindCanvas(); bindPropertyInputs(); bindColors(); bindEffects();
    new ResizeObserver(() => resizePreviewShell()).observe(els.viewport);
    try {
      const [workspace, requests, results] = await Promise.all([api("/api/workspace"), api("/api/requests"), api("/api/results")]);
      state.workspace = workspace;
      state.requests = requests.requests || [];
      state.activeRequest = requests.activeRequest || null;
      state.syncPages = requests.syncPages || [];
      state.requestRevision = Number(requests.revision || 0);
      state.results = results.results || [];
      state.latestResultId = state.results[0]?.requestId || null;
      await loadSystemFonts(false);
      state.currentFileId = state.workspace.currentFileId;
      state.workspace.files.forEach((file) => state.lastSha.set(file.id, file.sha256));
      els.project.textContent = state.workspace.projectName; renderTree(); selectFile(state.currentFileId, true);
      renderRequestStatus();
      state.pollTimer = setInterval(poll, 2000);
    } catch (error) { toast(error.message, "error"); els.connectionDot.classList.add("offline"); }
  }

  init();
})();
