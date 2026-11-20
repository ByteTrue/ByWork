# 方案（Plan）

适用：已经知道要做什么，进入动手前的方案设计与验收标准定义；或单轮做不完、涉及多处改动的工作。

## 步骤

1. **检索现行约束与避坑记录**：按主题扫描 `bywork/implemented/` 与 `bywork/rejected/`（排除 `archived/`），确认不违背既有决策、不重踩已否决方案。
2. **建立或更新 `proposed` 工作记录**：
   - 若项目尚未初始化 `bywork/`，先读 [`references/onboard.md`](onboard.md) 运行 `bw.py init --project .`。
   - 在 `bywork/proposed/<分类>/yyyy-mm-dd-topic.md` 建立提案（参考 [`templates/proposed.md`](../templates/proposed.md)，分类用小写英文目录名如 `architecture`、`feature`、`bug-fix`、`process` 等）。
   - 顶部保留 6 个过程检查点字段（`kind: work`、`status: in_progress | blocked`、`current_unit`、`next_action`、`must_hold`、`proof_gap`）。
   - 正文用一句话写清 `## 问题`、`## 提案`、`## 备选方案`（先写被弃方案最合理的理由再写放弃原因）、`## 验收标准`（6 列行为验收表）和 `## 风险与代价`。
3. **跨模块变更列出影响范围**：改动共享契约、公共入口或多处状态时，在 `## 提案` 下附影响范围表（位置 | 角色 | 改动 | 风险 | 连带验证）。
4. **最小完备原则**：优先复用项目已有机制，不加无人要求的配置项、抽象层或兜底分支。
