# Troubleshooting (Vue2 + Vite 7 + MF)

## 1) Dynamic Import Warning For Vue SFC

### Symptom
- Runtime warning or load failure for dynamic component import paths.

### Cause
- Missing `.vue` extension in dynamic import string under Vite analysis.

### Fix
- Prefer:
```js
() => import(`./template/${name}.vue`)
```

## 2) Bootstrap 3 / jQuery Global Timing

### Symptom
- `tooltip` or other bootstrap plugins fail at runtime.

### Cause
- Bootstrap executes before jQuery is attached globally in ESM order.

### Fix
1. Set globals before bootstrap import:
```js
import jQuery from 'jquery'
window.$ = jQuery
window.jQuery = jQuery
globalThis.$ = jQuery
globalThis.jQuery = jQuery
await import('bootstrap/dist/js/bootstrap.min.js')
```

## 3) CSS Path `url(~@/...)` Breakage

### Symptom
- CSS asset URLs unresolved after migration.

### Cause
- webpack `~` alias style is not recognized by Vite.

### Fix
- Replace `url(~@/x/y.png)` with `url(@/x/y.png)`.

## 4) GeoJSON Dynamic Require Failure

### Symptom
- Map registration fails when loading JSON by dynamic `require`.

### Cause
- Vite cannot resolve webpack-style runtime `require('./x/' + name + '.json')`.

### Fix
1. Preload with glob:
```js
const geoJsonModules = import.meta.glob('./geo-json/*.json', { eager: true })
```
2. Access by key:
```js
const m = geoJsonModules[`./geo-json/${name}.json`]
const data = m?.default || null
```

## 5) JSX In `.vue` Script Block

### Symptom
- Parsing errors in components using JSX syntax inside SFC script.

### Cause
- Missing explicit JSX language hint.

### Fix
- Use `<script lang="jsx">` for JSX-based script blocks.
- In plain module files, use `.jsx` extension when code uses JSX syntax.

## 6) Ace/File Loader Migration

### Symptom
- Editor worker/theme/mode URLs fail after removing webpack loaders.

### Cause
- Removed `file-loader` inline syntax is not valid in Vite.

### Fix
- Replace with `?url` imports and pass URLs to runtime registry APIs.

## 7) Module Federation Remote Entry Compatibility

### Symptom
- Webpack consumer cannot load Vite-generated remote entry as classic script.

### Cause
- Vite MF emits ESM entry; webpack `script/var` expects global container.

### Fix
- Standardize the federation ESM filename to `remoteEntry.es.js`.
- Configure `federation({ varFilename: 'remoteEntry.js' })` so `@module-federation/vite` generates the compatibility `script/var` entry.
- Do not create or retain a checked-in `public/remoteEntry.js` wrapper.

## 8) `process` / `Buffer` / Node Core Polyfills Undefined In Browser

### Symptom
- Runtime errors after migration in crypto or legacy libs.

### Cause
- Legacy libraries assume Node globals in browser.

### Fix
- Add dependencies (`buffer@6.0.3`, `process@0.11.10`, `crypto-browserify@3.12.1`, `events@3.3.0`, `stream-browserify@3.0.0`, `vm-browserify@1.1.2`) and alias them in Vite config when the project actually requires those Node core shims.
- Add polyfill bootstrap for `globalThis.Buffer` and `globalThis.process` when required.

## 9) Vue Singleton Not Preserved Across MF Boundary

### Symptom
- Remote and host do not actually share the same Vue singleton.
- Runtime behavior suggests duplicate Vue instances after Vite migration.

### Cause
- Vue2 Vite plugin resolution leaves `vue` pointed at `vue/dist/vue.runtime.esm.js`, which bypasses MF shared singleton resolution against bare `vue`.

### Fix
1. Add local plugin before `federation()`:
```js
function preserveVueFederationSingleton () {
  return {
    name: 'preserve-vue-federation-singleton',
    configResolved (config) {
      const aliases = config.resolve?.alias
      if (!Array.isArray(aliases)) return

      const filteredAliases = aliases.filter(alias => {
        return !(alias.find === 'vue' && alias.replacement === 'vue/dist/vue.runtime.esm.js')
      })

      aliases.splice(0, aliases.length, ...filteredAliases)
    }
  }
}
```
2. Register it before `federation()` in `vite.config.*`.

## 10) `Cannot find module 'typescript'` During Vite Config Load

### Symptom
- `vite` fails while loading `vite.config.*` with:
```txt
Error: Cannot find module 'typescript'
```
- Stack trace points into `@module-federation/dts-plugin` from `@module-federation/vite`.

### Cause
- Installed `@module-federation/vite` version drifted away from the skill baseline and brought in DTS-related startup behavior not expected by the migration.

### Fix
1. First verify the project is still pinned to the skill baseline:
```json
"@module-federation/vite": "1.11.0"
```
2. Compare the resolved dependency tree with a known-good project on the same baseline, such as `portal-app-web`, before changing config.
3. Reinstall dependencies and confirm the lock file resolves `@module-federation/vite` to `1.11.0`.
4. Only investigate repo-specific dependency gaps after confirming the MF plugin version did not drift from the baseline.

