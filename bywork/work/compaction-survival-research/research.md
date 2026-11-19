# 跨压缩规则保活：问题归类、成熟解法对照与推荐方向

结论先行：**这不是提示词写得不好的问题，是契约放错了层的问题。** 同一场会话、同一个模型、同一次压缩，放在宿主 system 层的 Ponytail 指令 100% 存活，放在消息历史里的 bw 契约 0% 存活。四家成熟工作流（superpowers、ospec、claude-mem、GSD Core）面对同一问题时，无一例外把保活交给宿主或工具，没有一家靠「提醒模型记得」。

## 一、问题的准确归类

### 1.1 自然实验：层决定存活，措辞不决定

两场复盘会话（均加载 bw 1.0.3，契约文本逐字在案）：

| 会话 | 压缩前收尾总结 | 压缩后收尾总结 | 同场次 Ponytail 说明 |
|---|---|---|---|
| `ses_e0d5fb568ffej2YAq72xhlu6yf`（byspace） | 4/4 | 0/3 | 3/3 |
| `ses_e0d28f98ffferhFEZuCS0Rp7Rn`（AGCopilot） | 首次回复前即被压缩 | 0/7 | 7/7 |

分界线精确到秒：byspace 会话 `seq516` 刚读完 `templates/work.md`，`seq686` 把 `SKILL.md` 与该模板一并折叠成一句 "Loaded `bw` skill"，**10 秒后** `seq696` 凭记忆手写 `index.md`——证明表 6 列变 5 列、结果值写 `pending`、整节漏 `## 完成核对`。此后 `seq3537` 手写出 `status: done` 与早已废弃的 v1 ByIssue 字段。两场会话全程 `check_work.py` 调用 0 次。

Ponytail 与 bw 的差别只有一个：Ponytail 由宿主注入 system prompt，bw 由 `skill` 工具作为普通工具返回值进入消息历史。**措辞、模板、可视化的努力（1.0.3 刚做完）全部作用在会被驱逐的那一层。**

本会话（ByWork 复盘会话）自身是第三个样本：经历十余次压缩后，项目根 `AGENTS.md` 的指令仍逐字在 system 层，而开头加载的 bw `SKILL.md` 正文早已被折叠。

### 1.2 这是什么问题的变体

**控制平面状态被误放进数据平面**（instruction eviction / workflow amnesia under context compaction）。

- 数据平面：对话历史，会被摘要、截断、驱逐，天然有损。
- 控制平面：工作流契约、状态机合法值、收口动作、输出格式，要求全程无损。

GSD Core 的 `docs/explanation/context-engineering.md` 对同一现象的命名是 **context rot**，并明确定性：

> The model does not fail loudly. It keeps answering. But the quality of its answers quietly degrades. Early instructions get pushed towards the edge of what it can attend to.
>
> None of this is a model bug. It is a fundamental property of how transformer attention works over long sequences.

其症状清单（contradicting earlier decisions / code style drifts / plans ignore requirements buried in history / hallucinates file names it had correct twenty messages ago）与我们的观测逐条对应。

### 1.3 我们的失败其实是两个，需要两种药

| 失败 | 表现 | 性质 |
|---|---|---|
| A. 契约文本被驱逐 | 收尾总结消失、状态值域写错、模板列数错、忘记有 `--close` | 控制平面存活问题 |
| B. 收口动作没有机械前置 | 手写 `status: done` 绕过 `check_work.py --close` | 完成门可绕出问题 |

1.0.2 的 `--close` 只解决了 B 的**一半**：提供了机械入口，但没有让绕过它变得不可能。A 完全没解决。两者都不该靠加提示词解决。

## 二、成熟工作流的一手取证

### 2.1 superpowers（obra/superpowers）——直接命中

`hooks/hooks.json` 全文只有一个钩子：

```json
SessionStart, matcher: "startup|clear|compact" → run-hook.cmd session-start, async: false
```

`hooks/session-start` 读 `skills/using-superpowers/SKILL.md` **全文**，JSON 转义后通过 `hookSpecificOutput.additionalContext` 注入，包在 `<EXTREMELY_IMPORTANT>` 里，并注明「其余技能仍用 Skill 工具按需加载」。

即：**入口契约在每次压缩后由宿主重新注入，渐进式披露保持不变**。这正是我们缺的那一步，而且它只重注入口层，不重注全部细节。

### 2.2 ospec（clawplays/ospec，显式支持 OpenCode）——同构，且写明了成本取舍

`ospec session hook --target claude --apply` 幂等写入 `.claude/settings.json`（可逆）。三条作用：

1. 工具级 announce 每次子代理派发与每条 ospec 命令；
2. required decision 未决时**硬阻断**子代理派发；
3. 原文：inject the static Announce-Before-Act / Brainstorm-First contract **only on startup, clear, or compact**, while prompt submission stays silent unless a required decision is pending。

第 3 条与 superpowers 完全同构，并明确了「每轮静默、只在启动/清空/压缩注入」的成本设计。另有 `.ospec/session-brief.json`（active changes、cache fingerprint、**next safe command**）供新进入者定向；状态迁移全部走 CLI，强制归档需 `--force-archive --confirm-force-archive <exact-name> --reason` 且产物标记 forced/incomplete。

### 2.3 claude-mem（thedotmack/claude-mem）——记忆外置 + 压缩后重注入

`SessionStart` matcher `startup|clear|compact` → `claude-mem hook claude-code context`（同步注入历史记忆）；`PostToolUse *` → observation（异步落库）；`Stop` → summarize。

同一类解法，注入内容换成历史观察而非技能正文。共同点：**权威在进程/DB，上下文只是缓存**。

### 2.4 GSD Core（open-gsd/gsd-core，旧仓 gsd-build/get-shit-done 已归档迁移）——结构性解法 + 工具守卫

三层，值得分别看：

1. **fresh-context 子代理**：「most of the work does not need to happen in the main context at all」。orchestrator 主会话从不碰源码，只 spawn / 收结果 / 更新共享状态 / 路由，重活交给全新 200k 上下文的子代理。自称「not a workaround for context rot. It is a structural solution.」
2. **`.planning/STATE.md` 为唯一脊柱**：「When any workflow starts, it reads STATE.md to orient itself. When any workflow finishes a meaningful step, it writes back」「Agents do not rely on memory; they rely on the file.」子代理隔离反过来强制了落盘纪律。
3. **工具级守卫**（`hooks/hooks.json`，next 分支）：`PreToolUse Write|Edit` → `gsd-prompt-guard.js` + `gsd-read-guard.js`；`Write|Edit|MultiEdit` → worktree-path-guard；`Agent|Task` → agent-isolation-guard；`PostToolUse`/`Stop`/`SubagentStop`/`PreCompact` → `gsd-context-monitor.js`。完成与写入靠守卫，不靠提示词。

诚实之处：编排层自身也会填满，1.4.0 起用生命周期 hook 观测 headroom，但明说「hooks give GSD a signal, not a guarantee」「headroom tracking is a heuristic」，只 warn/steer。另有 opt-in 的 `gsd-session-state.sh`，SessionStart 注入 `## Project State Reminder` + `head -20 .planning/STATE.md`。

### 2.5 agentic-os（KbWen/agentic-os）——把能与不能划得最清楚

定位金句：

> A rules file *asks* your agent to behave. Agentic OS **checks that it did**.
>
> A rules file — Cursor Rules, a plain AGENTS.md — is a prompt the agent can ignore.

它的分层表里有一行是对我们的直接警告：

| 失败模式 | 机械手段 | 强度 |
|---|---|---|
| 测试记录陈旧或失败 | `record_test_run.py` 记 exit code + 代码指纹，`/ship` 校验，代码变了或上次失败即 fail | 硬 |
| **agent 忽略工作流或技能清单** | **Nothing machine-side** | **Advisory, the same as a rules file** |

并自认边界：「The validator checks the record the agent keeps, so it catches a phase missing from that record, not a faked record or a task that never opened one.」

它的 `⚡ ACX` 每条回复标记与 bw 收尾总结同构，README 明说「It is self-reported, not proof — the persistent check is the validator warning when a work log lacks it.」

**这条证据的价值在于：一个成熟项目公开承认「模型不理会工作流」这件事在纯文件+CLI 架构下无解。我们观测到的正是这一格。**

### 2.6 归纳

| 工作流 | 契约保活靠什么 | 收口靠什么 | 是否靠模型记得 |
|---|---|---|---|
| superpowers | 宿主 SessionStart(compact) 重注入口全文 | verification-before-completion Iron Law | 否（保活）|
| ospec | 宿主 startup/clear/compact 重注静态契约 | CLI 状态机 + 硬阻断派发 | 否 |
| claude-mem | 宿主 compact 重注外置记忆 | 进程/DB 权威 | 否 |
| GSD Core | 主上下文不积累 + STATE.md 落盘 | PreToolUse 工具守卫 | 否 |
| agentic-os | AGENTS.md（自认 advisory） | validator + 真 CI + 指纹 | 部分（自认拦不住）|
| **bw 现状** | **消息历史里的 skill 返回值** | `--close`（可手写绕过） | **是** |

## 三、宿主提供的机制（OpenCode V2，逐字核实）

### 3.1 指令层：压缩免疫，且 bw 现在完全没用

`opencode.ai/docs/instructions` 的组装顺序：

```
1. Agent or provider system prompt
2. Code Mode tool guidance
3. MCP server, reference, and skill guidance
4. Global and project AGENTS.md files, then configured instructions
5. Built-in date and environment context
6. Session-specific instruction entries supplied through the API
```

这些是 **combined 进 system**，不是消息历史。compaction 页原文：*After compaction, the current versions of your instruction files become the session's baseline.*

**关键精度**：全局与向上发现的 `AGENTS.md`、config `instructions: []` 在 system 层，压缩免疫；**嵌套 `AGENTS.md` 是按路径懒加载进历史的**——「deduplicated while their instruction entry remains in model-visible history. If compaction or a revert removes that entry, a later read can load the file again」。所以只有前者可用。

