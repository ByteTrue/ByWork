---
kind: work
status: in_progress
current_unit: "调研：长任务/上下文压缩后 Agent Skill 规则退化的问题变体与成熟工作流解法"
next_action: "把 1.0.4 装到项目 .agents/skills/bw/ 后，在真实长会话跑到自然压缩，验收压缩后是否重新加载 bw、收尾总结是否恢复、收口是否走 --close；不通过即停，转评估 B"
must_hold: "不往提示词里塞「检测自己被压缩」或「把枚举/模板抄进模板与脚本」等打补丁式垃圾规则；不做安装器与逐宿主适配（用户明确否决）；指令层只放再入指针不放正文副本，内容单一归属于技能包"
proof_gap: "方案 A 已实施（1.0.4 description 一句话），但压缩后是否真的触发再入未实测；须真实长会话自然压缩验收"
---

# 跨压缩规则保活调研

## 目标与边界

- **目标**：弄清「长任务/上下文压缩后，模型忘记 Agent Skill 工作流契约（收尾总结格式、状态合法值、`--close` 收口、work 模板）」这一问题在分布式工作流、Agent 记忆架构与宿主生命周期中的本质变体，调研既有对象（openspec、superpowers、spec-kit、claude-mem、GSD、AgentOS/BMAD）及宿主原生机制（OpenCode plugin/hooks/instructions、Claude Code skills/hooks）的成熟解法，产出对照评估与推荐方向。
- **不做**：不往 `SKILL.md` 塞「被压缩后必须重读/摘要必须保留 XX」的元提示词；不把收尾总结模板、状态枚举复制进 `templates/work.md` 或新建 `--work` 脚本做肤浅修补。
- **起因**：复盘 `ses_e0d28f98ffferhFEZuCS0Rp7Rn`（AGCopilot）与 `ses_e0d5fb568ffej2YAq72xhlu6yf`（byspace）发现，两场会话均加载了 1.0.3 最新版 `bw`，但在 `compress` 把 `<skill_content name="bw">`（`SKILL.md`）压缩成一句话摘要的那一刻起，收尾总结 100% 消失（会话 2 压缩前 4/4 遵守，压缩后 0/3），work 退化为手写 `status: done` 与 v1 ByIssue 字段，全程 0 次调用 `check_work.py --close`。而 System Prompt 层的 Ponytail 指令全程未忘。

## 已定方案与约束

- 用户明确要求（m00515）：「如果确实很高概率出现压缩过后一定会忘记流程，我们应该去调研其他的方案，而不是这样往提示词里塞垃圾去补……我们要思考我们遇到的问题是什么问题的变体，然后去找别人成熟的解决方案，而不是在这里肤浅地、没有章法地去改。」
- 既有被否方案（`bywork/memory/project.md:62`）：「压缩后第一项工具调用必须是 read 的硬门」已被七轮提示堆叠证伪，不可重提。
- 调研维度：
  1. **宿主原生生命周期/持久层**：OpenCode plugin hooks（如 `experimental.chat.system.transform`、`experimental.session.compacting`、`instructions`）、Claude Code hooks（`SessionStart` / `PreCompact` / `UserPromptSubmit`）、原生 Skill 注入位置。
  2. **外部工作流与记忆系统**：openspec（CLI 驱动 vs 纯散文）、superpowers（hooks + verification-before-completion）、claude-mem（observation 注入）、spec-kit（checklist CLI）、GSD / AgentOS（state/ledger 驱动）。
  3. **问题归类**：这是「瞬态上下文中的指令 vs 持久状态/持久工具/宿主注入」的经典控制平面问题（Instruction Eviction / Workflow Amnesia under Context Compaction）。

## 行为证明

