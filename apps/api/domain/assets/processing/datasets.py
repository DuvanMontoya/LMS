# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
from __future__ import annotations

import csv
import json
from pathlib import Path

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import MAX_CSV_COLUMNS, MAX_JSON_DEPTH, MAX_JSON_NODES

from .common import ProcessingResult

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def process_dataset(source: Path, declared_mime_type: str) -> ProcessingResult:
    if declared_mime_type == "text/csv":
        return _process_csv(source)
    if declared_mime_type == "application/json":
        return _process_json(source)
    if declared_mime_type == "text/plain":
        return _process_text(source)
    raise AssetFormatInvalid("Unsupported dataset type.")


def _process_csv(source: Path) -> ProcessingResult:
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as raw:
            sample = raw.read(64 * 1024)
            if "\x00" in sample:
                raise AssetFormatInvalid("CSV contains NUL bytes.")
            raw.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            reader = csv.reader(raw, dialect)
            header = next(reader)
            if (
                not header
                or len(header) > MAX_CSV_COLUMNS
                or any(not column.strip() for column in header)
            ):
                raise AssetFormatInvalid("CSV header is invalid.")
            row_count = 0
            samples: list[list[str]] = []
            for row in reader:
                if len(row) != len(header):
                    raise AssetFormatInvalid("CSV rows have inconsistent columns.")
                row_count += 1
                if len(samples) < 10:
                    samples.append([_safe_preview(value) for value in row])
    except AssetFormatInvalid:
        raise
    except (UnicodeDecodeError, csv.Error, OSError, StopIteration) as error:
        raise AssetFormatInvalid("Malformed UTF-8 CSV.") from error
    return ProcessingResult(
        detected_mime_type="text/csv",
        extension=".csv",
        row_count=row_count,
        column_count=len(header),
        technical_metadata={
            "delimiter": dialect.delimiter,
            "columns": [column.strip()[:500] for column in header],
            "sample_rows": samples,
            "encoding": "utf-8",
        },
    )


def _safe_preview(value: str) -> str:
    limited = value[:500]
    if limited.startswith(_FORMULA_PREFIXES):
        return "'" + limited
    return limited


def _process_json(source: Path) -> ProcessingResult:
    try:
        text = source.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as error:
        raise AssetFormatInvalid("Dataset JSON must be UTF-8.") from error
    if "\x00" in text:
        raise AssetFormatInvalid("Dataset JSON contains NUL bytes.")
    depth = 0
    maximum_depth = 0
    nodes = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            nodes += 1
            maximum_depth = max(maximum_depth, depth)
        elif character in "]}":
            depth -= 1
            if depth < 0:
                raise AssetFormatInvalid("Dataset JSON is malformed.")
        elif character in ",:":
            nodes += 1
        if maximum_depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            raise AssetFormatInvalid("Dataset JSON complexity exceeds the limit.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise AssetFormatInvalid("Dataset JSON is malformed.") from error
    if not isinstance(payload, (dict, list)):
        raise AssetFormatInvalid("Dataset JSON must contain an object or array.")
    if isinstance(payload, dict):
        item_count = len(payload)
        sample_keys = [str(key)[:500] for key in list(payload)[:20]]
        top_level = "object"
    else:
        item_count = len(payload)
        sample_keys = []
        top_level = "array"
    return ProcessingResult(
        detected_mime_type="application/json",
        extension=".json",
        row_count=item_count,
        technical_metadata={
            "top_level_type": top_level,
            "item_count": item_count,
            "sample_keys": sample_keys,
            "maximum_depth": maximum_depth,
            "encoding": "utf-8",
        },
    )


def _process_text(source: Path) -> ProcessingResult:
    try:
        text = source.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as error:
        raise AssetFormatInvalid("Text dataset must be UTF-8.") from error
    if "\x00" in text:
        raise AssetFormatInvalid("Text dataset contains NUL bytes.")
    line_count = text.count("\n") + (1 if text else 0)
    return ProcessingResult(
        detected_mime_type="text/plain",
        extension=".txt",
        row_count=line_count,
        technical_metadata={
            "line_count": line_count,
            "character_count": len(text),
            "encoding": "utf-8",
            "sample": text[:2_000],
        },
    )
