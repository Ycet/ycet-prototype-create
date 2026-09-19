# ycet-prototype-create

[![简体中文](https://img.shields.io/badge/简体中文-red?style=for-the-badge)](README.md)
[![English](https://img.shields.io/badge/English-blue?style=for-the-badge)](README_en.md)

[![Version](https://img.shields.io/badge/version-v4.1.0-2563eb)](skill-outputs/ycet-prototype-create/VERSION)
[![Agent Skill](https://img.shields.io/badge/type-Agent%20Skill-0f766e)](skill-outputs/ycet-prototype-create/SKILL.md)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

An Agent Skill that turns product requirements into independently shareable HTML prototypes. It covers requirement refinement, UI direction confirmation, static, framed interactive, and frameless prototypes, reconstruction of existing prototypes, and a local workbench.

## Contents

- [Quick start](#quick-start)
- [v4.1.0 workflow](#v410-workflow)
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

# Copy the Skill directory into the configured skills directory of your Agent.
cp -R skill-outputs/ycet-prototype-create <agent-skill-directory>/ycet-prototype-create
~~~

After installation, describe the task in natural language or invoke:

~~~text
$ycet-prototype-create
~~~

For a new product request, the Skill follows “requirement refinement → UI direction confirmation → prototype production.” It waits for user confirmation between stages. Tasks based on an existing prototype or image enter feature four.

## v4.1.0 workflow

| Feature | Responsibility | Primary output |
| --- | --- | --- |
| Feature 1 | Refine product requirements | prototype/docs/Spec.md |
| Feature 2 | Confirm the UI direction | prototype/outputs/design-direction.html |
| Feature 3 | Select and create a prototype | Static, framed interactive, or frameless HTML prototype |
| Feature 4 | Reconstruct or edit an existing prototype or image | Updated prototype files and related documents |
| Feature 5 | Start the local prototype workbench | A workbench for browsing and editing prototypes under prototype/ |

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
└── ycet-prototype-create-v4.1.0.skill # Packaged release artifact
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
python scripts/release_audit.py --output <output-directory>/ycet-prototype-create-v4.1.0.skill
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

See [validation boundaries](skill-outputs/ycet-prototype-create/docs/prototype-validation.md), the [v4.1.0 plan](docs/spec/v4.1.0/优化执行方案.md) and [archived specifications](docs/spec/v4.0.0/).
