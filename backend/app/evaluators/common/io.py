from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional


def first_existing_dir(root: Path, candidates: list[str]) -> Optional[Path]:
    for candidate in candidates:
        target = root / candidate
        if target.is_dir():
            return target
    return None


def list_csv_files(directory: Path) -> list[Path]:
    return sorted([path for path in directory.glob("*.csv") if path.is_file()])


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return [row for row in reader if any(cell.strip() for cell in row)]


def load_json_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
        return records
    data = json.loads(text)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unsupported JSON content in {path}")


def normalize_stem(path: Path, suffixes: list[str]) -> str:
    stem = path.stem
    for suffix in suffixes:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem
