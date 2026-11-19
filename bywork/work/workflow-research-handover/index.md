---
kind: work
status: in_progress
current_unit: "重新调研并设计 ByWork 工作流机制"
next_action: "在新电脑上克隆下述参考仓库，从一手仓库与论坛原始材料出发重新独立调研并给出设计方案"
must_hold: "完全独立调研与思考，不采信旧会话的任何主观结论或方案草稿；保持轻量化工作流的极简体验，避免增加无意义的流程摩擦"
proof_gap: "待新会话完成独立调研、确定设计方案并在真实长会话中验证"
---

# 工作流调研交接与仓库克隆清单（跨设备接续）

## 目标与背景

- **待解决的核心问题**：
  1. 在真实长会话（经历多次上下文压缩）或简单任务中，如何让工作流规则（姿态判断、检查点维护、经验沉淀、收尾汇总等）稳定生效，同时**不破坏轻量化工作流的极简体验、不产生高昂的工具调用与重试摩擦**。
  2. 探索工作流的分发与承载形态：既可考察标准 Skill 目录（含 `scripts/` 等，如 OpenSpec、Trellis 的做法），也可考察专门针对 `pi`（派）宿主的 Package 形态（含 `skills`、extension、MCP 等），或参考 DeepSeek Super-agent、论坛实践（60 楼/68 楼）等架构设计。
- **前序真实会话中观察到的客观现象（原会话保存在旧设备上，新设备无需导出即可参考以下事实）**：
  - **现象 1（长会话压缩后规则退化）**：在两场加载了 `bw` 1.0.3 的真实会话中，当 `<skill_content name="bw">`（`SKILL.md` 正文）尚未被上下文压缩工具折叠时，模型 4/4 次回复均输出了完整的三段收尾总结；一旦 `SKILL.md` 与 `references/` 被压缩成一句话摘要后，后续全部回复（共 10 次）均不再输出收尾总结，且在未使用 `check_work.py --close` 的情况下直接手写 `status: done` 或旧版 v1 字段。同一场会话中，位于宿主 System Prompt 层的 Ponytail 指令在每次压缩后均存活。
  - **现象 2（仅靠 Skill `description` 一句话提示未能触发重读）**：在 `bw` 1.0.4 将 `SKILL.md` 的 `description` 改为 `软件开发工作流：做任何事之前，先调用它。` 后，实测一场经历 3 次压缩的简单 UI 修改会话：模型仅在开头调用过 1 次 `bw`，后续压缩后未再重新调用 `bw`，也未调用任何脚本，最终回复同样遗漏了三段收尾总结。

## 全部调研项目的 Git 仓库清单与一键克隆命令

新电脑上本地没有参考仓库，可按需在工作区旁创建 `reference/` 目录并一键克隆。

### 一、AI 工作流与记忆系统仓库（16 个）

一键克隆全部 16 个工作流仓库：

```bash
mkdir -p ../reference/ai-workflows && cd ../reference/ai-workflows && \
  git clone https://github.com/Fission-AI/OpenSpec.git openspec && \
  git clone https://github.com/mattpocock/skills.git matt-skills && \
  git clone https://github.com/obra/superpowers.git superpowers && \
  git clone https://github.com/github/spec-kit.git spec-kit && \
  git clone https://github.com/bmad-code-org/BMAD-METHOD.git bmad && \
  git clone https://github.com/garrytan/gstack.git gstack && \
  git clone https://github.com/snarktank/ralph.git ralph && \
  git clone https://github.com/czm15053/write-notes-like-deepseek.git write-notes-like-deepseek && \
  git clone https://github.com/cursor/plugins.git cursor-plugins && \
  git clone https://github.com/mindfold-ai/trellis.git trellis && \
  git clone https://github.com/deepseek-ai/dsh-superagent-prototype.git dsh-superagent-prototype && \
  git clone https://github.com/open-gsd/gsd-core.git gsd-core && \
  git clone https://github.com/clawplays/ospec.git ospec && \
  git clone https://github.com/KbWen/agentic-os.git agentic-os && \
  git clone https://github.com/thedotmack/claude-mem.git claude-mem && \
  git clone https://github.com/codestable/CodeStable-Lite.git codestable-lite
```

