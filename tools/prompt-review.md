# 提示词变更审查

改 `skills/bw/` 的提示词或模板前，核对以下五项：

1. **单一归属**：这条规则是否已经在 `skills/bw/SKILL.md` 或某个 `references/*.md` 里出现过？只留一处权威文本，其余用链接指向它。
2. **职责边界**：它属于 6 个主线动作（`understand` / `clarify` / `plan` / `implement` / `prove` / `close`）还是 2 个横切动作（`review` / `memory`）？放进对应单职责文件，不往 `SKILL.md` 堆细节，保持 `SKILL.md` 单次读取不截断。
3. **通用性与零枚举**：规则是否绑死了某个特定领域或枚举了具体领域例子？陈述通用工程判据，不枚举不完备的具体案例。
4. **注意力成本**：这条规则是否改变了模型的强默认行为或挡住过真实失败？模型本就会做对的常识不写。
5. **机械咬合**：凡能由 `skills/bw/scripts/bw.py` 或 `tools/check-skill-repository.py` 用非零退出码拦截的结构约束，优先落进脚本，不靠散文叮嘱。