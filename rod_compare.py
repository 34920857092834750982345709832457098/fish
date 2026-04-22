#!/usr/bin/env python3
"""Compare fishing rods using stats scraped from the Fisch wiki page.

Example:
    python rod_compare.py --rods "Trident Rod" "No-Life Rod" --sort luck --top 10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

DEFAULT_URL = "https://fischipedia.org/wiki/Fishing_Rods"


@dataclass
class Rod:
    name: str
    source: str
    lure_speed: float | None = None
    luck: float | None = None
    control: float | None = None
    resilience: float | None = None
    max_kg: float | None = None
    price: float | None = None
    passive: str | None = None


class WikiTableParser(HTMLParser):
    """Extract table rows from HTML, preserving enough structure for stat parsing."""

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_tag = ""

        self._table_depth = 0
        self._cell_parts: list[str] = []

        self.tables: list[list[dict[str, list[str]]]] = []
        self._current_table: list[dict[str, list[str]]] = []
        self._current_row_cells: list[str] = []
        self._current_row_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table_depth += 1
            if not self.in_table:
                self.in_table = True
                self._current_table = []
            return

        if self.in_table and tag == "tr":
            self.in_row = True
            self._current_row_cells = []
            self._current_row_tags = []
            return

        if self.in_row and tag in {"th", "td"}:
            self.in_cell = True
            self.cell_tag = tag
            self._cell_parts = []
            return

        if self.in_cell and tag == "br":
            self._cell_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_cell and tag in {"th", "td"}:
            text = normalize_space("".join(self._cell_parts))
            self._current_row_cells.append(text)
            self._current_row_tags.append(self.cell_tag)
            self.in_cell = False
            self.cell_tag = ""
            self._cell_parts = []
            return

        if self.in_row and tag == "tr":
            if self._current_row_cells:
                self._current_table.append(
                    {"tags": self._current_row_tags[:], "cells": self._current_row_cells[:]}
                )
            self.in_row = False
            return

        if tag == "table" and self.in_table:
            self._table_depth -= 1
            if self._table_depth == 0:
                self.in_table = False
                if self._current_table:
                    self.tables.append(self._current_table[:])
                self._current_table = []


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def strip_tags(value: str) -> str:
    return normalize_space(re.sub(r"<[^>]+>", " ", value))


def parse_number(value: str) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def choose_rod_table(tables: list[list[dict[str, list[str]]]]) -> tuple[list[str], list[list[str]]] | None:
    required = {"rod", "lure", "luck", "control", "resilience"}
    for table in tables:
        if not table:
            continue
        header_row = table[0]["cells"]
        lowered = [h.lower() for h in header_row]
        if required.issubset(" ".join(lowered).split()):
            rows = [r["cells"] for r in table[1:] if r["cells"]]
            return header_row, rows

        joined_headers = " | ".join(lowered)
        if all(k in joined_headers for k in required):
            rows = [r["cells"] for r in table[1:] if r["cells"]]
            return header_row, rows
    return None


def map_header_indices(headers: list[str]) -> dict[str, int]:
    key_map = {
        "name": [["rod"], ["name"]],
        "source": [["source"], ["obtain"]],
        "lure_speed": [["lure"]],
        "luck": [["luck"]],
        "control": [["control"]],
        "resilience": [["resilience"]],
        "max_kg": [["max", "kg"]],
        "price": [["price"], ["cost"], ["c$"], ["$"]],
        "passive": [["passive"]],
    }
    indices: dict[str, int] = {}
    normalized = [h.lower() for h in headers]

    for key, groups in key_map.items():
        for i, header in enumerate(normalized):
            if any(all(n in header for n in group) for group in groups):
                indices[key] = i
                break

    if "name" not in indices:
        indices["name"] = 0
    if "source" not in indices:
        indices["source"] = 1 if len(headers) > 1 else 0
    return indices


def row_to_rod(row: list[str], idx: dict[str, int]) -> Rod | None:
    def get(col: str) -> str:
        i = idx.get(col)
        if i is None or i >= len(row):
            return ""
        return row[i]

    name = get("name")
    if not name:
        return None

    return Rod(
        name=name,
        source=get("source"),
        lure_speed=parse_number(get("lure_speed")),
        luck=parse_number(get("luck")),
        control=parse_number(get("control")),
        resilience=parse_number(get("resilience")),
        max_kg=parse_number(get("max_kg")),
        price=parse_number(get("price")),
        passive=get("passive") or None,
    )


def parse_rods_from_html(html: str) -> list[Rod]:
    parser = WikiTableParser()
    parser.feed(html)

    selected = choose_rod_table(parser.tables)
    if not selected:
        raise RuntimeError("Could not find a fishing-rod stats table on the page.")

    headers, rows = selected
    indices = map_header_indices(headers)

    rods: list[Rod] = []
    for row in rows:
        rod = row_to_rod(row, indices)
        if rod:
            rods.append(rod)

    if not rods:
        raise RuntimeError("Table was found, but no rod rows were parsed.")
    return rods


def fetch_rods(url: str) -> list[Rod]:
    req = Request(url, headers={"User-Agent": "rod-compare-bot/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"Request failed with status {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc

    return parse_rods_from_html(html)


def load_rods_from_local_html(path: str) -> list[Rod]:
    file_path = Path(path)
    if not file_path.exists():
        raise RuntimeError(f"Local HTML file does not exist: {file_path}")
    try:
        html = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html = file_path.read_text(encoding="latin-1")
    return parse_rods_from_html(html)


def wiki_base_from_url(url: str) -> str:
    match = re.match(r"^(https?://[^/]+)/", url)
    if not match:
        return "https://fischipedia.org"
    return match.group(1)


def slugify_wiki_title(title: str) -> str:
    cleaned = re.sub(r"\s+", "_", title.strip())
    cleaned = cleaned.replace("/", "_")
    return cleaned


def extract_passive_from_rod_page(html: str) -> str | None:
    # Target common wiki table patterns like:
    # <th>Passive</th><td>...</td>
    patterns = [
        r"<th[^>]*>\s*Passive\s*</th>\s*<td[^>]*>(.*?)</td>",
        r"<td[^>]*>\s*Passive\s*</td>\s*<td[^>]*>(.*?)</td>",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            passive = strip_tags(match.group(1))
            if passive and passive != "-":
                return passive
    return None


def fetch_rod_page_passive(rod_name: str, wiki_base: str) -> str | None:
    rod_url = f"{wiki_base}/wiki/{slugify_wiki_title(rod_name)}"
    req = Request(rod_url, headers={"User-Agent": "rod-compare-bot/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError):
        return None
    return extract_passive_from_rod_page(html)


def enrich_passives_online(rods: list[Rod], fishing_rods_url: str) -> None:
    wiki_base = wiki_base_from_url(fishing_rods_url)
    for rod in rods:
        fetched = fetch_rod_page_passive(rod.name, wiki_base)
        if fetched:
            rod.passive = fetched


def filter_rods(rods: Iterable[Rod], names: list[str] | None) -> list[Rod]:
    if not names:
        return list(rods)
    wanted = {n.lower() for n in names}
    return [rod for rod in rods if rod.name.lower() in wanted]


def compare_rows(rods: list[Rod], sort_by: str) -> list[Rod]:
    return sorted(rods, key=lambda r: getattr(r, sort_by) if getattr(r, sort_by) is not None else float("-inf"), reverse=True)


def print_table(rods: list[Rod]) -> None:
    headers = ["Rod", "Lure", "Luck", "Control", "Resilience", "MaxKg", "Price", "Passive", "Source"]
    rows = [
        [
            rod.name,
            fmt(rod.lure_speed),
            fmt(rod.luck),
            fmt(rod.control),
            fmt(rod.resilience),
            fmt(rod.max_kg),
            fmt(rod.price),
            rod.passive or "-",
            rod.source,
        ]
        for rod in rods
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line(values: list[str]) -> str:
        return " | ".join(v.ljust(widths[i]) for i, v in enumerate(values))

    print(line(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(line(row))


def fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Fisch fishing rods from the wiki table.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Wiki page URL containing rod stats.")
    parser.add_argument(
        "--input-html",
        help="Optional path to a locally saved Fishing_Rods HTML page. If provided, no network request is made.",
    )
    parser.add_argument("--rods", nargs="*", help="Specific rod names to compare.")
    parser.add_argument(
        "--sort",
        choices=["lure_speed", "luck", "control", "resilience", "max_kg", "price"],
        default="luck",
        help="Stat used to sort output.",
    )
    parser.add_argument("--top", type=int, default=0, help="Show only the top N rods after sorting. 0 = all.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text table.")
    parser.add_argument(
        "--scan-passives",
        action="store_true",
        help="Online mode only: fetch each rod's wiki page and enrich/overwrite passive data.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.scan_passives and args.input_html:
        print("Error: --scan-passives requires online wiki access and cannot be used with --input-html.", file=sys.stderr)
        return 2

    try:
        if args.input_html:
            rods = load_rods_from_local_html(args.input_html)
        else:
            rods = fetch_rods(args.url)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.scan_passives:
        enrich_passives_online(rods, args.url)

    rods = filter_rods(rods, args.rods)
    if not rods:
        print("No matching rods found for the provided --rods names.", file=sys.stderr)
        return 2

    rods = compare_rows(rods, args.sort)
    if args.top and args.top > 0:
        rods = rods[: args.top]

    if args.json:
        print(json.dumps([asdict(r) for r in rods], indent=2))
    else:
        print_table(rods)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
