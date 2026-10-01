#!/usr/bin/env python3
"""Validate course structure and compare cited excerpts with source files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath


def class_set(attrs: dict[str, str | None]) -> set[str]:
    return set((attrs.get("class") or "").split())


@dataclass
class CodeCitation:
    source: str
    lines: str
    chunks: list[str] = field(default_factory=list)

    @property
    def code(self) -> str:
        return "".join(self.chunks).strip("\n")


class ModuleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.module_ids: list[str] = []
        self.screens = 0
        self.quizzes = 0
        self.quiz_correct_counts: list[int] = []
        self._quiz_depths: list[int] = []
        self._depth = 0
        self.chats = 0
        self.flows = 0
        self.definitions = 0
        self.citations: list[CodeCitation] = []
        self._citation_stack: list[tuple[int, CodeCitation]] = []
        self._capture_code: CodeCitation | None = None
        self.forbidden_shell_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        attrs = dict(attrs_list)
        classes = class_set(attrs)
        if tag in {"html", "head", "body", "style", "script"}:
            self.forbidden_shell_tags.append(tag)
        if "course-module" in classes:
            self.module_ids.append(attrs.get("id") or "")
        if "screen" in classes:
            self.screens += 1
        if "quiz" in classes:
            self.quizzes += 1
            self.quiz_correct_counts.append(0)
            self._quiz_depths.append(self._depth)
        if self._quiz_depths and tag == "button" and attrs.get("data-correct") == "true":
            self.quiz_correct_counts[-1] += 1
        if "component-chat" in classes:
            self.chats += 1
        if "data-flow" in classes:
            self.flows += 1
        if tag == "dfn" and attrs.get("data-definition"):
            self.definitions += 1
        if "code-translation" in classes:
            citation = CodeCitation(attrs.get("data-source") or "", attrs.get("data-lines") or "")
            self.citations.append(citation)
            self._citation_stack.append((self._depth, citation))
        if tag == "code" and self._citation_stack:
            self._capture_code = self._citation_stack[-1][1]

    def handle_endtag(self, tag: str) -> None:
        if tag == "code":
            self._capture_code = None
        if self._citation_stack and self._citation_stack[-1][0] == self._depth:
            self._citation_stack.pop()
        if self._quiz_depths and self._quiz_depths[-1] == self._depth:
            self._quiz_depths.pop()
        self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_code is not None:
            self._capture_code.chunks.append(data)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_dir", type=Path)
    parser.add_argument("--source-root", type=Path)
    return parser.parse_args(argv)


def safe_source_path(root: Path, relative: str) -> Path | None:
    if not relative or Path(relative).is_absolute():
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def verify_citation(citation: CodeCitation, source_root: Path) -> str | None:
    source = safe_source_path(source_root, citation.source)
    if source is None:
        return f"unsafe or missing source path {citation.source!r}"
    if not source.is_file():
        return f"source file does not exist: {citation.source}"
    match = re.fullmatch(r"(\d+)-(\d+)", citation.lines)
    if not match:
        return f"invalid line range {citation.lines!r} for {citation.source}"
    start, end = map(int, match.groups())
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return f"source file is not UTF-8 text: {citation.source}"
    if start < 1 or end < start or end > len(lines):
        return f"line range {start}-{end} is outside {citation.source} (1-{len(lines)})"
    expected = "\n".join(lines[start - 1 : end])
    if citation.code != expected:
        return f"code excerpt differs from {citation.source}:{start}-{end}"
    return None


def dependency_problems(value: object, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{label} must be a list of repository-relative paths or glob patterns"]
    problems = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            problems.append(f"{label} contains a non-string or empty dependency")
            continue
        normalized = item.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts:
            problems.append(f"{label} contains an unsafe dependency pattern: {item!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    course_dir = args.course_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        config = json.loads((course_dir / "course.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: Cannot read course.json: {exc}", file=sys.stderr)
        return 1

    configured_modules = config.get("modules", [])
    if not 3 <= len(configured_modules) <= 8:
        errors.append("course must contain between 3 and 8 modules")
    errors.extend(dependency_problems(config.get("globalDependsOn", []), "globalDependsOn"))
    source_root = (args.source_root or Path(config.get("source", {}).get("root", ""))).expanduser().resolve()
    if not source_root.is_dir():
        errors.append(f"source root is not a directory: {source_root}")

    total_chats = 0
    total_flows = 0
    seen_ids: set[str] = set()
    expected_citations: list[tuple[str, str, str]] = []
    for position, module in enumerate(configured_modules, start=1):
        errors.extend(
            dependency_problems(module.get("dependsOn", []), f"module {position} dependsOn")
        )
        module_file = course_dir / "modules" / str(module.get("file", ""))
        try:
            content = module_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            errors.append(f"missing module file: {module_file.name}")
            continue
        label = module_file.name
        if "TODO" in content:
            errors.append(f"{label}: unfinished scaffold marker remains")
        parser = ModuleParser()
        parser.feed(content)
        expected_citations.extend((c.source, c.lines, c.code) for c in parser.citations)
        if parser.forbidden_shell_tags:
            errors.append(f"{label}: module fragments cannot contain {', '.join(parser.forbidden_shell_tags)}")
        expected_id = str(module.get("id", ""))
        if parser.module_ids != [expected_id]:
            errors.append(f"{label}: expected one top-level course module with id {expected_id!r}")
        if expected_id in seen_ids:
            errors.append(f"{label}: duplicate module id {expected_id!r}")
        seen_ids.add(expected_id)
        if not 3 <= parser.screens <= 6:
            errors.append(f"{label}: expected 3-6 screens, found {parser.screens}")
        if not parser.citations:
            errors.append(f"{label}: add at least one exact code translation")
        if not parser.quizzes:
            errors.append(f"{label}: add at least one applied quiz")
        for quiz_number, correct_count in enumerate(parser.quiz_correct_counts, start=1):
            if correct_count != 1:
                errors.append(f"{label}: quiz {quiz_number} has {correct_count} correct answers; expected 1")
        if parser.definitions == 0:
            warnings.append(f"{label}: no first-use glossary definition found")
        total_chats += parser.chats
        total_flows += parser.flows
        if source_root.is_dir():
            for citation in parser.citations:
                problem = verify_citation(citation, source_root)
                if problem:
                    errors.append(f"{label}: {problem}")

    if total_chats == 0:
        errors.append("course needs at least one component conversation")
    if total_flows == 0:
        errors.append("course needs at least one stepwise data flow")

    if config.get("learningKit"):
        from learning_kit import inside, load_kit, render_documents, validate_kit
        try:
            _, kit = load_kit(course_dir, config)
            kit_errors = validate_kit(course_dir, config, kit, source_root)
            errors.extend(kit_errors)
            if not kit_errors:
                for name, expected in render_documents(course_dir, config, kit, write=False).items():
                    generated = inside(course_dir, name)
                    if not generated.is_file() or generated.read_text(encoding="utf-8") != expected:
                        errors.append(f"generated learning material missing or stale: {name}; rebuild")
        except (ValueError, OSError, TypeError, KeyError) as exc:
            errors.append(f"Cannot validate learning kit: {exc}")

    index = course_dir / "index.html"
    if not index.is_file():
        errors.append("index.html is missing; run build_course.py")
    else:
        built = index.read_text(encoding="utf-8")
        built_parser = ModuleParser()
        built_parser.feed(built)
        displayed = [(c.source, c.lines, c.code) for c in built_parser.citations]
        if displayed != expected_citations:
            errors.append("index.html displayed citations differ from editable modules; rebuild")
        if config.get("learningKit") and 'class="learning-panel"' not in built:
            errors.append("index.html is missing the progressive learning panel")
        inputs = [course_dir / "course.json"]
        if config.get("learningKit"):
            from learning_kit import inside
            try:
                inputs.append(inside(course_dir, config["learningKit"]))
            except ValueError:
                pass  # Reported above; do not follow an unsafe path.
        inputs.extend(course_dir / "modules" / str(module.get("file", "")) for module in configured_modules)
        inputs.extend((course_dir / "assets" / name) for name in ("base.html", "theme.css", "course.js"))
        existing_inputs = [path for path in inputs if path.exists()]
        if existing_inputs and index.stat().st_mtime_ns < max(path.stat().st_mtime_ns for path in existing_inputs):
            errors.append("index.html is older than a course source file; rebuild it")
        if re.search(r"<(?:script|link|img)[^>]+(?:src|href)=[\"']https?://", built, re.IGNORECASE):
            errors.append("index.html loads a remote script, stylesheet, or image; keep the course offline")
        if "TODO" in built:
            errors.append("index.html contains an unfinished TODO marker")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    print(
        f"Validation passed: {len(configured_modules)} modules, "
        f"{total_chats} component conversation(s), {total_flows} data flow(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
