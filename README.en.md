# ByWork (`bw`)

[中文](README.md)

ByWork is a general-purpose engineering management Agent Skill designed to keep **long single sessions from drifting** and **long-lived projects from rotting as they scale**.

Domain expertise comes from the model and other skills. ByWork routes the current action, keeps checkpoints and evidence in proposals, and turns completed or rejected proposals into durable records. Implemented records that no longer guide current work may be archived.

## Install

```bash
npx skills add https://github.com/ByteTrue/ByWork --skill bw
```

### Recommended: One-Line Baseline in `AGENTS.md`

To keep a discoverable entry point when earlier conversation is compacted, add this line to your project or global `AGENTS.md` (or `CLAUDE.md`):

```markdown
Before doing anything, read the `bw` skill (`SKILL.md`) and follow its action routing.
```

[`skills/bw/SKILL.md`](skills/bw/SKILL.md) contains the routing map and shared contract. Persistence depends on the host; following the instructions still depends on the model. Passing structural checks does not establish evidence quality or long-term effectiveness.

### Existing 1.x Projects

After updating the skill, migrate old `bywork/work/` and `bywork/memory/` using the [onboarding guide](skills/bw/references/onboard.md#从-1x-工作区迁移). `init` preserves the originals and reports the required migration; it only creates directories. Carry forward unfinished verification, current constraints, and links, then pass `bw.py check` before using the four-state workflow.

## Action Routing (6 Core + 2 Cross-Cutting)

| Action | Reference |
|---|---|
| **Understand** | [`references/understand.md`](skills/bw/references/understand.md) |
| **Clarify** | [`references/clarify.md`](skills/bw/references/clarify.md) |
| **Plan** | [`references/plan.md`](skills/bw/references/plan.md) |
| **Implement** | [`references/implement.md`](skills/bw/references/implement.md) |
| **Prove** | [`references/prove.md`](skills/bw/references/prove.md) |
| **Close** | [`references/close.md`](skills/bw/references/close.md) |
| **Review** | [`references/review.md`](skills/bw/references/review.md) |
| **Memory** | [`references/memory.md`](skills/bw/references/memory.md) |

## Workspace Structure

```text
bywork/
  proposed/<category>/yyyy-mm-dd-topic.md     # Active proposals & checkpoints with verification table
  implemented/<category>/yyyy-mm-dd-topic.md  # Current standing decisions (present tense)
  rejected/<category>/yyyy-mm-dd-topic.md     # Rejected alternatives & pitfalls to avoid
  archived/<category>/yyyy-mm-dd-topic.md     # Read-only historical records
  archived/manifest.json                      # SHA-256 integrity seal for archived files
  vision/index.md                             # Optional project-level goals and boundaries
```

## Commands and Integrity

For a project install in `.agents/skills/bw/`, use `python3 .agents/skills/bw/scripts/bw.py -h` to discover `init`, `check`, `complete`, `reject`, `archive`, `anchors`, and `board`. Use the actual skill directory reported by the installer if it differs; `skills/bw/` is the source path in this repository. Completion requires passing results and recorded evidence. Transitions refuse wrong lifecycles and existing destinations.

Facts are updated with the deliverable; partially superseded decisions stay active with explicit remaining scope. Archiving preserves the original bytes except for the added date. Git projects compare seals with `HEAD`, or the trusted commit in `BW_ARCHIVE_BASE_REF` for CI. Without Git or a first commit, checks only compare current files and hashes. Add `bw.py check` to the project’s existing delivery checks; the skill does not install hooks or CI.

## Repository Checks

The full check requires Python 3.10+ and Node.js 22+ and covers repository structure, the CLI, board parsing, and the evaluation runner. For browser interactions, pass a local Chrome binary; the test uses an isolated profile in offline mode.

```bash
bash tools/release-check.sh --no-deploy
node tools/test-bw-board.cjs "/path/to/chrome"
```

## License

MIT. See [`LICENSE`](LICENSE) and [`skills/bw/NOTICE.md`](skills/bw/NOTICE.md).