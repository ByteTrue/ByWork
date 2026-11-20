# 真实会话复盘

把一次真实使用 `bw` 的会话变成技能改进证据或记忆沉淀。

## 步骤

1. **导出原文**：用 `python3 tools/export-opencode-session.py --session "<标题或ID>"` 导出完整原文（含思考过程与工具调用），以原文为准核对，不只看最终产物。
2. **还原时间线**：核对当时加载的 `bw` 版本、每轮消息的行动路由、`bywork/proposed/` 检查点与验收表回写、真实生效路径验证以及 `bw.py` 流转调用。
3. **五判据筛选修改候选**：
   - **持久**：跨任务、跨项目重复出现，而非单次偶发或项目专属知识（项目专属经验记入该项目自己的 `bywork/implemented/` 或 `rejected/`）。
   - **改变决策**：能在具体决策点改变模型动作。
   - **单一归属**：有唯一明确的落点（某个单职责 reference 或 `bw.py`）。
   - **可验证**：修改后能通过脚本测试或对照运行检验。
   - **不重复**：不与现有契约重复。
4. **先确认再改技能**：先向用户汇报原文证据与推荐修法，获确认后再改 `skills/bw/`，并将复盘结论同步记入 [`bywork/implemented/testing/2026-11-18-evaluation-findings.md`](../bywork/implemented/testing/2026-11-18-evaluation-findings.md)。