config `instructions` 支持相对路径/glob/`~/`/绝对路径/http(s)，本地文件变更像 AGENTS.md 一样热更新。

### 3.2 每请求注入：`context` hook

`opencode.ai/docs/build/plugins/server`：

```ts
await ctx.session.hook("context", (event) => {
  event.system.push({ type: "text", text: "…" })
  delete event.tools.write          // 可直接摘掉能力
})
```

- 「`context` runs for the agent loop, **including tool-driven continuations**」——每次模型请求都跑，不只是每轮用户输入。
- 「Changes affect only the outgoing model call, not persisted history or configuration.」——不污染历史，不占压缩预算。
- `delete event.tools.write` 是**已文档化的硬能力**：按请求摘掉工具。GSD 的 write guard 在 OpenCode 有等价物。

### 3.3 工具守卫：`ctx.tool.hook`

```ts
await ctx.tool.hook("execute.before", (event) => { if (event.tool === "read") … })
await ctx.tool.hook("execute.after",  (event) => { … })
```

文档表述为 inspect or replace tool input / results。**能否直接否决一次调用，文档未写明**，列入穿刺清单。

### 3.4 其它相关

- `ctx.session.instructions.entry.put({sessionID, key, value})` → 渲染 `<context key="…">` 进 session instructions，下个 step 边界通告，不排队消息轮次（Experimental）。
- `ctx.session.hook("compaction", …)`：`event.messages` 是被总结的 transcript，设 `event.result = {summary}` 可自接管。
- `ctx.skill.transform(editor => editor.update(id, s => s.autoinvoke = true))` + `ctx.skill.reload()`。
- `ctx.storage` 持久 JSON、`ctx.event.subscribe` 事件流。
- **OpenCode skill frontmatter 没有 hooks 字段**（只有 name/description/`metadata.opencode/autoinvoke`/disable-model-invocation）。Claude Code 有——技能 frontmatter 声明的 hooks 在技能被调用时注册并在此后整个会话生效。**这是两个宿主的能力差，也是 bw 在 OpenCode 上必须走 plugin 或 config 的原因。**

### 3.5 Claude Code 侧（若将来跨宿主）

`SessionStart` matcher `startup|resume|clear|compact|fork`；`PreCompact`/`PostCompact`；`InstructionsLoaded`（matcher 含 `compact`）；`UserPromptSubmit` 每轮可注入 additionalContext。四家工作流用的都是这一组。

## 四、方案空间与对照评估

按「谁来保证」分层，而不是按「改哪个文件」：

| 方向 | 谁保证 | 治 A | 治 B | 代价 | 已有证据 |
|---|---|---|---|---|---|
| ① 常驻契约进宿主指令层 | 宿主 | ✅ | ❌ | 一段常驻 system 文本 | Ponytail 同层，本会话实测存活 |
| ② bw 专用 plugin：会话级激活 + 每请求注入 | 宿主插件 | ✅ | 可选 | 引入插件分发与安装 | superpowers/ospec 同构，OpenCode 有等价 API |
| ③ 工具守卫拦手写状态迁移 | 工具 | ❌ | ✅ | 同上，且否决能力待验 | GSD PreToolUse guard |
| ④ 主会话只路由，重活派 fresh 子代理 | 结构 | ✅（不触发压缩） | ✅（落盘强制） | 改变产品形态 | GSD 结构性解法 |
| ⑤ 脚本输出携带契约 | 脚本 | 条件性 | ❌ | 极小 | **不成立，见下** |
| ⑥ 让压缩摘要保留契约原文 | 模型 | ❌ | ❌ | 小 | **本仓已实测证伪** |
| ⑦ 加提示词提醒「压缩后要重读」 | 模型 | ❌ | ❌ | 小 | **本仓已七轮证伪** |

### 明确排除的三条，及理由

- **⑦**：`bywork/memory/project.md:62` 记录「压缩后第一项工具调用必须是 read」硬门经七轮提示堆叠（固定口令、入口硬门、持久化 cue）仍被忽略，已改为结果判据。用户本轮亦明确否决往提示词塞垃圾。
- **⑥**：`bywork/work/v2-delivery/final-evaluation-report.md:42-43` 记载，候选二十一第二轮证明**恢复指令逐字保留在压缩摘要中，模型仍不遵守**。这条路的失败不是「摘要没写全」，是「写在摘要里也没用」——因为摘要仍在数据平面。
- **⑤**：任何「跑脚本时把契约带回来」的设计，前提是脚本被调用。而两场会话压缩后 `check_work.py` 调用率为 **0**——触发调用的那句话本身就在被驱逐的文本里。**⑤ 只能作为 ①/②/③ 的补充，不能单独成立。**

同理，`bywork/work/large-repo-compaction/review.md:114` 提醒「错误不能简单归因于压缩」，压缩前已有同类错误。所以本次主张的是「层」这个变量，由 §1.1 的同场次对照支撑，而不是把一切退化都算在压缩头上。

## 五、推荐方向

### 方向一（先做，零代码）：把 bw 常驻契约搬进宿主指令层

