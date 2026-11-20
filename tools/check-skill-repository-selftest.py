#!/usr/bin/env python3
"""证明仓库 checker 的每个检查都能在坏夹具上失败。"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = "tools/check-skill-repository.py"
PROJECT_DOC = "bywork/implemented/architecture/2026-11-18-project-constraints.md"


def edit(rel, old, new):
    def apply(root: Path):
        path = root / rel
        text = path.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"{rel}: fixture anchor occurs {text.count(old)} times: {old!r}"
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    return apply


def append(rel, line):
    def apply(root: Path):
        with (root / rel).open("a", encoding="utf-8") as handle:
            handle.write(f"\n{line}\n")

    return apply


def write(rel, text):
    def apply(root: Path):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return apply


def delete(rel):
    return lambda root: (root / rel).unlink()


def both(*steps):
    def apply(root: Path):
        for step in steps:
            step(root)

    return apply


def duplicate_current_version(root: Path):
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    with (root / "CHANGELOG.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {version}\n\nagain\n")


CASES = [
    ("version without changelog section", write("VERSION", "9.9.9\n"), "missing version section 9.9.9"),
    ("version not semver", write("VERSION", "1.x\n"), "not valid semver"),
    ("second skill in package", write("skills/extra/SKILL.md", "# extra\n"), "must contain exactly the bw skill"),
    ("entry file missing", delete("skills/bw/agents/openai.yaml"), "required entry file is missing"),
    (
        "link to missing file",
        append("skills/bw/references/clarify.md", "[x](references/nope.md)"),
        "points at missing path: references/nope.md",
    ),
    ("packaged file nobody references", write("skills/bw/references/orphan.md", "# orphan\n"), "packaged but nothing references it"),
    ("skill names a repo-only file", append("skills/bw/references/clarify.md", "见 `VERSION`"), "repo-only file not distributed"),
    (
        "new tool file is repo-only without editing the checker",
        both(write("tools/brand-new-tool.md", "# new\n"), append("skills/bw/references/clarify.md", "见 `brand-new-tool.md`")),
        "repo-only file not distributed with skills/bw/: brand-new-tool.md",
    ),
    (
        "template carries a skill-internal path",
        append("skills/bw/templates/proposed.md", "[x](../references/clarify.md)"),
        "template contains skill-internal path",
    ),
    (
        "proposed template loses a checkpoint field",
        edit("skills/bw/templates/proposed.md", "status: in_progress", "state: in_progress"),
        "frontmatter fields must be",
    ),
    (
        "anchored link to missing file",
        append("skills/bw/references/clarify.md", "[x](references/nope.md#part)"),
        "points at missing path: references/nope.md",
    ),
    (
        "current doc names a deleted tool",
        append(PROJECT_DOC, "见 `tools/check-deleted.py`"),
        "names missing path: tools/check-deleted.py",
    ),
    (
        "current doc links a missing file",
        append("README.md", "[x](docs/nope.md)"),
        "link points at missing path: docs/nope.md",
    ),
    (
        "inline command names a deleted tool",
        append(PROJECT_DOC, "运行 python3 tools/deleted.py"),
        "command names missing path: tools/deleted.py",
    ),
    (
        "fenced command names a deleted tool",
        append("README.md", "```bash\npython3 tools/deleted.py\n```"),
        "command names missing path: tools/deleted.py",
    ),
    (
        "current proposal links a missing file",
        write("bywork/proposed/architecture/2026-11-20-example.md", "[proof](missing.md)\n"),
        "link points at missing path: missing.md",
    ),
    (
        "historical records left in active workspace",
        write("bywork/issues/legacy.md", "# historical issue\n"),
        "unexpected workspace entry; only proposed/, implemented/, rejected/, archived/, and vision/ belong here",
    ),
    ("changelog newest section is not VERSION", lambda root: (root / "CHANGELOG.md").write_text("## 0.0.0\n\nold\n\n" + (root / "CHANGELOG.md").read_text(encoding="utf-8"), encoding="utf-8"), "newest section is 0.0.0"),
    ("changelog repeats a version", duplicate_current_version, "has more than one section"),
    ("license edited but packaged NOTICE not", edit("LICENSE", "2026 ByteTrue", "2027 ByteTrue"), "must contain the repository LICENSE verbatim"),
    ("packaged NOTICE loses Matt attribution", edit("skills/bw/NOTICE.md", "Copyright (c) 2026 Matt Pocock", "Copyright (c) 2026"), "must keep the Matt Pocock upstream attribution"),
    ("packaged NOTICE loses CodeStable attribution", edit("skills/bw/NOTICE.md", "Copyright (c) liuzhengdong (CodeStable", "Copyright (c) someone (CodeStable"), "must keep the CodeStable upstream attribution"),
    ("packaged NOTICE loses write-notes-like-deepseek attribution", edit("skills/bw/NOTICE.md", "Copyright (c) 2026 czm15053", "Copyright (c) 2026 someone"), "must keep the write-notes-like-deepseek upstream attribution"),
    ("project constraints doc deleted", delete(PROJECT_DOC), f"{PROJECT_DOC}: file is missing"),
]


def run(root: Path) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(root / CHECKER)], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def fresh_copy(base: Path, name: str) -> Path:
    target = base / name
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    # Git checkouts do not recreate empty lifecycle directories.
    for directory in sorted(target.rglob("*"), reverse=True):
        if directory.is_dir() and not directory.is_symlink() and not any(directory.iterdir()):
            directory.rmdir()
    return target


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        code, output = run(fresh_copy(base, "clean"))
        if code != 0:
            print(output)
            print("FAIL clean copy: checker must pass before planted cases mean anything")
            return 1
        print("ok   clean copy without empty directories passes")
        for index, (name, plant, expected) in enumerate(CASES):
            root = fresh_copy(base, f"case{index}")
            plant(root)
            code, output = run(root)
            if code == 1 and expected in output:
                print(f"ok   {name}")
            else:
                failures.append(name)
                print(f"FAIL {name}: expected exit 1 with {expected!r}, got exit {code}\n{output}")
    print(f"{len(CASES) - len(failures)}/{len(CASES)} planted defects caught")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
