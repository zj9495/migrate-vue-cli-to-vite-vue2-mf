---
name: migrate-vue-cli-to-vite-vue2-mf
description: Migrate Vue2 frontend projects from vue-cli/webpack to Vite 7 with Module Federation compatibility. Use when requests mention vue-cli to vite migration, webpack-to-vite migration, Vue2 + ElementUI modernization, module federation runtime compatibility, removing vue.config.js/webpack aliases, or fixing migration errors such as require.context, module.hot, process.env, url(~@/...), dynamic require(asset), and remoteEntry compatibility.
---

# Vue CLI To Vite 7 (Vue2 + MF)

Execute deterministic migration workflow for Vue2 projects that currently rely on vue-cli + webpack and need to move to Vite 7 while preserving Module Federation interoperability. Use the exact dependency versions documented in `references/dependency-matrix.md`; this skill revision treats the current `gptbox` `yarn.lock` as the validated source of truth for those versions.

## Workflow

1. Run baseline scan first.
- Execute:
```bash
python3 scripts/scan_migration_gaps.py --project-root <project-root> --format markdown
```
- Treat `blocker` items as mandatory before expecting build success.

2. Load only the required references for the current stage.
- Migration sequence and rollout gates: `references/migration-playbook.md`
- Patch-derived code transformations: `references/patch-derived-patterns.md`
- Dependency/script migration and pinning: `references/dependency-matrix.md`
- Error signatures and fast fixes: `references/troubleshooting.md`

3. Implement migration in this order.
- Migrate `package.json` scripts and dependency set first, using the exact versions in `references/dependency-matrix.md`.
- Migrate runtime env contracts completely: custom frontend env keys must use `VITE_*`, business code must read them via `import.meta.env`, and completed migrations must not keep any `VUE_APP_*` contract or `process.env.VUE_APP_*` bridge.
- Keep `BASE_URL` on Vite's built-in contract and consume it as `import.meta.env.BASE_URL`; do not bridge it back to `process.env.BASE_URL`.
- Use neutral names for deploy-only/private variables (for example `SERVER_ID`), not `VITE_*` and not legacy `VUE_APP_*`.
- If project uses Module Federation, pin `@module-federation/vite` to the skill baseline `1.11.0` (aligned with `portal-app-web`) instead of using a floating `^` range.
- Treat `@module-federation/vite@1.11.0` as the only dependency in this skill that remains explicitly aligned with `portal-app-web`; the other locked versions in this skill come from the validated `gptbox` `yarn.lock` baseline.
- For Vue2 + Module Federation projects, standardize the federation ESM filename to `remoteEntry.es.js`.
- For Vue2 + Module Federation projects, standardize the compatibility `script/var` entry to plugin-generated `remoteEntry.js` via `federation({ varFilename: 'remoteEntry.js' })`.
- For Vue2 + Module Federation projects that consume `ueba`, standardize the remote declaration to `remotes: { ueba: 'ueba@/remoteEntry.js' }`, aligned with `portal-app-web`.
- For Vue2 + Module Federation projects, add `.__mf__temp` to the root `.gitignore`.
- For Vue2 + Module Federation projects, add `mf-app-version` as a required migration dependency and register `createMfAppVersionPlugin()` in `vite.config.js`; treat it as the standard replacement for legacy webpack-side app version plugins.
- For Vue2 + Module Federation projects, expose app version through the shared `mf-app-version` contract instead of maintaining per-app webpack version injection code; `./app-version` must be provided by the Vite-side migration result.
- Add/adjust `vite.config.js`; for Vue2 + Module Federation projects, do not keep a root `index.html` entry or standalone app-shell entry files such as `src/main.js`, `bootstrap.js`, or equivalent HTML-mounted shells.
- When migrating webpack-era Vue2 codebases that use extensionless relative SFC imports such as `import Foo from './Foo'`, add `resolve.extensions = ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json', '.vue']` in `vite.config.js` so Vite preserves its default extension set and explicitly resolves `.vue`.
- Add `@vitejs/plugin-vue2-jsx` only if the project actually contains JSX/TSX or `<script lang="jsx">`; do not add it by default when no JSX evidence exists.
- For Vue2 projects that still use legacy `lang="postcss"` syntax such as `%placeholder`, `@extend`, nesting, or `//` comments, inline the PostCSS plugin chain into `vite.config.js` using the `portal-app-web` baseline: `postcss-import@15.1.0`, `postcss-preset-env@9.6.0`, `postcss-calc@9.0.1`, `precss@4.0.0`.
- When standardizing on the `portal-app-web` PostCSS layout, remove duplicate root `postcss.config.js` files so Vite has a single source of truth for CSS preprocessing.
- For Vue2 + Module Federation projects aligned with `portal-app-web`, standardize the Vite production build profile to `target: 'esnext'`, `minify: 'esbuild'`, and `rollupOptions.output.format = 'esm'`.
- For Vue2 + Module Federation projects, set `build.rollupOptions.input = {}` so Vite stops treating `index.html` as a required build entry.
- Do not enable Vite production sourcemap output unless an explicit contract requires shipping `.map` artifacts.
- For Vue2 + Module Federation projects, add a local `preserveVueFederationSingleton()` plugin in `vite.config.js` and register it before `federation()`.
- For Vue2 + Module Federation projects, set `moduleParseTimeout: 60` in `federation()`.
- Refactor source patterns (`require.context`, `module.hot`, `process.env`, asset `require`, css `~@/`).
- Treat env migration as a single gate: scripts, `.env*`, `vite.config.js`, and source modules must switch together. Do not leave one layer on `VUE_APP_*` while another layer has already moved to `VITE_*`.
- When comparing against `portal-app-web`, treat it as the MF version baseline, not as proof that Sass warnings should be suppressed the same way. Check first whether the migrated project actually has the same global style entry chain; `portal-app-web` itself does not import the legacy SCSS/theme entry files that typically trigger Dart Sass deprecation noise.
- For Vue2 + Module Federation projects, use the federation plugin's generated `remoteEntry.js` compatibility entry when webpack consumers load remotes via `script/var`; do not create or retain a checked-in `public/remoteEntry.js` wrapper.
- Remove legacy webpack app-version plugins and related wiring such as `git-revision-webpack-plugin`; after migration, version metadata must come from `mf-app-version`.
- Do not promote project-specific missing direct dependencies such as `qs` or `identicon.js` into the default baseline. Add them only if the migrated project's source actually imports them or the dependency is otherwise proven required.
- Remove obsolete vue-cli/webpack config files.