**做什么**：抽出一份极小的常驻契约（行动路由 + 收尾总结可视模板 + work 状态值域 + 「收口跑 `check_work.py --close`」一行），放进全局 `~/.config/opencode/AGENTS.md` 或 config `instructions: ["~/.config/opencode/skills/bw/CONTRACT.md"]`。细节仍在 references，按需读，渐进式披露不变。

**为什么先做它**：它零代码、可立刻证伪或证实「层」这个假设，而且**同一层已有生效先例**——Ponytail 就是这么进来的，两场会话 10/10 存活。如果连这一层都保不住收尾总结，那说明问题不在层，后面所有方案都要重估。这是最便宜的关键实验。

**代价与边界**：全局生效，没用 bw 的会话也会带上这段文本。缓解是把契约压到最小并首句声明适用条件；但「判断是否适用」又回到模型自觉——不过此处误判成本极低（多几十行 system），与「忘记整个工作流」不是一个量级。这个污染问题最终由方向二消除。

**验收**：真实长会话跑到自然压缩，检查压缩后回复是否仍有三段收尾总结、work 是否仍走 `--close`。不通过就停下重估，不加码提示词。

### 方向二（并行穿刺，不先写实现）：bw 专用 plugin

**做什么**：一个小 plugin，`ctx.tool.hook("execute.before")` 捕获本会话是否加载过 bw（`ctx.storage` 按 sessionID 记），此后仅在激活会话的 `context` hook 里 `event.system.push` 常驻契约。等价 superpowers/ospec 的压缩后重注入，但比它们更省——**只对用了 bw 的会话生效，不污染其它会话**，且每次请求都在，不必等压缩事件。

**必须先验的三件事**（任一不成立则方向二作废，退回方向一）：

1. plugin 能否可靠观测到 `skill` 工具调用并拿到 skill id；
2. `context` hook 注入的文本能否在真实压缩后仍出现在出站请求里；
3. `ctx.tool.hook("execute.before")` 能否**否决**一次 write/edit（文档只写 inspect/replace）。能，则顺带治 B：目标匹配 `bywork/work/*/index.md` 且写入 `status: complete` 时拒绝并指向 `--close`；不能，则 B 仍只能靠 ① 的常驻提醒 + `--close` 的便利性。

**代价**：bw 目前是纯 skill（`npx skills add` 即装）。引入 plugin 会改变分发与安装形态，这是产品决策不是技术决策，需要用户拍板。

### 方向三（记录，暂不做）：GSD 式结构性解法

主会话只路由、重活派 fresh-context 子代理、work 文件作唯一状态脊柱。它从根上让压缩不发生，但把 bw 从轻量工作流变成编排框架，与现有定位和用户实际用法（自己在一个会话里推进）冲突。留作长期方向，等方向一/二的数据出来再谈。

### 不推荐现在做的

把状态枚举、收尾总结模板复制进 `templates/work.md`，或加 `--work` 生成脚本。前者是同一契约的第二套表述（违反单一归属），后者治的是「模板写错」这个症状而非「契约被驱逐」这个病因——契约回来后模板自然会被读到。

## 六、给用户的判断点

1. 是否认可「层」这个归因（而非措辞）——§1.1 的同场次对照是主要依据。
2. 是否接受方向一的全局污染代价，换取零代码的关键实验。
3. 是否接受 bw 引入 plugin 分发（方向二），这是产品形态决策。

## 七、用户收窄方向后的设计取证（2026-11-19 追加）

用户否决全局方案，改为「项目级 `AGENTS.md` + 某个模型一定会执行的脚本检查并补写 + 内容尽可能精简」。按这个方向取证，得到三个改变方案形状的事实。

### 7.1 项目根 `AGENTS.md` 确实在指令层，且本会话就是活证据

`opencode.ai/docs/instructions` 逐字：「OpenCode loads the global file followed by every `AGENTS.md` from the current workspace directory toward the home directory」——**当前工作区目录本身在向上发现链里**，不是懒加载的嵌套文件。

活证据：本复盘会话（cwd `/Users/zijie/workspace/ByWork`）的 system prompt 里逐字带着 `Instructions from: /Users/zijie/workspace/ByWork/AGENTS.md` 及全文，而本会话已经历 **8 次压缩**（b5–b14），该段一字未丢。这是「项目级指令层压缩免疫」的直接实测，不再是文档推断。

→ 方向一的机制成立，且**不需要全局文件**，用户的项目级收窄可行。

### 7.2 但「模型一定会执行的脚本」这个前提在真实样本里不成立

两份导出里 `check_work.py` / `init_bywork.py` 的**实际执行次数均为 0**：AGCopilot 4 处命中、byspace 6 处命中，全部是 `SKILL.md` / `change.md` / `prove.md` / `onboard.md` 的正文引用，没有一次 shell 调用。

即：**压缩后模型不但不遵守契约，也不调用任何 bw 脚本**。把安装动作挂在「模型一定会跑的脚本」上，等于把新机制挂在一个已被证伪的前提上——与排除 ⑤ 的理由同源。

