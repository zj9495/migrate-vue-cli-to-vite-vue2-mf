# Vue CLI / webpack 到 Vite 7 迁移技能（Vue2 + Module Federation）

## 1. 技能简介

这个目录提供一个面向 Vue2 项目的迁移技能，用于把仍依赖 `vue-cli` / webpack 的前端工程迁移到 `Vite 7`，并保持 `Module Federation` 兼容性。

技能正文定义在 [SKILL.md](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/SKILL.md)，其中包含默认假设、迁移顺序、依赖基线、校验要求和操作规则。`README.md` 只负责中文导航和使用入口，不替代正文规则。

## 2. 适用场景

适用于以下情况：

- 项目仍使用 `vue-cli-service` 或显式 webpack 配置。
- 目标是迁移到 `vite@7.x` 的 Vue2 工程。
- 需要保留 Module Federation 远程模块互操作能力。
- 需要处理典型迁移问题，例如 `require.context`、`module.hot`、`process.env`、`url(~@/...)`、动态 `require(...)`、`remoteEntry` 兼容性等。

默认假设：

- 目标技术栈是 Vue2 + ElementUI + Yarn + Module Federation。
- 依赖版本以当前技能定义的精确基线为准。
- 迁移目标是工程配置和兼容性收敛，不是业务重构。

默认不处理：

- Vue3 升级。
- UI 或产品功能重写。
- 脱离现有技能规则的自定义迁移策略。

## 3. 目录结构

- [SKILL.md](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/SKILL.md)
  技能正文，定义完整迁移流程、约束、依赖基线和完成标准。
- [scripts/](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/scripts)
  提供扫描与校验脚本，用于迁移前识别缺口、迁移后验证结果。
- [references/](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/references)
  提供分阶段参考材料，包括迁移步骤、补丁模式、依赖矩阵和故障排查。
- [agents/openai.yaml](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/agents/openai.yaml)
  定义这个技能在代理侧的展示名称、简述和默认提示词。

## 4. 安装方式

可以通过下面的命令全局安装这个技能：

```bash
npx skills add zj9495/migrate-vue-cli-to-vite-vue2-mf -y -g
```

安装后，这个技能可以作为一个现成的迁移能力直接使用。

## 5. 使用方法

这个技能的目标是直接用于 Vue2 + Module Federation 项目的 Vue CLI / webpack -> Vite 7 迁移，不需要先按 README 里的人工流程逐步执行。

可以直接在任务里明确使用这个技能，例如：

```text
使用 migrate-vue-cli-to-vite-vue2-mf 技能迁移这个 Vue2 项目到 Vite 7，并保留 Module Federation 兼容性。
```

或者更直接地描述你的目标，例如：

```text
把这个 Vue2 vue-cli 项目迁移到 Vite 7，处理 require.context、module.hot、process.env、url(~@/...) 和 remoteEntry 兼容问题。
```

技能执行时，实际规则仍然以 [SKILL.md](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/SKILL.md) 为准；其中已经定义了扫描、迁移、校验、依赖基线和操作约束。

## 6. 脚本说明

### `scripts/scan_migration_gaps.py`

文件：[`scripts/scan_migration_gaps.py`](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/scripts/scan_migration_gaps.py)

用途：

- 扫描目标项目里常见的 Vue CLI -> Vite 迁移缺口。
- 识别 `require.context`、`module.hot`、`process.env`、`VUE_APP_*`、CSS `url(~@/...)`、资源 `require(...)`、webpack inline loader 语法等问题。

输入参数：

- `--project-root <path>`：目标项目根目录。
- `--format markdown|json`：输出格式。

输出定位：

- `markdown` 适合人工查看和整理迁移待办。
- `json` 适合程序消费或结构化处理。
- 其中 `blocker` 应视为迁移完成前必须处理的问题。

### `scripts/verify_migration_state.py`

文件：[`scripts/verify_migration_state.py`](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/scripts/verify_migration_state.py)

用途：

- 校验迁移后的目标状态是否满足技能定义。
- 检查 `vite.config.*` 是否存在、旧配置是否移除、脚本是否切换为 Vite、以及 Vue2 + Module Federation 项目的远程入口契约是否成立。

输入参数：

- `--project-root <path>`：目标项目根目录。

输出定位：

- 输出 `PASS` / `FAIL` 结果。
- 只要还有 `FAIL`，就说明迁移未完成，不能直接收口。

## 7. 参考资料说明

- [`references/migration-playbook.md`](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/references/migration-playbook.md)
  用于按阶段执行迁移，重点看输入条件、动作、验收标准和回退点。
- [`references/patch-derived-patterns.md`](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/references/patch-derived-patterns.md)
  用于处理代码层面的典型改写模式，例如 webpack 运行时 API、资源导入、动态组件加载、MF 远程入口兼容等。
- [`references/dependency-matrix.md`](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/references/dependency-matrix.md)
  用于确定脚本映射、增删依赖和精确版本基线。
- [`references/troubleshooting.md`](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/references/troubleshooting.md)
  用于定位常见错误症状和对应修复路径，例如动态 `.vue` 导入、Bootstrap/jQuery 时序、Node polyfill、`remoteEntry` 兼容等。

## 8. 常用命令

```bash
# 1) 基线缺口扫描（Markdown）
python3 scripts/scan_migration_gaps.py --project-root <project-root> --format markdown

# 2) 基线缺口扫描（JSON）
python3 scripts/scan_migration_gaps.py --project-root <project-root> --format json

# 3) 迁移完成后校验
python3 scripts/verify_migration_state.py --project-root <project-root>
```

## 9. 维护约定

- `README.md` 是中文导航文档，不是规则源文件。
- 迁移流程、依赖基线、完成标准和操作约束，以 [SKILL.md](/Users/zj9495/.codex/skills/migrate-vue-cli-to-vite-vue2-mf/SKILL.md) 为准。
- 分阶段细节和问题处理，以 `references/` 下对应文档为准。
- 脚本行为、参数和检查逻辑，以 `scripts/` 下实际代码为准。
- 更新文档时，不要自行增加未在技能正文、参考资料或脚本中定义的兜底逻辑、兼容性黑话或额外流程。
