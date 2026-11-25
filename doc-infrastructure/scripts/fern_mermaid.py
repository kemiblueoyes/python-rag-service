#!/usr/bin/env python3
"""Stage Fern docs with Mermaid class definitions generated from a shared JSON palette.

No third-party Python packages needed. Run from repo root:
  python doc-infrastructure/scripts/fern_mermaid.py prepare
  python doc-infrastructure/scripts/fern_mermaid.py dev
  python doc-infrastructure/scripts/fern_mermaid.py publish

The staging tree defaults to .generated/fern. Source fern/ files are never modified.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

MERMAID_FENCE = re.compile(
    r"(?P<opening>^(?P<indent>[ \t]*)`{3,}mermaid[^\n]*\n)"
    r"(?P<body>.*?)"
    r"(?P<closing>^(?P=indent)`{3,}[ \t]*$)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
CLASSDEF = re.compile(r"^\s*classDef\s+([a-zA-Z][\w-]*)\b.*$", re.MULTILINE)
DIAGRAM_TYPES = re.compile(
    r"^\s*(?:flowchart|graph)\s+\S+",
    re.IGNORECASE | re.MULTILINE,
)
VALID_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
VALID_CSS_SIZE = re.compile(r"^\d+(?:\.\d+)?px$")
VALID_CLASS_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
# Only supported, well-defined properties are emitted into Mermaid source.
PROPERTIES = ("fill", "stroke", "color", "stroke-width")


def load_classes(theme_path: Path) -> dict[str, dict[str, str]]:
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    if theme.get("version") != 1 or not isinstance(theme.get("classes"), dict):
        raise ValueError("Theme must contain version: 1 and a classes object")
    classes = theme["classes"]
    for name, values in classes.items():
        if not VALID_CLASS_NAME.fullmatch(name) or not isinstance(values, dict):
            raise ValueError(f"Invalid Mermaid class: {name!r}")
        for prop in ("fill", "stroke", "color"):
            if not VALID_COLOR.fullmatch(values.get(prop, "")):
                raise ValueError(f"{name}.{prop} must be a 6-digit hex color")
        if "stroke-width" in values and not VALID_CSS_SIZE.fullmatch(
            values["stroke-width"]
        ):
            raise ValueError(f"{name}.stroke-width must be a px value")
    return classes


def inject_mermaid(source: str, classes: dict[str, dict[str, str]]) -> str:
    def replace(match: re.Match[str]) -> str:
        body = match.group("body")
        # Only flowcharts use classDef; don't modify other Mermaid diagram types.
        if not DIAGRAM_TYPES.search(body):
            return match.group(0)
        # Strip existing definitions for palette classes to avoid two sources of truth.
        names = set(classes)
        lines = body.splitlines(keepends=True)
        lines = [line for line in lines if not (
            (m := CLASSDEF.match(line)) and m.group(1) in names
        )]
        body = "".join(lines).rstrip("\n")
        defs = []
        for name, values in classes.items():
            props = ",".join(
                f"{key}:{values[key]}"
                for key in PROPERTIES
                if key in values
            )
            defs.append(f"classDef {name} {props}")
        # Append generated definitions, not a Mermaid init directive.
        body = body + "\n\n" + "\n".join(defs) + "\n"
        return match.group("opening") + body + match.group("closing")
    return MERMAID_FENCE.sub(replace, source)


def stage(
    source_fern: Path,
    output_fern: Path,
    classes: dict[str, dict[str, str]],
) -> int:
    if not source_fern.is_dir() or not (source_fern / "docs.yml").exists():
        raise FileNotFoundError(
            f"Fern source folder or docs.yml missing: {source_fern}"
        )
    if output_fern == source_fern or source_fern in output_fern.parents:
        raise ValueError("Staging must be outside the source fern/ directory")
    output_fern.mkdir(parents=True, exist_ok=True)
    files = set()
    changed = 0
    for src in source_fern.rglob("*"):
        if not src.is_file() or any(
            part.startswith(".git")
            for part in src.relative_to(source_fern).parts
        ):
            continue
        rel = src.relative_to(source_fern)
        files.add(rel)
        dst = output_fern / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in {".mdx", ".md"}:
            rendered = inject_mermaid(src.read_text(encoding="utf-8"), classes)
            if not dst.exists() or dst.read_text(encoding="utf-8") != rendered:
                dst.write_text(rendered, encoding="utf-8")
                changed += 1
        elif (
            not dst.exists()
            or src.stat().st_size != dst.stat().st_size
            or src.stat().st_mtime_ns > dst.stat().st_mtime_ns
        ):
            shutil.copy2(src, dst)
            changed += 1
    for dst in output_fern.rglob("*"):
        if dst.is_file() and dst.relative_to(output_fern) not in files:
            dst.unlink()
            changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("prepare", "dev", "publish", "preview", "check"),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.75,
        help="Seconds between syncs in dev mode",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    source_fern = root / "fern"
    output_fern = root / ".generated" / "fern"
    theme_path = root / "doc-infrastructure" / "diagram-styles" / "mermaid-theme.json"
    if args.interval <= 0:
        parser.error("--interval must be positive")
    classes = load_classes(theme_path)
    changed = stage(source_fern, output_fern, classes)
    print(f"Staged Fern site: {output_fern} ({changed} updated files)", flush=True)
    if args.action == "prepare":
        return 0
    command = {
        "dev": ["fern", "docs", "dev"],
        "publish": ["fern", "generate", "--docs"],
        "preview": ["fern", "generate", "--docs", "--preview"],
        "check": ["fern", "check"],
    }[args.action]
    if args.action != "dev":
        return subprocess.call(command, cwd=output_fern)
    process = subprocess.Popen(command, cwd=output_fern)
    try:
        while process.poll() is None:
            time.sleep(args.interval)
            # Re-read theme so edits to palette trigger a fresh render.
            classes = load_classes(theme_path)
            changed = stage(source_fern, output_fern, classes)
            if changed:
                print(f"Synced {changed} changed files", flush=True)
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130
    return process.returncode or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
