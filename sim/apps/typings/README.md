# Runtime Typings For Simulator Apps

This folder contains shared `.pyi` stub files used by Visual Studio Code
(Pylance/Pyright) when developing simulator apps on desktop Python.

## Why this folder exists

The badge software targets BadgeOS/MicroPython. Some imports used by the apps
(for example `machine`, `ota`, `egpio`, `vfs`) are available on badge hardware
or in the simulator runtime but not in a normal desktop Python environment.

Without stubs, editors report unresolved imports and missing members even when
runtime behavior on the badge is correct.

Repo modules that exist in this workspace, such as `system`, `events`,
`app_components`, `frontboards`, `settings`, `tildagonos`, and `app`, should be
resolved from source instead of being duplicated here.

## How this interacts with VS Code, Pylance, and pylint

- VS Code + Pylance/Pyright:
  - Root-workspace analysis is configured from `pyrightconfig.json`.
  - App-local analysis is configured from each app's `pyrightconfig.json`.
  - These stubs are only for runtime-only modules that cannot be resolved from source.

- pylint:
  - Configured from `sim/apps/pyproject.toml`.
  - pylint does not consume these stubs like Pylance does.
  - It should resolve repo modules from the real `modules` tree and only ignore
    runtime-only imports.

## What belongs in this folder

Add minimal, stable API surface only for runtime-only modules:

- Imported module names and package structure
- Classes/functions/constants used by project code
- Basic method signatures where useful

Avoid full re-implementation of runtime libraries. Keep stubs lightweight and
focused on editor correctness.

## When to update stubs

Update this folder when:

- A new runtime-only module is imported in project code
- Existing project code starts using additional attributes/methods on a runtime
  object
- BadgeOS/MicroPython API changes break editor diagnostics

## Notes

- `.pyi` files are for development-time tooling only and are not deployed to the
  badge.
- Prefer keeping behavior-neutral stubs with no executable logic.
