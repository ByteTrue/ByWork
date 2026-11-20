# ByWork (`bw`)

[English](README.en.md)

ByWork 是一个通用工程管理 Agent Skill：用检查点接续长会话，用现行决定、替代关系与验证证据维护长期项目。

具体领域能力由模型和其他技能提供。ByWork 按当前动作加载方法，将进行中的提案转为现行决定或被否记录；已实施但不再指导工作的记录可归档。检查点与长期记忆共享这套生命周期。

## 为什么这样设计

- **6+2 单职责路由**：入口 [`skills/bw/SKILL.md`](skills/bw/SKILL.md) 提供动作地图与共同契约。理解、澄清、方案、实现、证明、收尾各有对应方法；审查与记忆可随时穿插。按当前需要读取。
- **四态生命周期**：跨步骤工作保存在 `proposed/`，包含检查点与验收表。模型整理事实和理由，`bw.py complete` 核验后移入 `implemented/`；`reject` 留下被否提案；`archive` 封存历史并登记哈希。命令拒绝非法流转与同名覆盖。
- **维护现行知识**：按分类、关键词和链接检索；事实与产物同改，新篇明确旧篇哪些仍有效。仍有独立约束的记录保持活跃，充分吸收后再删除或归档。规则见 [旧记录治理](skills/bw/references/archiving.md)。

阅读 [为什么做 ByWork](<WHY BYWORK.md>) 了解背后的真实踩坑与演进过程。

## 安装

```bash
npx skills add https://github.com/ByteTrue/ByWork --skill bw
```

### 推荐：在指令文件中保留入口

长会话历经多次上下文压缩后，早期工具输出会被折叠。建议在全局（如 `~/.config/opencode/AGENTS.md`、`~/.claude/CLAUDE.md`）或项目根 `AGENTS.md` 中加入一行：

```markdown
做任何事之前，先读取 `bw` 技能（`SKILL.md`），按其中的行动路由开展工作。
```

这行指令提供重读入口；是否常驻取决于宿主加载方式，模型是否遵循仍需真实会话验证。结构检查通过也不代表证据真实或长期管理效果已经得到证明。

### 已有 1.x 项目

升级技能后，旧 `bywork/work/`、`bywork/memory/` 需要按[接入说明](skills/bw/references/onboard.md#从-1x-工作区迁移)迁移；`init` 会保留原件并提示，且只创建新目录。承接未完成验收和现行约束、核对链接后，通过 `bw.py check` 再开始四态工作流。

## 行动路由

| 行动 | 典型信号 | 按需读取 |
|---|---|---|
| **理解** | 怎么工作的、梳理现状、为什么这样、影响哪几处 | [`references/understand.md`](skills/bw/references/understand.md) |
| **澄清** | 聊聊、需求模糊、多方向未定、先别动手、拷问我 | [`references/clarify.md`](skills/bw/references/clarify.md) |
| **方案** | 怎么设计、定方案、列改动范围与验收标准 | [`references/plan.md`](skills/bw/references/plan.md) |
| **实现** | 做这个、推进、快改、修这个、直接开干 | [`references/implement.md`](skills/bw/references/implement.md) |
| **证明** | 验一下、跑通没、核对效果、补验证 | [`references/prove.md`](skills/bw/references/prove.md) |
| **收尾** | 做完了、收口、归档、准备交付 | [`references/close.md`](skills/bw/references/close.md) |
| **审查** | review、评审、挑刺、看看这改动或文稿 | [`references/review.md`](skills/bw/references/review.md) |
| **记忆** | 记一下坑、沉淀决定、淘汰旧方案、整理长期方向 | [`references/memory.md`](skills/bw/references/memory.md) |

## 工作区结构

```text
bywork/
  proposed/<分类>/yyyy-mm-dd-topic.md     # 进行中的提案与工作检查点（含验收证据表）
  implemented/<分类>/yyyy-mm-dd-topic.md  # 现行有效的长期决定（现在时，无过程流水账）
  rejected/<分类>/yyyy-mm-dd-topic.md     # 被否决的备选方案与避坑记录
  archived/<分类>/yyyy-mm-dd-topic.md     # 已被替代或完成历史使命的只读封存
  archived/manifest.json                  # 归档文件的 SHA-256 完整性封印
  vision/index.md                         # 项目级目标、边界与非目标（按需创建）
```

首次接入项目时运行。下面以项目级安装的 `.agents/skills/bw/` 为例；若安装器报告其他位置，用实际技能目录替换。维护本仓库时入口才是 `skills/bw/`：

```bash
# 查看全部子命令说明
python3 .agents/skills/bw/scripts/bw.py -h

# 初始化或保留 bywork/{proposed,implemented,rejected,archived}
python3 .agents/skills/bw/scripts/bw.py init --project /path/to/project

# 校验四态结构、禁 INDEX.md、必填节与验收表、相对链接死链及归档 SHA-256 封印
python3 .agents/skills/bw/scripts/bw.py check --project .

# 生命周期流转与归档封印
python3 .agents/skills/bw/scripts/bw.py complete yyyy-mm-dd-topic.md --project .
python3 .agents/skills/bw/scripts/bw.py reject yyyy-mm-dd-topic.md --reason "一句话原因" --project .
python3 .agents/skills/bw/scripts/bw.py archive yyyy-mm-dd-old.md --superseded-by yyyy-mm-dd-new.md --project .

# 源码反向锚点体检与工程决策看板生成
python3 .agents/skills/bw/scripts/bw.py anchors --project .
python3 .agents/skills/bw/scripts/bw.py board --init --project .
python3 .agents/skills/bw/scripts/bw.py board --bundle --project .
```

Git 项目的归档检查默认对照 `HEAD`，CI 可用 `BW_ARCHIVE_BASE_REF` 指定可信基线；无 Git 或尚无提交时，只核对当前文件与清单。`bw.py check` 应接入项目既有交付检查，技能本身不会安装宿主钩子或 CI。

## 维护这个仓库

完整检查需要 Python 3.10+ 与 Node.js 22+，覆盖仓库结构、CLI、看板解析和评测运行器。看板交互另用本机 Chrome 在隔离配置与离线模式下验证。

```bash
bash tools/release-check.sh --no-deploy
node tools/test-bw-board.cjs "/path/to/chrome"
```

提示词变更审查见 [`tools/prompt-review.md`](tools/prompt-review.md)，真实会话复盘见 [`tools/session-retro.md`](tools/session-retro.md)，评测运行器见 [`tools/evaluation/README.md`](tools/evaluation/README.md)。

## 致谢与许可

MIT，见 [`LICENSE`](LICENSE) 与随包分发的 [`skills/bw/NOTICE.md`](skills/bw/NOTICE.md)。感谢 [CodeStable-Lite](https://github.com/codestable/CodeStable-Lite)、[Matt Pocock 的 `skills`](https://github.com/mattpocock/skills) 与 [write-notes-like-deepseek](https://github.com/czm15053/write-notes-like-deepseek)。