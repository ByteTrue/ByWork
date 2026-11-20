# 对照 DSH 实际记录校正管理契约

Status: implemented

## 问题

收录工作流条文或通过结构测试，不能证明项目管理有效。记录既要保住仍有效的理由和验证边界，也要避免流转丢失与错误完成；现行文档中的命令、状态与效果承诺必须和实际能力一致。

## 决策

- 完成检查只接受模板规定的三种结果；完成要求各行通过、实际证据非空且无未决缺口。记录结构不能代替证据真实性审查。
- 流转仅作用于指定生命周期中的记录，拒绝同名覆盖、损坏清单与无效替代目标。完成转换保留验证正文；归档仅新增日期，其余原文字节保持不变。
- 归档检查同时核对文件哈希与可信 Git 基线，旧封印不能改删。默认基线为 HEAD，CI 可用 BW_ARCHIVE_BASE_REF 指定变更前提交；无 Git 或尚无提交时仅核对当前文件与清单。
- 方法按当前作用表达：部分替代明确剩余有效范围，仍有独立理由的旧篇保持活跃；完整吸收承接验证义务和具名覆盖缺口。现行事实与产物同改。
- 发布检查实际调用 [bw.py](../../../skills/bw/scripts/bw.py) 校验本仓记录。它不安装宿主钩子或 CI，也不能阻止模型绕过工具直接写文件。

### DSH 一手依据与适配边界

核对版本为官方仓库提交 `e8f7b93a344964de3dca1ace9e72b6e4d6de87cb`，本地为浅克隆；以下依据来自该快照，未据此推断整个演进过程或运行 DSH 产品测试。

| 官方产物 | 可核实的管理行为 | ByWork 的对应位置 |
|---|---|---|
| [Schedule rule storage](https://github.com/deepseek-ai/deepseek-harness/blob/e8f7b93a344964de3dca1ace9e72b6e4d6de87cb/.agents/notes/implemented/architecture/2026-10-21-schedule-rule-storage.md) 与其引用的 standalone schedules | 新记录明确替代存储与接口、保留目标与执行等决定；两篇保持活跃并互链 | [旧记录治理](../../../skills/bw/references/archiving.md) 的部分替代判据 |
| [Desktop updater qualification](https://github.com/deepseek-ai/deepseek-harness/blob/e8f7b93a344964de3dca1ace9e72b6e4d6de87cb/.agents/notes/implemented/testing/2026-09-10-desktop-local-updater-qualification.md) | 分别说明真实入口、替身边界、失败证据与未覆盖范围；局部通过不替代其他验收 | [证明](../../../skills/bw/references/prove.md)、[写作自检](../../../skills/bw/references/writing.md) 与证据保留 |
| [Archive verifier](https://github.com/deepseek-ai/deepseek-harness/blob/e8f7b93a344964de3dca1ace9e72b6e4d6de87cb/scripts/verify-archived-agent-notes.ts) 与 [CI](https://github.com/deepseek-ai/deepseek-harness/blob/e8f7b93a344964de3dca1ace9e72b6e4d6de87cb/.github/workflows/ci.yml) | 除当前哈希外还与可信提交清单比较；PR 检查使用 base.sha | bw.py 基线检查；[发布检查](../../../tools/release-check.sh) 校验本仓，用户项目自行接入既有交付检查 |
| [Persisted goal](https://github.com/deepseek-ai/deepseek-harness/blob/e8f7b93a344964de3dca1ace9e72b6e4d6de87cb/packages/goal/README.zh.md) | 目标由宿主持久化，恢复后可继续；自动续行是单独能力 | proposed 的文件检查点是跨宿主适配，读取和推进仍依赖模型，不能视为运行时等价 |

### 验收效果的尺度

后续真实项目观察四件事：接续能否还原当前工作和缺口；产物变化是否同步更新相关事实；新旧决定能否明确有效范围且不漏独特约束；完成声明能否回到真实证据和未覆盖边界。按 [评测判定边界](../../implemented/testing/2026-11-18-evaluation-findings.md) 保留原始动作与结果，结构测试只回答结构和命令行为。

## 备选方案

- **完整照搬 wnld 文本**：方便逐项比对，但文本相似不能证明效果，且会带入领域样例、无依据比例和不适用机制；保留有效判据，按本项目契约表达。
- **仅修文案**：改动最少，但无法阻止已复现的记录丢失和错误完成；脚本问题需行为回归。
- **只比较当前清单与正文**：不依赖 Git，能发现单边改动，但正文和哈希一起改便会通过；有提交基线时增加旧封印比较，无基线时明确保护范围。

## 验证

| 行为路径 | 计划证明 | 实际证据 | 范围覆盖 | 缺口 | 结果 |
|---|---|---|---|---|---|
| 完成判据 | 空白、非法值、缺证据均拒绝且保留源文件；有效记录通过 | 脚本测试 61/61：上述反例非零退出且文件快照不变；有效表格与模板通过 | bw.py、模板、脚本测试 | 无 | 通过 |
| 流转不丢记录 | 错生命周期、同名目标、坏清单、无效替代目标均拒绝 | complete/reject/archive 冲突、普通文件、源软链、坏清单、无效替代目标用例通过；原文件内容保留 | 三个流转命令的已列输入边界 | 无 | 通过 |
| 归档封印 | 对已提交基线拒绝改旧封印，允许新增，失败不写清单 | 临时 Git 仓库实测：正文与哈希一起改、同时删档与封印、不可读显式基线均失败；新增封印通过；CRLF 正文除新增日期字节不变 | archive/check、Git 基线、当前清单 | 无 | 通过 |
| 规则与产物一致 | 核对 DSH 真实样本，修复现行文档，运行发布检查 | release-check --no-deploy 通过：checker 24/24 反例、脚本 61/61、runner 14/14；实际工作区 proposed=1, implemented=3, archived=191 通过 | references、README、现行决定、发布检查 | 无 | 通过 |

## 收益和代价

结构校验不判断证据真假、理由完整性或模型是否调用脚本；基线需由调用方信任。这里验收的是列明的可复现缺陷和文档一致性，不包含长期效果等价。宿主自动续行、全部 I/O 中断的事务恢复与多进程同时修改未在本轮验证。命令将删除源文件放在目标及必要元数据写入之后，写入中断仍可能留下需人工核对的双份记录。

长期防漂移和防腐化仍需真实项目后续观察。`SKILL.md` 与 references 合计从 495 行减至 392 行，仅是文本规模变化，不作为管理效果证据。
