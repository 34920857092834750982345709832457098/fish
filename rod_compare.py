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
    location: str | None = None
    stage: str | None = None
    lure_speed: float | None = None
    luck: float | None = None
    control: float | None = None
    resilience: float | None = None
    max_kg: float | None = None
    price: float | None = None
    durability: str | None = None
    disturbance: str | None = None
    hunt_focus: str | None = None
    line_distance: str | None = None
    passive: str | None = None


DURABILITY_BONUS_MAP = {
    100: "Lava",
    150: "Lava, Noxious Fluid",
    200: "Lava, Noxious Fluid, Brine",
}


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
    lowered = value.lower().strip()
    if "infinite" in lowered or lowered in {"inf", "∞"}:
        return float("inf")
    cleaned = value.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def choose_rod_tables(tables: list[list[dict[str, list[str]]]]) -> list[tuple[list[str], list[list[str]]]]:
    target_keywords = ["rod", "lure", "luck", "control", "resilience", "max", "price", "passive"]
    matches: list[tuple[list[str], list[list[str]]]] = []
    for table in tables:
        if not table:
            continue
        for row_index, row in enumerate(table):
            header_row = row["cells"]
            lowered = [h.lower() for h in header_row]
            joined_headers = " | ".join(lowered)

            score = sum(1 for keyword in target_keywords if keyword in joined_headers)
            has_rod = "rod" in joined_headers or "name" in joined_headers
            has_any_stat = any(k in joined_headers for k in ("lure", "luck", "control", "resilience"))

            if has_rod and has_any_stat and score >= 4:
                rows = [r["cells"] for r in table[row_index + 1 :] if r["cells"]]
                matches.append((header_row, rows))
                break
    return matches


def parse_rods_from_wikitext(raw_text: str) -> list[Rod]:
    # Pull only table rows (`| ... || ...`) from wikitext.
    lines = [line.strip() for line in raw_text.splitlines()]
    row_lines = [line[1:].strip() for line in lines if line.startswith("|") and "||" in line]
    if not row_lines:
        raise RuntimeError("Could not find rod rows in raw wiki text.")

    # Build headers from the first `!` row when available.
    header_lines = [line[1:].strip() for line in lines if line.startswith("!") and "!!" in line]
    if header_lines:
        headers = [normalize_space(part) for part in header_lines[0].split("!!")]
    else:
        headers = ["Rod", "Source", "Lure Speed", "Luck", "Control", "Resilience", "Max Kg", "Price", "Passive"]

    idx = map_header_indices(headers)
    rods: list[Rod] = []
    for line in row_lines:
        cells = [normalize_space(c) for c in line.split("||")]
        rod = row_to_rod(cells, idx)
        if rod:
            rods.append(rod)

    if not rods:
        raise RuntimeError("Raw wiki text was found, but no rod rows were parsed.")
    return rods