| 行为路径 | 真实入口 | 操作 | 应观察到 | 证据 | 结果 |
|---|---|---|---|---|---|
| 确认两会话的压缩分界与退化事实 | 会话原文导出 | 对比 `SKILL.md` 存活期与压缩后的回复格式、work frontmatter、脚本调用 | 压缩前 100% 遵守收尾总结，压缩后 0% 且退化为 done/v1 字段/无 --close | `retro-e0d28f98.txt` seq449 与 `retro-e0d5fb56.txt` seq686/seq696/seq3537 | 通过 |
| 调研宿主原生持久注入/hook 机制 | OpenCode V2 docs / Claude Code docs | 查 instructions 组装顺序、compaction 基线、plugin `context`/`compaction`/`tool.hook`、skill frontmatter | 找到不依赖模型自觉、能在压缩后/每轮自动注入或强制校验的机制 | `research.md` §3；instructions 页组装顺序 6 项与「After compaction, the current versions of your instruction files become the session's baseline」；plugin 文档 :1437-1458 `context` 含 tool-driven continuations、`delete event.tools.write`；:1809-1819 `ctx.tool.hook`；:895 `skill.autoinvoke` | 通过 |
| 调研外部成熟工作流的解法 | 各仓一手 hooks/README/docs | 查 superpowers/ospec/claude-mem/GSD Core/agentic-os 如何处理契约保活与收口 | 归纳出各方案的保活机制与适用边界 | `research.md` §2：superpowers `SessionStart(startup\|clear\|compact)` 注入 SKILL 全文；ospec 仅 startup/clear/compact 注入静态契约；GSD `PreToolUse` 守卫 + STATE.md；agentic-os 自认「agent 忽略工作流 → Nothing machine-side → Advisory」 | 通过 |
| 产出对照评估与推荐方向 | 本 work `research.md` | 综合机制与问题变体，给出 2–3 个可选方向及取舍 | 用户能据此拍板下一步设计 | `research.md` §4 七方向对照（含 ⑤⑥⑦ 三条排除理由）、§5 方向一/二/三、§6 三个判断点 | 通过 |
| 查清纯 skill 有无压缩免疫通道 | OpenCode docs / superpowers 一手仓库 | 查 skill 加载时 description 与正文分别进哪一层，比对无 hook 宿主的做法 | 找到不需要安装器、不产生正文副本的免疫通道 | `research.md` §8：docs/skills「At each model step … lists only the ID, name, and description, not the full Markdown body」；本会话 14 次压缩后 description 仍逐字在 system prompt；superpowers README:92-94 Antigravity 段 + using-superpowers frontmatter 154 字符含行为要求 | 通过 |
| 查清 Matt/OpenSpec 的控偏机制与 bw 已吸收部分 | 本地 `reference/ai-workflows/` 一手副本 | 读 to-tickets/implement-spec/ask-matt/PHASE-BOUNDARIES 与 openspec-continue-change，比对 bw references 与 NOTICE | 分清「人工拆分」与「上下文结构」，找出可吸收与不可吸收项 | `research.md` §9：Matt 拆分由模型做（`to-tickets/SKILL.md:33`）、人只 Quiz（:42-56）、16 技能 user-invoked；OpenSpec 状态在 CLI（`continue-change:49,100,91`）；已吸收表 5 行 | 通过 |
| 候选修法在真实压缩后生效 | 真实长会话自然压缩 | 1.0.4 装入项目后跑到自然压缩，观测再入与格式恢复 | 压缩后重新加载 bw、三段收尾总结恢复、work 走 `--close` | 未实测；`description` 已改为一句话且发布检查通过 | 无法判定 |

## 证据与决定

