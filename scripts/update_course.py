#!/usr/bin/env python3
"""Detect source changes and drive targeted updates to an existing course."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from validate_course import ModuleParser, safe_source_path


SCHEMA_VERSION = 1
STATE_FILE = "course-state.json"
REPORT_JSON = "course-update-report.json"
REPORT_MD = "course-update-report.md"
LARGE_FILE_BYTES = 10 * 1024 * 1024
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "coverage",
    "node_modules",
    "target",
    "venv",
}
FIGURE_TAG_RE = re.compile(r"<figure\b[^>]*>", re.IGNORECASE | re.DOTALL)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.DOTALL)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_dir", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument(
        "--accept-baseline",
        action="store_true",
        help="Build, validate, and record the current source/course state as the new baseline",
    )
    parser.add_argument(
        "--apply-safe-rebases",
        action="store_true",
        help="Update data-lines when an unchanged excerpt moved to one unique line range",
    )
    return parser.parse_args(argv)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, value: dict) -> None:
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def revision_info(source_root: Path) -> dict:
    try:
        top = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(source_root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {
            "kind": "git",
            "repositoryRoot": top,
            "head": head,
            "dirty": dirty,
            "display": f"{head[:12]} + working changes" if dirty else head[:12],
        }
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {
            "kind": "directory",
            "repositoryRoot": str(source_root),
            "head": None,
            "dirty": None,
            "display": "unversioned working tree",
        }


def fingerprint_inventory(source_root: Path, course_dir: Path) -> tuple[dict[str, str], list[str]]:
    inventory: dict[str, str] = {}
    warnings: list[str] = []
    for current, dirnames, filenames in os.walk(source_root):
        current_path = Path(current)
        if is_within(current_path, course_dir):
            dirnames[:] = []
            continue
        kept_dirs = []
        for dirname in dirnames:
            candidate = current_path / dirname
            if dirname in IGNORED_DIRS or is_within(candidate, course_dir):
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            path = current_path / filename
            if is_within(path, course_dir):
                continue
            try:
                relative = path.relative_to(source_root).as_posix()
                if path.is_symlink():
                    inventory[relative] = f"symlink:{os.readlink(path)}"
                    continue
                stat = path.stat()
                if not path.is_file():
                    continue
                if stat.st_size > LARGE_FILE_BYTES:
                    inventory[relative] = f"large:{stat.st_size}:{stat.st_mtime_ns}"
                    warnings.append(
                        f"{relative}: larger than {LARGE_FILE_BYTES // (1024 * 1024)} MiB; "
                        "tracked by size and timestamp"
                    )
                else:
                    inventory[relative] = f"sha256:{sha256_file(path)}"
            except (OSError, ValueError) as exc:
                warnings.append(f"{path}: could not fingerprint ({exc})")
    return dict(sorted(inventory.items())), warnings


def normalize_patterns(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            continue
        pattern = item.replace("\\", "/")
        while pattern.startswith("./"):
            pattern = pattern[2:]
        normalized.append(pattern)
    return normalized


def path_matches(path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return False
    if normalized.endswith("/"):
        return path.startswith(normalized)
    if path == normalized:
        return True
    try:
        if PurePosixPath(path).match(normalized):
            return True
    except ValueError:
        pass
    return fnmatch.fnmatchcase(path, normalized)


def module_record(course_dir: Path, module: dict) -> dict:
    module_path = course_dir / "modules" / str(module.get("file", ""))
    content = module_path.read_text(encoding="utf-8")
    parser = ModuleParser()
    parser.feed(content)
    citations = []
    for citation in parser.citations:
        citations.append(
            {
                "source": citation.source,
                "lines": citation.lines,
                "text": citation.code,
                "excerptHash": sha256_text(citation.code),
            }
        )
    return {
        "id": str(module.get("id", "")),
        "title": str(module.get("title", "")),
        "file": str(module.get("file", "")),
        "moduleHash": sha256_text(content),
        "dependsOn": normalize_patterns(module.get("dependsOn", [])),
        "citations": citations,
    }


def capture_state(course_dir: Path, source_root: Path, config: dict) -> dict:
    inventory, warnings = fingerprint_inventory(source_root, course_dir)
    modules = {}
    for module in config.get("modules", []):
        record = module_record(course_dir, module)
        modules[record["id"]] = record
    state = {
        "schemaVersion": SCHEMA_VERSION,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "root": str(source_root),
            "revision": revision_info(source_root),
        },
        "globalDependsOn": normalize_patterns(config.get("globalDependsOn", [])),
        "modules": modules,
        "inventory": inventory,
        "inventoryWarnings": warnings,
    }
    if config.get("learningKit"):
        from learning_kit import digest, load_kit, snapshot_kit
        from learning_updates import lab_hashes
        _, kit = load_kit(course_dir, config)
        state["learningKit"] = snapshot_kit(course_dir, config, kit)
        state["learningKit"]["labFiles"] = lab_hashes(course_dir)
        state["learningKit"]["notesHash"] = digest(kit.get("notes", {}))
    return state


def run_course_tool(script: str, course_dir: Path, source_root: Path | None = None) -> int:
    command = [sys.executable, str(Path(__file__).with_name(script)), str(course_dir)]
    if source_root is not None:
        command.extend(["--source-root", str(source_root)])
    return subprocess.run(command, check=False).returncode


def accept_baseline(course_dir: Path, source_root: Path, config: dict) -> int:
    revision = revision_info(source_root)
    config.setdefault("source", {})
    config["source"].update(
        {"name": source_root.name, "root": str(source_root), "revision": revision["display"]}
    )
    write_json(course_dir / "course.json", config)
    if run_course_tool("build_course.py", course_dir) != 0:
        print("Baseline not accepted because the course build failed", file=sys.stderr)
        return 1
    if run_course_tool("validate_course.py", course_dir, source_root) != 0:
        print("Baseline not accepted because course validation failed", file=sys.stderr)
        return 1
    state = capture_state(course_dir, source_root, config)
    write_json(course_dir / STATE_FILE, state)
    print(f"Accepted incremental-update baseline: {course_dir / STATE_FILE}")
    print(f"Source revision: {revision['display']}; tracked files: {len(state['inventory'])}")
    return 0


def inventory_changes(previous: dict[str, str], current: dict[str, str]) -> list[dict[str, str]]:
    changes = []
    for path in sorted(previous.keys() | current.keys()):
        if path not in previous:
            kind = "added"
        elif path not in current:
            kind = "removed"
        elif previous[path] != current[path]:
            kind = "modified"
        else:
            continue
        changes.append({"path": path, "kind": kind})
    return changes


def parse_line_range(value: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d+)-(\d+)", value)
    if not match:
        return None
    start, end = map(int, match.groups())
    return (start, end) if start >= 1 and end >= start else None


def locate_citation(citation: dict, source_root: Path) -> dict:
    source_name = str(citation.get("source", ""))
    old_lines = str(citation.get("lines", ""))
    text = str(citation.get("text", ""))
    result = {"source": source_name, "oldLines": old_lines, "status": "changed", "newLines": None}
    source = safe_source_path(source_root, source_name)
    if source is None or not source.is_file():
        result["status"] = "missing"
        return result
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        result["status"] = "missing"
        result["detail"] = "source is not UTF-8 text"
        return result
    old_range = parse_line_range(old_lines)
    excerpt_lines = text.split("\n")
    if old_range:
        start, end = old_range
        if end <= len(lines) and "\n".join(lines[start - 1 : end]) == text:
            result.update({"status": "stable", "newLines": old_lines})
            return result
    width = len(excerpt_lines)
    occurrences = []
    if text:
        for index in range(0, max(0, len(lines) - width + 1)):
            if lines[index : index + width] == excerpt_lines:
                occurrences.append((index + 1, index + width))
    if len(occurrences) == 1:
        start, end = occurrences[0]
        result.update({"status": "moved", "newLines": f"{start}-{end}"})
    elif len(occurrences) > 1:
        result.update(
            {
                "status": "ambiguous",
                "detail": f"unchanged excerpt now appears {len(occurrences)} times",
            }
        )
    return result


def rebase_citation_tag(content: str, source: str, old_lines: str, new_lines: str) -> tuple[str, int]:
    replacements = 0

    def replace_tag(match: re.Match[str]) -> str:
        nonlocal replacements
        tag = match.group(0)
        attrs = {name.lower(): html.unescape(value) for name, _, value in ATTR_RE.findall(tag)}
        if "code-translation" not in attrs.get("class", "").split():
            return tag
        if attrs.get("data-source") != source or attrs.get("data-lines") != old_lines:
            return tag
        line_pattern = re.compile(
            r"(\bdata-lines\s*=\s*)([\"'])" + re.escape(old_lines) + r"\2",
            re.IGNORECASE,
        )
        updated, count = line_pattern.subn(lambda item: f"{item.group(1)}{item.group(2)}{new_lines}{item.group(2)}", tag, count=1)
        replacements += count
        return updated

    updated_content = FIGURE_TAG_RE.sub(replace_tag, content)
    if replacements:
        old_dash = old_lines.replace("-", "–")
        new_dash = new_lines.replace("-", "–")
        updated_content = updated_content.replace(f"{source}:{old_dash}", f"{source}:{new_dash}")
        updated_content = updated_content.replace(f"{source}:{old_lines}", f"{source}:{new_lines}")
    return updated_content, replacements


def summarize_module(
    baseline: dict,
    current: dict | None,
    changed_paths: list[str],
    global_changes: list[str],
    source_root: Path,
) -> dict:
    module_id = str(baseline.get("id", ""))
    result = {
        "id": module_id,
        "title": (current or baseline).get("title", ""),
        "file": (current or baseline).get("file", ""),
        "status": "unchanged",
        "reasons": [],
        "changedFiles": [],
        "citations": [],
        "moduleEditedSinceBaseline": False,
        "safeRebasesApplied": [],
    }
    if current is None:
        result.update({"status": "refresh", "reasons": ["baseline module is missing from course.json"]})
        return result

    explicit_patterns = normalize_patterns(current.get("dependsOn", baseline.get("dependsOn", [])))
    citation_paths = {str(item.get("source", "")) for item in baseline.get("citations", [])}
    explicit_changes = [
        path for path in changed_paths if any(path_matches(path, pattern) for pattern in explicit_patterns)
    ]
    cited_changes = [path for path in changed_paths if path in citation_paths]
    result["changedFiles"] = sorted(set(explicit_changes + cited_changes + global_changes))

    try:
        content = (Path(current["absolutePath"])).read_text(encoding="utf-8")
        result["moduleEditedSinceBaseline"] = sha256_text(content) != baseline.get("moduleHash")
    except (KeyError, FileNotFoundError, UnicodeDecodeError):
        result.update({"status": "refresh", "reasons": ["module file is missing or unreadable"]})
        return result

    bad_citation = False
    moved_citation = False
    for citation in baseline.get("citations", []):
        located = locate_citation(citation, source_root)
        result["citations"].append(located)
        if located["status"] in {"changed", "missing", "ambiguous"}:
            bad_citation = True
        elif located["status"] == "moved":
            moved_citation = True

    if bad_citation:
        result["status"] = "refresh"
        result["reasons"].append("one or more cited excerpts changed, disappeared, or became ambiguous")
    elif (
        moved_citation
        and not explicit_changes
        and not global_changes
        and not result["moduleEditedSinceBaseline"]
        and set(cited_changes) == set(result["changedFiles"])
    ):
        result["status"] = "rebase-only"
        result["reasons"].append("cited text is unchanged and moved to a unique new line range")
    elif result["changedFiles"] or moved_citation or result["moduleEditedSinceBaseline"]:
        result["status"] = "review"
        if explicit_changes:
            result["reasons"].append("a mapped module dependency changed")
        if cited_changes:
            result["reasons"].append("a cited source file changed outside or around the excerpt")
        if global_changes:
            result["reasons"].append("a course-wide dependency changed")
        if moved_citation:
            result["reasons"].append("an unchanged excerpt moved")
        if result["moduleEditedSinceBaseline"]:
            result["reasons"].append("the course module was edited after the accepted baseline")
    return result


def markdown_report(report: dict) -> str:
    counts = report["summary"]
    lines = [
        "# Course update report",
        "",
        f"- Baseline: `{report['baseline']['capturedAt']}` ({report['baseline']['revision']})",
        f"- Current source: `{report['current']['revision']}`",
        f"- Changed source files: {counts['changedFiles']}",
        f"- Safe citation rebases applied: {counts['safeRebasesApplied']}",
        "",
        "## Module work queue",
        "",
        "| Module | Status | Why |",
        "|---|---|---|",
    ]
    for module in report["modules"]:
        reasons = "; ".join(module["reasons"]) or "No mapped source change"
        title = str(module["title"]).replace("|", "\\|")
        lines.append(f"| {module['id']} · {title} | `{module['status']}` | {reasons} |")
        if module["changedFiles"]:
            lines.append("")
            lines.append(f"Changed files for `{module['id']}`:")
            lines.extend(f"- `{path}`" for path in module["changedFiles"])
        citation_changes = [item for item in module["citations"] if item["status"] != "stable"]
        if citation_changes:
            lines.append("")
            lines.append(f"Citation changes for `{module['id']}`:")
            for item in citation_changes:
                movement = f" → {item['newLines']}" if item.get("newLines") else ""
                lines.append(
                    f"- `{item['source']}:{item['oldLines']}`: **{item['status']}**{movement}"
                )
    lines.extend(["", "## Unmapped source changes", ""])
    if report["unmappedChanges"]:
        limit = 200
        lines.extend(
            f"- `{item['path']}` ({item['kind']})" for item in report["unmappedChanges"][:limit]
        )
        if len(report["unmappedChanges"]) > limit:
            lines.append(f"- … and {len(report['unmappedChanges']) - limit} more; see the JSON report")
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Next actions",
            "",
            "1. Preserve `unchanged` modules byte-for-byte.",
            "2. Inspect and patch only `refresh` and `review` modules; keep `rebase-only` lesson content.",
            "3. Triage meaningful unmapped architecture or feature changes before expanding coverage.",
            "4. Build, validate, preview affected modules, then run `--accept-baseline`.",
            "",
        ]
    )
    if report["inventoryWarnings"]:
        lines.extend(["## Inventory warnings", ""])
        lines.extend(f"- {warning}" for warning in report["inventoryWarnings"])
        lines.append("")
    return "\n".join(lines)


def check_updates(
    course_dir: Path,
    source_root: Path,
    config: dict,
    state: dict,
    apply_safe_rebases: bool,
) -> int:
    if state.get("schemaVersion") != SCHEMA_VERSION:
        raise SystemExit(
            f"Unsupported {STATE_FILE} schema {state.get('schemaVersion')!r}; expected {SCHEMA_VERSION}"
        )
    current_inventory, inventory_warnings = fingerprint_inventory(source_root, course_dir)
    changes = inventory_changes(state.get("inventory", {}), current_inventory)
    changed_paths = [item["path"] for item in changes]
    global_patterns = normalize_patterns(config.get("globalDependsOn", state.get("globalDependsOn", [])))
    global_changes = [
        path for path in changed_paths if any(path_matches(path, pattern) for pattern in global_patterns)
    ]

    current_modules: dict[str, dict] = {}
    for module in config.get("modules", []):
        item = dict(module)
        item["absolutePath"] = str(course_dir / "modules" / str(module.get("file", "")))
        current_modules[str(module.get("id", ""))] = item

    results = []
    mapped_paths = set(global_changes)
    baseline_modules = state.get("modules", {})
    for module_id, baseline in baseline_modules.items():
        current = current_modules.get(module_id)
        result = summarize_module(
            baseline,
            current,
            changed_paths,
            global_changes,
            source_root,
        )
        mapped_paths.update(result["changedFiles"])
        if apply_safe_rebases and current and not result["moduleEditedSinceBaseline"]:
            module_path = Path(current["absolutePath"])
            content = module_path.read_text(encoding="utf-8")
            for citation in result["citations"]:
                if citation["status"] != "moved" or not citation.get("newLines"):
                    continue
                content, count = rebase_citation_tag(
                    content,
                    citation["source"],
                    citation["oldLines"],
                    citation["newLines"],
                )
                if count:
                    result["safeRebasesApplied"].append(
                        {
                            "source": citation["source"],
                            "oldLines": citation["oldLines"],
                            "newLines": citation["newLines"],
                        }
                    )
            if result["safeRebasesApplied"]:
                module_path.write_text(content, encoding="utf-8")
        results.append(result)

    for module_id, current in current_modules.items():
        if module_id in baseline_modules:
            continue
        results.append(
            {
                "id": module_id,
                "title": current.get("title", ""),
                "file": current.get("file", ""),
                "status": "new-module",
                "reasons": ["module has no accepted baseline"],
                "changedFiles": [],
                "citations": [],
                "moduleEditedSinceBaseline": False,
                "safeRebasesApplied": [],
            }
        )

    all_dependency_patterns = list(global_patterns)
    all_citation_paths: set[str] = set()
    for module_id, baseline in baseline_modules.items():
        current = current_modules.get(module_id, {})
        all_dependency_patterns.extend(
            normalize_patterns(current.get("dependsOn", baseline.get("dependsOn", [])))
        )
        all_citation_paths.update(str(item.get("source", "")) for item in baseline.get("citations", []))
    for module_id, current in current_modules.items():
        if module_id not in baseline_modules:
            all_dependency_patterns.extend(normalize_patterns(current.get("dependsOn", [])))
    for path in changed_paths:
        if path in all_citation_paths or any(path_matches(path, pattern) for pattern in all_dependency_patterns):
            mapped_paths.add(path)
    from learning_updates import learning_changes
    learning_report, learning_mapped = learning_changes(
        course_dir, source_root, config, state, changed_paths, apply_safe_rebases
    )
    mapped_paths.update(learning_mapped)
    unmapped = [item for item in changes if item["path"] not in mapped_paths]

    current_revision = revision_info(source_root)
    safe_count = sum(len(module["safeRebasesApplied"]) for module in results)
    status_counts = {status: 0 for status in ("unchanged", "rebase-only", "review", "refresh", "new-module")}
    for module in results:
        status_counts[module["status"]] = status_counts.get(module["status"], 0) + 1
    report = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "capturedAt": state.get("capturedAt", "unknown"),
            "revision": state.get("source", {}).get("revision", {}).get("display", "unknown"),
        },
        "current": {"revision": current_revision["display"], "sourceRoot": str(source_root)},
        "summary": {
            **status_counts,
            "changedFiles": len(changes),
            "unmappedFiles": len(unmapped),
            "safeRebasesApplied": safe_count,
        },
        "modules": results,
        "sourceChanges": changes,
        "unmappedChanges": unmapped,
        "inventoryWarnings": inventory_warnings,
    }
    if learning_report is not None:
        report["learning"] = learning_report
    write_json(course_dir / REPORT_JSON, report)
    report_text = markdown_report(report)
    if learning_report is not None:
        report_text += "\n## Learning concepts and labs\n\n"
        report_text += "| Concept | Source/teaching status | Prerequisite review |\n|---|---|---|\n"
        for concept in learning_report.get("concepts", []):
            report_text += f"| {concept['id']} | {concept['status']} | {concept.get('dependentReview', False)} |\n"
        report_text += "\nMilestones: " + ", ".join(
            f"{m['id']}={m['status']}" for m in learning_report.get("milestones", [])
        ) + "\n\nKeep learner history; source/rubric changes require new assessment evidence.\n"
    (course_dir / REPORT_MD).write_text(report_text, encoding="utf-8")
    print(f"Wrote incremental update report: {course_dir / REPORT_MD}")
    print(
        "Modules — "
        + ", ".join(f"{status}: {count}" for status, count in status_counts.items())
        + f"; changed files: {len(changes)}; unmapped: {len(unmapped)}"
    )
    if safe_count:
        print(f"Applied {safe_count} safe line-reference rebase(s); rebuild before validation")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.accept_baseline and args.apply_safe_rebases:
        raise SystemExit("Use --accept-baseline and --apply-safe-rebases in separate runs")
    course_dir = args.course_dir.expanduser().resolve()
    config = read_json(course_dir / "course.json")
    default_root = config.get("source", {}).get("root")
    if args.source_root is not None:
        source_root = args.source_root.expanduser().resolve()
    elif default_root:
        source_root = Path(default_root).expanduser().resolve()
    else:
        raise SystemExit("Provide --source-root; course.json has no source root")
    if not source_root.is_dir():
        raise SystemExit(f"Source root is not a directory: {source_root}")

    if args.accept_baseline:
        return accept_baseline(course_dir, source_root, config)
    state_path = course_dir / STATE_FILE
    if not state_path.is_file():
        raise SystemExit(
            f"Missing {state_path}. Build and validate the current course, then run --accept-baseline once."
        )
    return check_updates(
        course_dir,
        source_root,
        config,
        read_json(state_path),
        args.apply_safe_rebases,
    )


if __name__ == "__main__":
    raise SystemExit(main())