| 项目名称 | Git 克隆地址 | 补充链接 / 说明 |
|---|---|---|
| **OpenSpec** (`Fission-AI/OpenSpec`) | `https://github.com/Fission-AI/OpenSpec.git` | CLI + Skills 规范驱动工作流 |
| **Matt Pocock Skills** (`mattpocock/skills`) | `https://github.com/mattpocock/skills.git` | `grilling` / `domain-modeling` / `to-tickets` / `implement-spec` 等 |
| **Superpowers** (`obra/superpowers`) | `https://github.com/obra/superpowers.git` | Hooks + Skills 工作流 |
| **Trellis** (`mindfold-ai/trellis`) | `https://github.com/mindfold-ai/trellis.git` | 文档：`https://docs.trytrellis.app` |
| **DeepSeek Super-agent Prototype** (`deepseek-ai/dsh-superagent-prototype`) | `https://github.com/deepseek-ai/dsh-superagent-prototype.git` | DeepSeek 官方开源的 Super-agent 原型插件 |
| **write-notes-like-deepseek** (`czm15053/write-notes-like-deepseek`) | `https://github.com/czm15053/write-notes-like-deepseek.git` | 提炼自 `deepseek-harness` 的决策笔记体系与校验脚本 |
| **GSD Core** (`open-gsd/gsd-core`) | `https://github.com/open-gsd/gsd-core.git` | 原 `https://github.com/gsd-build/get-shit-done.git` 迁移后的主仓 |
| **OSpec** (`clawplays/ospec`) | `https://github.com/clawplays/ospec.git` | 主页：`https://ospec.ai` |
| **Agentic OS** (`KbWen/agentic-os`) | `https://github.com/KbWen/agentic-os.git` | 基于 `AGENTS.md` 与校验脚本的工作流 |
| **claude-mem** (`thedotmack/claude-mem`) | `https://github.com/thedotmack/claude-mem.git` | 跨会话与压缩的记忆插件 |
| **Spec Kit** (`github/spec-kit`) | `https://github.com/github/spec-kit.git` | GitHub Spec-Driven Development 工具包 |
| **BMAD-METHOD** (`bmad-code-org/BMAD-METHOD`) | `https://github.com/bmad-code-org/BMAD-METHOD.git` | 多角色敏捷开发工作流 |
| **gstack** (`garrytan/gstack`) | `https://github.com/garrytan/gstack.git` | 工程规划、审查与验证技能集 |
| **Ralph** (`snarktank/ralph`) | `https://github.com/snarktank/ralph.git` | 自主循环执行 Agent 工作流 |
| **Cursor Plugins** (`cursor/plugins`) | `https://github.com/cursor/plugins.git` | Cursor 插件与规则示例 |
| **CodeStable-Lite** (`codestable/CodeStable-Lite`) | `https://github.com/codestable/CodeStable-Lite.git` | `NOTICE.md` 中引用的工程原则上游 |

### 二、宿主、运行环境与 Pi Package / Extension 参考仓库（9 个）

一键克隆宿主与扩展参考仓库：

```bash
mkdir -p ../reference/harnesses && cd ../reference/harnesses && \
  git clone https://github.com/deepseek-ai/deepseek-harness.git deepseek-harness && \
  git clone https://github.com/yetone/magpie.git magpie && \
  git clone https://github.com/DietrichGebert/ponytail.git ponytail && \
  git clone https://github.com/ByteTrue/pi-extensions-collection.git pi-extensions-collection && \
  git clone https://github.com/anomalyco/opencode.git opencode-anomalyco && \
  git clone https://github.com/sst/opencode.git opencode && \
  git clone https://github.com/cortexkit/magic-context.git magic-context && \
  git clone https://github.com/multica-ai/multica.git multica && \
  git clone https://github.com/getpaseo/paseo.git paseo
```

