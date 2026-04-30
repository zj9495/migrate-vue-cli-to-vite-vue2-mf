# Patch-Derived Migration Patterns

Source baseline: `patchs/0001~0005` (Vue CLI -> Vite migration commit sequence).

## Must Change

### 1) Entry And Build Pipeline
- Replace CLI scripts:
  - `vue-cli-service serve` -> `vite`
  - `vue-cli-service build` -> `vite build`
- Create `vite.config.*` with Vue2 plugins.
- For Vue2 + Module Federation, remove standalone page-entry files such as root `index.html`, `src/main.js`, and `bootstrap.js`, set `build.rollupOptions.input = {}`, and emit only remote federation entries.
- For Vue2 + Module Federation, add local plugin `preserveVueFederationSingleton()` before `federation()` to remove the resolved alias `vue -> vue/dist/vue.runtime.esm.js`.

### 2) Webpack Runtime APIs
- `require.context(...)` -> `import.meta.glob(..., { eager: true })`
- `module.hot.accept(...)` -> `import.meta.hot.accept(...)`
- `__webpack_public_path__` usage must be removed/replaced.

### 3) Env Access
- `process.env.NODE_ENV` -> `import.meta.env.DEV` / `import.meta.env.PROD`
- `process.env.BASE_URL` -> `import.meta.env.BASE_URL`
- Custom runtime env keys must use Vite naming (`VITE_*`).
- Completed migrations must not keep `VUE_APP_*` env keys or `define` bridges that re-inject legacy `process.env.VUE_APP_*` / `process.env.BASE_URL` contracts into business code.
- Deploy-only/private variables should use neutral names such as `SERVER_ID`, not `VITE_*` and not `VUE_APP_*`.

### 4) Asset Imports
- Replace asset `require(...)` with explicit static `import`.
- In CSS/PostCSS, replace `url(~@/path)` with `url(@/path)`.

### 5) Remove Legacy Vue CLI/webpack Config Files
- `vue.config.js`
- `webpack.alias.config.js`
- `setup-public-path.js`
- `generateProxy.js`
- `babel.config.js` (if only used for vue-cli preset)

## Scenario-Based Changes

### 1) Node Core Polyfills In Browser
When legacy code imports Node built-ins (e.g. `crypto`):
- Switch import:
  - `import crypto from 'crypto'` -> `import crypto from 'crypto-browserify'`
- Add dependencies as needed:
  - `crypto-browserify`, `buffer`, `process`, `stream-browserify`
- Add aliases and global shims where required.

### 2) Loader Syntax To Vite Asset URL
When webpack `file-loader` patterns are used:
- Replace with direct `?url` imports:
  - `import x from 'pkg/file.js?url'`
- Register runtime URLs via library APIs (e.g. Ace editor module URLs).

### 3) Dynamic Vue Component Import Warning
When template name is dynamic:
- Use extension-explicit dynamic import:
  - `import(\`./template/${name}.vue\`)`

### 4) Module Federation Remote Compatibility
If webpack consumers expect `remoteType=script/var`:
- Keep Vite ESM remote entry and standardize `federation({ filename: 'remoteEntry.es.js', varFilename: 'remoteEntry.js' })`.
- Use the plugin-generated `remoteEntry.js` compatibility entry; do not create a checked-in `public/remoteEntry.js` wrapper.

### 5) Vue Singleton Preservation Under MF
When Vue2 remote shares `vue` through Module Federation:
- Do not leave the Vite-resolved `vue/dist/vue.runtime.esm.js` alias in place for federation resolution.
- Add `preserveVueFederationSingleton()` in `vite.config.*` and register it before `federation()`.
- The plugin should strip the `vue` runtime alias during `configResolved`, so shared singleton lookup still binds to bare `vue`.

## Search Patterns For Fast Triage

```bash
rg -n "require\\.context|module\\.hot|process\\.env|__webpack_public_path__" src
rg -n "url\\(~@/" src
rg -n "require\\(.+\\.(png|jpe?g|svg|gif|webp|ttf|woff2?)" src
rg -n "file-loader|raw-loader|url-loader" src
```

## Priority Guidance

- `blocker`: bundler/runtime incompatibility (`require.context`, `module.hot`, legacy config gating build).
- `warning`: likely breakage in specific runtime paths (asset require, env bridge, CSS tilde alias).
- `info`: best-practice cleanup and consistency tasks.
