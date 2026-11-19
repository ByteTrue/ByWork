## 1.0.3

- 收尾总结改为在 `SKILL.md`「汇报」段直接给出可视模板（「做了什么」一句总领加无序列表、「下一步」有序列表、「需要你」有序列表带推荐与理由），删掉 `references/writing.md` 重复的「收尾总结」小节与 `SKILL.md` 共同规则里的重复短语。起因：1.0.2 把收尾总结拆成 `SKILL.md` 的三行 `- **标签**：…` 单行列表和 `writing.md` 的散文描述两半，实战中模型直接照抄 `SKILL.md` 的三行单行形状而忽略了 `writing.md` 的列表结构。

## 1.0.2

- `complete` 改由 `scripts/check_work.py --close {slug}` 写入，不再手写。脚本先核对完成门（证明行全过、`proof_gap` 恰为空、complete-work 封存），通过才把 `status` 写成 `complete`，不通过拒绝并保持文件原状；盘上的非法状态值（如 `done`）在完成门满足时也被该命令自然覆盖。起因：byspace「Greeting」会话手写 `status: done` 且带非空缺口，`check_work.py` 能拒但全程未被调用——校验器存在却没被触发。把「写 complete」从模型的自觉动作变成校验器的输出，消除手写非法值的机会（调研对照：v1 把 `check_open_issues.py` 绑在提交链、openspec 的 archive 是命令、superpowers 要求完成声明前有刚跑出的证据）。完成门机制的权威归属在 `references/prove.md`「完成与接续」，SKILL.md 核心流程与底线、change.md 出口、templates/work.md 完成门只留指针或不可协商的一句，不复述机制。
- 汇报改为每次回复末尾的固定收尾总结：用平实语言讲清「做了什么 / 下一步 / 需要你」，让用户不读前面的技术细节也能掌握全局和该自己拍板的事。「需要你」集中列等用户决策、授权、支持或信息的内容，没有写「无」。精炼简洁，按内容需要写清，不硬限字数。起因：用户反馈每次回来面对一堆技术细节看不懂，总得再问「下一步是什么/需要我做什么」。结构归 SKILL.md 汇报段，写法归 writing.md「收尾总结」节，两处不重复。
- 提示词去重与去锚：把 `--close` 机制和收尾总结从多份文件的重复复述收敛为单一权威归属加指针（此前 prove.md 完成门漏改、与 SKILL.md「不手写」矛盾，是重复造成漂移的实证）；删掉「几小时的工作」这类具体时长锚（会让模型把更长的工作误判为超出范畴），改为「按内容需要写清」；收尾总结的否定 framing 改正面。行为契约不变。

## 1.0.1

- 行动路由触发点从「调用 bw 时」改为「每条用户消息」，并明确摘要/上文里的行动标签是历史不是当前状态。起因：AGCopilot「飞书 Grimm」会话从分析转修改时未重新分类主行动，沿用压缩摘要里的旧标签惯性滑入实现，多行为路径全程无 work（真实偏离案例，见 `bywork/memory/evaluation.md`）。

## 1.0.0

ByWork 首个公开版本。一个名为 `bw` 的 Agent Skill，用 `work/{slug}/`、`memory/{topic}.md` 与按需的 `vision/` 管理软件演化：按用户当前行动推进澄清、改变、理解与审查、记忆与方向。

- 当前工作保存在 `bywork/work/{slug}/index.md`，顶部五项检查点（status / current_unit / next_action / must_hold / proof_gap）；行为证明表逐行从真实入口验证并回写。
- 长期判断按主题写入 `bywork/memory/`；产品方向按需整理到 `bywork/vision/`。
- 完成门：所有证明通过、范围覆盖、外部验收无失败且 `proof_gap` 恰为空才写 `status: complete`；`scripts/check_work.py` 机械校验状态值、缺口与 complete-work 封存。
- 维护侧 `tools/` 提供发布检查、checker 自检、脚本夹具与效果评测运行器。