可行的替代触发点，按可靠性排序：

1. **`skill` 工具加载本身**：模型调用 bw 时宿主必然读取 `SKILL.md`。把「首次加载 bw 后运行一次 `init_bywork.py`」写在 `SKILL.md` 开头，触发点在**压缩之前**（加载即触发），不依赖压缩后的自觉。缺点：仍是一次提示词依赖，但发生在契约尚未被驱逐的时刻，与压缩后提醒不同性质。
2. **宿主 plugin**（方向二）：`skill` 调用被 plugin 观测到即执行，完全不经模型。最可靠，但引入分发形态变化。
3. **用户手动**：接入时人跑一次。最可靠且零机制，但要求用户动作，与 project.md:56 现有边界冲突。

**结论：脚本自动补写这件事本身可行且简单；难点只在「谁来触发第一次」。这是本方案唯一未决的机制问题，需要用户拍板。**

### 7.3 两个真实项目的落地形状不同

| 项目 | 现状 | 落地动作 |
|---|---|---|
| `/Users/zijie/workspace/AGCopilot` | **没有 `AGENTS.md`，也没有 `CLAUDE.md`** | 从零创建。`.gitignore:86-90` 只忽略 `.agents/*` 与 `.claude/*`，`AGENTS.md` 不被忽略，可提交 |
| `/Users/zijie/workspace/byspace` | `AGENTS.md` 存在，175 行 20824 字节，`## Repository map` 开头 | 幂等追加一段；`scripts/repo-config.test.mjs:276-300` 的守卫只做**包含性**断言（每个根目录与 `docs/*.md` 必须被提到），追加内容不会破坏它 |

注意 `AGENTS.md` 存在时 `CLAUDE.md` 不会被读（同目录 `AGENTS.md` 优先），所以目标文件名固定为 `AGENTS.md` 即可，不需要双写。

### 7.4 最小内容集的判据

判据不是「重要就放进去」，而是：**这条规则失效时，模型有没有别的机会重新拿到它？**

- **必须进指令层**：每次回复都要产出、且没有任何工具调用会把原文带回来的东西。收尾总结模板是唯一符合的——它是纯输出格式，没有对应的脚本或文件读取动作，压缩后 100% 消失且无法自愈。
- **应该进指令层**：一句话就能把模型引回自愈路径的**指针**。例如「继续或压缩接续时先读 `bywork/work/` 的检查点」——读到 `index.md` 就重新拿到状态字段与证明表结构；「收口用 `check_work.py --close`」——脚本自己会校验值域与缺口，模型不需要记住枚举。
- **不必进**：状态枚举、frontmatter 六字段、证明表列名、四种行动表、改变四步、底线五条、目录树。它们要么在 `index.md` 里现成可读，要么在脚本校验里机械把关，要么在按需 reference 里。**抄进指令层就是第二套表述**，违反单一归属，且正是用户否决的「往提示词塞垃圾」。

按此判据，候选常驻内容约 5–7 行：适用声明一句 + 收尾总结可视模板 + 检查点指针一句 + 收口命令一句。四行动表、枚举、模板结构一律不进。

**但这仍是同一契约的第二处表述**（收尾总结模板已在 `SKILL.md:90-104`）。这是本方案必须正面承认的代价：要么接受「指令层副本 + 单一生成源」——即 `SKILL.md` 与 `AGENTS.md` 段由同一份源生成、脚本校验两处一致；要么放弃模板进指令层、只放指针，接受格式仍可能漂移。**推荐前者，并用脚本把「两处一致」变成机械校验**，否则漂移只是时间问题。

### 7.5 与既有边界的冲突（必须显式处理，不能绕过）

`bywork/memory/project.md:56` 现文：「接入只运行初始化脚本，不要求用户为 bw 修改 `AGENTS.md`。即使用户项目的 `AGENTS.md` 没有提到 bw，手动调用技能也必须完整生效；全部工作流规则都在技能包内。」

用户新方向与这条直接冲突。需要更新该条并写明理由：**手动调用技能仍必须完整生效**（这半句保留，是不变量）；变的是「不碰 `AGENTS.md`」——因为实测证明纯技能包内的契约在压缩后必然丢失，宿主指令层是唯一压缩免疫的位置。这是有证据支撑的边界修订，不是偷偷绕过。

## 8. 纯 skill 有没有压缩免疫的通道？有，而且我们一直没用

用户问：纯 skill 是不是永远没办法，知名工作流是不是都有安装器。两个问题分别查证，答案都出人意料。

### 8.1 安装器确实是这些方案的共同成本，不是我们偷懒

| 对象 | 安装动作 | 逐宿主适配 |
|---|---|---|
| superpowers | 各宿主 plugin marketplace（`/plugin install`、`agy plugin install`、`devin plugins install`、`droid plugin install`） | README:54 明说「Installation differs by harness. If you use more than one, install Superpowers separately for each one.」 |
| spec-kit | `uv tool install specify-cli` + `specify init --integration copilot` | init 带 `--integration` 逐客户端参数 |
| openspec | `install.sh` / `npm i -g` + `openspec init` | 子代理机制按宿主分叉（Claude Task / Codex spawn_agent / Gemini @generalist / OpenCode @mention） |
| agentic-os | `installers/deploy_brain.sh [--dry-run] <project>` | 部署器 + git hook + CI job |