def map_header_indices(headers: list[str]) -> dict[str, int]:
    key_map = {
        "name": [["rod"], ["name"]],
        "source": [["source"], ["obtain"]],
        "location": [["location"], ["loc"]],
        "stage": [["stage"]],
        "lure_speed": [["lure"]],
        "luck": [["luck"]],
        "control": [["control"]],
        "resilience": [["resilience"]],
        "max_kg": [["max", "kg"]],
        "price": [["price"], ["cost"], ["c$"], ["$"]],
        "durability": [["durability"]],
        "disturbance": [["disturbance"]],
        "hunt_focus": [["hunt", "focus"]],
        "line_distance": [["line", "distance"]],
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

    source_text, location_text, price_value = split_source_location_price(
        get("source"),
        get("location"),
        parse_number(get("price")),
    )

    disturbance, hunt_focus = split_disturbance_and_focus(get("disturbance"), get("hunt_focus"))

    return Rod(
        name=name,
        source=source_text,
        location=location_text,
        stage=get("stage") or None,
        lure_speed=parse_number(get("lure_speed")),
        luck=parse_number(get("luck")),
        control=parse_number(get("control")),
        resilience=parse_number(get("resilience")),
        max_kg=parse_number(get("max_kg")),
        price=price_value,
        durability=normalize_durability_text(get("durability") or None),
        disturbance=disturbance,
        hunt_focus=hunt_focus,
        line_distance=get("line_distance") or None,
        passive=get("passive") or None,
    )


def split_source_location_price(
    source_text: str,
    location_text: str,
    price_value: float | None,
) -> tuple[str, str | None, float | None]:
    source_clean = source_text.strip()
    location_clean = location_text.strip() or None
    price_clean = price_value

    if price_clean is None and source_clean:
        if "c$" in source_clean.lower() or "$" in source_clean:
            parsed = parse_number(source_clean)
            if parsed is not None:
                price_clean = parsed
                source_clean = re.sub(r"(?i)c?\$\s*[0-9,]+(?:\.[0-9]+)?", "", source_clean).strip(" -|/")

    if not location_clean and " - " in source_clean:
        left, right = source_clean.split(" - ", 1)
        left_l = left.lower()
        location_hints = ("island", "swamp", "sea", "pond", "river", "ocean", "cave", "bay", "desert", "forest")
        if any(hint in left_l for hint in location_hints):
            location_clean = left.strip()
            source_clean = right.strip()

    return source_clean, location_clean, price_clean


def split_disturbance_and_focus(
    disturbance_text: str,
    hunt_focus_text: str,
) -> tuple[str | None, str | None]:
    disturbance_clean = disturbance_text.strip() or None
    hunt_focus_clean = hunt_focus_text.strip() or None
    if disturbance_clean:
        match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s+(.+)$", disturbance_clean)
        if match and re.search(r"[A-Za-z]", match.group(2)):
            disturbance_clean = match.group(1)
            if not hunt_focus_clean:
                hunt_focus_clean = match.group(2).strip()
    return disturbance_clean, hunt_focus_clean


def normalize_durability_text(value: str | None) -> str | None:
    if not value:
        return None
    numeric = parse_number(value)
    if numeric is None:
        return value
    return DURABILITY_BONUS_MAP.get(int(numeric), value)


def parse_rods_from_html(html: str) -> list[Rod]:
    parser = WikiTableParser()
    parser.feed(html)

    selected = choose_rod_tables(parser.tables)
    if not selected:
        raise RuntimeError("Could not find a fishing-rod stats table on the page.")

    rods: list[Rod] = []
    seen_names: set[str] = set()
    for headers, rows in selected:
        indices = map_header_indices(headers)
        for row in rows:
            rod = row_to_rod(row, indices)
            if rod and rod.name.lower() not in seen_names:
                rods.append(rod)
                seen_names.add(rod.name.lower())

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

    try:
        return parse_rods_from_html(html)
    except RuntimeError:
        # Fallback: many MediaWiki pages expose stable raw markup.
        raw_url = f"{url}?action=raw"
        raw_req = Request(raw_url, headers={"User-Agent": "rod-compare-bot/1.0"})
        try:
            with urlopen(raw_req, timeout=30) as response:
                raw_text = response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError) as exc:
            raise RuntimeError(
                "Could not find a fishing-rod stats table in HTML and raw wiki fallback failed."
            ) from exc
        return parse_rods_from_wikitext(raw_text)


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


