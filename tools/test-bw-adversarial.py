#!/usr/bin/env python3
"""Regression checks for the CLI failures found in the 2.0.0 adversarial review."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fixtures", ROOT / "tools/check-skill-scripts.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
VALID = fixtures.VALID_PROPOSED
NAME = "2026-11-20-review.md"
TABLE = VALID.split("## 验收标准\n\n", 1)[1].split("\n## 风险与代价", 1)[0].strip()


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_bw("init")

    def run_bw(self, *args, success=True):
        code, output = fixtures.run_bw(self.root, *args)
        self.assertEqual(code == 0, success, output)
        return output

    def note(self, text=VALID, name=NAME):
        return fixtures.write_proposed(self.root, name, text)

    def test_existing_non_utf8_board_survives_both_modes(self):
        target = self.root / "existing.html"
        original = "已有文件，须保留".encode("gbk")
        for mode in ("--init", "--bundle"):
            with self.subTest(mode=mode):
                target.write_bytes(original)
                self.run_bw("board", mode, target.name, success=False)
                self.assertEqual(target.read_bytes(), original)
                self.run_bw("board", mode, target.name, "--force")
                self.assertIn('content="agent-notes-board"', target.read_text())

    def test_acceptance_is_unique_and_bound_to_its_section(self):
        failed = TABLE.replace("| 通过 |", "| 未通过 |")
        variants = {
            "second table": VALID.replace(TABLE, TABLE + "\n\n" + failed),
            "duplicate section": VALID + "\n## 验收标准\n\n" + failed + "\n",
            "unrelated example": VALID.replace("## 提案\n", "## 提案\n\n" + TABLE + "\n").replace("## 验收标准\n\n" + TABLE, "## 验收标准\n\n" + failed),
            "no acceptance table": VALID.replace("## 提案\n", "## 提案\n\n" + TABLE + "\n").replace("## 验收标准\n\n" + TABLE, "## 验收标准\n\n未填写"),
        }
        for label, text in variants.items():
            with self.subTest(label=label):
                source = self.note(text)
                self.run_bw("complete", NAME, success=False)
                self.assertEqual(source.read_text(), text)
                self.assertFalse((self.root / "bywork/implemented/feature" / NAME).exists())

    def test_fences_preserve_literals_and_cannot_supply_evidence(self):
        for fence in ("~~~", "`" * 4):
            for command, dest in (("complete", "implemented"), ("reject", "rejected")):
                with self.subTest(fence=fence, command=command):
                    example = "\n" + fence + "markdown\n```\n## 提案\nStatus: proposed\n" + TABLE + "\n" + fence + "\n"
                    self.note(VALID + example)
                    args = [command, NAME] + (["--reason", "取消"] if command == "reject" else [])
                    self.run_bw(*args)
                    target = self.root / "bywork" / dest / "feature" / NAME
                    self.assertIn(example.strip(), target.read_text())
                    target.unlink()
                    self.note(VALID.replace(TABLE, "待验证") + example)
                    self.run_bw("complete", NAME, success=False)

    def test_moves_preserve_destinations_and_reference_titles(self):
        peer = "2026-11-20-peer.md"
        original = self.note(name=peer)
        for command, dest in (("complete", "implemented"), ("reject", "rejected")):
            with self.subTest(command=command):
                decoy = self.root / "bywork" / dest / "feature" / peer
                decoy.parent.mkdir(parents=True, exist_ok=True)
                decoy.write_text("different record")
                links = f'\n[peer]({peer}#part "背景")\n[ref][source]\n[source]: <{peer}> "依据"\n'
                self.note(VALID + links)
                self.run_bw(command, NAME, *(["--reason", "取消"] if command == "reject" else []))
                text = (decoy.parent / NAME).read_text()
                expected = "../../proposed/feature/" + peer
                self.assertIn(f'({expected}#part "背景")', text)
                self.assertIn(f'<{expected}> "依据"', text)
                self.assertEqual(original.read_text(), VALID)
                decoy.unlink()
                self.run_bw("check")

    def test_move_links_before_destination_category_exists(self):
        peer = "2026-11-20-peer.md"
        self.note(name=peer)
        for command, dest in (("complete", "implemented"), ("reject", "rejected")):
            with self.subTest(command=command):
                self.assertFalse((self.root / "bywork" / dest / "feature").exists())
                self.note(VALID + f"\n[peer]({peer})\n")
                self.run_bw(command, NAME, *(["--reason", "取消"] if command == "reject" else []))
                self.run_bw("check")

    def test_moves_allow_self_links_but_reject_missing_other_targets(self):
        for command, dest in (("complete", "implemented"), ("reject", "rejected")):
            with self.subTest(command=command):
                args = (command, NAME, *(["--reason", "取消"] if command == "reject" else []))
                source = self.note(VALID + f"\n[self]({NAME}#evidence)\n[missing](missing.md)\n")
                before = source.read_bytes()
                self.run_bw(*args, success=False)
                self.assertEqual(source.read_bytes(), before)
                source.write_text(VALID + f"\n[self]({NAME}#evidence)\n")
                self.run_bw(*args)
                self.run_bw("check")
                self.assertIn(f"({NAME}#evidence)", (self.root / "bywork" / dest / "feature" / NAME).read_text())

    def test_init_reports_legacy_layout_without_changing_originals(self):
        originals = {"work/active/index.md": "unfinished work\n", "memory/limits.md": "durable constraint\n"}
        for name, text in originals.items():
            file = self.root / "bywork" / name
            file.parent.mkdir(parents=True)
            file.write_text(text)
        output = self.run_bw("init")
        self.assertIn("migration required", output)
        self.assertIn("references/onboard.md", output)
        for name, text in originals.items():
            self.assertEqual((self.root / "bywork" / name).read_text(), text)
        self.run_bw("check", success=False)

    def test_reference_links_are_checked_and_reported(self):
        source = self.note()
        self.run_bw("complete", NAME)
        self.note(VALID + f'\n[earlier][old]\n[old]: ../../implemented/feature/{NAME} "旧依据"\n', "2026-11-20-caller.md")
        self.run_bw("check")
        self.assertIn("2026-11-20-caller.md", self.run_bw("archive", NAME))
        self.assertIn("broken relative link", self.run_bw("check", success=False))

    def test_heading_aliases_convert_with_suffixes(self):
        self.note(VALID.replace("## 提案", "## proposal（当前决定）").replace("## 验收标准", "## Acceptance criteria (本轮)").replace("## 风险与代价", "## risks（影响）"))
        self.run_bw("check")
        self.run_bw("complete", NAME)
        self.run_bw("check")
        text = (self.root / "bywork/implemented/feature" / NAME).read_text()
        for heading in ("## 决策（当前决定）", "## 验证 (本轮)", "## 收益和代价（影响）"):
            self.assertIn(heading, text)

    def test_board_rejects_symlink_inputs_before_overwrite(self):
        self.note()
        sentinel = "SYNTHETIC_SECRET_OUTSIDE_NOTE_ROOT"
        outside = self.root / "outside.md"
        outside.write_text(VALID + sentinel)
        out = self.root / "bundle.html"
        for level in ("file", "category", "lifecycle", "root"):
            with self.subTest(level=level):
                if level == "file":
                    link = self.root / "bywork/proposed/feature/2026-11-20-secret.md"
                    target = outside
                else:
                    link = self.root / {"category": "bywork/proposed/feature", "lifecycle": "bywork/proposed", "root": "bywork"}[level]
                    target = self.root / ("saved-" + level)
                    link.rename(target)
                link.symlink_to(target, target_is_directory=level != "file")
                out.write_text('content="agent-notes-board" existing')
                self.run_bw("board", "--bundle", out.name, success=False)
                self.assertEqual(out.read_text(), 'content="agent-notes-board" existing')
                link.unlink()
                if level != "file":
                    target.rename(link)

    def test_board_escapes_title_and_redacts_all_content_fields(self):
        self.note(VALID.replace("must_hold: 幂等与错误处理", "must_hold: PRIVATE_CHECKPOINT") + "\n## 补充\nPRIVATE_EXTRA\n")
        title = '<img src=x onerror="globalThis.XSS=7">'
        for mode in ("--init", "--bundle"):
            self.run_bw("board", mode, "board.html", "--title", title, "--metadata-only")
            text = (self.root / "board.html").read_text()
            self.assertNotIn(title, text)
            self.assertIn("&lt;img", text)
            self.assertNotIn("PRIVATE_", text)

    def test_anchors_reports_all_refs_and_incomplete_scans(self):
        source = self.root / "code.js"
        source.write_text('const s = "// Note: bywork/implemented/feature/fake.md";\n// Note: bywork/implemented/feature/first.md and bywork/implemented/feature/second.md\n')
        output = self.run_bw("anchors")
        self.assertIn("anchors found: 2", output)
        self.assertIn("second.md does not exist", output)
        self.assertNotIn("fake.md", output)
        output = self.run_bw("anchors", "--code-root", str(self.root / "missing"))
        self.assertIn("[scan incomplete]", output)
        self.assertNotIn("[dangling anchors] none", output)
        source.write_bytes(b"\xff")
        self.assertIn("[scan incomplete]", self.run_bw("anchors"))


class MaintenanceTests(unittest.TestCase):
    def test_durable_memory_acceptance_is_layout_neutral(self):
        case = ROOT / "tools/evaluation/cases/memory-selection"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(case / "project/config.json", root / "config.json")
            command = [sys.executable, str(case / "acceptance.py"), str(root), "1"]
            def check(expected):
                proc = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(proc.returncode == 0, expected, proc.stdout + proc.stderr)
            check(False)
            for directory in ("memory", "implemented/process", "rejected/process"):
                path = root / "bywork" / directory / "2026-11-20-decision.md"
                path.parent.mkdir(parents=True)
                path.write_text("The durable decision and its rationale")
                check(True)
                path.unlink()
            path.write_text("decision")
            (root / "config.json").write_text("{}")
            check(False)

    def test_ab_driver_reports_failures_and_passes_explicit_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "skill source"
            (source / "skills/bw").mkdir(parents=True)
            (source / "skills/bw/SKILL.md").write_text("fixture")
            control, skill, runs = (root / name for name in ("control case", "skill case", "runs"))
            control.mkdir(); skill.mkdir()
            for arm in ("control", "skill"):
                for index in range(1, 4):
                    run = runs / f"ab-{arm}-{index:02d}"
                    run.mkdir(parents=True)
                    (run / "seed.json").write_text("{}")
            fake = root / "python3"
            fake.write_text(f"#!{sys.executable}\n" +
                            "import json, os, sys\n"
                            "with open(os.environ['BW_TEST_LOG'], 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                            "sys.exit(int(os.environ['BW_TEST_EXIT']))\n")
            fake.chmod(0o755)
            log = root / "calls.jsonl"
            env = {**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"],
                   "BW_TEST_LOG": str(log)}
            command = ["bash", str(ROOT / "tools/evaluation/ab_driver.sh"), str(runs), str(source), str(control), str(skill), "provider/model"]
            for failure in ("42", "0"):
                env["BW_TEST_EXIT"] = failure
                log.write_text("")
                proc = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1 if failure == "42" else 0, proc.stderr)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(len(calls), 6)
                for i, args in enumerate(calls):
                    self.assertEqual(args[args.index("--case") + 1], str(control if i % 2 == 0 else skill))
                    self.assertEqual("--no-skill" in args, i % 2 == 0)
                    if i % 2:
                        self.assertEqual(args[args.index("--source") + 1], str(source))
                if failure == "42":
                    self.assertIn("6 of six runs failed", proc.stderr)
                    self.assertNotIn("All six runs passed", proc.stdout)
            (runs / "ab-skill-03/seed.json").unlink()
            log.write_text("")
            proc = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(log.read_text(), "")


if __name__ == "__main__":
    unittest.main()