四个都有安装/部署动作。**用户不想做安装器，指向的正是这套方案共同的复杂成本来源。**

### 8.2 但 skill 有一条被我们忽略的压缩免疫通道：description

`opencode.ai/docs/skills`「Loading」节逐字：

> At each model step, OpenCode lists permitted skills that have a description and do not set `opencode/autoinvoke` to `false`. The list includes only the ID, name, and description, not the full Markdown body.

拆开看是两件事：

- **正文**：`skill` 工具加载时「Adds the Markdown body … to the conversation」→ 进消息历史 → **可被压缩**。这就是 §1 观测到的失效。
- **ID + name + description**：**每个 model step 重新列出**，属 system prompt 第 3 层 skill guidance → 不进消息历史 → **压缩无法驱逐**。

活证据：本会话已压缩 14 次（b5–b17），system prompt 的 `available_skills` 里 bw 的 description 仍逐字完整存在，与 §7.1 的 `AGENTS.md` 同级别免疫。

**即：我们一直把 description 当「什么时候用我」的触发词表，而它其实是一条每步都在的指令层通道。**

### 8.3 superpowers 在没有 hook 的宿主上，用的正是这条通道

README:92-94（Antigravity 段）逐字：

> Antigravity lists each installed skill's description, and the description of the `using-superpowers` skill prompts the model to load that skill at the start of a conversation.

它的 `skills/using-superpowers/SKILL.md` frontmatter 逐字（154 字符）：

```
description: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
```

注意这条 description 的后半句不是「何时用」，而是**行为要求**：任何回复（含澄清提问）之前必须先调用技能。

**关键区别：superpowers 没有把技能正文塞进 description，只放了一句「去加载我」。** hook（`SessionStart` matcher `startup|clear|compact`）只是部分宿主的加强件；description 才是同一份技能包在所有宿主上的通用底座。

### 8.4 这条通道解决的是「再入」，不是「存放」——因此不产生第二套表述

§7.4 的判据在这里得到更好的答案。之前认为收尾总结模板必须抄进指令层，代价是同一契约两处表述。但 superpowers 的做法绕开了这个代价：

```
description（免疫层，每步重列）
    → 促使模型重新调用 skill / 重读 SKILL.md
        → 正文回到历史，模板、值域、--close 全部恢复
```

指令层只放**指针**，内容仍由技能包单一归属。这是一个**自愈回路**，不是静态副本。§7.4 里「必须进指令层：收尾总结模板」这一条据此可以降级——模板不必抄，只要模型能被引回来重读。

bw 现状对照：`skills/bw/SKILL.md:3-5` 的 description **301 字符 / 695 字节**，是 superpowers 那条的 2.0 倍，但内容 100% 是「什么时候用」+ 一长串触发词（聊聊、先理清、拷问我、快改、review、记一下坑…），**零行为契约、零再入指针**。这条已经在指令层的通道，当前完全没被用来承载契约。

### 8.5 与被否方案的区别（必须说清楚，否则是重提旧案）

`bywork/memory/project.md:62` 记录「压缩后第一项工具调用必须 read」硬门经七轮提示堆叠仍被忽略，已废。表面上 8.4 也是「让模型压缩后去读」，但**承载层不同**：

- 被否的七轮：指令写在 `SKILL.md` 正文或压缩摘要里 → **指令本身和契约一起被驱逐** → 失败是必然的，测的是数据平面。
- 8.4：指针写在 description → **每个 model step 重新列出，永不消失** → 测的是指令层。

同一个动作、不同的层。这不是重提旧案，但**也不能据此宣称一定成功**——它仍是提示词依赖，agentic-os 公开承认「agent 忽略工作流 → Nothing machine-side → Advisory」正是这一格。区别在于这次假设可证伪且成本极低。

### 8.6 三条纯 skill / 低适配路线的对照

| | A. description 再入指针 | B. onboard 技能 + 脚本写项目 AGENTS.md | C. plugin / 适配器 |
|---|---|---|---|
| 安装器 | 无 | 无（技能自带，用户每项目调一次） | 有，且逐宿主 |
| 逐客户端适配 | 无（description 是各家共有字段） | 无（`AGENTS.md` 是跨厂商开放标准，见下） | 有 |
| 免疫层承载 | 指针（约 1 句） | 完整模板（5–7 行） | 完整正文，每请求注入 |
| 第二套表述 | **无**（内容仍单一归属于技能包） | 有，须单一源生成 + 脚本校验一致 | 无 |
| 用户动作 | 零 | 每项目一次 | 每宿主一次 |
| 保证强度 | 弱（仍靠模型愿意重读） | 中（模板常驻，但状态机仍靠自觉） | 强（不经模型） |
| 边界冲突 | 无 | 与 `project.md:56`「接入不要求改 AGENTS.md」冲突，须显式修订 | 改变分发形态（现为纯 skill，`npx skills add` 即装） |

