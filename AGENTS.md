更新 `bw` 的核心结构或行动路由时，同步检查相关 references、templates、scripts 和 README，避免同一契约出现两套表述。

单个 skill 或 `bywork/` 文档应当精炼高密度，优先完整说明会影响判断的结构、原则与底线；细节按单职责拆到同目录下的 `references/`、`templates/`、`scripts/`，并在入口文件里清楚指过去。

工作流文档只写给现在用它的人（`skills/bw/` 与 `bywork/implemented/`）：规则只陈述当前成立的契约。演变原因、证据与取舍留在对应决策或归档记录中。

- 否定式表述要挣得它的注意力成本：一条「不要 X」只在 X 是模型的强默认行为时才写。项目约束见 `bywork/implemented/architecture/2026-11-18-project-constraints.md`。

当前工作从 `bywork/proposed/` 的检查点继续，现行决定与避坑记录按分类检索 `bywork/implemented/` 与 `bywork/rejected/`（排除 `bywork/archived/`）。技能契约读取本仓库 `skills/bw/SKILL.md`。
