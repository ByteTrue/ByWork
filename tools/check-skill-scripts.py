#!/usr/bin/env python3
"""测试技能包分发到用户项目里的统一脚本 bw.py：四态目录初始化、结构校验、生命周期流转、锚点体检与看板生成。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BW = ROOT / "skills/bw/scripts/bw.py"

VALID_PROPOSED = """---
kind: work
status: in_progress
current_unit: 订单提交流程
next_action: 验证 CLI 入口
must_hold: 幂等与错误处理
proof_gap: ""
---

# 订单提交流程

Status: proposed

## 问题

缺少统一的订单提交 CLI 入口。

## 提案

新增提交入口并校验订单号返回。

## 备选方案

- **备选方案 A**：直接写数据库。最强理由是省去接口层，但绕过校验故不采用。

## 验收标准

| 行为路径 | 计划证明 | 实际证据 | 范围覆盖 | 缺口 | 结果 |
|---|---|---|---|---|---|
| 下单成功 | CLI 提交订单 | logs/order.txt | cli.py | 无 | 通过 |

## 风险与代价

新增一个 CLI 子命令。
"""


def run_bw(project: Path, *args: str, base_ref: str | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    env.pop("BW_ARCHIVE_BASE_REF", None)
    if base_ref is not None:
        env["BW_ARCHIVE_BASE_REF"] = base_ref
    proc = subprocess.run(
        [sys.executable, str(BW), *args, "--project", str(project)],
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def write_proposed(root: Path, name: str, text: str, category: str = "feature") -> Path:
    path = root / "bywork" / "proposed" / category / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    failures = 0
    cases = 0

    def case(label: str, ok: bool, output: str = "") -> None:
        nonlocal failures, cases
        cases += 1
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
        if not ok:
            failures += 1
            print(output)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "project"
        project.mkdir()
        checked = root / "checked"
        checked.mkdir()

        # -h self-documentation
        proc_h = subprocess.run([sys.executable, str(BW), "-h"], capture_output=True, text=True)
        out_h = proc_h.stdout + proc_h.stderr
        case(
            "bw.py -h documents all subcommands",
            proc_h.returncode == 0
            and all(cmd in out_h for cmd in ("init", "check", "complete", "reject", "archive", "anchors", "board")),
            out_h,
        )

        code, output = run_bw(project, "init")
        created = all(
            (project / "bywork" / name).is_dir()
            for name in ("proposed", "implemented", "rejected", "archived")
        )
        case("fresh init creates four lifecycle dirs", code == 0 and created and "created" in output, output)

        marker = project / "bywork/proposed/feature/2026-11-20-example.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("# existing\n", encoding="utf-8")
        code, output = run_bw(project, "init")
        case(
            "rerun keeps existing notes",
            code == 0 and marker.read_text(encoding="utf-8") == "# existing\n" and "kept" in output,
            output,
        )

        vision = project / "bywork/vision/index.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("# user vision\n", encoding="utf-8")
        code, output = run_bw(project, "init")
        case(
            "rerun preserves optional vision",
            code == 0 and vision.read_text(encoding="utf-8") == "# user vision\n",
            output,
        )

        run_bw(checked, "init")
        code, output = run_bw(checked, "check")
        case("check passes on empty initialized workspace", code == 0, output)

        note_name = "2026-11-20-order-cli.md"
        write_proposed(checked, note_name, VALID_PROPOSED)
        code, output = run_bw(checked, "check")
        case("check accepts a valid proposed note", code == 0, output)

        for bad in ("done", "completed", "finished", "in-progress", "complete"):
            write_proposed(checked, note_name, VALID_PROPOSED.replace("status: in_progress", f"status: {bad}"))
            code, output = run_bw(checked, "check")
            case(f"check rejects proposed status: {bad}", code != 0 and "must be one of" in output, output)

        # Forbidden centralized INDEX.md
        write_proposed(checked, note_name, VALID_PROPOSED)
        idx_file = checked / "bywork/INDEX.md"
        idx_file.write_text("# index\n", encoding="utf-8")
        code, output = run_bw(checked, "check")
        case("check rejects centralized INDEX.md", code != 0 and "INDEX.md is forbidden" in output, output)
        idx_file.unlink()

        # Evidence column quoting 未通过 should not trigger bad verdict
        quoted = VALID_PROPOSED.replace("| logs/order.txt | cli.py | 无 | 通过 |", "| 旧版未通过，见日志 | cli.py | 无 | 通过 |")
        write_proposed(checked, note_name, quoted)
        code, output = run_bw(checked, "check")
        case("check ignores 未通过 quoted in evidence column", code == 0, output)

        # Formatter-padded table header
        padded = VALID_PROPOSED.replace("| 行为路径 | 计划证明 |", "| 行为路径        | 计划证明 |")
        write_proposed(checked, note_name, padded)
        code, output = run_bw(checked, "check")
        case("check accepts formatter-padded verification table header", code == 0, output)

        # Missing frontmatter field
        write_proposed(checked, note_name, VALID_PROPOSED.replace("must_hold: 幂等与错误处理\n", ""))
        code, output = run_bw(checked, "check")
        case("check reports missing frontmatter field", code != 0 and "must_hold" in output, output)

        # Missing required section
        write_proposed(checked, note_name, VALID_PROPOSED.replace("## 备选方案", "## 其他"))
        code, output = run_bw(checked, "check")
        case("check reports missing required section", code != 0 and "## 备选方案" in output, output)

        # Broken relative link
        write_proposed(checked, note_name, VALID_PROPOSED + "\n详见 [不存在](missing.md)。\n")
        code, output = run_bw(checked, "check")
        case("check reports broken relative link", code != 0 and "broken relative link" in output, output)

        # complete refuses non-empty proof_gap
        write_proposed(checked, note_name, VALID_PROPOSED.replace('proof_gap: ""', 'proof_gap: "未跑集成验证"'))
        code, output = run_bw(checked, "complete", "order-cli")
        case("complete refuses non-empty proof_gap", code != 0 and "proof_gap" in output, output)

        # complete refuses unresolved row
        write_proposed(checked, note_name, VALID_PROPOSED.replace("| 通过 |", "| 待跑 |"))
        code, output = run_bw(checked, "complete", "order-cli")
        case("complete refuses unresolved verification row", code != 0 and "unresolved" in output, output)

        # complete molts valid proposed note into implemented/
        write_proposed(checked, note_name, VALID_PROPOSED)
        code, output = run_bw(checked, "complete", "order-cli")
        impl_path = checked / "bywork/implemented/feature" / note_name
        case(
            "complete molts proposed note into implemented/ and removes source",
            code == 0 and impl_path.is_file() and not (checked / "bywork/proposed/feature" / note_name).exists(),
            output,
        )
        code, output = run_bw(checked, "check")
        case("molted implemented note passes workspace check", code == 0, output)

        # archive moves implemented note into archived/ and seals manifest.json
        new_impl = checked / "bywork/implemented/feature/2026-11-21-order-v2.md"
        new_impl.write_text(
            impl_path.read_text(encoding="utf-8").replace("# 订单提交流程", "# 订单提交流程 v2"),
            encoding="utf-8",
        )
        code, output = run_bw(checked, "archive", note_name, "--superseded-by", "2026-11-21-order-v2.md")
        arch_path = checked / "bywork/archived/feature" / note_name
        case(
            "archive moves note, seals manifest.json, and appends superseded pointer",
            code == 0
            and arch_path.is_file()
            and (checked / "bywork/archived/manifest.json").is_file()
            and "历史替代快照见" in new_impl.read_text(encoding="utf-8"),
            output,
        )
        code, output = run_bw(checked, "check")
        case("workspace with sealed archived note passes check", code == 0, output)

        # Tampering with archived file must fail SHA-256 check
        orig_arch = arch_path.read_text(encoding="utf-8")
        arch_path.write_text(orig_arch + "\ntampered\n", encoding="utf-8")
        code, output = run_bw(checked, "check")
        case("check rejects tampered archived file", code != 0 and "sha256 mismatch" in output, output)
        arch_path.write_text(orig_arch, encoding="utf-8")

        # reject moves proposed note into rejected/ with frozen Status: rejected — <reason>
        rej_name = "2026-11-20-bad-idea.md"
        write_proposed(checked, rej_name, VALID_PROPOSED)
        code, output = run_bw(checked, "reject", "bad-idea", "--reason", "开销过大且破坏隔离")
        rej_path = checked / "bywork/rejected/feature" / rej_name
        case(
            "reject moves proposed note into rejected/ with Status: rejected — reason",
            code == 0
            and rej_path.is_file()
            and "Status: rejected — 开销过大且破坏隔离" in rej_path.read_text(encoding="utf-8"),
            output,
        )
        code, output = run_bw(checked, "check")
        case("workspace with rejected note passes check", code == 0, output)

        # anchors soft check
        src_file = checked / "cli.py"
        src_file.write_text("# Note: 订单入口约束。见 bywork/implemented/feature/2026-11-21-order-v2.md\n", encoding="utf-8")
        code, output = run_bw(checked, "anchors")
        case("anchors scans code comments and exits 0", code == 0 and "anchors found: 1" in output, output)

        # board --init and --bundle
        code, output = run_bw(checked, "board", "--init")
        case("board --init generates board.html", code == 0 and (checked / "board.html").is_file(), output)
        code, output = run_bw(checked, "board", "--bundle")
        case(
            "board --bundle generates demo.html with inline notes",
            code == 0
            and (checked / "demo.html").is_file()
            and "2026-11-21-order-v2" in (checked / "demo.html").read_text(encoding="utf-8"),
            output,
        )

        def snapshot(folder: Path) -> dict[str, bytes]:
            return {p.relative_to(folder).as_posix(): p.read_bytes()
                    for p in folder.rglob("*") if p.is_file() and ".git" not in p.relative_to(folder).parts}

        def fresh(name: str) -> tuple[Path, Path]:
            folder = root / name
            assert run_bw(folder, "init")[0] == 0
            return folder, write_proposed(folder, note_name, VALID_PROPOSED)

        for i, verdict in enumerate(("", "pending", "通过（未验证）", "未通过", "无法判定")):
            folder, source = fresh(f"verdict-{i}")
            source.write_text(VALID_PROPOSED.replace("| 通过 |", f"| {verdict} |"), encoding="utf-8")
            before = snapshot(folder)
            code, output = run_bw(folder, "complete", note_name)
            case(f"complete refuses result {verdict!r} without changing files",
                 code != 0 and snapshot(folder) == before, output)

        folder, source = fresh("no-evidence")
        source.write_text(VALID_PROPOSED.replace("logs/order.txt", ""), encoding="utf-8")
        before = snapshot(folder)
        code, output = run_bw(folder, "complete", note_name)
        case("complete refuses passing row without evidence", code != 0 and snapshot(folder) == before, output)

        folder, source = fresh("remaining-gap")
        source.write_text(VALID_PROPOSED.replace("| 无 | 通过 |", "| 入口未验证 | 通过 |"), encoding="utf-8")
        before = snapshot(folder)
        code, output = run_bw(folder, "complete", note_name)
        case("complete refuses a passing label with a recorded gap", code != 0 and snapshot(folder) == before, output)

        folder, source = fresh("escaped-pipe")
        source.write_text(VALID_PROPOSED.replace("logs/order.txt", r"结果 A\|B，见 logs/order.txt"), encoding="utf-8")
        code, output = run_bw(folder, "complete", note_name)
        case("complete accepts an escaped pipe inside an evidence cell", code == 0, output)

        folder, source = fresh("wrong-header")
        source.write_text(VALID_PROPOSED.replace("| 实际证据 | 范围覆盖 |", "| 范围覆盖 | 实际证据 |"), encoding="utf-8")
        before = snapshot(folder)
        code, output = run_bw(folder, "complete", note_name)
        case("complete refuses reordered evidence columns", code != 0 and snapshot(folder) == before, output)

        example = "\n" + "`" * 3 + "markdown\nStatus: proposed\n## 提案\n" + "`" * 3 + "\n"
        for command, dest in (("complete", "implemented"), ("reject", "rejected")):
            folder, source = fresh(f"literal-example-{command}")
            source.write_text(VALID_PROPOSED + example, encoding="utf-8")
            args = ("--reason", "test") if command == "reject" else ()
            code, output = run_bw(folder, command, note_name, *args)
            destination = folder / "bywork" / dest / "feature" / note_name
            case(f"{command} preserves literal status and headings inside examples",
                 code == 0 and example.strip() in destination.read_text(encoding="utf-8"), output)

        folder, source = fresh("multiline-reason")
        before = snapshot(folder)
        code, output = run_bw(folder, "reject", note_name, "--reason", "first line\nStatus: rejected")
        case("reject refuses multi-line reason without changing source", code != 0 and snapshot(folder) == before, output)

        folder, source = fresh("template")
        source.write_text((ROOT / "skills/bw/templates/proposed.md").read_text(encoding="utf-8"), encoding="utf-8")
        code, output = run_bw(folder, "check")
        case("shipped proposed template satisfies checker", code == 0, output)

        for command, dest in (("complete", "implemented"), ("reject", "rejected"), ("archive", "archived")):
            folder, source = fresh(f"collision-{command}")
            if command == "archive":
                assert run_bw(folder, "complete", note_name)[0] == 0
                source = folder / "bywork/implemented/feature" / note_name
            target = folder / "bywork" / dest / "feature" / note_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("existing decision MUST SURVIVE\n", encoding="utf-8")
            if command == "archive":
                assert run_bw(folder, "check", "--write-manifest")[0] == 0
            before = snapshot(folder)
            args = ("--reason", "test") if command == "reject" else ()
            code, output = run_bw(folder, command, note_name, *args)
            case(f"{command} refuses destination collision without changing either file",
                 code != 0 and snapshot(folder) == before, output)

        folder, source = fresh("outside-note")
        ordinary = folder / "ordinary.md"
        ordinary.write_text(VALID_PROPOSED, encoding="utf-8")
        before = snapshot(folder)
        code, output = run_bw(folder, "reject", "ordinary.md", "--reason", "test")
        case("reject refuses ordinary project file", code != 0 and snapshot(folder) == before, output)
        source.unlink()
        source.symlink_to(ordinary)
        code, output = run_bw(folder, "complete", note_name)
        case("complete refuses source symlink outside lifecycle", code != 0 and ordinary.is_file() and source.is_symlink(), output)
        source.unlink()
        source.write_text(VALID_PROPOSED, encoding="utf-8")
        assert run_bw(folder, "complete", note_name)[0] == 0
        before = snapshot(folder)
        code, output = run_bw(folder, "reject", f"bywork/implemented/feature/{note_name}", "--reason", "test")
        case("reject refuses wrong lifecycle even with explicit path", code != 0 and snapshot(folder) == before, output)

        folder, source = fresh("preserve-evidence")
        source.write_text(VALID_PROPOSED.replace("## 风险与代价", "- [x] 已验证入口；未覆盖的部署环境另列。\n\n## 风险与代价"), encoding="utf-8")
        code, output = run_bw(folder, "complete", note_name)
        impl = folder / "bywork/implemented/feature" / note_name
        case("complete retains verification details and coverage limits",
             code == 0 and "- [x] 已验证入口；未覆盖的部署环境另列。" in impl.read_text(encoding="utf-8"), output)
        before = snapshot(folder)
        code, output = run_bw(folder, "archive", note_name, "--superseded-by", "does-not-exist")
        case("archive refuses invalid replacement before moving", code != 0 and snapshot(folder) == before, output)
        manifest = folder / "bywork/archived/manifest.json"
        for malformed in ("{", '{"files": []}', '{"files": {"feature/bad.md": {"sha256": 3}}}'):
            manifest.write_text(malformed, encoding="utf-8")
            before = snapshot(folder)
            code, output = run_bw(folder, "archive", note_name)
            case("archive refuses malformed manifest without rewriting it", code != 0 and snapshot(folder) == before, output)
        manifest.unlink()
        raw = impl.read_bytes().replace(b"\n", b"\r\n") + b"\r\n  "
        impl.write_bytes(raw)
        code, output = run_bw(folder, "archive", note_name)
        archived = folder / "bywork/archived/feature" / note_name
        remainder = b"".join(line for line in archived.read_bytes().splitlines(keepends=True) if not line.startswith(b"Archived:"))
        case("archive preserves exact original bytes except added date", code == 0 and remainder == raw, output)

        def git(*args: str) -> str:
            proc = subprocess.run(["git", "-C", str(folder), "-c", "user.name=ByWork test",
                                   "-c", "user.email=bywork@example.invalid", "-c", "commit.gpgsign=false",
                                   "-c", f"core.hooksPath={folder / 'no-hooks'}", *args],
                                  capture_output=True, text=True)
            assert proc.returncode == 0, proc.stderr
            return proc.stdout.strip()

        git("init", "-q")
        git("add", "bywork")
        git("commit", "-qm", "archive baseline")
        baseline = git("rev-parse", "HEAD")
        original_file, original_manifest = archived.read_bytes(), manifest.read_bytes()
        archived.write_bytes(original_file + b"tampered")
        data = json.loads(original_manifest)
        key = archived.relative_to(folder / "bywork/archived").as_posix()
        data["files"][key]["sha256"] = hashlib.sha256(archived.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(data), encoding="utf-8")
        before = snapshot(folder)
        code, output = run_bw(folder, "check", "--write-manifest")
        case("committed baseline rejects jointly changed archive and hash without resealing",
             code != 0 and "committed archive seal" in output and snapshot(folder) == before, output)
        archived.unlink()
        manifest.write_text('{"files": {}}', encoding="utf-8")
        before = snapshot(folder)
        code, output = run_bw(folder, "check", "--write-manifest")
        case("committed baseline rejects deletion of archived file and its seal",
             code != 0 and snapshot(folder) == before, output)
        archived.write_bytes(original_file)
        manifest.write_bytes(original_manifest)
        code, output = run_bw(folder, "check", base_ref="not-a-commit")
        case("explicit unavailable baseline fails closed", code != 0 and "cannot read archive baseline" in output, output)
        new_name = "2026-11-21-another-decision.md"
        write_proposed(folder, new_name, VALID_PROPOSED)
        assert run_bw(folder, "complete", new_name)[0] == 0
        code, output = run_bw(folder, "archive", new_name)
        case("baseline allows adding a new archive without changing old seals", code == 0, output)
        code, output = run_bw(folder, "check", base_ref=baseline)
        case("explicit committed baseline accepts append-only archive", code == 0, output)
        new_archived = folder / "bywork/archived/feature" / new_name
        new_archived.unlink()
        before = snapshot(folder)
        code, output = run_bw(folder, "check", "--write-manifest")
        case("missing sealed file prevents manifest writes", code != 0 and snapshot(folder) == before, output)

        proc = subprocess.run([sys.executable, str(BW), "--project", str(root / "project-prefix"), "init"],
                              capture_output=True, text=True)
        case("--project works before the subcommand", proc.returncode == 0 and (root / "project-prefix/bywork").is_dir(), proc.stderr)

    print(
        f"{'all' if not failures else failures} packaged script case{'s' if cases != 1 else ''} "
        f"{'pass' if not failures else 'failed'} ({cases - failures}/{cases})"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