补一条事实澄清：**`AGENTS.md` 不是逐客户端适配**。它是 Linux Foundation / Agentic AI Foundation 托管的开放标准（agents.md），Codex、opencode、Cursor、Copilot coding agent、Gemini CLI、Windsurf、Zed、Aider、goose、Devin 等均支持，无必填字段、纯 Markdown。真正需要逐家适配的是 hooks，不是 `AGENTS.md`。所以 B 的「通用性」并不比 A 差，差别在用户动作与副本代价。

### 8.7 推荐与验收

**先做 A，它最便宜且能证伪核心假设。** 在 description 里加一句再入契约（保留触发词，不动正文），然后跑一次真实长会话到自然压缩：

- 通过判据：压缩后模型重新加载 bw / 重读检查点，且回复恢复三段收尾总结、收口走 `--close`。
- 不通过就停，不加码提示词——那正是七轮堆叠的老路。转而评估 B。

**B 作为 A 失败后的下一档**，不是并行做。C 只在 A、B 都不成立时才值得，因为它要用户接受分发形态变化。

诚实标注 A 的三个未验点：①模型是否真的服从 description 里的行为句（superpowers 有先例但未在我们场景实测）；②description 变长是否影响触发准确率（当前 301 字符已是 superpowers 的 2 倍，加契约句需同时考虑精简触发词）；③其它宿主对 description 长度上限不一（OpenCode V2 明确不设上限，但我们已有 `skills/bw/agents/openai.yaml` 这一处 Codex 适配，说明跨宿主并非完全零差异）。

## 九、Matt 与 OpenSpec 的控偏机制（本地一手复核）

先纠正取证路径：这两家早就拉在 `/Users/zijie/workspace/reference/ai-workflows/`（连同 bmad、cursor-plugins、gstack、ralph、spec-kit、superpowers、write-notes-like-deepseek 共 8 仓），matt-skills 本地 HEAD=5863806 与线上一致。本节全部用本地副本，不走网络。

### 9.1 Matt：拆分不是人工，跑偏靠上下文结构

用户问「靠人工拆 issue 吗」——不是。`matt-skills/skills/engineering/to-tickets/SKILL.md:33` 由模型拆 tracer-bullet 垂直切片，判据是「Each slice is sized to fit in a single fresh context window」，每片穿透 schema/API/UI/tests 且可独立演示。人只参与第 4 步 `### 4. Quiz the user`（:42-56）确认颗粒度、阻塞边与合并拆分。宽重构走 expand–contract 分批。

真正的控偏是**上下文结构**，不是提示词：

- `implement-spec/SKILL.md:15`「Start every subagent with a fresh context window.」:29 每个 ticket 一个 fresh implementer 子代理，各自 worktree/branch。
- `implement-spec/SKILL.md:17`「Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.」
- `ask-matt/SKILL.md:38` grilling→to-spec→to-tickets 三步必须在**一个不被打断的 context window** 内完成，`/to-tickets` 之前不许 compact/clear；之后每个 `/implement` 从 ticket 全新开始。:40 smart zone ≈150k tokens，接近就在最近 phase boundary compact。
- `ask-matt/PHASE-BOUNDARIES.md:5`「The **phase boundary** … is the only place this decision belongs … Compacting mid-phase makes the agent lose the thread.」五选项有序树：Continue → `/clear` → `/handoff` → Subagent → `/compact`（兜底而非首选）。核心概念 primary vs secondary source：除 Continue 外每个动作都把一手变二手，失败模式是「a fresh session that is confidently wrong about a decision the summary flattened」。

**它不是全自动，而且是有意的。** 本地 grep `disable-model-invocation: true` 命中 16 个技能，主流程全在其中（ask-matt、grill-with-docs、grill-me、implement、implement-spec、to-spec、to-tickets、triage、wayfinder、retro、handoff、teach、to-questionnaire、wait-what、setup、improve-codebase-architecture）——**模型不能自己跳段，人按顺序点**。README 一手立场：「Approaches like GSD, BMAD, and Spec-Kit try to help by owning the process. But while doing so, they take away your control and make bugs in the process hard to resolve.」

### 9.2 OpenSpec：状态在 CLI 里，不在对话里

`openspec/skills/` 12 个技能共 2875 行，**全部 model-invoked**（`disable-model-invocation` 零命中），description 带 `openspec xxx`/`opsx xxx` 显式触发词——所以用户感受到的「手动三段」其实是人喊命令，模型自己也能触发。

机械性集中在 `openspec-continue-change/SKILL.md`（137 行）：

- :49 `openspec status --change "<name>" --json` 返回每个 artifact 的 done/skipped/ready/blocked 与 isPlanningComplete；**模型不自己决定下一步**，取第一个 ready 的 artifact，再 `openspec instructions <artifact-id> --change --json` 取 context/rules/template/instruction/resolvedOutputPath/dependencies。
- :100「STOP after creating ONE artifact」、:129「Create ONE artifact per invocation」。
- :91「Read any completed dependency files for context - always **re-read them from disk**, even if you saw them earlier in the conversation」。
- :22 auto-selected 且无 openspec root 时停止使用 OpenSpec 正常回答，不擅自 init。

