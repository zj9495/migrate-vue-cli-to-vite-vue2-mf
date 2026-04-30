# Vue2 + MF: Vue CLI -> Vite 7 Migration Playbook

## 1. Baseline Inventory

### Input Conditions
- Project still runs with `vue-cli-service`.
- `package.json`, `vue.config.js`, webpack-specific loaders/plugins exist.

### Actions
1. Run:
```bash
python3 scripts/scan_migration_gaps.py --project-root <project-root> --format markdown
```
2. Capture blockers and warnings as migration backlog.
3. Snapshot baseline:
```bash
git status
yarn build
```

### Acceptance
- You have a prioritized gap list and baseline build result.

### Rollback Point
- No repo mutation yet; safe to continue.

## 2. Scripts And Dependencies

### Input Conditions
- Backlog from step 1 exists.

### Actions
1. Replace primary scripts:
- `dev`: `vite`
- `build`: `vite build`
- `preview`: `vite preview`
2. Move from vue-cli deps to Vite 7 stack:
- Add `vite@7.3.1`, `@vitejs/plugin-vue2@2.3.4`, `vue@2.7.16`, and `vue-template-compiler@2.7.16`.
- Add `@vitejs/plugin-vue2-jsx` only when the project actually contains JSX/TSX or `<script lang="jsx">`.
- Add MF runtime/plugin when host exposes or consumes remotes: `@module-federation/vite@1.11.0`, `@module-federation/runtime@0.8.12`, `typescript@4.9.5`.
- If browser Node core shims are needed, add `buffer@6.0.3`, `crypto-browserify@3.12.1`, `events@3.3.0`, `process@0.11.10`, `stream-browserify@3.0.0`, `vm-browserify@1.1.2`.
- If the migrated CSS pipeline needs the standard PostCSS baseline, add `postcss@8.5.10`, `postcss-import@15.1.0`, `postcss-preset-env@9.6.0`, `postcss-calc@9.0.1`, `precss@4.0.0`, `sass@1.99.0`.
- Remove `@vue/cli-*`, `vue-cli-service`, webpack-only plugins/loaders that no longer apply.
3. Install the exact versions from `references/dependency-matrix.md` and keep them exact. Do not rewrite them to `^`, `~`, or `x` ranges during migration.

### Acceptance
- `yarn dev --help` and `yarn build --help` resolve to Vite commands.
- `package.json` uses the validated exact baseline versions for the migrated stack instead of range placeholders.

### Rollback Point
- Commit package changes separately before source refactors.

## 3. Vite Config Mapping

### Input Conditions
- `package.json` already migrated.

### Actions
1. Create `vite.config.js` (or `.ts`) with:
- Vue2 plugin, plus Vue2 JSX plugin only if the project actually uses JSX/TSX or `<script lang="jsx">`.
- Alias mapping from webpack (`@`, `@components`, etc.).
- Dev server host/port/proxy.
- Env loading aligned to Vite contracts only. Read custom runtime vars from `VITE_*`, keep `BASE_URL` on Vite's built-in contract, and do not re-inject legacy `process.env.VUE_APP_*` / `process.env.BASE_URL` bridges into source code.
2. For Vue2 + Module Federation projects, add a local `preserveVueFederationSingleton()` plugin before `federation()` in the Vite plugin list.
3. Make the preserve plugin remove the `vue` -> `vue/dist/vue.runtime.esm.js` alias injected during Vue2 plugin resolution, so MF shared singleton resolution still targets `vue`.
4. If Node core modules are used in browser, add alias/polyfill strategy that matches the exact baseline polyfill package set in `references/dependency-matrix.md`.
5. If the project still relies on legacy `lang="postcss"` syntax such as `%placeholder`, `@extend`, nesting, or `//` comments, inline the PostCSS chain into `vite.config.*` using the `portal-app-web` baseline:
```js
css: {
  postcss: {
    plugins: [
      require('postcss-import')({
        path: ['src/styles', 'src/styles/themes/']
      }),
      require('postcss-preset-env')({
        features: {
          'custom-properties': {
            preserve: true
          }
        }
      }),
      require('postcss-calc')(),
      require('precss')()
    ]
  }
}
```
6. When standardizing on that layout, remove duplicate root `postcss.config.js` files so Vite uses a single PostCSS source of truth.
7. For Vue2 + Module Federation projects, do not keep a root `index.html` entry or standalone HTML-mounted app-shell files; configure `build.rollupOptions.input = {}` so Vite builds only the remote entries.
8. For Vue2 + Module Federation projects aligned with `portal-app-web`, standardize the Vite production build profile to:
```js
build: {
  target: 'esnext',
  minify: 'esbuild',
  rollupOptions: {
    output: {
      format: 'esm'
    }
  }
}
```
9. Do not enable `build.sourcemap` for production output unless an explicit artifact contract requires shipping `.map` artifacts.

