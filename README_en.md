# ycet-prototype-create

[![简体中文](https://img.shields.io/badge/简体中文-red?style=for-the-badge)](README.md)
[![English](https://img.shields.io/badge/English-blue?style=for-the-badge)](README_en.md)

Turn product ideas into standalone HTML prototypes, then preview and edit them in a local workbench.

[![Version](https://img.shields.io/badge/version-v4.2.4-2563eb)](skill-outputs/ycet-prototype-create/VERSION)
[![Agent Skill](https://img.shields.io/badge/type-Agent%20Skill-0f766e)](skill-outputs/ycet-prototype-create/SKILL.md)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

![ycet-prototype-create cover](assets/images/prototype-cover.png)

The Skill covers requirement refinement, UI direction, static, framed interactive, and frameless prototypes, existing-prototype adaptation, and a local workbench. The UI direction board and prototype shell follow the confirmed product style instead of applying one fixed visual theme.

## Contents

- [Quick start](#quick-start)
- [Features and demos](#features-and-demos)
- [Deliverables and portability](#deliverables-and-portability)
- [Editing and iteration rules](#editing-and-iteration-rules)
- [Repository layout](#repository-layout)
- [Validation and release](#validation-and-release)
- [Documentation](#documentation)
- [License](#license)
- [Finishing prototype edits](#finishing-prototype-edits)

## Quick start

~~~bash
git clone https://github.com/Ycet/ycet-prototype-create.git
cd ycet-prototype-create

# For Codex, copy the Skill directory into the local skills directory.
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skill-outputs/ycet-prototype-create "${CODEX_HOME:-$HOME/.codex}/skills/"
~~~

After installation, describe the task in natural language or invoke:

~~~text
$ycet-prototype-create
~~~

For a new product request, the Skill follows “requirement refinement → UI direction confirmation → prototype production.” It waits for user confirmation between stages. Tasks based on an existing prototype or image enter feature four.

## Features and demos

| Feature | Responsibility | Primary output |
| --- | --- | --- |
| Feature 1 | Refine product requirements | prototype/docs/Spec.md |
| Feature 2 | Confirm the UI direction | prototype/outputs/design-direction.html |
| Feature 3 | Select and create a prototype | Static, framed interactive, or frameless HTML prototype |
| Feature 4 | Reconstruct or edit an existing prototype or image | Updated prototype files and related documents |
| Feature 5 | Start the local prototype workbench | A workbench for browsing and editing prototypes under prototype/ |

The following GIFs demonstrate the features. Demos are expanded by default and can be collapsed as needed.

<details open>
<summary>Feature 2 · UI direction preview</summary>

![Feature 2: UI direction preview](assets/images/功能二--设计方向预览.gif)

</details>

<details open>
<summary>Feature 3 · Static pages</summary>

![Feature 3: static pages](assets/images/功能三--静态页面.gif)

</details>

<details open>
<summary>Feature 3 · Framed interactive demo</summary>

![Feature 3: framed interactive demo](assets/images/功能三--可交互demo.gif)

</details>

<details open>
<summary>Feature 3 · Frameless interactive demo</summary>

![Feature 3: frameless interactive demo](assets/images/功能三--无边框交互demo.gif)

</details>

<details open>
<summary>Feature 4 · Image to HTML prototype</summary>

![Feature 4: image to HTML prototype](assets/images/功能四--图片转原型html.gif)

</details>

<details open>
<summary>Feature 5 · Prototype workbench</summary>

![Feature 5: prototype workbench](assets/images/功能五--工作台.gif)

</details>

Feature three first asks the user to choose a prototype type:

| Option | Type | Initial filename |
| --- | --- | --- |
| A | Static prototype pages | prototype/outputs/prototype-pages.html |
| B | Interactive prototype demo | prototype/outputs/prototype-demo.html |
| C | Frameless interactive prototype demo | prototype/outputs/prototype-nonframe.html |

Feature four preserves source image proportions and appearance; existing HTML enters UI direction confirmation only for a full redesign, then follows the same A/B/C rules. The feature-five workbench edits the current file directly; it does not ask for a prototype type and no longer includes a “Sync pages” action.

## Deliverables and portability

All generated prototype files are stored in prototype/outputs/. Each HTML file contains the DOM, styles, and interaction logic for every page:

- no dependency on pages/, runtime-pages/, or nested-page structures;
- no iframe, srcdoc, or external framework files;
- inline delivery of icons, images, and other resources;
- each file can be copied, shared, and opened directly in a browser.

## Editing and iteration rules

The Skill asks before editing when a request contains a breaking change, adds or removes pages, or changes the UI style, elements, or interactions across every page. The user chooses either:

1. edit the current prototype file; or
2. create a versioned iteration such as prototype-demo-v2.html or prototype-pages-v3.html.

Changes submitted through the prototype workbench always update the current file and do not create an iteration copy. The Skill does not automatically maintain EditLog.md or synchronize content between prototype types.

## Repository layout

~~~text
skill-outputs/
├── ycet-prototype-create/             # Installable Skill directory
│   ├── SKILL.md
│   ├── VERSION
│   ├── docs/
│   └── scripts/
└── ycet-prototype-create-v4.2.4.skill # Packaged release artifact
~~~

During a user task, the project-level prototype/ directory stores requirements, assets, and every prototype output.

## Validation and release

For Skill development and releases only, run these commands in skill-outputs/ycet-prototype-create/:

~~~bash
python scripts/test_prototype_v4.py
python scripts/test_prototype_workbench.py
python scripts/validate_skill.py
~~~

Optional runtime validation requires Node.js:

~~~bash
python scripts/test_prototype_v4.py --fixtures <empty-test-directory>
node scripts/test_runtime_v4.cjs <empty-test-directory>
node scripts/test_workbench_v4.cjs <empty-test-directory>
~~~

Generate a release audit report before publishing:

~~~bash
python scripts/release_audit.py --output <output-directory>/ycet-prototype-create-v4.2.4.skill
~~~

## Documentation

- [Feature 1: Requirement refinement](skill-outputs/ycet-prototype-create/docs/function-1-requirements.md)
- [Feature 2: UI direction confirmation](skill-outputs/ycet-prototype-create/docs/function-2-ui-direction.md)
- [Feature 3: Prototype production](skill-outputs/ycet-prototype-create/docs/function-3-prototype-production.md)
- [Feature 4: Existing prototype reconstruction and editing](skill-outputs/ycet-prototype-create/docs/function-4-existing-prototype-edit.md)
- [Feature 5: Prototype workbench](skill-outputs/ycet-prototype-create/docs/function-5-workbench.md)
- [Validation notes](skill-outputs/ycet-prototype-create/docs/verification.md)

## License

This project is licensed under the [MIT License](LICENSE).

## Finishing prototype edits

C supports mobile and desktop products using the actual browser viewport, with normal scrolling for long content. After saving requested prototype edits, finish the task without automatic static checks, browser acceptance or regression tests. Run tests only when explicitly requested. Workbench transaction completion remains required. Initial generation and Skill development retain their own validation requirements.

See the [validation boundaries](skill-outputs/ycet-prototype-create/docs/prototype-validation.md) and the [v4.2.4 validation record](skill-outputs/ycet-prototype-create-v4.2.4-validation.md). The [v4.1.0 plan](docs/spec/v4.1.0/优化执行方案.md) remains available as an archive.
