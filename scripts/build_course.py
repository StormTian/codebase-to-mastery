#!/usr/bin/env python3
"""Assemble editable course modules into one self-contained HTML file."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import tempfile
from pathlib import Path

from learning_kit import learning_panel, load_kit, render_documents


TOKENS = {
    "{{TITLE}}",
    "{{SUBTITLE}}",
    "{{LANG}}",
    "{{ACCENT}}",
    "{{SOURCE_NAME}}",
    "{{REVISION}}",
    "{{MODULE_COUNT}}",
    "{{NAV}}",
    "{{MODULES}}",
    "{{CSS}}",
    "{{JS}}",
    "{{LEARNING_PANEL}}",
    "{{START_TARGET}}",
    "{{START_LABEL}}",
    "{{MOTION_LABEL}}",
    "{{OVERVIEW_LABEL}}", "{{NAV_LABEL}}", "{{SOURCE_LABEL}}",
    "{{KEY_HINT}}", "{{KICKER}}", "{{FORMAT_LABEL}}",
    "{{REVISION_LABEL}}", "{{MODULES_LABEL}}", "{{FOOTER_TEXT}}", "{{BACK_LABEL}}",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_dir", type=Path)
    return parser.parse_args(argv)


def load_config(course_dir: Path) -> dict:
    config_path = course_dir / "course.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing {config_path}") from exc
    required = {"title", "subtitle", "lang", "accent", "source", "modules"}
    missing = sorted(required - config.keys())
    if missing:
        raise SystemExit(f"course.json is missing: {', '.join(missing)}")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", config["accent"]):
        raise SystemExit("course.json accent must be a six-digit hex color")
    return config


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    course_dir = args.course_dir.expanduser().resolve()
    config = load_config(course_dir)
    try:
        _, kit = load_kit(course_dir, config)
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Cannot load learning kit: {exc}") from exc
    if kit:
        render_documents(course_dir, config, kit)
    assets = course_dir / "assets"
    base = (assets / "base.html").read_text(encoding="utf-8")
    if kit and "{{LEARNING_PANEL}}" not in base:
        if '<main id="course">' not in base:
            raise SystemExit('Kit requires {{LEARNING_PANEL}} or <main id="course"> in its template')
        base = base.replace('<main id="course">', '{{LEARNING_PANEL}}\n<main id="course">', 1)
    if kit:
        base = re.sub(r'(<a\b[^>]*class="start-link"[^>]*href=")#module-01(")', r'\1#learning-path\2', base, count=1)
    css = (assets / "theme.css").read_text(encoding="utf-8")
    javascript = (assets / "course.js").read_text(encoding="utf-8")

    zh = str(config["lang"]).startswith("zh")
    modules = []
    nav = []
    for module in config["modules"]:
        module_path = course_dir / "modules" / module["file"]
        content = module_path.read_text(encoding="utf-8").strip()
        modules.append(content)
        target = html.escape(str(module["id"]), quote=True)
        title = html.escape(str(module["title"]), quote=True)
        nav.append(
            f'<button class="nav-dot" type="button" data-target="{target}" '
            f'aria-label="{("进入 " if zh else "Go to ")}{title}" title="{title}">'
            f'<span class="nav-title">{title}</span><span class="nav-arrow" aria-hidden="true">↗</span></button>'
        )

    replacements = {
        "{{TITLE}}": html.escape(str(config["title"])),
        "{{SUBTITLE}}": html.escape(str(config["subtitle"])),
        "{{LANG}}": html.escape(str(config["lang"]), quote=True),
        "{{ACCENT}}": html.escape(str(config["accent"]), quote=True),
        "{{SOURCE_NAME}}": html.escape(str(config["source"].get("name", "unknown"))),
        "{{REVISION}}": html.escape(str(config["source"].get("revision", "unknown"))),
        "{{MODULE_COUNT}}": str(len(modules)),
        "{{NAV}}": "\n      ".join(nav),
        "{{MODULES}}": "\n\n".join(modules),
        "{{CSS}}": css,
        "{{JS}}": javascript.replace("</script>", "<\\/script>"),
        "{{LEARNING_PANEL}}": learning_panel(config, kit) if kit else "",
        "{{START_TARGET}}": "#learning-path" if kit else "#module-01",
        "{{START_LABEL}}": "开始学习" if str(config["lang"]).startswith("zh") else "Start learning",
        "{{MOTION_LABEL}}": "减少动效" if str(config["lang"]).startswith("zh") else "Reduce motion",
        "{{OVERVIEW_LABEL}}": "学习总览" if zh else "Overview",
        "{{NAV_LABEL}}": "课程目录" if zh else "Lessons",
        "{{SOURCE_LABEL}}": "学习源码" if zh else "Source",
        "{{KEY_HINT}}": "切换章节" if zh else "Move between lessons",
        "{{KICKER}}": "源码掌握工坊" if zh else "Source learning workshop",
        "{{FORMAT_LABEL}}": "离线交互课" if zh else "Offline interactive course",
        "{{REVISION_LABEL}}": "源码版本" if zh else "Revision",
        "{{MODULES_LABEL}}": "章节" if zh else "Lessons",
        "{{FOOTER_TEXT}}": "基于已检查的源码。摘录保留原文件与连续行号，学习结论可回到证据。" if zh else "Built from inspected source. Follow every excerpt back to its original file and line range.",
        "{{BACK_LABEL}}": "返回顶部" if zh else "Back to top",
    }
    template_tokens = set(re.findall(r"\{\{[A-Z_]+\}\}", base))
    unresolved = sorted(template_tokens - replacements.keys())
    if unresolved:
        raise SystemExit(f"Unresolved template tokens: {', '.join(unresolved)}")
    # Substitute the template once. Literal tokens inside source excerpts must survive.
    result = re.sub(r"\{\{[A-Z_]+\}\}", lambda match: replacements[match.group()], base)

    output = course_dir / "index.html"
    descriptor, temp_name = tempfile.mkstemp(prefix=".index-", suffix=".html", dir=course_dir)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(result)
            handle.write("\n")
        os.replace(temp_name, output)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Built self-contained course: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
