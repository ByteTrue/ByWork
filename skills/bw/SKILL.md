---
name: bw
description: 通用工程工作流：做任何事之前，先调用它。
---

# ByWork (`bw`)

每收到一条消息或开启新阶段，先判断**当前这一步的单一动作**，只读该动作对应的那份短文档（摘要里的旧标签是历史，不沿用）：

| 当前动作 | 什么时候选它 | 必读（只读这一份） |
| :--- | :--- | :--- |
| **理解** | 刚接手、摸清现状与链路、定位问题根因 | [`references/understand.md`](references/understand.md) |
| **澄清** | 目标/边界/取舍未定，需要追问或收敛范围 | [`references/clarify.md`](references/clarify.md) |
| **方案** | 进入改动前拆解设计、写 `proposed/` 提案与验收标准 | [`references/plan.md`](references/plan.md) |
| **实现** | 按既有要求或 `proposed/` 逐项落地 | [`references/implement.md`](references/implement.md) |
| **证明** | 跑真实入口验证、填验收表证据与缺口 | [`references/prove.md`](references/prove.md) |
| **收尾** | 验收通过蜕皮为 `implemented/`、否决入 `rejected/` 或清理 | [`references/close.md`](references/close.md) |
| **审查** | 评审改动/方案、找漏洞与可删减冗余（可随时穿插） | [`references/review.md`](references/review.md) |
| **记忆** | 实施中途或事后沉淀长期决策、更新现行约束或归档旧篇 | [`references/memory.md`](references/memory.md) |

## 工作区结构（进行中与长期记忆四态合一）

```text
bywork/
├── proposed/<分类>/yyyy-mm-dd-topic.md     # 进行中的工作提案与检查点（含 frontmatter + 验收表）
├── implemented/<分类>/yyyy-mm-dd-topic.md  # 当前生效的长期决策与约束（现在时，无过程噪音）
├── rejected/<分类>/yyyy-mm-dd-topic.md     # 被证伪/否决的方案与避坑记录（Status: rejected — <原因>）
├── archived/<分类>/yyyy-mm-dd-topic.md     # 被替代的历史快照（由 archived/manifest.json SHA-256 封印）
└── vision/index.md                         # 项目方向与不变量（按需创建，模板见 templates/vision.md）
```

- **分类目录**：按主题使用一层小写目录名（如 `architecture`、`feature`、`bug-fix`、`simplification`、`process`、`testing` 等）。
- **禁止 `INDEX.md`**：任何层级都不建中心化索引文件；靠目录树、相对 Markdown 链接、`// Note: ... 见 bywork/...` 源码锚点与排除 `archived/` 的检索定位。
- **压缩或新会话接续**：先扫描 `bywork/proposed/` 读取活跃工作的 frontmatter（`status` / `current_unit` / `next_action` / `must_hold` / `proof_gap`），从检查点继续。

## 底线

- `proposed/` 经 `bw.py complete` 或 `reject` 转为现行或被否记录；已实施记录经 `archive` 封存。命令用法见 `scripts/bw.py -h`。
- `implemented/` 只用现在时陈述当前生效的决策，严禁留未来时计划章节，严禁当成按日期追加的流水账。
- 写新篇时当场审计同主题旧篇，明确仍有效的范围；保留、替代与清理按 [旧记录治理](references/archiving.md) 执行。
- 既有验收标准与基线只读，不删改既有标准或篡改期望值来凑通过；阻塞或无法验证时如实保留在 `proof_gap`。
- 节省上下文见 [`references/economy.md`](references/economy.md)；写持久文档、提交说明和汇报前读 [`references/writing.md`](references/writing.md)。

## 汇报

结论先给；推断与无法判定集中放到「需要你」，每项带推荐做法与一句理由。每次回复末尾附上三段收尾总结：

```markdown
**做了什么**：一句总领起头；多件事换行用 `-` 列出：
- 要点一
- 要点二

**下一步**
1. 下一步动作

**需要你**（没有写「无」）
1. 待决定或待验证事项——推荐做法与一句理由
```

## 工具、模板与资产

- [`scripts/bw.py`](scripts/bw.py)：统一 CLI（运行 `python3 <bw-skill>/scripts/bw.py -h` 查看 `init / check / complete / reject / archive / anchors / board` 用法；接入或升级项目读 [`references/onboard.md`](references/onboard.md)）。
- [`templates/proposed.md`](templates/proposed.md) / [`templates/implemented.md`](templates/implemented.md) / [`templates/rejected.md`](templates/rejected.md) / [`templates/vision.md`](templates/vision.md)：四态与方向模板。
- [`assets/board.html`](assets/board.html)：本地工程决策看板 HTML 模板（由 `bw.py board --init` 或 `--bundle` 生成）。
