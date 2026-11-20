#!/usr/bin/env python3
"""ByWork 统一命令行工具 (bw.py)。

整合工作区初始化、四态结构与格式门禁、提案蜕皮流转、归档 SHA-256 封印、
源码反向锚点体检与工程决策看板生成。请通过 `python3 bw.py -h` 查看子命令用法。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import posixpath
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote

LIFECYCLES = ("proposed", "implemented", "rejected", "archived")
ACTIVE_LIFECYCLES = ("proposed", "implemented", "rejected")
WORK_FIELDS = ("kind", "status", "current_unit", "next_action", "must_hold", "proof_gap")
PROPOSED_STATUSES = ("in_progress", "blocked")
VERDICTS = ("通过", "未通过", "无法判定")
FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9._-]*\.md$")
CATEGORY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
LINK_DEST = r'(?P<target><[^>\n]*>|(?:\\.|[^\s()\\]|\([^()\n]*\))+)'
LINK_TITLE = r'(?:\s+(?:"[^"\n]*"|\'[^\'\n]*\'|\([^()\n]*\)))?'
LINK_RE = re.compile(r'!?\[(?:\\.|[^\]\\])*\]\(\s*' + LINK_DEST + LINK_TITLE + r'\s*\)')
REFERENCE_LINK_RE = re.compile(r'^ {0,3}\[[^\]]+\]:\s*' + LINK_DEST + LINK_TITLE + r'\s*$')

SECTION_ALIASES = {
    "problem": ("问题", "Problem"),
    "proposal": ("提案", "Proposal"),
    "decision": ("决策", "Decision"),
    "alternatives": ("备选方案", "Alternatives considered", "已考虑的备选方案", "曾考虑的替代方案", "曾考虑的备选"),
    "acceptance": ("验收标准", "Acceptance criteria"),
    "risks": ("风险与代价", "Risks", "风险"),
    "consequences": ("收益和代价", "Consequences", "后果"),
}
FORBIDDEN_IN_IMPLEMENTED = (
    "提案",
    "Proposal",
    "计划",
    "Plan",
    "迁移计划",
    "Migration plan",
    "验收标准",
    "Acceptance criteria",
)

CODE_EXT = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".go", ".rs", ".java", ".kt", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".swift", ".vue", ".svelte", ".php", ".sh",
}
SKIP_DIR = {
    "node_modules", ".git", "dist", "build", "out", "coverage", ".next",
    ".cache", ".agents", "vendor", "target", "bywork", "__pycache__",
}
ANCHOR_RE = re.compile(r"^\s*(?://|#|/\*|\*|<!--)\s*Note[:：]")
ANCHOR_PATH_RE = re.compile(r"(?:bywork|\.agents/notes)/([^\s'>)]+?\.md)")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_fenced_and_comments(text: str) -> list[str]:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<!--[\s\S]*?-->", lambda m: re.sub(r"[^\n]", " ", m.group()), text)
    out: list[str] = []
    fence = ""
    for line in text.split("\n"):
        marker = re.match(r"^ {0,3}(\x60{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = ""
            out.append("")
        elif marker and not (marker[1][0] == chr(96) and chr(96) in marker[2]):
            fence = marker[1]
            out.append("")
        else:
            out.append(line)
    return out

def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str, str | None]:
    norm = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, norm, None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, norm, "frontmatter is not closed with '---'"
    fields: dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            return None, norm, f"invalid frontmatter line: {raw!r}"
        k, v = raw.split(":", 1)
        val = v.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        fields[k.strip()] = val
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return fields, body, None


def normalize_heading(title: str) -> str:
    return re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", title.strip()).strip().lower()


def extract_sections(lines: list[str]) -> list[str]:
    return [normalize_heading(line[3:]) for line in lines if line.startswith("## ")]


def section_bodies(body: str) -> list[tuple[str, str]]:
    raw_lines = body.split("\n")
    headings = [(i, line[3:].strip()) for i, line in enumerate(strip_fenced_and_comments(body)) if line.startswith("## ")]
    return [(title, "\n".join(raw_lines[start + 1: headings[n + 1][0] if n + 1 < len(headings) else len(raw_lines)]).strip())
            for n, (start, title) in enumerate(headings)]

def has_alias(sections: list[str], key: str) -> bool:
    aliases = {a.lower() for a in SECTION_ALIASES[key]}
    return any(s.lower() in aliases for s in sections)


def extract_status_lines(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip().startswith("Status:")]


def markdown_links(line: str) -> list[tuple[int, int, str]]:
    # Keep offsets so a move rewrites only destinations, preserving titles and prose.
    visible = re.sub(r"(\x60+)(.+?)\1(?!\x60)", lambda m: " " * len(m.group()), line)
    matches = list(LINK_RE.finditer(visible)) + list(REFERENCE_LINK_RE.finditer(visible))
    links = []
    for match in matches:
        start, end = match.span("target")
        if line[start:start + 1] == "<":
            start, end = start + 1, end - 1
        links.append((start, end, line[start:end]))
    return sorted(links)


def local_link_path(href: str) -> str:
    if re.match(r"^[a-z][a-z0-9+.-]*:|^//", href, re.I):
        return ""
    return unquote(re.split(r"[?#]", href, maxsplit=1)[0])


def check_relative_links(note_path: Path, lines: list[str], root: Path) -> list[str]:
    errors: list[str] = []
    rel = note_path.relative_to(root).as_posix()
    for idx, line in enumerate(lines, 1):
        for _, _, href in markdown_links(line):
            target = local_link_path(href)
            if not target:
                continue
            resolved = (note_path.parent / target).resolve()
            if resolved != note_path.resolve() and not resolved.exists():
                errors.append(f"{rel}:{idx}: broken relative link -> {href}")
    return errors


def rebase_links(body: str, source: Path, destination: Path) -> str:
    out = []
    for line, visible in zip(body.split("\n"), strip_fenced_and_comments(body)):
        for start, end, href in reversed(markdown_links(visible)):
            target = local_link_path(href)
            if not target or Path(target).is_absolute():
                continue
            original = (source.parent / target).resolve()
            if original == source:
                original = destination
            relative = os.path.relpath(original, destination.parent).replace(os.sep, "/")
            suffix = href[len(re.split(r"[?#]", href, maxsplit=1)[0]):]
            line = line[:start] + quote(relative, safe="/._-~") + suffix + line[end:]
        out.append(line)
    return "\n".join(out)

def check_verification_table(lines: list[str], rel: str) -> tuple[list[str], list[str]]:
    def split_row(line: str) -> list[str]:
        return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip()[1:].removesuffix("|"))]

    errors: list[str] = []
    unresolved_rows: list[str] = []
    acceptance = [i for i, line in enumerate(lines) if line.startswith("## ")
                  and normalize_heading(line[3:]) in {a.lower() for a in SECTION_ALIASES["acceptance"]}]
    if len(acceptance) != 1:
        return [f"{rel}: expected exactly one acceptance section, got {len(acceptance)}"], []
    begin = acceptance[0] + 1
    end = next((i for i in range(begin, len(lines)) if re.match(r"^#{1,2} ", lines[i])), len(lines))
    lines = lines[begin:end]
    tables = []
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and (i == 0 or not lines[i - 1].strip().startswith("|")):
            tables.append(i)
    if len(tables) != 1:
        return [f"{rel}: acceptance section requires exactly one verification table, got {len(tables)}"], []
    header_idx = tables[0]
    if "行为路径" not in lines[header_idx] or "结果" not in lines[header_idx]:
        return [f"{rel}: missing verification table header ('| 行为路径 | ... | 结果 |')"], []

    if split_row(lines[header_idx]) != ["行为路径", "计划证明", "实际证据", "范围覆盖", "缺口", "结果"]:
        errors.append(f"{rel}: verification table must use the six template columns in order")
    data_rows = 0
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if data_rows > 0:
                break
            continue
        cells = split_row(stripped)
        if all(not c or set(c) <= {"-", ":"} for c in cells):
            continue
        if len(cells) != 6:
            errors.append(f"{rel}: verification row has {len(cells)} columns, expected 6: {stripped}")
            continue
        data_rows += 1
        verdict = cells[-1]
        if verdict not in VERDICTS:
            errors.append(f"{rel}: verification result must be one of {VERDICTS}, got {verdict!r}")
        if verdict != "通过":
            unresolved_rows.append(f"{cells[0]} ({verdict})")
        elif cells[2] in ("", "待填", "待验证", "无", "-"):
            errors.append(f"{rel}: passing verification row requires actual evidence: {cells[0]}")
        if verdict == "通过" and cells[4] not in ("", "无", "-"):
            errors.append(f"{rel}: passing verification row still has a gap: {cells[0]} ({cells[4]})")
    if data_rows == 0:
        errors.append(f"{rel}: verification table must contain at least one behavior row")
    return errors, unresolved_rows


def check_proposed_note(path: Path, root: Path, *, require_complete_ready: bool = False) -> list[str]:
    rel = path.relative_to(root).as_posix()
    raw = path.read_text(encoding="utf-8")
    fields, body, fm_err = parse_frontmatter(raw)
    if fm_err:
        return [f"{rel}: {fm_err}"]
    if fields is None:
        return [f"{rel}: proposed note requires YAML frontmatter checkpoint"]

    errors: list[str] = []
    missing = [f for f in WORK_FIELDS if f not in fields]
    if missing:
        errors.append(f"{rel}: missing frontmatter field(s): {', '.join(missing)}")
    if fields.get("kind") != "work":
        errors.append(f"{rel}: frontmatter kind must be 'work', got {fields.get('kind')!r}")
    status = fields.get("status", "")
    if status not in PROPOSED_STATUSES:
        errors.append(
            f"{rel}: proposed frontmatter status must be one of {PROPOSED_STATUSES}, got {status!r} "
            "(use 'bw.py complete' to transition to implemented/)"
        )

    lines = strip_fenced_and_comments(body)
    non_empty = [l for l in lines if l.strip()]
    if not non_empty or not non_empty[0].startswith("# "):
        errors.append(f"{rel}: body must start with '# <标题>' or '# Agent Note: <标题>'")
    statuses = extract_status_lines(lines)
    if statuses != ["Status: proposed"]:
        errors.append(f"{rel}: expected exactly one 'Status: proposed' line, got {statuses}")

    sections = extract_sections(lines)
    for req_key, label in (
        ("problem", "问题 / Problem"),
        ("proposal", "提案 / Proposal"),
        ("alternatives", "备选方案 / Alternatives considered"),
        ("acceptance", "验收标准 / Acceptance criteria"),
        ("risks", "风险与代价 / Risks"),
    ):
        if not has_alias(sections, req_key):
            errors.append(f"{rel}: missing required section '## {label.split(' / ')[0]}'")

    tbl_errors, unresolved = check_verification_table(lines, rel)
    errors.extend(tbl_errors)
    errors.extend(check_relative_links(path, lines, root))

    if require_complete_ready:
        gap = fields.get("proof_gap", "").strip()
        if gap:
            errors.append(f"{rel}: cannot complete while proof_gap is non-empty ({gap!r})")
        if unresolved:
            errors.append(f"{rel}: cannot complete with unresolved verification row(s): {', '.join(unresolved)}")

    return errors


def check_implemented_note(path: Path, root: Path, *, text: str | None = None) -> list[str]:
    rel = path.relative_to(root).as_posix()
    raw = path.read_text(encoding="utf-8") if text is None else text
    fields, body, _ = parse_frontmatter(raw)
    errors: list[str] = []
    if fields is not None:
        errors.append(f"{rel}: implemented note must not retain proposed YAML frontmatter")

    lines = strip_fenced_and_comments(body)
    non_empty = [l for l in lines if l.strip()]
    if not non_empty or not non_empty[0].startswith("# "):
        errors.append(f"{rel}: must start with '# <标题>' or '# Agent Note: <标题>'")
    statuses = extract_status_lines(lines)
    if statuses != ["Status: implemented"]:
        errors.append(f"{rel}: expected exactly one 'Status: implemented' line, got {statuses}")

    sections = extract_sections(lines)
    for req_key, label in (
        ("problem", "问题 / Problem"),
        ("decision", "决策 / Decision"),
        ("alternatives", "备选方案 / Alternatives considered"),
        ("consequences", "收益和代价 / Consequences"),
    ):
        if not has_alias(sections, req_key):
            errors.append(f"{rel}: missing required section '## {label.split(' / ')[0]}'")

    forbidden_lower = {f.lower() for f in FORBIDDEN_IN_IMPLEMENTED}
    for sec in sections:
        if sec.lower() in forbidden_lower:
            errors.append(f"{rel}: implemented note must not contain proposal-stage section '## {sec}'")

    errors.extend(check_relative_links(path, lines, root))
    return errors


def check_rejected_note(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    raw = path.read_text(encoding="utf-8")
    fields, body, _ = parse_frontmatter(raw)
    errors: list[str] = []
    if fields is not None:
        errors.append(f"{rel}: rejected note must not retain proposed YAML frontmatter")

    lines = strip_fenced_and_comments(body)
    non_empty = [l for l in lines if l.strip()]
    if not non_empty or not non_empty[0].startswith("# "):
        errors.append(f"{rel}: must start with '# <标题>' or '# Agent Note: <标题>'")
    statuses = extract_status_lines(lines)
    if len(statuses) != 1 or not re.fullmatch(r"Status:\s*rejected\s*[—–-]\s*\S+.*", statuses[0]):
        errors.append(f"{rel}: expected 'Status: rejected — <一句话原因>', got {statuses}")

    sections = extract_sections(lines)
    if not has_alias(sections, "problem"):
        errors.append(f"{rel}: missing required section '## 问题'")
    if not has_alias(sections, "alternatives"):
        errors.append(f"{rel}: missing required section '## 备选方案'")

    errors.extend(check_relative_links(path, lines, root))
    return errors


def parse_manifest(text: str) -> dict[str, dict[str, str]]:
    data = json.loads(text)
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict):
        raise ValueError("archive manifest must contain a 'files' object")
    for name, seal in files.items():
        parts = Path(name).parts
        if (len(parts) < 2 or Path(name).is_absolute() or ".." in parts
                or Path(name).as_posix() != name or not CATEGORY_RE.fullmatch(parts[0])):
            raise ValueError(f"invalid archive manifest path: {name!r}")
        if not isinstance(seal, dict) or not isinstance(seal.get("sha256"), str):
            raise ValueError(f"invalid archive seal: {name}")
        if not re.fullmatch(r"[0-9a-f]{64}", seal["sha256"]):
            raise ValueError(f"invalid archive sha256: {name}")
    return files


def save_manifest(path: Path, files: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".manifest-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"files": dict(sorted(files.items()))}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def archive_baseline_errors(root: Path, files: dict[str, dict[str, str]]) -> list[str]:
    explicit_ref = os.environ.get("BW_ARCHIVE_BASE_REF")
    ref = explicit_ref if explicit_ref is not None else "HEAD"

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)

    try:
        top = git("rev-parse", "--show-toplevel")
    except FileNotFoundError:
        return ["archive baseline requires git"] if explicit_ref is not None else []
    if top.returncode:
        return ["archive baseline requires a Git worktree"] if explicit_ref is not None else []
    commit = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if commit.returncode:
        if explicit_ref is None and git("rev-parse", "--verify", "HEAD").returncode:
            return []  # No committed baseline yet; current seals are still checked.
        return [f"cannot read archive baseline {ref!r}: {commit.stderr.strip()}"]
    manifest = (root / "bywork/archived/manifest.json").relative_to(Path(top.stdout.strip()).resolve()).as_posix()
    present = git("ls-tree", "--name-only", commit.stdout.strip(), "--", manifest)
    if present.returncode:
        return [f"cannot inspect archive baseline {ref!r}: {present.stderr.strip()}"]
    if not present.stdout.strip():
        return []
    saved = git("show", f"{commit.stdout.strip()}:{manifest}")
    if saved.returncode:
        return [f"cannot read archive baseline {ref!r}: {saved.stderr.strip()}"]
    try:
        baseline = parse_manifest(saved.stdout)
    except ValueError as exc:
        return [f"invalid archive baseline {ref!r}: {exc}"]
    return [
        f"bywork/archived/{name}: committed archive seal changed or removed (baseline {ref})"
        for name, seal in baseline.items() if files.get(name) != seal
    ]


def check_archived(bywork: Path, root: Path, *, write_manifest: bool = False) -> tuple[list[str], int]:
    archived_dir = bywork / "archived"
    manifest_path = archived_dir / "manifest.json"
    try:
        manifest = parse_manifest(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    except ValueError as exc:
        return [f"{manifest_path.relative_to(root)}: invalid manifest ({exc})"], 0
    errors = archive_baseline_errors(root, manifest)
    actual_files: dict[str, Path] = {}
    for entry in sorted(archived_dir.iterdir()) if archived_dir.exists() else []:
        if entry.name.startswith(".") or entry.name == "manifest.json":
            continue
        if entry.name.upper() == "INDEX.MD":
            errors.append(f"{entry.relative_to(root)}: centralized INDEX.md is forbidden")
            continue
        if not entry.is_dir() or not CATEGORY_RE.fullmatch(entry.name):
            errors.append(f"{entry.relative_to(root)}: expected category directory under archived/")
            continue
        for f in sorted(entry.rglob("*")):
            if f.name.startswith("."):
                continue
            if f.name.upper() == "INDEX.MD" and f.parent == entry:
                errors.append(f"{f.relative_to(root)}: centralized INDEX.md is forbidden")
                continue
            if f.is_file():
                actual_files[f.relative_to(archived_dir).as_posix()] = f

    additions: dict[str, dict[str, str]] = {}
    for name, fpath in actual_files.items():
        actual_hash = sha256_file(fpath)
        if name in manifest:
            if manifest[name]["sha256"] != actual_hash:
                errors.append(f"bywork/archived/{name}: sha256 mismatch (archived files are immutable)")
        elif write_manifest:
            additions[name] = {"sha256": actual_hash, "archived": dt.date.today().isoformat()}
        else:
            errors.append(f"bywork/archived/{name}: unsealed file (missing from archived/manifest.json)")
    for name in manifest:
        if name not in actual_files:
            errors.append(f"bywork/archived/{name}: sealed file is missing")
    if write_manifest and not errors and additions:
        save_manifest(manifest_path, manifest | additions)
    return errors, len(actual_files)


def check_workspace(root: Path, *, write_manifest: bool = False) -> tuple[list[str], dict[str, int]]:
    bywork = root / "bywork"
    counts = {k: 0 for k in LIFECYCLES}
    if not bywork.is_dir():
        return [f"{bywork}: directory does not exist (run 'bw.py init --project .')"], counts

    errors: list[str] = []
    allowed_top = set(LIFECYCLES) | {"vision"}
    for entry in sorted(bywork.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.name.upper() == "INDEX.MD":
            errors.append(f"{entry.relative_to(root)}: centralized INDEX.md is forbidden")
            continue
        if entry.name not in allowed_top or not entry.is_dir():
            errors.append(
                f"{entry.relative_to(root)}: unexpected entry; only proposed/, implemented/, rejected/, archived/, and optional vision/ belong in bywork/"
            )

    for lifecycle in ACTIVE_LIFECYCLES:
        ldir = bywork / lifecycle
        if not ldir.exists():
            continue
        for cat in sorted(ldir.iterdir()):
            if cat.name.startswith("."):
                continue
            if cat.name.upper() == "INDEX.MD":
                errors.append(f"{cat.relative_to(root)}: centralized INDEX.md is forbidden")
                continue
            if not cat.is_dir() or not CATEGORY_RE.match(cat.name):
                errors.append(
                    f"{cat.relative_to(root)}: notes must live under '{lifecycle}/<category>/yyyy-mm-dd-topic.md'"
                )
                continue
            for note in sorted(cat.iterdir()):
                if note.name.startswith("."):
                    continue
                if note.name.upper() == "INDEX.MD":
                    errors.append(f"{note.relative_to(root)}: centralized INDEX.md is forbidden")
                    continue
                if not note.is_file() or not FILENAME_RE.match(note.name):
                    errors.append(
                        f"{note.relative_to(root)}: filename must match 'yyyy-mm-dd-topic.md'"
                    )
                    continue
                counts[lifecycle] += 1
                if lifecycle == "proposed":
                    errors.extend(check_proposed_note(note, root))
                elif lifecycle == "implemented":
                    errors.extend(check_implemented_note(note, root))
                elif lifecycle == "rejected":
                    errors.extend(check_rejected_note(note, root))

    arch_errors, arch_count = check_archived(bywork, root, write_manifest=write_manifest and not errors)
    errors.extend(arch_errors)
    counts["archived"] = arch_count
    return errors, counts


def resolve_note(bywork: Path, lifecycle: str, target: str, root: Path) -> Path | None:
    ldir = bywork / lifecycle
    if not ldir.is_dir() or ldir.is_symlink():
        return None
    candidates = [(root / target).resolve(), (bywork / target).resolve()]
    candidates.extend(
        note.resolve() for note in ldir.glob("*/*.md")
        if note.name == target or note.stem == target or note.stem.endswith(f"-{target}")
    )
    matches: set[Path] = set()
    for note in candidates:
        if not note.is_file() or not note.is_relative_to(ldir):
            continue
        parts = note.relative_to(ldir).parts
        if len(parts) == 2 and CATEGORY_RE.fullmatch(parts[0]) and FILENAME_RE.fullmatch(parts[1]):
            matches.add(note)
    return next(iter(matches)) if len(matches) == 1 else None


def find_inbound_links(bywork: Path, old_path: Path, root: Path) -> list[str]:
    inbound: list[str] = []
    for lc in ACTIVE_LIFECYCLES:
        ldir = bywork / lc
        if not ldir.is_dir():
            continue
        for note in sorted(ldir.rglob("*.md")):
            if note.resolve() == old_path.resolve():
                continue
            for idx, line in enumerate(strip_fenced_and_comments(note.read_text(encoding="utf-8")), 1):
                for _, _, href in markdown_links(line):
                    target = local_link_path(href)
                    if target and (note.parent / target).resolve() == old_path.resolve():
                        inbound.append(f"{note.relative_to(root).as_posix()}:{idx}")
    return inbound

def molt_proposed_to_implemented(body: str) -> str:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    replacements = {"proposal": "决策", "risks": "收益和代价", "acceptance": "验证"}
    out: list[str] = []
    for line, visible in zip(lines, strip_fenced_and_comments(body)):
        if visible.strip() == "Status: proposed":
            line = "Status: implemented"
        elif visible.startswith("## "):
            title = normalize_heading(visible[3:])
            for key, replacement in replacements.items():
                if title in {a.lower() for a in SECTION_ALIASES[key]}:
                    suffix = re.search(r"\s*[（(][^）)]*[）)]\s*$", line)
                    line = "## " + replacement + (suffix[0] if suffix else "")
                    break
        out.append(line)
    return "\n".join(out).strip() + "\n"

def cmd_init(root: Path) -> int:
    bywork = root / "bywork"
    legacy = [name for name in ("work", "memory") if (bywork / name).exists()]
    if legacy:
        print(f"migration required: legacy {', '.join(legacy)} preserved; init only creates directories. "
              "Follow references/onboard.md before running check.")
    print(f"Initialized ByWork workspace at {bywork}")
    for name in LIFECYCLES:
        path = bywork / name
        existed = path.exists()
        path.mkdir(parents=True, exist_ok=True)
        state = "= kept" if existed else "+ created"
        print(f"  {state} {path.relative_to(root)}")
    return 0


def write_new_note(path: Path, content: bytes) -> None:
    if path.resolve() != path:
        raise ValueError(f"destination must not traverse a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def cmd_complete(root: Path, target: str) -> int:
    bywork = root / "bywork"
    note = resolve_note(bywork, "proposed", target, root)
    if note is None:
        print(f"error: proposed note {target!r} not found or ambiguous under {bywork / 'proposed'}")
        return 1
    errors = check_proposed_note(note, root, require_complete_ready=True)
    _, body, _ = parse_frontmatter(note.read_text(encoding="utf-8"))
    impl_body = molt_proposed_to_implemented(body)
    dst = bywork / "implemented" / note.parent.name / note.name
    impl_body = rebase_links(impl_body, note, dst)
    errors.extend(check_implemented_note(dst, root, text=impl_body))
    if errors:
        print("\n".join(errors))
        return 1
    inbound = find_inbound_links(bywork, note, root)
    write_new_note(dst, impl_body.encode("utf-8"))
    note.unlink()
    print(f"completed {dst.relative_to(root)}")
    if inbound:
        print(f"warning: update active-note inbound links still pointing to old path: {', '.join(inbound)}")
    return 0


def cmd_reject(root: Path, target: str, reason: str) -> int:
    if not reason.strip() or len(reason.strip().splitlines()) != 1:
        print("error: 'reject' requires a non-empty, single-line --reason")
        return 1
    bywork = root / "bywork"
    note = resolve_note(bywork, "proposed", target, root)
    if note is None:
        print(f"error: proposed note {target!r} not found or ambiguous under {bywork / 'proposed'}")
        return 1
    errors = check_proposed_note(note, root)
    if errors:
        print("\n".join(errors))
        return 1
    inbound = find_inbound_links(bywork, note, root)
    _, body, _ = parse_frontmatter(note.read_text(encoding="utf-8"))
    out = [f"Status: rejected — {reason.strip()}" if visible.strip() == "Status: proposed" else line
           for line, visible in zip(body.split("\n"), strip_fenced_and_comments(body))]
    dst = bywork / "rejected" / note.parent.name / note.name
    rejected_body = rebase_links("\n".join(out).strip() + "\n", note, dst)
    errors = check_relative_links(dst, strip_fenced_and_comments(rejected_body), root)
    if errors:
        print("\n".join(errors))
        return 1
    write_new_note(dst, rejected_body.encode("utf-8"))
    note.unlink()
    print(f"rejected {dst.relative_to(root)}")
    if inbound:
        print(f"warning: update active-note inbound links still pointing to old path: {', '.join(inbound)}")
    return 0


def cmd_archive(root: Path, target: str, superseded_by: str | None) -> int:
    bywork = root / "bywork"
    note = resolve_note(bywork, "implemented", target, root)
    if note is None:
        print(f"error: implemented note {target!r} not found or ambiguous under {bywork / 'implemented'}")
        return 1
    errors = check_implemented_note(note, root)
    archive_errors, _ = check_archived(bywork, root)
    errors.extend(archive_errors)
    sup = None
    if superseded_by is not None:
        sup = resolve_note(bywork, "implemented", superseded_by, root) or resolve_note(bywork, "proposed", superseded_by, root)
        if sup is None or sup == note:
            errors.append(f"invalid superseded-by note: {superseded_by!r}")
    raw = note.read_bytes()
    visible = strip_fenced_and_comments(raw.decode("utf-8"))
    if any(line.startswith("Archived:") for line in visible):
        errors.append(f"{note.relative_to(root)}: already has an Archived marker")
    if errors:
        print("\n".join(errors))
        return 1

    manifest_path = bywork / "archived/manifest.json"
    files = parse_manifest(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    inbound = find_inbound_links(bywork, note, root)
    today = dt.date.today().isoformat()
    lines = raw.splitlines(keepends=True)
    status_idx = next(i for i, line in enumerate(visible) if line.strip() == "Status: implemented")
    newline = b"\r\n" if lines[status_idx].endswith(b"\r\n") else b"\n"
    lines.insert(status_idx + 1, f"Archived: {today}".encode("utf-8") + newline)
    dst = bywork / "archived" / note.parent.name / note.name
    write_new_note(dst, b"".join(lines))
    key = dst.relative_to(bywork / "archived").as_posix()
    files[key] = {"sha256": sha256_file(dst), "archived": today}
    save_manifest(manifest_path, files)
    if sup is not None:
        rel_link = os.path.relpath(dst, sup.parent).replace(os.sep, "/")
        sup_text = sup.read_text(encoding="utf-8").rstrip()
        if rel_link not in sup_text:
            sup.write_text(sup_text + f"\n\n历史替代快照见 [`{dst.name}`]({rel_link})。\n", encoding="utf-8")
    note.unlink()
    print(f"archived {dst.relative_to(root)}")
    if inbound:
        print(f"warning: update active-note inbound links still pointing to old path: {', '.join(inbound)}")
    return 0


def cmd_anchors(root: Path, code_root: Path) -> int:
    bywork = root / "bywork"
    anchor_hits: dict[str, list[str]] = {}
    dangling: list[str] = []
    without_path: list[str] = []
    scan_errors: list[str] = []

    def walk(cur: Path, depth: int) -> None:
        if depth > 12:
            scan_errors.append(f"{cur}: depth limit reached")
            return
        try:
            entries = sorted(cur.iterdir())
        except OSError as exc:
            scan_errors.append(f"{cur}: {exc}")
            return
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_symlink():
                scan_errors.append(f"{entry}: symlink skipped")
                continue
            if entry.is_dir():
                if entry.name not in SKIP_DIR:
                    walk(entry, depth + 1)
                continue
            if entry.suffix not in CODE_EXT:
                continue
            rel = entry.relative_to(code_root).as_posix()
            try:
                lines = entry.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                scan_errors.append(f"{entry}: {exc}")
                continue
            for idx, line in enumerate(lines, 1):
                if not ANCHOR_RE.search(line):
                    continue
                matches = list(ANCHOR_PATH_RE.finditer(line))
                if not matches:
                    without_path.append(f"{rel}:{idx} — Note anchor without a bywork/ path")
                for match in matches:
                    key = match.group(1).split("#", 1)[0].lstrip("./")
                    anchor_hits.setdefault(key, []).append(f"{rel}:{idx}")
                    if not (bywork / key).is_file():
                        dangling.append(f"{rel}:{idx} — bywork/{key} does not exist")

    walk(code_root, 0)

    impl_notes: list[str] = []
    impl_dir = bywork / "implemented"
    if impl_dir.is_dir():
        for f in sorted(impl_dir.rglob("*.md")):
            impl_notes.append(f.relative_to(bywork).as_posix())

    unanchored = [rel for rel in impl_notes if rel not in anchor_hits]
    total_hits = sum(len(v) for v in anchor_hits.values())
    print(f"scanned: {code_root}")
    print("format: standalone comment lines beginning with //, #, /*, *, or <!-- followed by Note:")
    if scan_errors:
        print("[scan incomplete]")
        for error in scan_errors:
            print(f"  - {error}")
    print(f"anchors found: {total_hits} across {len(anchor_hits)} note(s)")
    if without_path:
        print(f"\n[anchors without note path] {len(without_path)}")
        for r in without_path[:20]:
            print(f"  - {r}")
    if dangling:
        print(f"\n[dangling anchors] {len(dangling)}")
        for d in dangling[:20]:
            print(f"  - {d}")
    else:
        print("\n[dangling anchors] undetermined (scan incomplete)" if scan_errors else "\n[dangling anchors] none")
    print(f"\n[implemented notes without any code anchor] {len(unanchored)} of {len(impl_notes)}")
    for u in unanchored[:20]:
        print(f"  - {u}")
    return 0


def parse_note_for_board(raw: str, rel_path: str, note_ids: dict[str, str]) -> dict[str, object]:
    fields, body, _ = parse_frontmatter(raw)
    visible = strip_fenced_and_comments(body)
    lifecycle, cls, filename = rel_path.split("/")
    slug = filename.removesuffix(".md")
    title = next((re.sub(r"^#\s+(?:Agent Note[^:：]*[:：]\s*)?", "", line).strip()
                  for line in visible if line.startswith("# ")), slug)
    sections = section_bodies(body)

    def section(*keys: str) -> str:
        aliases = {a.lower() for key in keys for a in SECTION_ALIASES[key]}
        return "\n\n".join(content for heading, content in sections if normalize_heading(heading) in aliases)

    main_aliases = {a.lower() for key in ("problem", "decision", "proposal", "alternatives", "consequences", "risks")
                    for a in SECTION_ALIASES[key]}
    links: list[str] = []
    for line in visible:
        for _, _, href in markdown_links(line):
            path = local_link_path(href)
            if not path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path), path))
            if target in note_ids and target != rel_path and target not in links:
                links.append(target)
    return {
        "id": rel_path, "slug": slug, "lifecycle": lifecycle, "cls": cls,
        "date": slug[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", slug) else "",
        "title": title, "status": lifecycle,
        "checkpoint": {key: fields.get(key, "") for key in WORK_FIELDS} if fields else {},
        "problem": section("problem"), "decision": section("decision", "proposal"),
        "alternatives": section("alternatives"), "consequences": section("consequences", "risks"),
        "extraSections": [{"title": heading, "body": content} for heading, content in sections
                          if normalize_heading(heading) not in main_aliases],
        "outLinks": links, "rawBody": raw,
    }

def check_target_safety(target_path: Path, force: bool) -> bool:
    if target_path.exists() and not force:
        try:
            existing = target_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            print(f"error: cannot verify existing board {target_path}: {exc} (pass --force to overwrite)")
            return False
        if 'content="agent-notes-board"' not in existing:
            print(f"error: target file exists ({target_path}) and is not a generated board file (pass --force to overwrite)")
            return False
    return True

def cmd_board(root: Path, mode: str, out_file: str | None, title: str, metadata_only: bool, force: bool) -> int:
    template_path = Path(__file__).resolve().parent.parent / "assets/board.html"
    if not template_path.is_file():
        print(f"error: board template not found at {template_path}")
        return 1
    template = template_path.read_text(encoding="utf-8")
    template = template.replace('id="brand-project-title">工程决策看板<', f'id="brand-project-title">{html.escape(title)}<')

    if mode == "init":
        out_path = (root / (out_file or "board.html")).resolve()
        if not check_target_safety(out_path, force):
            return 1
        out_path.write_text(template, encoding="utf-8")
        print(f"generated lightweight board: {out_path}")
        return 0

    bywork = root / "bywork"
    if not bywork.is_dir():
        print(f"error: bywork directory not found at {bywork}")
        return 1
    out_path = (root / (out_file or "demo.html")).resolve()
    if not check_target_safety(out_path, force):
        return 1

    if bywork.is_symlink():
        raise ValueError(f"board input must not be a symlink: {bywork}")
    note_files: dict[str, Path] = {}
    for lc in LIFECYCLES:
        ldir = bywork / lc
        if ldir.is_symlink():
            raise ValueError(f"board input must not be a symlink: {ldir}")
        if not ldir.is_dir():
            continue
        for cat in sorted(ldir.iterdir()):
            if not CATEGORY_RE.fullmatch(cat.name):
                continue
            if cat.is_symlink():
                raise ValueError(f"board input must not be a symlink: {cat}")
            if not cat.is_dir():
                continue
            for note in sorted(cat.iterdir()):
                if not FILENAME_RE.fullmatch(note.name):
                    continue
                if note.is_symlink():
                    raise ValueError(f"board input must not be a symlink: {note}")
                if note.is_file():
                    note_files[note.relative_to(bywork).as_posix()] = note
    slug_to_id = {rel: rel for rel in note_files}

    notes = []
    for rel, fpath in note_files.items():
        raw = fpath.read_text(encoding="utf-8")
        item = parse_note_for_board(raw, rel, slug_to_id)
        if metadata_only:
            item["problem"] = "[正文已脱敏]"
            item["decision"] = "[正文已脱敏]"
            item["alternatives"] = ""
            item["consequences"] = ""
            item["checkpoint"] = {}
            item["extraSections"] = []
            item["rawBody"] = f"# Agent Note: {item['title']}\n\nStatus: {item['status']}\n"
        notes.append(item)

    json_safe = json.dumps(notes, ensure_ascii=False).replace("<", "\\u003c")
    template = template.replace("window.__INLINE_DATA__ = null;", f"window.__INLINE_DATA__ = {json_safe};")
    out_path.write_text(template, encoding="utf-8")
    print(f"bundled {len(notes)} note(s) into {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bw.py",
        description="ByWork 统一命令行工具：管理 bywork/ 四态工作区（proposed / implemented / rejected / archived）与决策看板。",
    )
    parser.add_argument("--project", default=".", help="项目根目录（默认当前目录 '.'）")

    sub = parser.add_subparsers(dest="cmd", metavar="<subcommand>")

    p_init = sub.add_parser("init", help="初始化或保留 bywork/{proposed,implemented,rejected,archived} 四目录")
    p_init.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")

    p_check = sub.add_parser("check", help="校验四态目录结构、禁 INDEX.md、必填节与验收表、相对链接死链及归档 SHA-256 封印")
    p_check.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")
    p_check.add_argument("--write-manifest", action="store_true", help="校验既有归档封印并为未封印归档文件补齐 manifest.json")

    p_comp = sub.add_parser("complete", help="核验验收表全通过且 proof_gap 为空后，将 proposed 笔记蜕皮移入 implemented/")
    p_comp.add_argument("note", help="proposed 笔记文件名、slug 或相对路径")
    p_comp.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")

    p_rej = sub.add_parser("reject", help="将 proposed 笔记写入一句话原因并冻结移入 rejected/")
    p_rej.add_argument("note", help="proposed 笔记文件名、slug 或相对路径")
    p_rej.add_argument("--reason", required=True, help="一句话否决原因（写入 Status: rejected — <原因>）")
    p_rej.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")

    p_arch = sub.add_parser("archive", help="为 implemented 笔记插入 Archived 日期、移入 archived/ 并写入 manifest.json SHA-256 封印")
    p_arch.add_argument("note", help="implemented 笔记文件名、slug 或相对路径")
    p_arch.add_argument("--superseded-by", metavar="NEW_NOTE", help="在新笔记末尾追加指向该归档快照的相对链接")
    p_arch.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")

    p_anc = sub.add_parser("anchors", help="扫描源码中的 '// Note: ... 见 bywork/...' 反向锚点并输出软体检报告（退出码恒 0）")
    p_anc.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")
    p_anc.add_argument("--code-root", default=None, help="要扫描的源码目录（默认同 --project）")

    p_board = sub.add_parser("board", help="生成 ~70KB 本地热同步看板 HTML (--init) 或内联全量数据的离线看板 (--bundle)")
    p_board.add_argument("--project", default=argparse.SUPPRESS, help="项目根目录")
    p_board.add_argument("--init", nargs="?", const="board.html", metavar="OUT_HTML", help="生成轻量本地热同步看板（默认 board.html）")
    p_board.add_argument("--bundle", nargs="?", const="demo.html", metavar="OUT_HTML", help="打包内联 bywork/ 数据的单文件看板（默认 demo.html）")
    p_board.add_argument("--title", default="工程决策看板", help="看板标题")
    p_board.add_argument("--metadata-only", action="store_true", help="打包时剥离正文，仅保留标题与拓扑关系")
    p_board.add_argument("--force", "-f", action="store_true", help="允许覆盖非看板生成的同名 HTML 文件")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = Path(args.project).resolve()

    cmd = args.cmd or "check"
    if cmd == "init":
        return cmd_init(root)
    if cmd == "complete":
        return cmd_complete(root, args.note)
    if cmd == "reject":
        return cmd_reject(root, args.note, args.reason)
    if cmd == "archive":
        return cmd_archive(root, args.note, args.superseded_by)
    if cmd == "anchors":
        code_root = Path(args.code_root).resolve() if args.code_root else root
        return cmd_anchors(root, code_root)
    if cmd == "board":
        mode = "bundle" if args.bundle and not args.init else "init"
        out_file = args.bundle if mode == "bundle" else args.init
        return cmd_board(root, mode, out_file, args.title, args.metadata_only, args.force)

    errors, counts = check_workspace(root, write_manifest=getattr(args, "write_manifest", False))
    if errors:
        for err in errors:
            print(err)
        return 1
    summary = ", ".join(f"{k}={counts[k]}" for k in LIFECYCLES)
    print(f"ByWork workspace consistent ({summary})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