→ **压缩丢的是「怎么问 CLI」，不是「当前到哪一步」**。这是 bw 目前缺的一环：bw 的 `next_action` 是自由文本，没有可查询的状态机。

### 9.3 bw 已吸收与未吸收

已吸收（有据）：

| 来源 | bw 落点 |
|---|---|
| Matt `grilling` | `references/grilling.md` 逐字镜像，MIT，见 `skills/bw/NOTICE.md:65-75` |
| Matt domain-modeling | `references/domain-modeling.md` 含其材料，同上 |
| Matt「完成靠外在机械前置」归纳（`bywork/memory/evaluation.md:89`） | `scripts/check_work.py --close` |
| OpenSpec「稳定真相与 change 分离」（`bywork/work/v2-delivery/research-evidence-matrix.md:61-69`） | `bywork/memory/` 与 `bywork/work/` 分离；change 可在执行中修正 |
| OpenSpec「从磁盘重读而非信记忆」 | `references/change.md:21` frontmatter 是唯一状态来源、`prove.md` 完成与接续的重读要求 |

明确未吸收：OpenSpec 的 artifact 状态机与 `openspec status` 式可查询下一步；Matt 的 fresh-context-per-ticket 子代理编排与 phase boundary 上下文纪律；Matt 的 user-invoked 分段（bw 是单技能四行动路由）。

### 9.4 对「学四段式」的判断：不学拆分，学边界

用户担心「四段式也会压缩跑偏」——**这个担心是对的，而且拆技能会让它更糟**。四段式若拆成四个技能，压缩后模型要同时记住「有哪些段、现在哪段、下段是谁」，比记住一份契约更难；OpenSpec 敢拆是因为每段都能重新问 CLI 拿状态，Matt 敢拆是因为人手动点。**我们没有 CLI 状态机也不想让人手动点，拆开只会增加遗忘面。**

真正值得吸收的是 Matt 的 **phase boundary** 概念，它与 bw 现有的「行为单元」同构但多了一条纪律：`change.md:25` 已经要求每轮只完成一条用户行为、回写后才选下一行——**这已经是 phase boundary，只差把「压缩只该发生在边界上」这层意思说清**。当前 bw 没有任何一句提到上下文容量与单元边界的关系，模型不知道「单元没做完就压缩」是它自己该避免的事。

这是候选，不是结论：它仍是提示词依赖，且属于「让模型管理自己的上下文」——与用户否决过的「让模型知道自己被压缩」相邻，须先向用户确认是否越界。

## 附：一手来源

- 本地参考仓库 `/Users/zijie/workspace/reference/ai-workflows/`（matt-skills HEAD=5863806、openspec、superpowers、spec-kit、bmad、gstack、ralph、cursor-plugins、write-notes-like-deepseek）：`matt-skills/skills/engineering/to-tickets/SKILL.md:33,42-56`、`implement-spec/SKILL.md:15,17,29,38`、`ask-matt/SKILL.md:36-40,69-79`、`ask-matt/PHASE-BOUNDARIES.md:5`、`.agents/invocation.md`、`openspec/skills/openspec-continue-change/SKILL.md:22,49,91,100,129`

- `opencode.ai/docs/instructions`、`/docs/compaction`、`/docs/skills`、`/docs/build/plugins/server`（后者全文缓存 `/Users/zijie/.local/share/opencode/tool-output/tool_1f3cda6500011DlDGfWD0e50xY`，关键段 :826-831、:870-905、:966-1065、:1431-1476、:1804-1837）
- `code.claude.com/docs/en/hooks`（全文缓存 `/Users/zijie/.local/share/opencode/tool-output/tool_1f3cdc870001ffhgLGEUvpia9k`）
- `raw.githubusercontent.com/obra/superpowers/main/hooks/hooks.json`、`hooks/session-start`、`README.md:54,92-94`、`skills/using-superpowers/SKILL.md` frontmatter
- `opencode.ai/docs/references`（带 description 的 reference 进 agent instructions，但需改 `opencode.json`，属 per-client 配置）
- `agents.md`（AGENTS.md 开放标准与支持宿主清单）
- `open-gsd/gsd-core`：`docs/explanation/context-engineering.md`（main）、`hooks/hooks.json`（next）、`hooks/gsd-session-state.sh`
- `KbWen/agentic-os` README、`clawplays/ospec` README、`thedotmack/claude-mem` `plugin/hooks/hooks.json`
- 会话原文导出：`/private/var/folders/df/g_fkd79n7b503kmv28_l2myc0000gn/T/opencode/retro-e0d28f98.txt`、`retro-e0d5fb56.txt`
- 本仓既有证据：`bywork/work/v2-delivery/final-evaluation-report.md:42-43`、`bywork/work/large-repo-compaction/review.md:107-114`、`bywork/memory/project.md:62`、`bywork/memory/evaluation.md:89`