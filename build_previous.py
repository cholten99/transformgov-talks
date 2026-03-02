#!/usr/bin/env python3
"""
Build previous.shtml from YAML + Jinja2 template.

Usage:
  python build_previous.py \
    --input-yaml previous_events.yml \
    --template previous_template.shtml.j2 \
    --output previous.shtml \
    --log-level INFO
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


LOG = logging.getLogger("build_previous")


def _configure_logging(level: str) -> None:
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        raise ValueError(f"Invalid log level: {level!r}")
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML {path}: {e}") from e

    if not isinstance(data, dict) or "events" not in data:
        raise ValueError("YAML must be a mapping with a top-level 'events' key.")
    if not isinstance(data["events"], list):
        raise ValueError("'events' must be a list.")
    return data


def _validate_events(events: List[Dict[str, Any]]) -> None:
    for idx, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise ValueError(f"events[{idx}] must be a mapping/dict.")
        if not isinstance(ev.get("month"), str) or not ev["month"].strip():
            raise ValueError(f"events[{idx}].month must be a non-empty string.")
        if "items" in ev and not isinstance(ev["items"], list):
            raise ValueError(f"events[{idx}].items must be a list (or omitted).")
        if "links" in ev and not isinstance(ev["links"], dict):
            raise ValueError(f"events[{idx}].links must be a dict (or omitted).")


def _format_links_line(links: Dict[str, str]) -> str:
    """
    Convert a dict of {label: href} to a human-friendly, comma-separated set of <a> tags
    using the preferred order: Blog, YouTube, Spotify, Apple Podcasts.
    """
    order = [("blog", "Blog"), ("youtube", "YouTube"), ("spotify", "Spotify"), ("apple podcasts", "Apple Podcasts")]
    parts: List[str] = []
    for key, title in order:
        href = links.get(key)
        if href:
            parts.append(
                f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
                f'class="underline underline-offset-2 hover:underline-offset-4">{title}</a>'
            )

    if not parts:
        return ""

    if len(parts) == 1:
        return parts[0] + "."

    if len(parts) == 2:
        return parts[0] + " and " + parts[1] + "."

    # Oxford comma style: A, B and C.
    return ", ".join(parts[:-1]) + " and " + parts[-1] + "."


def build(input_yaml: Path, template_path: Path, output_path: Path) -> None:
    data = _load_yaml(input_yaml)
    events = data["events"]
    _validate_events(events)

    # Prepare a richer structure for the template:
    # - ensure items/links exist
    # - pre-render the "links line" as HTML, matching your current site style
    prepared = []
    for ev in events:
        items = ev.get("items") or []
        links = ev.get("links") or {}
        if not isinstance(items, list):
            raise ValueError(f"Invalid items for month {ev.get('month')!r}")
        if not isinstance(links, dict):
            raise ValueError(f"Invalid links for month {ev.get('month')!r}")

        prepared.append(
            {
                "month": ev["month"],
                "bullets": [str(x) for x in items],
                "links": {str(k).lower(): str(v) for k, v in links.items()},
                "links_html": _format_links_line({str(k).lower(): str(v) for k, v in links.items()}),
            }
        )

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=False,  # we're controlling HTML output
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template(template_path.name)

    rendered = template.render(events=prepared)

    # Post-process: replace the placeholder link list item (if present) with links_html.
    # In the template, we include a <li> that contains anchor tags.
    # Easiest is to have template check for ev.links_html; but we keep it simple:
    # We'll render using a small convention: if links_html exists, it should appear as raw HTML in a <li>.
    rendered = rendered.replace(
        "<!--LINKS_PLACEHOLDER-->",
        "",
    )

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    LOG.info("Wrote %s", output_path)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate previous.shtml from YAML + template.")
    parser.add_argument("--input-yaml", required=True, type=Path, help="Path to previous_events.yml")
    parser.add_argument("--template", required=True, type=Path, help="Path to Jinja2 template (.j2)")
    parser.add_argument("--output", required=True, type=Path, help="Output HTML/SSI file path")
    parser.add_argument("--log-level", default="INFO", help="DEBUG, INFO, WARNING, ERROR")
    args = parser.parse_args(argv)

    try:
        _configure_logging(args.log_level)
        build(args.input_yaml, args.template, args.output)
        return 0
    except Exception as e:
        # Always emit a clear error for CI logs / terminal use
        print(f"ERROR: {e}", file=sys.stderr)
        LOG.exception("Build failed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