def extract_rod_page_details(html: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    matches = re.findall(
        r"<th[^>]*>\s*(.*?)\s*</th>\s*<td[^>]*>(.*?)</td>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for label_html, value_html in matches:
        label = strip_tags(label_html).lower()
        value = strip_tags(value_html)
        if not label or not value:
            continue
        fields[label] = value
    return fields


def normalize_rod_detail_fields(fields: dict[str, str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    mapping = {
        "location": "location",
        "source": "source",
        "price": "price",
        "stage": "stage",
        "lure speed": "lure_speed",
        "luck": "luck",
        "control": "control",
        "resilience": "resilience",
        "max kg": "max_kg",
        "durability": "durability",
        "disturbance": "disturbance",
        "hunt focus": "hunt_focus",
        "line distance": "line_distance",
        "passive": "passive",
    }
    for label, value in fields.items():
        key = mapping.get(label)
        if key:
            mapped[key] = value
    return mapped


def fetch_rod_page_details(rod_name: str, wiki_base: str) -> dict[str, str]:
    rod_url = f"{wiki_base}/wiki/{slugify_wiki_title(rod_name)}"
    req = Request(rod_url, headers={"User-Agent": "rod-compare-bot/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError):
        return {}

    details = normalize_rod_detail_fields(extract_rod_page_details(html))
    if "passive" not in details:
        passive = extract_passive_from_rod_page(html)
        if passive:
            details["passive"] = passive
    return details


def enrich_rod_details_online(rods: list[Rod], fishing_rods_url: str) -> None:
    wiki_base = wiki_base_from_url(fishing_rods_url)
    for rod in rods:
        details = fetch_rod_page_details(rod.name, wiki_base)
        if not details:
            continue
        if details.get("location"):
            rod.location = details["location"]
        if details.get("source"):
            rod.source = details["source"]
        if details.get("stage"):
            rod.stage = details["stage"]
        if details.get("lure_speed"):
            rod.lure_speed = parse_number(details["lure_speed"])
        if details.get("luck"):
            rod.luck = parse_number(details["luck"])
        if details.get("control"):
            rod.control = parse_number(details["control"])
        if details.get("resilience"):
            rod.resilience = parse_number(details["resilience"])
        if details.get("max_kg"):
            rod.max_kg = parse_number(details["max_kg"])
        if details.get("price"):
            parsed_price = parse_number(details["price"])
            if parsed_price is not None:
                rod.price = parsed_price
        if details.get("durability"):
            rod.durability = normalize_durability_text(details["durability"])
        if details.get("disturbance"):
            rod.disturbance = details["disturbance"]
        if details.get("hunt_focus"):
            rod.hunt_focus = details["hunt_focus"]
        rod.disturbance, rod.hunt_focus = split_disturbance_and_focus(rod.disturbance or "", rod.hunt_focus or "")
        if details.get("line_distance"):
            rod.line_distance = details["line_distance"]
        if details.get("passive"):
            rod.passive = details["passive"]


def filter_rods(rods: Iterable[Rod], names: list[str] | None) -> list[Rod]:
    if not names:
        return list(rods)
    wanted = {n.lower() for n in names}
    return [rod for rod in rods if rod.name.lower() in wanted]


def compare_rows(rods: list[Rod], sort_by: str) -> list[Rod]:
    return sorted(rods, key=lambda r: getattr(r, sort_by) if getattr(r, sort_by) is not None else float("-inf"), reverse=True)


def print_table(rods: list[Rod]) -> None:
    headers = [
        "Rod",
        "Lure",
        "Luck",
        "Control",
        "Resilience",
        "MaxKg",
        "Price",
        "Stage",
        "Durability",
        "Disturbance",
        "Hunt Focus",
        "Passive",
        "Location",
        "Source",
    ]
    rows = [
        [
            rod.name,
            fmt(rod.lure_speed),
            fmt(rod.luck),
            fmt(rod.control),
            fmt(rod.resilience),
            fmt(rod.max_kg),
            fmt_price(rod.price, rod.source),
            rod.stage or "-",
            rod.durability or "-",
            rod.disturbance or "-",
            rod.hunt_focus or "-",
            rod.passive or "-",
            rod.location or "-",
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
    if value is None:
        return "-"
    if value == float("inf"):
        return "inf."
    return f"{value:g}"


def fmt_price(value: float | None, source: str) -> str:
    if value is not None:
        return fmt(value)
    if "quest" in source.lower():
        return "quest reward"
    return "-"


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
        help="Online mode only: fetch each rod's wiki page and enrich passive and detailed rod factors.",
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
        enrich_rod_details_online(rods, args.url)

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