### Acceptance
- `vite.config.*` exists and parses.
- For Vue2 + MF, `vite.config.*` registers `preserveVueFederationSingleton()` before `federation()`.
- If the project keeps legacy `lang="postcss"` syntax, `vite.config.*` must inline the `portal-app-web` PostCSS plugin chain and include `precss`.
- For Vue2 + MF, the config does not require root `index.html` and explicitly disables HTML entry builds with `build.rollupOptions.input = {}`.

### Rollback Point
- Commit config migration before codewide rewrites.

## 4. Source Refactor Pass

### Input Conditions
- Vite config is in place and, for MF projects under this standard, remote-only outputs are configured instead of an HTML entry.

### Actions
1. Apply deterministic pattern refactors:
- `require.context` -> `import.meta.glob`.
- `module.hot` -> `import.meta.hot`.
- `process.env` -> `import.meta.env`.
- Asset `require(...)` -> static `import`.
- CSS `url(~@/...)` -> `url(@/...)`.
2. Apply the env migration gate as one unit:
- `package.json` scripts must export `VITE_*` runtime vars instead of `VUE_APP_*`.
- `.env*` files must rename runtime vars to `VITE_*` and rename deploy-only vars to neutral names such as `SERVER_ID`.
- `vite.config.*` must read `VITE_*` and must not define legacy `process.env.VUE_APP_*` / `process.env.BASE_URL` bridges.
- Business code must read runtime env from `import.meta.env.VITE_*` / `import.meta.env.BASE_URL`, not from `process.env.*`.
3. Fix dynamic import paths for Vue SFC:
- `import(\`./x/${name}\`)` -> `import(\`./x/${name}.vue\`)` where needed.
4. Replace webpack loader syntax (`file-loader!...`) with Vite `?url` imports when loading runtime assets.

### Acceptance
- Static scan no longer reports core blocker patterns.

### Rollback Point
- Commit after each refactor class, not one giant commit.

## 5. Module Federation Compatibility

### Input Conditions
- Project has MF host/remote behavior.

### Actions
1. Configure `@module-federation/vite` in Vite plugins.
2. Standardize the federation filename to:
```js
federation({
  filename: 'remoteEntry.es.js',
  varFilename: 'remoteEntry.js'
})
```
3. Set `moduleParseTimeout: 240` in `federation()` for Vue2 + Module Federation projects.
4. When the project consumes `ueba`, standardize the remote declaration to:
```js
remotes: {
  ueba: 'ueba@/remoteEntry.js'
}
```
aligned with `portal-app-web`.
5. Keep the Vue shared singleton path stable by preserving bare `vue` resolution via `preserveVueFederationSingleton()`.
6. If downstream webpack consumers load remote via classic script:
- Keep ESM entry `remoteEntry.es.js` for Vite runtime.
- Use the federation plugin-generated `remoteEntry.js` compatibility entry via `varFilename`; do not create or retain a checked-in `public/remoteEntry.js` wrapper.
7. Harden remote registration/loading with callable checks and clear error logs.

### Acceptance
- Remote container loads with expected type in both Vite and webpack consumer paths.
- Vue2 + MF output is remote-only: `remoteEntry.es.js` and `remoteEntry.js` are the only required public entry URLs, and root HTML is not a required app entry.
- Vue shared singleton still resolves through `vue` instead of a hard-coded `vue/dist/vue.runtime.esm.js` alias.

### Rollback Point
- Commit MF compatibility as dedicated change.

## 6. Legacy Cleanup

### Input Conditions
- Vite pipeline works at least for dev boot.

### Actions
1. Remove obsolete files if no longer used:
- `vue.config.js`, `webpack.alias.config.js`, `setup-public-path.js`, `generateProxy.js`, legacy `babel.config.js`.
2. Remove stale temp outputs and add ignore entries (e.g. `.__mf__temp`).

### Acceptance
- No remaining references to removed legacy files in active scripts.

### Rollback Point
- Cleanup changes isolated in one commit.

## 7. Verification And Sign-off

### Input Conditions
- Migration and cleanup complete.

### Actions
1. Run:
```bash
python3 scripts/verify_migration_state.py --project-root <project-root>
```
2. Run project checks:
```bash
yarn dev
yarn build
```
3. For MF project, test remote load path from consumer.

### Acceptance
- `verify_migration_state.py` has no required `FAIL`.
- Local dev/build succeeds.
- MF loading path validated.
- For Vue2 + MF, validation does not depend on a root HTML entry and confirms both `remoteEntry.es.js` and `remoteEntry.js`.

### Rollback Point
- If fail, rollback to previous stage commit and reapply scoped fix.