4. Verify migration state before closing.
- Execute:
```bash
python3 scripts/verify_migration_state.py --project-root <project-root>
```
- If any `FAIL` remains, fix and rerun until all required checks pass.
- For Vue2 + Module Federation projects, the expected remote-only result is: no required root `index.html`, no source-managed `public/remoteEntry.js`, build output emits `remoteEntry.es.js` and `remoteEntry.js`, and the root path is not treated as a required app entry.

## Validated Dependency Baseline

- Source of truth: current repo `yarn.lock`. Use `package-lock.json` only as corroborating evidence when present.
- Core baseline: `vite@7.3.1`, `@vitejs/plugin-vue2@2.3.4`, `vue@2.7.16`, `vue-template-compiler@2.7.16`.
- Module Federation baseline: `@module-federation/vite@1.11.0`, `@module-federation/runtime@0.8.12`, `typescript@4.9.5`.
- Required MF app version baseline for Vite MF projects: `mf-app-version`.
- PostCSS baseline for the standard Vite CSS pipeline: `postcss@8.5.10`, `postcss-import@15.1.0`, `postcss-preset-env@9.6.0`, `postcss-calc@9.0.1`, `precss@4.0.0`, `sass@1.99.0`.
- Browser polyfills when required by source or runtime: `buffer@6.0.3`, `crypto-browserify@3.12.1`, `events@3.3.0`, `process@0.11.10`, `stream-browserify@3.0.0`, `vm-browserify@1.1.2`.
- Conditional only: `@vitejs/plugin-vue2-jsx` is not part of the default baseline. Add it only when the project truly uses JSX/TSX or `<script lang="jsx">`.
- Conditional only: if a project already uses Tiptap 2, lock all direct `@tiptap/*` packages to the same patch version. The validated patch in this skill revision is `2.10.4`; see `references/troubleshooting.md` for the required override set.
- Not baseline: project-specific missing direct dependencies such as `qs` or `identicon.js`. Add them only when the migrated project truly depends on them.

## Default Assumptions

- Target stack: Vue2 + ElementUI + Yarn + Module Federation.
- Target bundler baseline: `vite@7.3.1`.
- Default MF baseline: `@module-federation/vite@1.11.0` and `@module-federation/runtime@0.8.12`, with only the Vite plugin alignment claim inherited from `portal-app-web`.
- Validated dependency source: current repo `yarn.lock`.
- Scope: engineering migration and compatibility fixes only.
- Out of scope by default: Vue3 migration, business logic redesign, UI feature rewrites.

## Operating Rules

- Prefer incremental commits by stage to reduce regression blast radius.
- Keep changes reversible: avoid broad regex rewrites without scoped review.
- Do not preserve legacy Vue CLI env compatibility by default. A finished Vite migration should not depend on `VUE_APP_*`, `process.env.VUE_APP_*`, or `process.env.BASE_URL`.
- Do not rewrite validated baseline versions back to `^`, `~`, or `x` ranges during migration.
- Do not keep or introduce webpack-only app version plugins in Vite migrations. `mf-app-version` is the required app version solution for MF projects in this skill.
- Do not create or retain root `index.html`, HTML-mounted app-shell entries, or handwritten `public/remoteEntry.js` wrappers for Vue2 + Module Federation migrations covered by this skill.
- Do not promote project-specific dependency fixes into the default baseline. If a missing package is only needed because a specific repo imports it, treat it as a repo-level addition instead of a skill-wide default.
- Do not claim migration complete without both scans:
  `scan_migration_gaps.py` + `verify_migration_state.py`.

## Commands

```bash
# 1) Baseline gap scan
python3 scripts/scan_migration_gaps.py --project-root <project-root> --format markdown

# 2) Machine-readable gap scan
python3 scripts/scan_migration_gaps.py --project-root <project-root> --format json

# 3) Post-migration verification
python3 scripts/verify_migration_state.py --project-root <project-root>
```
