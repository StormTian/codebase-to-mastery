#!/usr/bin/env python3
"""Create an editable, offline codebase-course workspace."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
from pathlib import Path


DEFAULT_ACCENT = "#D95D39"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "module"


def git_revision(source_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        revision = result.stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(source_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return f"{revision} + working changes" if dirty else revision
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unversioned working tree"


def module_stub(number: int, title: str) -> str:
    module_id = f"module-{number:02d}"
    safe_title = html.escape(title, quote=True)
    return f'''<section class="course-module" id="{module_id}" data-title="{safe_title}">
  <!-- TODO: Replace this scaffold with source-grounded course content. -->
  <div class="screen hero-screen" data-number="{number:02d}">
    <p class="eyebrow">Module {number}</p>
    <h2>{safe_title}</h2>
    <p class="lede">State the practical learner outcome here.</p>
  </div>
</section>
'''


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", required=True)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--module", action="append", dest="modules", required=True)
    parser.add_argument("--accent", default=DEFAULT_ACCENT)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--force", action="store_true", help="Overwrite files owned by this scaffold")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()
    source_root = args.source_root.expanduser().resolve()
    if not source_root.is_dir():
        raise SystemExit(f"Source root is not a directory: {source_root}")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", args.accent):
        raise SystemExit("--accent must be a six-digit hex color such as #D95D39")
    if len(args.modules) < 3 or len(args.modules) > 8:
        raise SystemExit("Choose between 3 and 8 focused modules")

    owned_paths = [output_dir / "course.json", output_dir / "assets", output_dir / "modules"]
    if any(path.exists() for path in owned_paths) and not args.force:
        raise SystemExit(f"Course files already exist in {output_dir}; choose another directory or use --force")

    template_dir = Path(__file__).resolve().parents[1] / "assets" / "course-template"
    assets_dir = output_dir / "assets"
    modules_dir = output_dir / "modules"
    assets_dir.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)
    for name in ("base.html", "theme.css", "course.js"):
        shutil.copy2(template_dir / name, assets_dir / name)

    module_entries = []
    seen_slugs: dict[str, int] = {}
    for number, title in enumerate(args.modules, start=1):
        base_slug = slugify(title)
        seen_slugs[base_slug] = seen_slugs.get(base_slug, 0) + 1
        suffix = f"-{seen_slugs[base_slug]}" if seen_slugs[base_slug] > 1 else ""
        filename = f"{number:02d}-{base_slug}{suffix}.html"
        (modules_dir / filename).write_text(module_stub(number, title), encoding="utf-8")
        module_entries.append(
            {"id": f"module-{number:02d}", "title": title, "file": filename, "dependsOn": []}
        )

    config = {
        "title": args.title,
        "subtitle": args.subtitle,
        "lang": args.lang,
        "accent": args.accent.upper(),
        "globalDependsOn": [],
        "source": {
            "name": source_root.name,
            "root": str(source_root),
            "revision": git_revision(source_root),
        },
        "modules": module_entries,
    }
    (output_dir / "course.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created course workspace: {output_dir}")
    print(
        f"Author {len(module_entries)} module files, map their dependencies, "
        "then build, validate, and accept a baseline"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
