[![中文](https://img.shields.io/badge/简体中文-red?style=for-the-badge)](README.md)
[![EN](https://img.shields.io/badge/English-blue?style=for-the-badge)](README_en.md)

<div align="center">

![YCET Prototype Create](assets/cover/prototype-cover.png)

# YCET Prototype Create

`ycet-prototype-create` is a product prototyping Skill for AI agents such as Codex, Claude Code, and OpenCode. It covers product requirement clarification, UI direction confirmation, high-fidelity static prototypes, visual precision editing, multi-page interactive demos, takeover and migration of existing HTML/image prototypes, and offline single-file mobile previews.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/version-v3.0.10-blue?style=for-the-badge)](#-quick-start)
[![Agent Skill](https://img.shields.io/badge/type-Agent%20Skill-purple?style=for-the-badge)](#-quick-start)
[![GitHub last commit](https://img.shields.io/github/last-commit/Ycet/ycet-prototype-create?style=for-the-badge&logo=github)](../../commits)

</div>

---

# 📚 Table of Contents

- [✨ Quick Start](#-quick-start)
- [📖 Feature Overview](#-feature-overview)
- [🎬 Demo Previews](#-demo-previews)
- [🖥️ Workbench Architecture & Lifecycle](#️-workbench-architecture--lifecycle)
- [💻 Command Line Interface](#-command-line-interface)
- [🤝 Agent Handoff Protocol](#-agent-handoff-protocol)
- [📁 Workspace State & File Safety](#-workspace-state--file-safety)
- [🔗 Feature-to-Workbench Relationship](#-feature-to-workbench-relationship)
- [🛡️ Security Rules](#️-security-rules)
- [🧪 Environment & Verification](#-environment--verification)
- [📄 Documentation Index](#-documentation-index)
- [⚠️ Known Limitations](#️-known-limitations)
- [📜 License](#-license)

---

## ✨ Quick Start

### Installation

Install the deliverable directory `outputs/skills/ycet-prototype-create/` as an Agent Skill:

<details>
<summary>Claude Code / Codex / OpenCode (Windows)</summary>

```powershell
# Example with Claude Code: copy to the global Skill directory
Copy-Item -Recurse outputs\skills\ycet-prototype-create $env:USERPROFILE\.claude\skills\ycet-prototype-create
```

</details>

<details>
<summary>macOS / Linux</summary>

```bash
# Example with Claude Code: copy to the global Skill directory
cp -r outputs/skills/ycet-prototype-create ~/.claude/skills/ycet-prototype-create
```

</details>

### Usage

Trigger `ycet-prototype-create` in an agent session and follow this flow to build prototypes:

1. **Feature 1**: Generate a high-fidelity static prototype from scattered ideas or a PRD (requirement clarification → UI direction confirmation → static page generation).
2. **Feature 2**: Start the local workbench for visual precision editing of prototype pages (element selection, annotations, property adjustments, change-package handoff).
3. **Feature 3**: Convert confirmed static pages into a multi-page interactive demo.
4. **Feature 4**: Take over and migrate existing HTML or full-page image prototypes.
5. **Feature 5**: Package a mobile offline single-file prototype.

All prototype artifacts are written to `prototype/` under the user's project root; workbench runtime state is written separately to `.ycet-editor/` under the user's project root.

---

## 📖 Feature Overview

This project splits prototyping into five features, each with a clear confirmation gate. The following boundaries are mandatory rules:

- Web preview, element selection, annotations, and property adjustments only produce browser-session drafts; they never modify HTML, images, or other resources on disk before sending.
- Source files may only be modified after an Agent claims and executes a workbench change package.
- External HTML is not added via web buttons; to register one, the user must explicitly ask the Agent to pass an absolute path via CLI `ensure --add` or `sync --add`.
- The file panel can remove a registered HTML from the workbench, but the action requires a second confirmation and never deletes, moves, or renames files on disk; external HTML can still only be registered explicitly via the CLI.
- Prototype page CSS/JS must be inlined or localized; Tailwind CDN or other network runtime dependencies are forbidden in deliverables.
- Feature 3 treats static pages and `index.html` as read-only baselines; cross-page logic goes into version-specific `runtime-pages/` and `prototype*.html`.
- Feature 5 may only add one incrementally named `prototype-mobile*.html`; it must never overwrite existing prototypes, resources, logs, or older mobile files.

### Feature 1: High-Fidelity Static Prototype

Generates a static high-fidelity prototype from scattered ideas or a PRD. Typical artifacts:

```text
prototype/
  docs/Spec.md
  docs/EditLog.md
  design-direction.html
  previews/home-preview.html
  index.html
  pages/*.html
  assets/frames/frame-config.json
  assets/frames/<selected-frame>.html
  assets/images/
  assets/icons/
```

The flow has three stages: product requirements, UI direction, and static page generation. The requirements stage only clarifies scope, users, pages, features, flows, rules, and exceptions — it never decides the visual style in advance. The UI direction stage selects UI Skills, colors, fonts, references, and device frames based on user confirmation. Static pages implement only in-page interactions; cross-page controls keep only `data-ycet-nav-target` intent metadata.

Feature 1 does not start the workbench; when the user later explicitly chooses Feature 2, the workbench scans `design-direction.html`, `pages/**/*.html`, `previews/**/*.html`, and `index.html` generated this session.

### Feature 2: Visual Precision Editing of Prototype Pages

Feature 2 replaces manually copying CSS selectors and HTML paths via F12 with a local workbench. The workbench renders real HTML, nested iframes, and runtime pages directly; users can select elements, add annotations, preview property changes, and hand the changes to an Agent for execution.

Only Feature 2 can start the workbench. On start and on file refresh it recursively scans HTML under the project root and ignores workbench state, version control, dependencies, virtual environments, and cache directories. With no HTML it still starts an empty workbench; the left refresh button later pulls in project HTML not yet displayed. Refresh also restores project HTML that was previously removed from the workbench only. The left file tree groups files by directory (e.g. `pages`, `runtime-pages`); files inside a group indent to the right of the folder title, root-level files are not grouped, and the default order is ascending filename. It provides search, group collapse, project file refresh, sidebar collapse, open-in-new-tab, and remove-from-workbench. The jump and delete icons appear only on row hover or keyboard focus; the delete icon is red. Removal only deletes the workbench registration, requires a second confirmation, and never deletes local HTML; "Clean missing files" is shown only when missing registrations exist.

The central preview area supports:

- "Select element" is inactive by default when entering the workbench; after the user activates it, a blue selection box appears on hover and clicking an element shows a green selection box, element name, and annotation entry; closing selection mode clears the hover box, selection box, element name, and annotation entry.
- The annotation entry sits outside the selection box at the top-right or bottom-right; it is hidden once the same element already has an annotation. Annotations can be edited, deleted, or cleared at once for the current HTML page; annotation drafts are not removed by "Clear modifications".
- The central red-bordered area is the built-in browser window; the outer frame fills all available width/height at every zoom level. `Ctrl + mouse wheel` zooms the page browser-style; page overflow scrolls within the HTML itself. Above 100% zoom, middle mouse drag pans via an internal preview layer offset without a horizontal scrollbar, and the outer frame never moves. Persistent operation hints sit at the bottom-left of the canvas.
- When an element scrolls out of view, goes stale, or the page scrolls, the selection and hover boxes recompute or hide instead of staying at old positions. The preview runtime reports real content width/height so the page is never clipped by a fixed container.

The right property editor refreshes for the selected element and includes:

- Position: X/Y, rotation, rotate 90° clockwise, flip horizontal, flip vertical; X/Y are shown in current viewport coordinates and applied as deltas on top of the element's original offsets, so an element inside a positioned container moves exactly 1px when its value increases by 1; static elements are converted to effective relative positioning.
- Layout: width, height, and Flex/Grid or positioning controls depending on element type.
- Appearance: overall opacity, uniform border radius, and per-corner radius.
- Text: text nodes such as Text 1, Text 2…, with system-installed font families, font weights, font sizes, text colors, line heights, letter spacing, and iconized alignment.
- Fill & border: fill color, fill opacity, border color, border width, and solid/dashed/dotted border types.
- Shadow & blur: multiple outer shadows, inner shadows, layer blurs, or background blurs; each effect can be individually configured, removed, and edited for color, offset, blur, spread, etc.
- Image: pick a replacement image via the Python service's system file picker; the image only registers its original absolute path for preview and is never copied or rewritten before sending.
- Custom CSS: any CSS properties/values are allowed in preview by default; when the Agent executes, values with remote URLs, `@import`, `javascript:`, `expression()`, path traversal, or guard violations are rejected.

Workbench draft rules:

- Drafts live only in browser memory. They are kept per HTML file when switching files; they are not guaranteed to survive closing the tab, closing the workbench process, or refreshing the page.
- Files with modifications show a red dot next to their icon in the left panel.
- "Clear modifications" clears only style, text, image, CSS, and `sync pages` drafts for the current file; "Clear annotations" clears only annotations for the current file.
- `runtime-pages/*.html` shows "sync pages" only when the corresponding `pages/*.html` succeeded in the most recent Agent request and its SHA-256 actually changed. Clicking it generates only a `sync-pages` draft tied to that successful request and previews reusable style, CSS, and text operations in the central canvas; it must be sent to the Agent again before runtime files may be written. The entry hides after a successful sync until a new real static-page modification appears. The Agent must preserve `navigate`, `set-screen`, `screen-changed`, the page registry, the target whitelist, event-source validation, and `prototype.html` interactions.

### Feature 3: Interactive Prototype Demo

Converts confirmed static pages into a multi-page interactive demo:

- Takes SHA-256 read-only snapshots of `prototype/index.html` and existing `prototype/pages/**/*.html`.
- Generates version-matched `runtime-pages/<source>--<demo>.html` for each static page; cross-page logic is written only into runtime copies and `prototype.html`/`prototype-vN.html`.
- `prototype.html`/`prototype-vN.html` use a dedicated adaptive demo layout at browser default 100% zoom: the nav bar width stays readable and the device frame scales proportionally to the viewport and stays fully visible.
- Uses the `ycet-prototype` message protocol with `navigate`, `set-screen`, `screen-changed` for two-layer iframe navigation relay, page registry, back history, and target-whitelist validation.
- Feature 3 artifacts do not start the workbench; when the user later explicitly chooses Feature 2, everything is scanned together and the static baseline stays unmodified.
- Runs `prototype_guard.py snapshot/verify` before and after generation; any change to protected static files must stop generation and be reported.

### Feature 4: Takeover & Migration of Existing HTML/Image Prototypes

When taking over HTML or full-page PNG/JPG prototypes not generated by this Skill, first confirm the product scope, then read and audit the prototype. After parsing the HTML entry and its associated CSS, JS, images, and fonts, generate `prototype/docs/Spec.md` without invoking a requirement-clarification Skill. After the Spec is confirmed, reuse Feature 1's visual flow and Feature 3's interaction flow; stop after the static prototype is complete, and only generate the runtime demo after the user explicitly confirms again.

Full-page images must first be saved to `prototype/assets/images/`; both the static carrier page and runtime copies reference the original image from that directory. By default, images are not split, OCR'd, or redrawn as HTML elements; lossless splitting is allowed only after the user explicitly confirms the fixed/scrollable area boundaries. Image hot zones are written only into runtime copies, transparent by default, showing a semi-transparent dashed outline on hover or keyboard focus.

### Feature 5: Mobile Offline Single-File Prototype

Packages the runtime pages of the same demo version and their enumerable CSS, JavaScript, image, icon, and font dependencies into one self-contained `prototype-mobile*.html`:

- Shows the product page full-screen by default; a top-left button expands an overlay page-navigation drawer; no desktop device frame or debug info is shown.
- For fixed-pixel logical canvases, the offline package adapts each page's `srcdoc` to the actual phone visible width/height without rewriting `runtime-pages/` sources, avoiding content clipping across phone sizes.
- Reuses Feature 3's message protocol, page registry, query/hash, and browser back logic.
- Acquires the workbench lock before packaging; packaging is blocked while unsent drafts exist. During the lock, previews are read-only and no new workbench requests can be sent.
- A successful package adds only one incrementally named mobile file and does not auto-start or open the workbench; it never modifies `pages/`, `runtime-pages/`, `index.html`, resources, or `EditLog.md`.
- Dynamic remote dependencies, login state, path traversal, missing resources, or non-enumerable network dependencies block generation; pages or resources are never deleted to "pass" validation.

---

## 🎬 Demo Previews

The previews and videos below are recordings of actual deliverables (iPhone 15 Pro · 390×844 logical canvas), produced from the real artifacts in the `prototype/` directory.

### Feature 1 · High-Fidelity Static Prototype

**UI design direction page (`design-direction.html`)**

![design-direction.html preview animation](assets/demos/design-direction.gif)

**High-fidelity entry page (`index.html`)**

![index.html preview animation](assets/demos/index.gif)

### Feature 2 · Prototype Workbench

![Prototype workbench preview animation](assets/demos/workbench.gif)

### Feature 3 · Interactive Prototype Demo (`prototype.html`)

![prototype.html preview animation](assets/demos/prototype-demo.gif)

### Feature 4 · Takeover & Migration of Existing HTML/Image Prototypes

<video src="assets/demos/function-4-demo.mp4" controls></video>

### Feature 5 · Mobile Offline Single-File Prototype

<video src="assets/demos/function-5-demo.mp4" controls></video>

---

## 🖥️ Workbench Architecture & Lifecycle

The workbench consists of:

- `scripts/prototype_workbench.py`: Python 3 standard-library local service, file scanning/polling, system image picker, request state, execution transactions, and the Feature 5 lock.
- `assets/workbench/index.html`, `styles.css`, `app.js`: glassmorphism three-column UI and session interaction.
- `assets/workbench/preview-runtime.js`: injected into preview pages in a restricted same-origin manner; handles element fingerprints, nested iframes, selection, annotations, preview drafts, zoom, and pan.
- `assets/workbench/icons.svg`: local SVG icon set, no remote icon service dependency.

The service binds only to `127.0.0.1` and uses an instance token, Host/Origin validation, a path whitelist, safe MIME types, and CSP. Source HTML bytes never change due to preview injection. A standard-library poll checks registered file digests and new project HTML every second; with no drafts it refreshes the preview, and with drafts it marks external changes as conflicts and blocks sending stale drafts.

The top "Close workbench process" button uses a Power icon. Clicking it always asks for a second confirmation; when unsent drafts exist it shows the affected HTML file count and a loss warning. After confirmation it calls the token-protected `POST /api/shutdown`; the service returns `202` and then gracefully stops the HTTP service, file watcher, and system dialog proxy, and clears `server.json` for the current PID. The web page never force-kills the PID, auto-closes tabs, or auto-restarts. Generated or in-flight Agent requests and results are not deleted when the workbench closes; the next `ensure` restores request state and results.

---

## 💻 Command Line Interface

Run the following commands from the project root; `<skill目录>` points to `outputs/skills/ycet-prototype-create`:

### Start, Reuse & Sync

```powershell
python <skill目录>\scripts\prototype_workbench.py ensure --project-root <项目根目录>
python <skill目录>\scripts\prototype_workbench.py ensure --project-root <项目根目录> --add <HTML绝对路径>
python <skill目录>\scripts\prototype_workbench.py sync --project-root <项目根目录> --add <新增HTML绝对路径>
python <skill目录>\scripts\prototype_workbench.py status --project-root <项目根目录>
```

`ensure` is used only by Feature 2: it reuses a healthy instance of the same project and starts one on a random local port only when none exists. `sync` only reuses a running instance; if none is running it only updates the local workspace registration and never starts or opens a browser. Command output JSON always includes the URL (except when `sync` is not running). If auto-opening the browser fails or `--no-open` is used, the output URL must be given to the user to open manually. `--add` can be repeated; it is the only entry point for registering external HTML — there is no corresponding web button.

Core APIs used by the workbench frontend (all require the current instance token and accept only local Host/Origin):

| Method & Path | Purpose |
| --- | --- |
| `GET /api/workspace` | Read file registrations, groups, current file, and zoom preference |
| `POST /api/workspace/sync` | Scan `prototype/` and add new HTML; never deletes disk files |
| `POST /api/workspace/remove` | Confirmed web action: remove workbench registration only, never delete disk HTML |
| `GET /api/fonts` | Return system font families discovered by the Python service |
| `GET /api/requests` | Return current active request and recent request summaries |
| `POST /api/requests` | Validate and persist an immutable change package |
| `POST /api/requests/<id>/cancel` | Cancel a `pending` request not yet claimed by an Agent |
| `GET /api/results`、`GET /api/state` | Return per-file results, draft summary, and packaging lock |
| `POST /api/shutdown` | Gracefully close the current workbench process after confirmation, returns `202` |
| `POST /api/dialog` | Open the image system file picker from the Python main thread |

### Agent Requests

```powershell
python <skill目录>\scripts\prototype_workbench.py request list --project-root <项目根目录>
python <skill目录>\scripts\prototype_workbench.py request show --project-root <项目根目录> --request-id <请求ID>
python <skill目录>\scripts\prototype_workbench.py request begin --project-root <项目根目录> --request-id <请求ID>
python <skill目录>\scripts\prototype_workbench.py request complete --project-root <项目根目录> --request-id <请求ID> --result <结果JSON>
python <skill目录>\scripts\prototype_workbench.py request abort --project-root <项目根目录> --request-id <请求ID> --reason <原因>
```

`request begin` accepts only `pending` requests and atomically creates a transaction directory and a pre-modification snapshot; after execution, `request complete` writes per-file results. `request abort` lets an Agent abort an active request. Transaction snapshots are cleaned up after a request completes or aborts; there is no undo command for AI modifications.

### Feature 5 Packaging Lock

```powershell
python <skill目录>\scripts\prototype_workbench.py lock acquire --project-root <项目根目录>
python <skill目录>\scripts\prototype_workbench.py lock status --project-root <项目根目录>
python <skill目录>\scripts\prototype_workbench.py lock release --project-root <项目根目录> --token <锁令牌>
```

The lock must be released in a `finally` path. `lock acquire` fails when the workbench has related unsent drafts; drafts must never be auto-cleared or sent on the user's behalf.

---

## 🤝 Agent Handoff Protocol

"Send to AI" is a change-package handoff, not direct web control of an Agent. The flow:

1. The workbench validates file SHA-256, element fingerprints, operations, and dependency groups, then generates an immutable request package.
2. After the package is written to `.ycet-editor/requests/<request-id>.json`, all sent drafts in this session are cleared; on write failure, drafts are kept.
3. A dialog shows the request ID, file count, operation count, current status, and execution instructions in full without horizontal scrolling; close and copy buttons are clearly separated.
4. After clicking "Copy instructions" the dialog closes immediately and a Toast reports the real copy result; on success, paste the instructions into the current Codex, Claude Code, OpenCode, or other Agent session; on failure, retry from the request details.
5. The Agent reads the shared protocol and runs `request show`, `request begin`, staged modifications, guard validation, and `request complete`; it may also use `request abort`.
6. The workbench polls and shows pending, processing, and per-file final states; after closing and restarting the workbench it restores them from `.ycet-editor/requests/`.

The workbench recognizes a JSON as a formal request package only when its filename matches the `requestId` inside and it contains `files`. Temporary results such as `*.result.pending.json` produced while an Agent works never create fake `pending` requests; "Send to AI" becomes available again after the formal request completes.

Fixed operation types in a change package:

| Type | Purpose |
| --- | --- |
| `annotation` | Element annotations and modification intent |
| `style` | Style diffs from the design panel |
| `text` | Text node replacement |
| `image-replace` | Local image replacement |
| `css` | Arbitrary CSS properties/values added by the user |
| `sync-pages` | Controlled static-to-runtime page sync |

Dynamic state lives in `<request-id>.state.json` and never rewrites the original change package:

| State | Meaning | Workbench behavior |
| --- | --- | --- |
| `pending` | Package generated, waiting for Agent | Copy instructions again or cancel |
| `processing` | Agent claimed atomically | Files are locked; no web force-termination |
| `success` | All files succeeded | Show per-file results |
| `partial` | Some files succeeded | Show success, failure, and conflict reasons |
| `failed` | No files succeeded or execution failed | Show failure reason |
| `aborted` | User cancelled or Agent aborted | Show abort reason |

Only one `pending` or `processing` request is allowed per project at a time. Files involved in the active request — and static source files of `sync-pages` — are locked for editing; drafts for other HTML may still be prepared but cannot be sent until the current request terminates. After a request completes, successful in-project modifications append to `prototype/docs/EditLog.md` per the rules; external files are modified at their original paths and no project execution history is written.

---

## 📁 Workspace State & File Safety

Main contents of `.ycet-editor/`:

```text
.ycet-editor/
  workspace.json              # registered files, sources, groups, current file, zoom preference
  server.json                 # current instance URL, PID, token (cleared when service stops)
  server.log                  # local service diagnostic log
  requests/                   # immutable change packages, dynamic state, per-file results
  transactions/               # staged snapshots while an Agent executes
  mobile-pack.lock.json       # Feature 5 packaging lock
```

Workbench runtime state is never written into `prototype/`, and the workbench never modifies `.gitignore` automatically. `workspace.json` persists only file registrations, sources, groups, sort-compatible data, the current file, and zoom preference — never unsent drafts. External HTML can be registered as `source: external` and modified at its original absolute path, but no `EditLog.md` entry and no permanent execution history is created.

---

## 🔗 Feature-to-Workbench Relationship

| Feature | Workbench action on generation/takeover | Key limitation |
| --- | --- | --- |
| Feature 1 | No workbench; Feature 2 scans later | Static pages implement in-page interactions only |
| Feature 2 | `ensure` reuses/starts the workbench; refresh scans project HTML; changes handed to Agent as packages | Empty projects keep the service running; no web external file picker |
| Feature 3 | No workbench; Feature 2 scans runtime artifacts later | `pages/`, `index.html` read-only; `sync-pages` must preserve demo interactions |
| Feature 4 | No workbench; Feature 2 scans takeover artifacts later | Confirm product scope first; original images and static inputs are protected |
| Feature 5 | Acquires lock before packaging; never auto-joins or opens the workbench | Drafts block packaging; old files or logs are never modified |

---

## 🛡️ Security Rules

- Preview routes bind to localhost only and reject directory traversal, dangerous protocols, unregistered paths, and unsafe MIME types; the official Tailwind CDN is allowed in the preview CSP only for legacy page compatibility — new artifacts still forbid remote runtime dependencies.
- The Agent must verify file SHA-256, full element fingerprints, dependency groups, and the target whitelist together; non-unique selectors, digest mismatches, or dead paths are reported as conflicts, never guessed.
- `sync-pages` must not overwrite runtime pages directly; it merges into a staged copy in a controlled way and verifies that `prototype.html`/the current demo still loads the target page.
- Image replacement, new resources, and `EditLog.md` updates must be part of the same transaction; real unregistered changes must never be hidden from results before the transaction completes.
- Independent files may partially succeed, but the final result must list successful, failed, and conflicted files with per-item reasons.

---

## 🧪 Environment & Verification

### Requirements

- Python 3; verified on Python 3.14.
- Browser verification needs Python Playwright; the testers try Playwright Chromium, system Chrome, system Edge, and Playwright Firefox in order, and browsers that are not installed must be marked `[SKIP]`, never faked as passing.
- The system image picker depends on Python `tkinter`; verified with Tk 8.6. If Tk is unavailable, the Agent can only register paths via the CLI — Tk windows must never be created from an HTTP request thread.

### Structure, Service & Runtime Verification

```powershell
python outputs\skills\ycet-prototype-create\scripts\validate_skill.py
python outputs\skills\ycet-prototype-create\scripts\test_prototype_workbench.py
python outputs\skills\ycet-prototype-create\scripts\test_workbench_runtime.py
python outputs\skills\ycet-prototype-create\scripts\test_prototype_guard.py
python outputs\skills\ycet-prototype-create\scripts\test_build_mobile_prototype.py
python outputs\skills\ycet-prototype-create\scripts\test_frames_runtime.py
python outputs\skills\ycet-prototype-create\scripts\test_mobile_prototype_runtime.py
python outputs\skills\ycet-prototype-create\scripts\release_audit.py --installed-skill <optional global Skill directory>
```

To force real Firefox runs:

```powershell
python outputs\skills\ycet-prototype-create\scripts\test_frames_runtime.py --require-firefox
```

Static boundary and Feature 3 read-only protection on a real prototype:

```powershell
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py static --prototype-dir <prototype dir>
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py snapshot --prototype-dir <prototype dir> --output <temp snapshot file>
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py verify --prototype-dir <prototype dir> --snapshot <temp snapshot file>
```

Generate and validate a mobile version of existing runtime pages:

```powershell
python outputs\skills\ycet-prototype-create\scripts\build_mobile_prototype.py --prototype-dir <prototype dir>
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py mobile --prototype-dir <prototype dir> --mobile-file <generated file>
```

Already verified: workbench service and request-state tests (29 cases), Chrome/Edge workbench runtime with three layout tiers, real Chrome close-process interaction, five device-frame runtimes, `prototype_guard.py`, Feature 5 packaging regression, mobile offline single-file runtime, `validate_skill.py`, `quick_validate.py`, JavaScript syntax checks, and `git diff --check`. Playwright Chromium/Firefox were not completed due to environment limits; Firefox, real mobile devices, and full Agent-dialogue evaluation remain unverified.

---

## 📄 Documentation Index

- `outputs/skills/ycet-prototype-create/SKILL.md`: Skill entry point, routing, and global rules.
- `outputs/skills/ycet-prototype-create/docs/function-1-static-prototype.md`: Feature 1 requirements, UI direction, and static prototype flow.
- `outputs/skills/ycet-prototype-create/docs/function-2-precision-edit.md`: Feature 2 workbench, change packages, and sync flow.
- `outputs/skills/ycet-prototype-create/docs/function-3-interactive-demo.md`: Feature 3 runtime copies, message protocol, and read-only protection.
- `outputs/skills/ycet-prototype-create/docs/function-4-existing-prototype-edit.md`: Feature 4 takeover & migration of existing HTML/image prototypes.
- `outputs/skills/ycet-prototype-create/docs/function-5-mobile-single-file.md`: Feature 5 input gates, packaging lock, single-file generation, and acceptance.
- `outputs/skills/ycet-prototype-create/docs/shared-prototype-standards.md`: Directory, frame, canvas, path, and page standards.
- `outputs/skills/ycet-prototype-create/docs/shared-editlog-rules.md`: In-project EditLog recording rules.
- `outputs/skills/ycet-prototype-create/docs/shared-workbench-protocol.md`: Workbench lifecycle, drafts, change packages, request states, sync, and Feature 5 lock.
- `outputs/skills/ycet-prototype-create/assets/frames/manifest.json`: Single source of truth for device frames, logical canvas, preview sizes, and port mapping.
- `outputs/skills/ycet-prototype-create/assets/workbench/`: Workbench browser frontend, preview runtime, and local icons.
- `docs/brainstorms/specs/`: Confirmed requirement specs.
- `docs/brainstorms/plan/`: Implementation plans and verification records.

---

## ⚠️ Known Limitations

- The workbench never starts, injects into, or controls Codex, Claude Code, OpenCode, or other Agent sessions on its own; the user must hand the execution instructions to the current Agent.
- Closing the workbench loses unsent annotation, style, text, image, CSS, and sync drafts in the browser session; already generated or in-flight requests are not cancelled.
- Passing the desktop Chrome/Edge mobile viewport is not the same as passing on real Safari iOS, Chrome Android, or Edge Android devices; runs without real-device testing must be marked "unverified".
- Fully self-contained mobile files can be large and are limited by dynamic network, login state, and non-enumerable runtime dependencies.
- The Skill never installs itself, replaces global Skills, publishes, deploys, pushes remote repositories, creates PRs, or runs Git commits.

---

## 📜 License

This project is open source under the [MIT License](LICENSE), Copyright (c) 2026 Ycet.