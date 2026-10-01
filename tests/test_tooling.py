#!/usr/bin/env python3
"""End-to-end smoke tests for the course scaffolder, builder, and validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"


def run_script(name: str, *args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        check=check,
        capture_output=True,
        text=True,
    )


def module_html(number: int, title: str, include_course_interactions: bool) -> str:
    extra = ""
    if include_course_interactions:
        extra = '''
    <div class="component-chat" aria-label="Conversation between components">
      <div class="chat-message" data-speaker="Caller">Please add one.</div>
      <div class="chat-message" data-speaker="Function">I will return the transformed value.</div>
      <button type="button" class="replay-chat">Replay conversation</button>
    </div>
    <div class="data-flow" aria-label="Function data flow">
      <button type="button" class="flow-step is-active" data-detail="A value enters.">1. Input</button>
      <button type="button" class="flow-step" data-detail="The function adds one.">2. Transform</button>
      <p class="flow-detail" aria-live="polite">A value enters.</p>
    </div>'''
    return f'''<section class="course-module" id="module-{number:02d}" data-title="{title}">
  <div class="screen hero-screen" data-number="{number:02d}">
    <p class="eyebrow">Module {number}</p><h2>{title}</h2><p class="lede">Trace one real function.</p>
  </div>
  <div class="screen">
    <h3>The transformation</h3>
    <p>A <dfn data-definition="A reusable named block of behavior.">function</dfn> receives a value.</p>
    <figure class="code-translation" data-source="app.py" data-lines="1-2">
      <div class="code-pane"><p class="pane-label source-label"></p><pre><code>def add_one(value):
    return value + 1</code></pre></div>
      <figcaption><p class="pane-label">Plain English</p><p>Return the input plus one.</p></figcaption>
    </figure>{extra}
  </div>
  <div class="screen">
    <div class="quiz" data-explanation="The function contains the transformation.">
      <p class="quiz-kicker">Try it</p><h3>Where would you change the arithmetic?</h3>
      <div class="quiz-options">
        <button type="button" data-correct="true">The function body</button>
        <button type="button">The page color</button>
      </div>
      <p class="quiz-feedback" aria-live="polite"></p>
    </div>
  </div>
</section>
'''


class ToolingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.course = self.root / "course"
        self.source.mkdir()
        (self.source / "app.py").write_text("def add_one(value):\n    return value + 1\n", encoding="utf-8")
        run_script(
            "scaffold_course.py",
            self.course,
            "--title",
            "A Tiny Course",
            "--subtitle",
            "Understand one transformation",
            "--source-root",
            self.source,
            "--module",
            "Start",
            "--module",
            "Trace",
            "--module",
            "Change",
        )
        config = json.loads((self.course / "course.json").read_text(encoding="utf-8"))
        for number, module in enumerate(config["modules"], start=1):
            (self.course / "modules" / module["file"]).write_text(
                module_html(number, module["title"], number == 1),
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def accept_baseline(self) -> None:
        run_script("update_course.py", self.course, "--source-root", self.source, "--accept-baseline")

    def test_build_and_validate(self) -> None:
        run_script("build_course.py", self.course)
        result = run_script("validate_course.py", self.course, "--source-root", self.source)
        self.assertIn("Validation passed", result.stdout)
        built = (self.course / "index.html").read_text(encoding="utf-8")
        self.assertIn("A Tiny Course", built)
        self.assertIn("const modules", built)
        self.assertNotIn("https://", built)

    def test_validator_rejects_modified_excerpt(self) -> None:
        first_module = next((self.course / "modules").glob("01-*.html"))
        content = first_module.read_text(encoding="utf-8").replace("return value + 1", "return value + 2")
        first_module.write_text(content, encoding="utf-8")
        run_script("build_course.py", self.course)
        result = run_script(
            "validate_course.py",
            self.course,
            "--source-root",
            self.source,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code excerpt differs", result.stderr)

    def test_literal_template_tokens_survive_build_and_built_tampering_fails(self) -> None:
        source = 'def add_one(value):\n    return "{{JS}} and {{CSS}}"\n'
        (self.source / "app.py").write_text(source, encoding="utf-8")
        for file in (self.course / "modules").glob("*.html"):
            file.write_text(file.read_text().replace('return value + 1', 'return "{{JS}} and {{CSS}}"'), encoding="utf-8")
        run_script("build_course.py", self.course)
        run_script("validate_course.py", self.course)
        index = self.course / "index.html"
        built = index.read_text()
        self.assertEqual(built.count('return "{{JS}} and {{CSS}}"'), 3)
        index.write_text(built.replace('return "{{JS}} and {{CSS}}"', 'return "fabricated"', 1))
        result = run_script("validate_course.py", self.course, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("displayed citations differ", result.stderr)

    def test_incremental_update_rebases_unchanged_excerpts(self) -> None:
        self.accept_baseline()
        (self.source / "app.py").write_text(
            "# A new comment moves the function.\ndef add_one(value):\n    return value + 1\n",
            encoding="utf-8",
        )
        result = run_script(
            "update_course.py",
            self.course,
            "--source-root",
            self.source,
            "--apply-safe-rebases",
        )
        self.assertIn("Applied 3 safe line-reference rebase", result.stdout)
        report = json.loads((self.course / "course-update-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["rebase-only"], 3)
        self.assertEqual(report["summary"]["safeRebasesApplied"], 3)
        for module_file in (self.course / "modules").glob("*.html"):
            self.assertIn('data-lines="2-3"', module_file.read_text(encoding="utf-8"))
        run_script("build_course.py", self.course)
        run_script("validate_course.py", self.course, "--source-root", self.source)
        self.accept_baseline()
        run_script("update_course.py", self.course, "--source-root", self.source)
        clean_report = json.loads(
            (self.course / "course-update-report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(clean_report["summary"]["changedFiles"], 0)
        self.assertEqual(clean_report["summary"]["unchanged"], 3)

    def test_incremental_update_marks_semantic_excerpt_changes_for_refresh(self) -> None:
        self.accept_baseline()
        (self.source / "app.py").write_text(
            "def add_one(value):\n    return value + 2\n",
            encoding="utf-8",
        )
        run_script("update_course.py", self.course, "--source-root", self.source)
        report = json.loads((self.course / "course-update-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["refresh"], 3)
        self.assertTrue(
            all(module["citations"][0]["status"] == "changed" for module in report["modules"])
        )

    def test_incremental_update_maps_explicit_dependency_to_one_module(self) -> None:
        (self.source / "support.json").write_text('{"mode": "old"}\n', encoding="utf-8")
        config_path = self.course / "course.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["modules"][1]["dependsOn"] = ["support.json"]
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self.accept_baseline()
        (self.source / "support.json").write_text('{"mode": "new"}\n', encoding="utf-8")
        run_script("update_course.py", self.course, "--source-root", self.source)
        report = json.loads((self.course / "course-update-report.json").read_text(encoding="utf-8"))
        statuses = {module["id"]: module["status"] for module in report["modules"]}
        self.assertEqual(statuses["module-01"], "unchanged")
        self.assertEqual(statuses["module-02"], "review")
        self.assertEqual(statuses["module-03"], "unchanged")
        self.assertEqual(report["summary"]["unmappedFiles"], 0)

    def test_incremental_update_keeps_unmapped_change_out_of_modules(self) -> None:
        self.accept_baseline()
        (self.source / "unrelated.txt").write_text("not part of the lesson\n", encoding="utf-8")
        run_script("update_course.py", self.course, "--source-root", self.source)
        report = json.loads((self.course / "course-update-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["unchanged"], 3)
        self.assertEqual(report["summary"]["unmappedFiles"], 1)
        self.assertEqual(report["unmappedChanges"][0]["path"], "unrelated.txt")


if __name__ == "__main__":
    unittest.main()
