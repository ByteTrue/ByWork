## 1.0.1

- 行动路由触发点从「调用 bw 时」改为「每条用户消息」，并明确摘要/上文里的行动标签是历史不是当前状态。起因：AGCopilot「飞书 Grimm」会话从分析转修改时未重新分类主行动，沿用压缩摘要里的旧标签惯性滑入实现，多行为路径全程无 work（真实偏离案例，见 `bywork/memory/evaluation.md`）。

## 1.0.0

ByWork 首个公开版本。一个名为 `bw` 的 Agent Skill，用 `work/{slug}/`、`memory/{topic}.md` 与按需的 `vision/` 管理软件演化：按用户当前行动推进澄清、改变、理解与审查、记忆与方向。

- 当前工作保存在 `bywork/work/{slug}/index.md`，顶部五项检查点（status / current_unit / next_action / must_hold / proof_gap）；行为证明表逐行从真实入口验证并回写。
- 长期判断按主题写入 `bywork/memory/`；产品方向按需整理到 `bywork/vision/`。
- 完成门：所有证明通过、范围覆盖、外部验收无失败且 `proof_gap` 恰为空才写 `status: complete`；`scripts/check_work.py` 机械校验状态值、缺口与 complete-work 封存。
- 维护侧 `tools/` 提供发布检查、checker 自检、脚本夹具与效果评测运行器。