| 项目名称 | Git 克隆地址 | 说明 |
|---|---|---|
| **DeepSeek Harness** (`deepseek-ai/deepseek-harness`) | `https://github.com/deepseek-ai/deepseek-harness.git` | DeepSeek 官方 Agent 宿主（含 `.agents/notes/` 原生笔记实践） |
| **Magpie** (`yetone/magpie`) | `https://github.com/yetone/magpie.git` | 桌面端宿主 |
| **Ponytail** (`DietrichGebert/ponytail`) | `https://github.com/DietrichGebert/ponytail.git` | 包含 `pi-extension` 与 `skills` 的 Pi Package 示例 |
| **pi-extensions-collection** (`ByteTrue/pi-extensions-collection`) | `https://github.com/ByteTrue/pi-extensions-collection.git` | 自研 Pi Extensions 集合（含 `goal`、`auto-compact`、`subagent` 等） |
| **OpenCode (anomalyco)** (`anomalyco/opencode`) | `https://github.com/anomalyco/opencode.git` | OpenCode 分支实现 |
| **OpenCode (sst)** (`sst/opencode`) | `https://github.com/sst/opencode.git` | OpenCode 上游仓库（文档：`https://opencode.ai/docs`） |
| **magic-context** (`cortexkit/magic-context`) | `https://github.com/cortexkit/magic-context.git` | 上下文管理参考 |
| **multica** (`multica-ai/multica`) | `https://github.com/multica-ai/multica.git` | 多 Agent 协作参考 |
| **paseo** (`getpaseo/paseo`) | `https://github.com/getpaseo/paseo.git` | Agent 运行环境参考 |

> 注：若新电脑安装了 `pi`（`@earendil-works/pi-coding-agent` 或 `@mariozechner/pi-coding-agent`），可在其 npm 全局安装目录的 `docs/` 下直接查阅官方 `packages.md`、`extensions.md`、`skills.md` 文档。

### 三、论坛讨论与技术文章原始链接

1. **Linux.do 讨论帖 1：《彻底抛弃 Trellis，工作已经完全交给 AI 了，分享下我的工作流》**
   - 网页链接：`https://linux.do/t/topic/3143498/60`（重点看 **60 楼** `planetarium1001` 与 **68 楼** `SenMing`）
   - Discourse JSON 接口（在已登录 `linux.do` 的浏览器中可直读）：`https://linux.do/t/3143498/60.json`
2. **Linux.do 讨论帖 2：《通了个宵，终于把 Super-Agent 架构玩明白了》**
   - 网页链接：`https://linux.do/t/topic/3109398`（看 **1 楼**）
   - Discourse JSON 接口：`https://linux.do/t/3109398.json`
3. **DeepSeek 官方文章：《Super-agent 设计探索：迈向更自主的 Agent 系统》**
   - 发布日期：2026-10-31（DeepSeek 产品部 / DeepSeek Harness 团队）
   - 配套开源原型仓库：`https://github.com/deepseek-ai/dsh-superagent-prototype.git`

### 四、本仓库内的历史背景文档（随本仓 Git 同步）

- `bywork/work/v2-delivery/research-direction.md`
- `bywork/work/v2-delivery/research-evidence-matrix.md`
- `bywork/work/v2-delivery/principles-review.md`
- `bywork/memory/project.md`
- `bywork/memory/evaluation.md`

## 行为证明

| 行为路径 | 真实入口 | 操作 | 应观察到 | 证据 | 结果 |
|---|---|---|---|---|---|
| 整理跨设备客观交接索引与全量克隆清单 | `bywork/work/workflow-research-handover/index.md` | 去除本机路径依赖，提供全量仓库 `git clone` 命令并通过 `check_work.py` 校验 | 新电脑仅凭本仓库即可一键克隆全部参考项目，不含旧会话主观观点 | `python3 skills/bw/scripts/check_work.py --project .` | 通过 |
| 新会话独立完成工作流调研与新方案验证 | 新会话 | 从一手仓库与原始材料出发重新调研、设计并实测验证 | 产出用户认可的工作流设计并通过真实会话验证 | 待新会话执行 | 待跑 |

## 完成核对

- 行为门：跨设备交接文档已就绪，新方案调研与实测待新会话执行，缺口已写入 `proof_gap`
- 范围门：无 `scope.md`
- 契约门：已移除旧 `compaction-survival-research/` 及本机路径假设，仅保留客观事实与全量 Git 克隆清单
- 完成门：保持 `in_progress` 供新电脑的新会话直接接手
- 需要用户看的推断或无法判定：要在另一台电脑上拉取到这份交接文档，需要将当前工作区改动 commit 并 push 到远端仓库
