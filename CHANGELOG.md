## 1.0.0

ByWork 首个公开版本。一个名为 `bw` 的 Agent Skill，用 `work/{slug}/`、`memory/{topic}.md` 与按需的 `vision/` 管理软件演化：按用户当前行动推进澄清、改变、理解与审查、记忆与方向。

- 当前工作保存在 `bywork/work/{slug}/index.md`，顶部五项检查点（status / current_unit / next_action / must_hold / proof_gap）；行为证明表逐行从真实入口验证并回写。
- 长期判断按主题写入 `bywork/memory/`；产品方向按需整理到 `bywork/vision/`。
- 完成门：所有证明通过、范围覆盖、外部验收无失败且 `proof_gap` 恰为空才写 `status: complete`；`scripts/check_work.py` 机械校验状态值、缺口与 complete-work 封存。
- 维护侧 `tools/` 提供发布检查、checker 自检、脚本夹具与效果评测运行器。