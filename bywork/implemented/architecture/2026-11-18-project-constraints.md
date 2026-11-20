# 项目约束与发布依据

Status: implemented

## 问题

维护 ByWork 技能仓库时，散文规则、模板与脚本就是工作流逻辑本身。如果缺少单一权威归属、机械校验与发布闭环，提示词会在迭代中膨胀、重复或与已部署副本脱节。

## 决策

适用范围：维护 ByWork 技能仓库。工作流契约以 `skills/bw/SKILL.md` 及其 `references/` 为准。

### 项目定位与自足边界

- ByWork 是一个单技能仓库，分发 `skills/bw/` 下名为 `bw` 的通用工作流 Agent Skill。产品形态是极薄路由入口、单职责方法文件、状态模板、单一标准库 Python CLI（`scripts/bw.py`）和静态看板模板。
- 技能包内的每个文件都必须从入口、模板或另一个已达文件被引用，内部路径必须自足。
- `skills/bw/NOTICE.md` 随包携带根 `LICENSE` 和按文件标注的上游归属（CodeStable-Lite、Matt Pocock、czm15053/write-notes-like-deepseek）。
- 仓库使用标准库 Python、Markdown、shell 和浏览器 JavaScript。维护侧检查需要 Python 3.10+ 与 Node.js 22+；看板交互检查使用本机 Chrome。技能本体以中文为主。

### 提示词与工作区契约

- 一条规则只有一个权威归属；其他文件只通过链接或短指针进入它。
- 核心入口先按单职责判断当前行动（6 个主线动作：理解、澄清、方案、实现、证明、收尾；2 个横切动作：审查、记忆），再读取对应最小必读文件。
- 工作流文档只陈述当前成立的契约。演变原因、证据和取舍放在历史记录中。
- 否定式规则只在它阻止模型的强默认行为时保留；其他情况直接陈述正确动作。
- 提示词极简优雅：不绑定领域或宿主工具，不枚举具体领域例子，每行规则必须挣得它的注意力成本（改变模型默认行为或对应真实失败）。评测依据见 [2026-11-18-evaluation-findings.md](../testing/2026-11-18-evaluation-findings.md)。
- 当前 `bywork/` 统一采用四态生命周期目录（`proposed/`、`implemented/`、`rejected/`、`archived/`）与按需的 `vision/`，不设手工维护的全局 `INDEX.md`。

### 检查与发布

维护侧检查各自负责一件事：

| 规则 | 检查 |
|---|---|
| 版本号与发布记录一致 | `tools/check-skill-repository.py` |
| 技能包入口、许可证、路径可达且没有本仓专属路径 | `tools/check-skill-repository.py` |
| 工作区只含四态目录与按需的 `vision/`、无全局 `INDEX.md` | `tools/check-skill-repository.py`、`skills/bw/scripts/bw.py` |
| `proposed` 模板保留唯一检查点字段与验收标准表 | `tools/check-skill-repository.py` |
| checker 的每项检查可以变红 | `tools/check-skill-repository-selftest.py` |
| 初始化脚本在项目创建并保留四态目录 | `tools/check-skill-scripts.py` |
| 校验脚本执行四态结构校验、死链检查与 `complete`/`reject`/`archive` 流转 | `tools/check-skill-scripts.py` |
| 已知文件写入、Markdown 流转、锚点与评测失败反例 | `tools/test-bw-adversarial.py` |
| 看板两种载入方式数据一致；可选离线浏览器交互 | `tools/test-bw-board.cjs` |
| 本仓实际记录的结构、链接与归档基线一致 | `tools/release-check.sh` 调用 `bw.py check` |
| 项目级安装副本与源代码一致 | `tools/release-check.sh` |
| 评测运行器的证据采集与失败处理 | `tools/evaluation/test_runner.py` |

发布顺序：修改 `skills/bw/`，运行 `bash tools/release-check.sh --no-deploy`，更新 `VERSION` 和 `CHANGELOG.md`，用 `npx skills add` 同步用户项目的 `.agents/skills/bw/`，再运行 `bash tools/release-check.sh <项目级安装目录>`，最后按用户要求提交或分发。本仓库用相对软链接自举（`.agents/skills/bw` 指向 `../../skills/bw`）。用户通过 Magpie 管理的全局技能（`~/.config/magpie/library/skills/bw`，软链至 `~/.config/opencode/skills/bw`）在远端推送后可用 `magpie library skill update bw` 同步到最新提交。

## 备选方案

- **备选方案 A：压缩后第一项工具调用必须是 `read` 的硬门**。最强理由是试图强制模型在压缩后立即重读检查点；但七轮提示堆叠（固定口令、入口硬门、持久化 cue）仍被模型忽略，且未拦截过真实事故，故改为结果判据（动作与检查点一致、状态诚实、缺口不丢）。
- **备选方案 B：按已验证行为单元自动 commit**。最强理由是留存细粒度回滚点；但候选三十一实测模型全程 0 提交且业务全绿，未证明质量收益，故保持本地 commit 不禁止也不要求、push 必须授权。
- **备选方案 C：分开维护扁平 `work/{slug}/index.md` 与 `memory/{topic}.md`**。最强理由是初期目录少；但在长周期大型工程中扁平 `memory/` 会退化为缺乏分类、生命周期与淘汰机制的散沙，且 `work/` 与 `memory/` 割裂导致二次搬运，故在 2.0.0 升级为四态蜕皮统一架构（见 [2026-11-20-workflow-v3-redesign.md](2026-11-20-workflow-v3-redesign.md)）。
- **备选方案 D：手工写入宿主全局技能目录作为部署目标，或用外部公开评测集作为主验收**。宿主索引会清除不受管理的全局副本，公开评测集测不到检查点与诚实缺口纪律，故均不采用。

## 收益和代价

- 收益：方法按单一职责维护；结构、流转与封印可由自动化测试和发布脚本核查。事实新鲜度、理由完整性与模型是否遵循仍需真实会话和产物审查，机械检查不证明长期管理效果等价。
- 代价：修改技能结构时需同步更新仓库 checker、自测夹具与脚本测试。原始设计演进记录封存于 [2026-11-15-v2-readiness.md](../../archived/process/2026-11-15-v2-readiness.md) 与 [2026-11-17-v2-delivery.md](../../archived/process/2026-11-17-v2-delivery.md)。