## 11) Dart Sass `@import` Deprecation Noise During `vite` Dev Startup

### Symptom
- `yarn serve` starts successfully, but the console prints warnings such as:
```txt
Deprecation Warning [import]: Sass @import rules are deprecated
```

### Cause
- The migrated project still imports legacy SCSS entry files through Sass `@import`.
- Do not assume `portal-app-web` has a hidden Vite suppression for this. It avoids the same warning largely because it does not import the same legacy global SCSS/theme entry chain.

### Fix
1. Convert local side-effect style entry files from `@import` to `@use`.
2. If the warning chain originates in `element-ui/packages/theme-chalk/src/*`, treat it as legacy third-party theme-source debt, not as a sign that `portal-app-web` has some missing Vite suppression.
3. Do not blindly rewrite the Element UI theme entry to `@use ... with (...)`; Element UI's theme variables are legacy private Sass variables and that rewrite can introduce new `with-private` warnings immediately.
4. Only add Sass warning suppression after separating project-local warnings from third-party dependency warnings.

## 12) Migration Still Depends On Legacy Vue CLI Env Contract

### Symptom
- The app still only works when source code reads `process.env.VUE_APP_*` or `process.env.BASE_URL`.

### Cause
- The env migration stopped halfway: scripts, `.env*`, `vite.config.*`, and source code were not switched together.

### Fix
1. Rename runtime custom env keys to `VITE_*` in scripts and `.env*`.
2. Read runtime env in source via `import.meta.env.VITE_*` and `import.meta.env.BASE_URL`.
3. Remove `define` bridges that re-inject legacy `process.env.VUE_APP_*` or `process.env.BASE_URL` into business code.
4. Keep deploy-only/private vars on neutral names such as `SERVER_ID`.

## 13) Legacy `lang="postcss"` Syntax Reaches Vite CSS Minify

### Symptom
- `yarn build` prints warnings such as:
```txt
Comments in CSS use "/* ... */" instead of "//"
Unexpected "%"
```
- Built `dist/assets/*.css` still contains raw `%normal`, `@extend`, or `//padding` fragments.

### Cause
- The migrated Vite CSS pipeline no longer runs `precss`, so legacy Vue CLI-era `lang="postcss"` syntax is passed through to esbuild CSS minification unexpanded.

### Fix
1. Inline the PostCSS plugin chain into `vite.config.*` using the `portal-app-web` baseline:
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
2. Remove duplicate root `postcss.config.js` files if the project standardizes on inline Vite PostCSS config.
3. Rebuild and confirm the generated CSS no longer contains `%placeholder`, `@extend`, or `//` comment syntax.

## 14) Tiptap 2 Patch Versions Drift Or Mix During Migration

### Symptom
- `npm install` or `yarn install` fails with peer or resolution conflicts across `@tiptap/*`.
- Build-time or runtime editor errors appear only after some Tiptap packages moved to `2.10.x` while others stayed on `2.9.x`.

### Cause
- The project already uses Tiptap 2, but direct dependencies and transitive extensions were not locked to the same patch version during migration.

### Fix
1. Only apply this rule if the project already uses Tiptap 2. Tiptap is not part of the default Vue2 -> Vite baseline.
2. Lock the direct Tiptap dependencies that exist in the project to `2.10.4`. In the validated `gptbox` migration, that set is:
```json
{
  "@tiptap/core": "2.10.4",
  "@tiptap/extension-character-count": "2.10.4",
  "@tiptap/extension-mention": "2.10.4",
  "@tiptap/extension-placeholder": "2.10.4",
  "@tiptap/pm": "2.10.4",
  "@tiptap/starter-kit": "2.10.4",
  "@tiptap/suggestion": "2.10.4",
  "@tiptap/vue-2": "2.10.4"
}
```
3. Copy the full override set so the extension family resolves to the same patch version instead of mixing `2.9.x` and `2.10.x`:
```json
{
  "@tiptap/extension-bubble-menu": "2.10.4",
  "@tiptap/extension-floating-menu": "2.10.4",
  "@tiptap/extension-blockquote": "2.10.4",
  "@tiptap/extension-bold": "2.10.4",
  "@tiptap/extension-bullet-list": "2.10.4",
  "@tiptap/extension-code": "2.10.4",
  "@tiptap/extension-code-block": "2.10.4",
  "@tiptap/extension-document": "2.10.4",
  "@tiptap/extension-dropcursor": "2.10.4",
  "@tiptap/extension-gapcursor": "2.10.4",
  "@tiptap/extension-hard-break": "2.10.4",
  "@tiptap/extension-heading": "2.10.4",
  "@tiptap/extension-history": "2.10.4",
  "@tiptap/extension-horizontal-rule": "2.10.4",
  "@tiptap/extension-italic": "2.10.4",
  "@tiptap/extension-list-item": "2.10.4",
  "@tiptap/extension-ordered-list": "2.10.4",
  "@tiptap/extension-paragraph": "2.10.4",
  "@tiptap/extension-strike": "2.10.4",
  "@tiptap/extension-text": "2.10.4",
  "@tiptap/extension-text-style": "2.10.4"
}
```
4. Reinstall and confirm the lock file resolves the entire active Tiptap set to `2.10.4`.
