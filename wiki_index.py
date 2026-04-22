#!/usr/bin/env python3
"""Index management for Fisch wiki rod data.

Architecture role:
1) Pull/refresh online data from the wiki.
2) Store a condensed local JSON index for fast UI search/compare.
3) Reload cached data for offline desktop usage.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rod_compare import (
    Rod,
    apply_passive_overrides,
    enrich_rod_details_online,
    fetch_rods,
    load_passive_overrides,
)

DEFAULT_INDEX_FILE = "rods_index.json"


def normalize_rods(rods: list[Rod]) -> list[dict[str, Any]]:
    normalized = [asdict(rod) for rod in rods]
    normalized.sort(key=lambda r: (r.get("name") or "").lower())
    return normalized


def save_index(rods: list[Rod], path: str = DEFAULT_INDEX_FILE) -> Path:
    file_path = Path(path)
    file_path.write_text(json.dumps(normalize_rods(rods), indent=2), encoding="utf-8")
    return file_path


def load_index(path: str = DEFAULT_INDEX_FILE) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Index file not found: {file_path}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def refresh_index(
    wiki_url: str,
    output_path: str = DEFAULT_INDEX_FILE,
    scan_passives: bool = True,
    passive_overrides_path: str = "passive_overrides.txt",
) -> list[dict[str, Any]]:
    rods = fetch_rods(wiki_url)
    if scan_passives:
        enrich_rod_details_online(rods, wiki_url)
    overrides = load_passive_overrides(passive_overrides_path, [rod.name for rod in rods])
    apply_passive_overrides(rods, overrides)
    save_index(rods, output_path)
    return normalize_rods(rods)