- 2026-11-19：用户否决了「在 SKILL.md 写压缩保留句 / 在 work 模板塞枚举与总结提示 / 加 --work 脚本」的肤浅修补方案，要求先做系统性调研。
- 两会话原文取证：会话 2 `seq516` 刚读完 `templates/work.md`，`seq686`（L5780）将其与 `SKILL.md` 一并压缩，10 秒后 `seq696`（L5800）凭记忆手写 `index.md`（6 列变 5 列、状态 pending、漏 `## 完成核对`）；`seq3537` 手写 `status: done` 与 v1 字段。会话 1 `seq449`（L2980）在首次回复前即压掉 `SKILL.md`，整场 7 次回复 0 次收尾总结。
- 2026-11-19 调研定论：问题归类为「控制平面契约被放进数据平面」，非措辞问题。决定性依据是同场次对照——Ponytail（宿主 system 层）10/10 存活，bw（消息历史里的 skill 返回值）0/10。四家成熟工作流均把保活交给宿主重注入或工具守卫，无一家靠提醒模型。
- 排除三条并记录理由：⑦提示词硬门（本仓七轮证伪，project.md:62）、⑥摘要保留原文（v2-delivery 候选二十一第二轮实测模型仍不遵守）、⑤脚本携带契约（压缩后脚本调用率为 0，触发调用的句子本身已被驱逐，只能作补充）。
- 关键机制事实：OpenCode skill frontmatter **无 hooks 字段**（Claude Code 有），故 OpenCode 侧只能走 config instructions 或 plugin；全局/向上 AGENTS.md 与 config instructions 压缩免疫，嵌套 AGENTS.md 走历史会被驱逐。
- `ctx.tool.hook("execute.before")` 能否**否决**调用，文档只写 inspect/replace，未证实——列为方向二穿刺项，不假设成立。
- 2026-11-19 用户收窄为项目级 `AGENTS.md` + 脚本幂等补写 + 极简内容，取证结论见 `research.md` §7：①项目根 `AGENTS.md` 在向上发现链里、属指令层，本复盘会话经 8 次压缩后 system prompt 仍逐字带着它，机制实测成立；②**「模型一定会执行的脚本」前提被证伪**——两会话 `check_work.py`/`init_bywork.py` 实际执行 0 次，命中全是文档正文，故第一次触发点是唯一未决机制问题；③AGCopilot 无 `AGENTS.md` 也无 `CLAUDE.md`（从零创建，不被 gitignore），byspace 有 175 行且其 `repo-config.test.mjs:276-300` 只做包含性断言故追加安全；④最小集判据=「失效后模型有无别的机会重新拿到」；⑤与 project.md:56「不要求用户为 bw 修改 AGENTS.md」直接冲突，须显式修订并保留「手动调用技能必须完整生效」这半句。
- 2026-11-19 用户追问「纯 skill 是不是永远没办法、知名工作流是不是都有安装器」，明确不想做安装器也不想逐宿主适配。取证结论见 `research.md` §8：①四个对象（superpowers/spec-kit/openspec/agentic-os）确实都有安装或部署动作且逐宿主适配，用户的顾虑指向这套方案共同的复杂成本；②**发现被忽略的免疫通道**——skill 的 ID+name+description 每个 model step 重新列出、属指令层，只有正文进历史可被压缩，本会话 14 次压缩后 description 仍逐字存在；③superpowers 在无 hook 宿主（Antigravity）上正是靠 description 促使模型加载技能，其 154 字符 description 含行为要求而非仅触发条件；④据此指令层只需放**再入指针**、不必抄正文，§7.4「模板必须进指令层」降级，第二套表述的代价被绕开；⑤bw 现有 description 301 字符是 superpowers 的 2.0 倍却零行为契约，这条通道当前完全闲置。
- 方案排序改为 A（description 再入指针，零安装器零副本）→ B（onboard 技能 + 脚本写项目 `AGENTS.md`，A 失败后的下一档）→ C（plugin/适配器，仅 A、B 均不成立时）。A 与被否的七轮硬门**承载层不同**（那些写在会被驱逐的正文/摘要里，A 写在每步重列的 description），不是重提旧案，但仍是提示词依赖，须真实会话验收、不通过即停不加码。
- 事实澄清：`AGENTS.md` 是 Linux Foundation / Agentic AI Foundation 托管的跨厂商开放标准（Codex、opencode、Cursor、Copilot、Gemini CLI、Windsurf、Zed、Aider 等均支持），写它**不算逐客户端适配**；真正需要逐家适配的是 hooks。故 B 的通用性不比 A 差，差别在用户动作与副本代价。
- 2026-11-19 用户批准「先试试吧」，并要求 `description` 只留一句话表达两件事：身份是开发工作流、触发是永远。已实施 1.0.4：`skills/bw/SKILL.md:3` 改为 `description: 软件开发工作流：做任何事之前，先调用它。`（原 301 字符）。砍掉的触发词并非丢信息——`SKILL.md:20-23` 四种行动表里逐个都在，原本就是两处重复。措辞不出现「压缩」字样（用户否决过「让模型知道自己被压缩」这种说法）。
- **触发条件两次被用户纠正，最终落在「做任何事之前」**：①不能绑「每条用户消息」——AGCopilot 那场只有两条用户消息，中间是极长的自主工作并自行压缩多轮，按消息计数在那些工具驱动的续跑轮次一次都不触发；②也不能绑「改代码/下结论/收尾」这类具体动作——**bw 的第一个动作是判断姿态，必须发生在探索之前**，等到改代码才调用，姿态判断已被跳过（我曾以「读代码也算动手会导致过度调用」为由收窄，这个顾虑本身错了：过度调用的代价远小于跳过姿态判断）。最终形状与 superpowers `using-superpowers` 的 description 同构（before ANY response including clarifying questions）。`SKILL.md:12` 的行动路由仍写「每条用户消息」——那是选主行动，与再入触发是两件事，未改。
- A 方案不需要碰 `AGENTS.md`，故 `bywork/memory/project.md:56`「接入不要求用户为 bw 修改 AGENTS.md」这条边界**依然成立，未修订**。只有 B 方案才与它冲突。
- 2026-11-19 用户问 Matt（Matt Pocock）与 OpenSpec 如何控跑偏，并纠正我走网络取证是绕远路——**本地早已有 `/Users/zijie/workspace/reference/ai-workflows/` 八仓副本**（matt-skills HEAD=5863806 与线上一致）。结论见 `research.md` §9：①Matt 不靠人工拆 issue，模型拆 tracer-bullet 切片（判据「装得进一个 fresh context window」），人只 Quiz 颗粒度与阻塞边；控偏靠 fresh-context-per-ticket 子代理 + context pointers + phase boundary 纪律，且 16 个主流程技能是 `disable-model-invocation: true`（人手动点，有意不全自动）；②OpenSpec 12 技能全 model-invoked，机械性在 `openspec status --json` 返回 artifact 状态、模型取第一个 ready、每次只做一个 artifact、依赖必须从磁盘重读——**压缩丢的是「怎么问 CLI」而非「当前到哪步」**，这正是 bw 缺的可查询状态机；③bw 已吸收 grilling/domain-modeling 镜像、完成机械前置、真相与 change 分离、从磁盘重读，未吸收状态机与 fresh-context 编排；④**判断不学四段拆分**：拆成四技能会让压缩后要记的东西更多，OpenSpec 敢拆因为有 CLI 可重问、Matt 敢拆因为人手动点，两者前提 bw 都没有；⑤值得考虑的是 phase boundary 纪律（`change.md:25` 的行为单元已同构，缺的是「压缩只该发生在单元边界」这层），但它仍属提示词依赖且与用户否决过的「让模型知道自己被压缩」相邻，须先确认是否越界。
- `bash tools/release-check.sh --no-deploy` 通过（checker、selftest、脚本夹具、runner 14/14）。过程中踩到 checker 老坑：`tools/check-skill-repository.py` 的路径正则不认 `review.md:107,114` 这种逗号双行号，须写成 `:107-114` 区间。

## 完成核对

- 行为门：需求逐项有证明行，每行有实际断言，剩余缺口已写入 `proof_gap`：调研四行已通过，修法生效行未实施
- 范围门：无 `scope.md` / 已逐项对账：无
- 契约门：共享路径改动有基线和同入口比较，可选策略逐分支验证，持久化/生命周期经过新进程或重启入口，既有测试保持原文件原断言：本阶段纯调研不改技能
- 完成门：外部验收无失败，`proof_gap` 恰为空，运行 `scripts/check_work.py --close {slug}` 收口（由脚本写入 `complete`）；否则保留 `in_progress`/`blocked` 并点名缺口：未收口，修法待用户拍板
- 需要用户看的推断或无法判定：是否先做方案 A（description 再入指针）及其「模型会服从 description 行为句」这一未实测假设；A 失败后是否接受 B 的用户每项目动作与 `project.md:56` 边界修订