# Dependency And Script Matrix (Vue CLI -> Vite 7, Vue2 + MF)

## Script Mapping

| Legacy | Target |
| --- | --- |
| `serve: vue-cli-service serve` | `dev: vite` |
| `build: vue-cli-service build --no-module` | `build: vite build` |
| N/A | `preview: vite preview` |
| `lint: vue-cli-service lint` | `lint: eslint src --ext .js,.vue` (or team equivalent) |

## Add / Keep (Validated Target Baseline)

### Core
- `vite@7.3.1`
- `@vitejs/plugin-vue2@2.3.4`
- `vue@2.7.16`
- `vue-template-compiler@2.7.16`

### Module Federation (when applicable)
- `@module-federation/vite@1.11.0` (fixed, aligned with `portal-app-web`; do not use `^`)
- `@module-federation/runtime@0.8.12`
- `typescript@4.9.5`

### Browser Polyfill Set (when needed)
- `buffer@6.0.3`
- `crypto-browserify@3.12.1`
- `events@3.3.0`
- `process@0.11.10`
- `stream-browserify@3.0.0`
- `vm-browserify@1.1.2`

### PostCSS (if migrated into Vite pipeline)
- `postcss@8.5.10`
- `postcss-import@15.1.0`
- `postcss-preset-env@9.6.0`
- `postcss-calc@9.0.1`
- `precss@4.0.0` for projects that retain legacy `lang="postcss"` syntax; treat this as required compatibility support, not an optional nicety
- `sass@1.99.0`
- `postcss-mixins`: add only if existing styles already require it; it is not part of the validated default baseline for this skill revision
- Optional based on existing styles: `postcss-color-mod-function`, `postcss-extend-rule`, `postcss-nested`

### Conditional Additions
- `@vitejs/plugin-vue2-jsx`: add only if the project actually contains JSX/TSX or `<script lang="jsx">`. This skill revision does not pin a version for it because the current validated repo baseline does not install it.
- Tiptap 2: if the project already uses `@tiptap/*`, lock all direct Tiptap packages to `2.10.4` and copy the full override set from `references/troubleshooting.md`. Do not mix `2.9.x` and `2.10.x`.
- Project-specific missing direct dependencies such as `qs` or `identicon.js` are not baseline migration dependencies. Add them only when source imports or verified runtime errors prove the project truly needs them.

## Remove / Decommission (Typical)

- `@vue/cli-service`
- `@vue/cli-plugin-babel`
- `@vue/cli-plugin-eslint`
- `vue-cli-service` script references
- webpack-only loaders/plugins no longer used after migration:
  - `file-loader`
  - `url-loader`
  - `raw-loader`
  - `node-polyfill-webpack-plugin` (if replaced by Vite alias/polyfill strategy)
  - `compression-webpack-plugin` (only if previously wired only in webpack build config)
  - `speed-measure-webpack-plugin`
  - `webpack-bundle-analyzer` (if no Vite alternative configured)

## Version Strategy

- Default in this skill: use the exact versions above, validated against the current repo `yarn.lock`.
- Default in this skill for Vue2 + MF: `@module-federation/vite@1.11.0` fixed strategy, aligned with `portal-app-web`.
- Do not convert the validated baseline back to `^`, `~`, or `x` ranges during migration.
- Do not leave `@module-federation/vite` on a floating range such as `^1.11.0`; otherwise installs can drift to later plugin releases and introduce new default behavior.
- Upgrade separately from migration if environment constraints require Vite 5 first.

## Validation Commands

```bash
yarn install
yarn dev
yarn build
python3 scripts/verify_migration_state.py --project-root <project-root>
```

## Notes

- Keep `sass` pinned if team has known compiler behavior requirements.
- Remove dependency entries only after confirming no source/config references remain.
- If project contains nested packages (e.g. local libs), evaluate their `package.json` independently.
- Treat `yarn.lock` as the write-back source of truth for this skill revision. Use `package-lock.json` only as a consistency check when both lock files exist.
- Only `@module-federation/vite@1.11.0` keeps an explicit `portal-app-web` alignment claim in this skill. The other exact versions above come from the validated `gptbox` migration baseline.
- If the migrated project keeps Vue CLI-era `lang="postcss"` constructs (`%placeholder`, `@extend`, nesting, `//` comments), inline the `portal-app-web` PostCSS chain in `vite.config.*` and keep `precss` enabled.
