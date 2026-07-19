(() => {
  "use strict";

  if (window.parent !== window.top || window.__YCET_EDITOR_RUNTIME__) return;
  window.__YCET_EDITOR_RUNTIME__ = true;

  const CHANNEL = "ycet-editor";
  const config = window.__YCET_EDITOR_CONFIG__ || {};
  const contexts = new Map();
  let selectMode = true;
  let selected = null;
  let hoverBox = null;
  let selectionBox = null;
  let nameBadge = null;
  let annotateButton = null;
  let annotations = [];
  let canvasPanning = false;
  let overlayFrame = 0;
  const originalText = new WeakMap();

  function emit(type, payload = {}) {
    window.parent.postMessage({ channel: CHANNEL, version: 1, type, ...payload }, window.location.origin);
  }

  function safeFrame(frame) {
    try {
      return frame.contentDocument && frame.contentWindow ? frame.contentDocument : null;
    } catch (_error) {
      return null;
    }
  }

  function cssEscape(value) {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return String(value).replace(/[^a-zA-Z0-9_-]/g, (char) => `\\${char.codePointAt(0).toString(16)} `);
  }

  function uniqueSelector(element, doc) {
    if (element.id) {
      const selector = `#${cssEscape(element.id)}`;
      if (doc.querySelectorAll(selector).length === 1) return selector;
    }
    const parts = [];
    let node = element;
    while (node && node.nodeType === 1 && node !== doc.documentElement) {
      let part = node.tagName.toLowerCase();
      const classes = [...node.classList].filter((item) => !item.startsWith("ycet-editor-")).slice(0, 3);
      if (classes.length) part += classes.map((item) => `.${cssEscape(item)}`).join("");
      const parent = node.parentElement;
      if (parent) {
        const matches = [...parent.children].filter((item) => item.tagName === node.tagName);
        if (matches.length > 1) part += `:nth-of-type(${matches.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      const selector = parts.join(" > ");
      try {
        if (doc.querySelectorAll(selector).length === 1) return selector;
      } catch (_error) {
        // 继续向祖先扩展选择器。
      }
      node = parent;
    }
    return parts.join(" > ") || element.tagName.toLowerCase();
  }

  function textFeature(element) {
    return (element.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80);
  }

  function framePathFor(doc) {
    return contexts.get(doc)?.framePath || [];
  }

  function docConfig(doc) {
    try {
      return doc.defaultView.__YCET_EDITOR_CONFIG__ || config;
    } catch (_error) {
      return config;
    }
  }

  function fingerprint(element) {
    const doc = element.ownerDocument;
    const ancestors = [];
    let node = element.parentElement;
    for (let index = 0; node && index < 5; index += 1, node = node.parentElement) {
      ancestors.push({ tag: node.tagName.toLowerCase(), id: node.id || "", classes: [...node.classList].slice(0, 3) });
    }
    return {
      framePath: framePathFor(doc),
      selector: uniqueSelector(element, doc),
      tag: element.tagName.toLowerCase(),
      id: element.id || "",
      classes: [...element.classList].filter((item) => !item.startsWith("ycet-editor-")).slice(0, 8),
      textFeature: textFeature(element),
      ancestors,
      siblingIndex: element.parentElement ? [...element.parentElement.children].indexOf(element) : 0,
    };
  }

  function textNodes(element) {
    const nodes = [];
    const walker = element.ownerDocument.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    while (walker.nextNode() && nodes.length < 20) nodes.push(walker.currentNode);
    return nodes;
  }

  function selectionPayload(element) {
    const doc = element.ownerDocument;
    const meta = docConfig(doc);
    const style = doc.defaultView.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return {
      fileId: meta.fileId || config.fileId,
      rootFileId: config.rootFileId || config.fileId,
      path: meta.path || config.path,
      sha256: meta.sha256 || config.sha256,
      fingerprint: fingerprint(element),
      element: {
        name: element.id ? `${element.tagName.toLowerCase()}#${element.id}` : element.tagName.toLowerCase(),
        tag: element.tagName.toLowerCase(),
        classes: [...element.classList].slice(0, 8),
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) },
        styles: {
          position: style.position,
          left: style.left,
          top: style.top,
          width: style.width,
          height: style.height,
          display: style.display,
          flexDirection: style.flexDirection,
          justifyContent: style.justifyContent,
          alignItems: style.alignItems,
          gap: style.gap,
          opacity: style.opacity,
          borderTopLeftRadius: style.borderTopLeftRadius,
          borderTopRightRadius: style.borderTopRightRadius,
          borderBottomLeftRadius: style.borderBottomLeftRadius,
          borderBottomRightRadius: style.borderBottomRightRadius,
          fontFamily: style.fontFamily,
          fontWeight: style.fontWeight,
          fontSize: style.fontSize,
          color: style.color,
          lineHeight: style.lineHeight,
          letterSpacing: style.letterSpacing,
          textAlign: style.textAlign,
          backgroundColor: style.backgroundColor,
          borderColor: style.borderColor,
          borderWidth: style.borderWidth,
          borderStyle: style.borderStyle,
          boxShadow: style.boxShadow,
          filter: style.filter,
          backdropFilter: style.backdropFilter,
          transform: style.transform,
        },
        textFields: textNodes(element).map((node, index) => ({ index, value: node.nodeValue.trim() })),
        imageSource: element instanceof doc.defaultView.HTMLImageElement ? element.getAttribute("src") || "" : "",
      },
    };
  }

  function intersectRect(rect, bounds) {
    const left = Math.max(rect.left, bounds.left);
    const top = Math.max(rect.top, bounds.top);
    const right = Math.min(rect.left + rect.width, bounds.left + bounds.width);
    const bottom = Math.min(rect.top + rect.height, bounds.top + bounds.height);
    return right > left && bottom > top ? { left, top, width: right - left, height: bottom - top } : null;
  }

  function rootCoordinates(element) {
    let currentWindow = element.ownerDocument.defaultView;
    let visible = intersectRect(element.getBoundingClientRect(), { left: 0, top: 0, width: currentWindow.innerWidth, height: currentWindow.innerHeight });
    if (!visible) return null;
    while (currentWindow && currentWindow !== window) {
      const frame = currentWindow.frameElement;
      if (!frame) break;
      const frameRect = frame.getBoundingClientRect();
      const layoutWidth = frame.offsetWidth;
      const layoutHeight = frame.offsetHeight;
      if (!layoutWidth || !layoutHeight || !frameRect.width || !frameRect.height) return null;
      const scaleX = frameRect.width / layoutWidth;
      const scaleY = frameRect.height / layoutHeight;
      const contentBounds = {
        left: frameRect.left + frame.clientLeft * scaleX,
        top: frameRect.top + frame.clientTop * scaleY,
        width: frame.clientWidth * scaleX,
        height: frame.clientHeight * scaleY,
      };
      // 子文档坐标必须经过当前 iframe 的实际显示比例，再映射到父文档视口。
      visible = {
        left: contentBounds.left + visible.left * scaleX,
        top: contentBounds.top + visible.top * scaleY,
        width: visible.width * scaleX,
        height: visible.height * scaleY,
      };
      visible = intersectRect(visible, contentBounds);
      if (!visible) return null;
      currentWindow = frame.ownerDocument.defaultView;
      visible = intersectRect(visible, { left: 0, top: 0, width: currentWindow.innerWidth, height: currentWindow.innerHeight });
      if (!visible) return null;
    }
    return visible;
  }

  function overlay(className) {
    const node = document.createElement("div");
    node.className = `ycet-editor-overlay ${className}`;
    document.documentElement.appendChild(node);
    return node;
  }

  function ensureOverlay() {
    if (hoverBox) return;
    const style = document.createElement("style");
    style.dataset.ycetEditor = "runtime";
    style.textContent = `
      .ycet-editor-overlay{position:fixed;z-index:2147483600;pointer-events:none;box-sizing:border-box;font:12px/1.2 system-ui,sans-serif}
      .ycet-editor-hover{border:1.5px solid #4f8cff;background:rgba(79,140,255,.08)}
      .ycet-editor-selected{border:2px solid #16a34a;background:rgba(22,163,74,.06)}
      .ycet-editor-name{padding:4px 6px;border-radius:4px;color:#fff;background:#4f8cff;white-space:nowrap}
      .ycet-editor-annotate{padding:5px 9px;border:0;border-radius:5px;color:#fff;background:#4f8cff;box-shadow:0 4px 16px rgba(0,0,0,.2);pointer-events:auto;cursor:pointer}
      .ycet-editor-marker{display:grid;width:24px;height:24px;place-items:center;border:2px solid #fff;border-radius:50%;color:#fff;background:#ef4444;box-shadow:0 3px 12px rgba(0,0,0,.25);font-weight:700;pointer-events:auto;cursor:pointer}
      .ycet-editor-note{display:none;position:absolute;left:28px;top:0;width:240px;padding:9px;border:1px solid #dbeafe;border-radius:6px;color:#102033;background:#fff;box-shadow:0 12px 30px rgba(16,32,51,.18);white-space:normal}
      .ycet-editor-marker:hover .ycet-editor-note{display:block}
    `;
    document.head.appendChild(style);
    hoverBox = overlay("ycet-editor-hover");
    selectionBox = overlay("ycet-editor-selected");
    nameBadge = overlay("ycet-editor-name");
    annotateButton = document.createElement("button");
    annotateButton.type = "button";
    annotateButton.className = "ycet-editor-overlay ycet-editor-annotate";
    annotateButton.textContent = "批注";
    annotateButton.addEventListener("click", () => selected && emit("annotation-request", { selection: selectionPayload(selected) }));
    document.documentElement.appendChild(annotateButton);
    [hoverBox, selectionBox, nameBadge, annotateButton].forEach((node) => { node.hidden = true; });
  }

  function place(node, rect, extra = {}) {
    Object.assign(node.style, {
      left: `${Math.max(0, rect.left)}px`,
      top: `${Math.max(0, rect.top)}px`,
      width: `${Math.max(0, rect.width)}px`,
      height: `${Math.max(0, rect.height)}px`,
      ...extra,
    });
    node.hidden = false;
  }

  function drawHover(element) {
    ensureOverlay();
    const rect = rootCoordinates(element);
    if (!rect) {
      hoverBox.hidden = true;
      nameBadge.hidden = true;
      return;
    }
    place(hoverBox, rect);
    nameBadge.textContent = element.id ? `${element.tagName.toLowerCase()}#${element.id}` : element.tagName.toLowerCase();
    place(nameBadge, rect, { width: "auto", height: "auto", top: `${Math.max(0, rect.top - 25)}px` });
  }

  function drawSelection(element) {
    ensureOverlay();
    const rect = rootCoordinates(element);
    if (!rect) {
      selectionBox.hidden = true;
      annotateButton.hidden = true;
      return;
    }
    place(selectionBox, rect);
    place(annotateButton, rect, { width: "auto", height: "auto", left: "0px", top: "0px", visibility: "hidden" });
    const buttonRect = annotateButton.getBoundingClientRect();
    const gap = 6;
    const candidates = [
      { left: rect.left, top: rect.top - buttonRect.height - gap },
      { left: rect.left + rect.width + gap, top: rect.top },
      { left: rect.left, top: rect.top + rect.height + gap },
      { left: rect.left - buttonRect.width - gap, top: rect.top },
    ];
    const position = candidates.find((item) => (
      item.left >= 0 && item.top >= 0
      && item.left + buttonRect.width <= window.innerWidth
      && item.top + buttonRect.height <= window.innerHeight
    )) || candidates[0];
    Object.assign(annotateButton.style, {
      left: `${Math.max(0, Math.min(window.innerWidth - buttonRect.width, position.left))}px`,
      top: `${Math.max(0, Math.min(window.innerHeight - buttonRect.height, position.top))}px`,
      visibility: "visible",
    });
  }

  function scheduleOverlayRefresh() {
    if (overlayFrame) return;
    overlayFrame = requestAnimationFrame(() => {
      overlayFrame = 0;
      if (selectMode && selected?.isConnected) drawSelection(selected);
      else if (selectionBox) {
        selectionBox.hidden = true;
        annotateButton.hidden = true;
      }
      renderAnnotations(annotations);
    });
  }

  function eventElement(event) {
    const element = event.target;
    return element instanceof event.view.Element ? element : null;
  }

  function rootPoint(event) {
    let x = event.clientX;
    let y = event.clientY;
    let currentWindow = event.view;
    while (currentWindow && currentWindow !== window) {
      const frame = currentWindow.frameElement;
      if (!frame) break;
      const rect = frame.getBoundingClientRect();
      x += rect.left;
      y += rect.top;
      currentWindow = frame.ownerDocument.defaultView;
    }
    return { x, y };
  }

  function onWheel(event) {
    if (!event.ctrlKey) return;
    event.preventDefault();
    emit("canvas-wheel", { point: rootPoint(event), deltaY: event.deltaY, ctrlKey: true });
  }

  function onMouseDown(event) {
    if (event.button !== 1) return;
    event.preventDefault();
    canvasPanning = true;
    emit("canvas-pan-start", { point: rootPoint(event) });
  }

  function onMouseMove(event) {
    if (!canvasPanning || !(event.buttons & 4)) return;
    event.preventDefault();
    emit("canvas-pan-move", { point: rootPoint(event) });
  }

  function onMouseUp(event) {
    if (event.button !== 1 || !canvasPanning) return;
    canvasPanning = false;
    emit("canvas-pan-end", { point: rootPoint(event) });
  }

  function onMove(event) {
    if (!selectMode) return;
    const element = eventElement(event);
    if (!element || element.closest?.(".ycet-editor-overlay")) return;
    drawHover(element);
  }

  function onLeave() {
    if (hoverBox) {
      hoverBox.hidden = true;
      nameBadge.hidden = true;
    }
  }

  function onClick(event) {
    if (!selectMode) return;
    const element = eventElement(event);
    if (!element || element.closest?.(".ycet-editor-overlay")) return;
    event.preventDefault();
    event.stopPropagation();
    selected = element;
    drawSelection(element);
    emit("selection", { selection: selectionPayload(element) });
  }

  function installDocument(doc, framePath = []) {
    if (!doc || contexts.has(doc)) return;
    contexts.set(doc, { framePath });
    doc.addEventListener("mousemove", onMove, true);
    doc.addEventListener("mouseleave", onLeave, true);
    doc.addEventListener("click", onClick, true);
    doc.addEventListener("wheel", onWheel, { capture: true, passive: false });
    doc.addEventListener("mousedown", onMouseDown, true);
    doc.addEventListener("mousemove", onMouseMove, true);
    doc.addEventListener("mouseup", onMouseUp, true);
    doc.addEventListener("scroll", scheduleOverlayRefresh, true);
    [...doc.querySelectorAll("iframe")].forEach((frame, index) => installFrame(frame, [...framePath, index]));
    const observer = new MutationObserver((changes) => {
      for (const change of changes) {
        for (const node of change.addedNodes) {
          if (node.nodeType !== 1) continue;
          if (node.tagName === "IFRAME") installFrame(node, [...framePath, [...doc.querySelectorAll("iframe")].indexOf(node)]);
          node.querySelectorAll?.("iframe").forEach((frame, index) => installFrame(frame, [...framePath, index]));
        }
      }
    });
    observer.observe(doc.documentElement, { childList: true, subtree: true });
  }

  function installFrame(frame, framePath) {
    const attach = () => {
      const doc = safeFrame(frame);
      if (doc) installDocument(doc, framePath);
    };
    frame.addEventListener("load", () => setTimeout(attach, 0));
    attach();
  }

  function findContext(framePath = []) {
    let doc = document;
    for (const index of framePath) {
      const frame = doc.querySelectorAll("iframe")[Number(index)];
      doc = frame ? safeFrame(frame) : null;
      if (!doc) return null;
    }
    return doc;
  }

  function findElement(operation) {
    let doc = null;
    if (operation.fileId) {
      for (const candidate of contexts.keys()) {
        if (docConfig(candidate).fileId === operation.fileId) {
          doc = candidate;
          break;
        }
      }
    }
    doc ||= findContext(operation.fingerprint?.framePath || []);
    if (!doc) return null;
    try {
      const matches = [...doc.querySelectorAll(operation.fingerprint.selector)];
      if (matches.length !== 1) return null;
      return matches[0];
    } catch (_error) {
      return null;
    }
  }

  function applyOperation(operation) {
    const element = findElement(operation);
    if (!element) return;
    if (operation.type === "style" || operation.type === "css") {
      element.style.setProperty(operation.property, operation.value);
    } else if (operation.type === "text") {
      const node = textNodes(element)[Number(operation.index)];
      if (node) {
        if (!originalText.has(node)) originalText.set(node, node.nodeValue);
        node.nodeValue = operation.value;
      }
    } else if (operation.type === "image-replace" && element.tagName === "IMG") {
      element.src = operation.previewUrl;
    }
  }

  function clearPreview() {
    for (const doc of contexts.keys()) {
      doc.querySelectorAll("[data-ycet-editor-original-style]").forEach((element) => {
        const original = element.getAttribute("data-ycet-editor-original-style");
        if (original) element.setAttribute("style", original); else element.removeAttribute("style");
        element.removeAttribute("data-ycet-editor-original-style");
      });
      doc.querySelectorAll("[data-ycet-editor-original-src]").forEach((element) => {
        element.setAttribute("src", element.getAttribute("data-ycet-editor-original-src"));
        element.removeAttribute("data-ycet-editor-original-src");
      });
      doc.querySelectorAll("[data-ycet-editor-original-text]").forEach((element) => {
        element.textContent = element.getAttribute("data-ycet-editor-original-text");
        element.removeAttribute("data-ycet-editor-original-text");
      });
      const walker = doc.createTreeWalker(doc.documentElement, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (originalText.has(node)) {
          node.nodeValue = originalText.get(node);
          originalText.delete(node);
        }
      }
    }
  }

  function applyOperations(operations) {
    clearPreview();
    for (const operation of operations || []) {
      const element = findElement(operation);
      if (!element) continue;
      if ((operation.type === "style" || operation.type === "css") && !element.hasAttribute("data-ycet-editor-original-style")) {
        element.setAttribute("data-ycet-editor-original-style", element.getAttribute("style") || "");
      }
      if (operation.type === "image-replace" && !element.hasAttribute("data-ycet-editor-original-src")) {
        element.setAttribute("data-ycet-editor-original-src", element.getAttribute("src") || "");
      }
      applyOperation(operation);
    }
    scheduleOverlayRefresh();
  }

  function renderAnnotations(items) {
    document.querySelectorAll(".ycet-editor-marker").forEach((node) => node.remove());
    annotations = items || [];
    annotations.forEach((annotation, index) => {
      const element = findElement(annotation);
      if (!element) return;
      const rect = rootCoordinates(element);
      if (!rect) return;
      const marker = document.createElement("button");
      marker.type = "button";
      marker.className = "ycet-editor-overlay ycet-editor-marker";
      marker.style.left = `${Math.max(0, rect.left + rect.width - 12)}px`;
      marker.style.top = `${Math.max(0, rect.top - 12)}px`;
      const number = document.createTextNode(String(index + 1));
      const note = document.createElement("span");
      note.className = "ycet-editor-note";
      const copy = document.createElement("span");
      copy.textContent = annotation.text;
      const actions = document.createElement("span");
      actions.style.cssText = "display:flex;gap:6px;margin-top:8px";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.textContent = "编辑";
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "删除";
      [edit, remove].forEach((button) => { button.style.cssText = "padding:3px 7px;border:1px solid #dbeafe;border-radius:4px;background:#fff;cursor:pointer"; });
      edit.addEventListener("click", (event) => { event.stopPropagation(); emit("annotation-edit", { annotation }); });
      remove.addEventListener("click", (event) => { event.stopPropagation(); emit("annotation-delete", { annotation }); });
      actions.append(edit, remove);
      note.append(copy, actions);
      marker.append(number, note);
      let hideTimer;
      marker.addEventListener("mouseenter", () => { clearTimeout(hideTimer); note.style.display = "block"; });
      marker.addEventListener("mouseleave", () => {
        note.style.display = "block";
        hideTimer = setTimeout(() => { note.style.display = "none"; }, 1000);
      });
      document.documentElement.appendChild(marker);
    });
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || event.source !== window.parent) return;
    const message = event.data || {};
    if (message.channel !== CHANNEL) return;
    if (message.type === "select-mode") {
      selectMode = Boolean(message.active);
      if (!selectMode && hoverBox) {
        hoverBox.hidden = true;
        nameBadge.hidden = true;
        selectionBox.hidden = true;
        annotateButton.hidden = true;
      }
    } else if (message.type === "apply") {
      applyOperations(message.operations);
      renderAnnotations(message.annotations);
    } else if (message.type === "annotations") {
      renderAnnotations(message.annotations);
    } else if (message.type === "refresh-selection" && selected) {
      scheduleOverlayRefresh();
      emit("selection", { selection: selectionPayload(selected) });
    } else if (message.type === "scroll-page") {
      window.scrollBy({ left: Number(message.deltaX) || 0, top: Number(message.deltaY) || 0, behavior: "auto" });
    }
  });

  ensureOverlay();
  installDocument(document, []);
  const emitMetrics = () => emit("metrics", {
    metrics: {
      contentWidth: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0, window.innerWidth),
      contentHeight: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0, window.innerHeight),
    },
  });
  emit("ready", { fileId: config.fileId, rootFileId: config.rootFileId || config.fileId, path: config.path, sha256: config.sha256 });
  requestAnimationFrame(emitMetrics);
  window.addEventListener("load", () => requestAnimationFrame(emitMetrics), { once: true });
  window.addEventListener("resize", () => {
    requestAnimationFrame(emitMetrics);
    scheduleOverlayRefresh();
  });
})();
