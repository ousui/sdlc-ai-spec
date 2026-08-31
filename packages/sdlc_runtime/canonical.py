"""Deterministic Markdown/YAML helpers shared by SDLC Phase runtimes.

This module intentionally supports only the constrained artifact syntax emitted by
sdlc-ai-spec runtimes. It is not a general YAML or Markdown implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
import re
from typing import Any, Mapping, Sequence

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REFERENCE_RE = re.compile(
    r"^(?P<artifact>(?:CTX|REQ|DSN|PLN|IMP|VFY|RLS)-[0-9]{14}-[0-9]{2,})"
    r"@(?P<revision>[1-9][0-9]*)(?:[#/][A-Za-z0-9._:+%-]+)?$"
)
GATE_HEADING = "## 门禁 Gate"
CHECK_HEADERS = (
    "Check ID",
    "检查项 Check",
    "结果 Result",
    "证据或说明 Evidence or Notes",
)
FINAL_CONFIRMATION_HEADERS = (
    "Revision",
    "Control Input Digest",
    "Evaluation Contract Set",
    "Check Set Result Digest",
    "Result",
    "Mode",
    "Confirmer",
    "Role",
    "Authority Reference",
    "Accepted Exception References",
    "Confirmed At",
)
GATE_SUMMARY_HEADERS = (
    "Evaluated Revision",
    "Control Input Digest",
    "Evaluation Contract Set",
    "Check Set Result Digest",
    "Gate Result",
    "Exception References",
    "Evaluator",
    "Evaluated At",
)


class CanonicalFormatError(ValueError):
    """Raised when canonical artifact bytes violate the supported fixed syntax."""

    code = "CANONICAL_FORMAT_ERROR"


@dataclass(frozen=True)
class MarkdownTable:
    headers: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]
    raw_rows: tuple[str, ...]


@dataclass(frozen=True)
class ParsedCanonicalArtifact:
    front_matter: Mapping[str, Any]
    text: str
    body: str
    tables: tuple[MarkdownTable, ...]


def sha256_bytes(raw_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw_bytes).hexdigest()


def decode_primary_markdown(raw_bytes: bytes) -> str:
    if not isinstance(raw_bytes, bytes):
        raise CanonicalFormatError("primary Canonical Blob must be raw bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise CanonicalFormatError("primary Markdown must not contain a UTF-8 BOM")
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalFormatError("primary Markdown must be valid UTF-8") from exc
    if "\r" in text:
        raise CanonicalFormatError("primary Markdown must use LF line endings")
    return text


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "[]":
        return []
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if re.fullmatch(r"[0-9]+", value):
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise CanonicalFormatError("primary Markdown must start with YAML Front Matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise CanonicalFormatError("YAML Front Matter closing marker is missing")
    raw = text[4:end]
    body = text[end + 5 :]
    result: dict[str, Any] = {}
    active_list: str | None = None
    for number, line in enumerate(raw.splitlines(), start=2):
        if not line.strip():
            continue
        if line.startswith("  - "):
            if active_list is None:
                raise CanonicalFormatError(
                    f"Front Matter list item has no owning key at line {number}"
                )
            result[active_list].append(_parse_scalar(line[4:]))
            continue
        if line.startswith((" ", "\t")):
            raise CanonicalFormatError(
                f"Unsupported Front Matter indentation at line {number}"
            )
        if ":" not in line:
            raise CanonicalFormatError(
                f"Front Matter entry is not key:value at line {number}"
            )
        key, value = line.split(":", 1)
        key = key.strip()
        if not key or key in result:
            raise CanonicalFormatError(
                f"Front Matter key is empty or duplicated at line {number}"
            )
        if value.strip():
            result[key] = _parse_scalar(value)
            active_list = None
        else:
            result[key] = []
            active_list = key
    return result, body


def _split_table_row(line: str) -> tuple[str, ...]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise CanonicalFormatError("Markdown table rows must start and end with |")
    return tuple(cell.strip() for cell in stripped[1:-1].split("|"))


def _is_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_markdown_tables(text: str) -> tuple[MarkdownTable, ...]:
    lines = text.splitlines()
    tables: list[MarkdownTable] = []
    index = 0
    while index + 1 < len(lines):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            index += 1
            continue
        try:
            headers = _split_table_row(line)
            separator = _split_table_row(lines[index + 1])
        except CanonicalFormatError:
            index += 1
            continue
        if len(headers) != len(separator) or not _is_separator(separator):
            index += 1
            continue
        raw_rows: list[str] = []
        rows: list[Mapping[str, str]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            raw_line = lines[cursor].strip()
            cells = _split_table_row(raw_line)
            if len(cells) != len(headers):
                raise CanonicalFormatError(
                    f"Markdown table row has {len(cells)} cells; expected {len(headers)}"
                )
            rows.append(dict(zip(headers, cells)))
            raw_rows.append(raw_line)
            cursor += 1
        tables.append(
            MarkdownTable(
                headers=tuple(headers), rows=tuple(rows), raw_rows=tuple(raw_rows)
            )
        )
        index = cursor
    return tuple(tables)


def parse_canonical_artifact(raw_bytes: bytes) -> ParsedCanonicalArtifact:
    text = decode_primary_markdown(raw_bytes)
    front_matter, body = parse_front_matter(text)
    return ParsedCanonicalArtifact(
        front_matter=front_matter,
        text=text,
        body=body,
        tables=parse_markdown_tables(text),
    )


def find_tables(
    artifact: ParsedCanonicalArtifact, headers: Sequence[str]
) -> tuple[MarkdownTable, ...]:
    expected = tuple(headers)
    return tuple(table for table in artifact.tables if table.headers == expected)


def require_single_table(
    artifact: ParsedCanonicalArtifact, headers: Sequence[str], name: str
) -> MarkdownTable:
    matches = find_tables(artifact, headers)
    if len(matches) != 1:
        raise CanonicalFormatError(
            f"{name} must appear exactly once; found {len(matches)}"
        )
    return matches[0]


def require_single_row(table: MarkdownTable, name: str) -> Mapping[str, str]:
    if len(table.rows) != 1:
        raise CanonicalFormatError(
            f"{name} must contain exactly one data row; found {len(table.rows)}"
        )
    return table.rows[0]


def compute_control_input_digest(raw_bytes: bytes) -> str:
    text = decode_primary_markdown(raw_bytes)
    if not text.startswith("---\n"):
        raise CanonicalFormatError("YAML Front Matter is required")
    front_end = text.find("\n---\n", 4)
    if front_end < 0:
        raise CanonicalFormatError("YAML Front Matter closing marker is missing")
    front = text[4:front_end]
    body = text[front_end + 5 :]
    status_matches = list(re.finditer(r"(?m)^status:[^\n]*(?:\n|$)", front))
    if len(status_matches) != 1:
        raise CanonicalFormatError(
            f"Front Matter must contain exactly one status line; found {len(status_matches)}"
        )
    match = status_matches[0]
    projected_front = front[: match.start()] + front[match.end() :]
    gate_index = body.find(GATE_HEADING)
    if gate_index < 0:
        raise CanonicalFormatError("Gate heading is missing")
    projected = "---\n" + projected_front + "\n---\n" + body[:gate_index]
    return sha256_bytes(projected.encode("utf-8"))


def check_set_rows(artifact: ParsedCanonicalArtifact) -> tuple[str, ...]:
    rows: list[tuple[str, str]] = []
    tables = find_tables(artifact, CHECK_HEADERS)
    for table_index, table in enumerate(tables):
        table_ids = tuple(row["Check ID"] for row in table.rows)
        if table_ids != tuple(sorted(table_ids)):
            raise CanonicalFormatError(
                "Current Check rows must be sorted by Check ID inside each Check table"
            )
        contains_core = any(check_id.startswith("CORE-G-") for check_id in table_ids)
        if table_index == 0 and not contains_core:
            raise CanonicalFormatError("The first Check table must be the Core Check group")
        if table_index > 0 and contains_core:
            raise CanonicalFormatError("Core Checks must appear only in the first Check table")
        for row, raw_line in zip(table.rows, table.raw_rows):
            check_id = row["Check ID"]
            if check_id == "CORE-G-009":
                continue
            if not re.fullmatch(r"[A-Z0-9-]+", check_id):
                raise CanonicalFormatError(f"Invalid Check ID: {check_id}")
            result = row["结果 Result"]
            if result == "pending":
                raise CanonicalFormatError(
                    f"Check Set Result Digest cannot include pending Check: {check_id}"
                )
            rows.append((check_id, raw_line))
    if not rows:
        raise CanonicalFormatError("No Check rows were found")
    seen: set[str] = set()
    ordered: list[str] = []
    for check_id, raw_line in rows:
        if check_id in seen:
            raise CanonicalFormatError(f"Duplicate current Check ID: {check_id}")
        seen.add(check_id)
        ordered.append(raw_line)
    return tuple(ordered)


def compute_check_set_result_digest(artifact: ParsedCanonicalArtifact) -> str:
    data = "".join(row + "\n" for row in check_set_rows(artifact)).encode("utf-8")
    return sha256_bytes(data)


def parse_reference_set(value: str) -> tuple[str, ...]:
    value = value.strip()
    if value in {"", "None", "N/A"}:
        return ()
    items = tuple(part.strip() for part in value.split(","))
    if any(not item for item in items) or len(set(items)) != len(items):
        raise CanonicalFormatError("Reference Set contains empty or duplicate entries")
    return items


def validate_digest(value: str, name: str) -> None:
    if not DIGEST_RE.fullmatch(value):
        raise CanonicalFormatError(f"{name} must be sha256:<64 lowercase hex>")


def exact_artifact_reference(value: str) -> tuple[str, int]:
    match = REFERENCE_RE.fullmatch(value)
    if match is None:
        raise CanonicalFormatError("Reference must identify an exact numeric Revision")
    return match.group("artifact"), int(match.group("revision"))


def authority_reference(value: str) -> tuple[str, str]:
    marker = "@sha256:"
    if not isinstance(value, str) or marker not in value:
        raise CanonicalFormatError(
            "Authority Reference must be project-relative path@sha256:<digest>"
        )
    path_value, separator, suffix = value.rpartition(marker)
    digest = "sha256:" + suffix
    if not separator or not path_value or "\n" in path_value or "\r" in path_value:
        raise CanonicalFormatError(
            "Authority Reference must contain a non-empty project-relative path"
        )
    path = PurePosixPath(path_value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CanonicalFormatError(
            "Authority Reference path must remain inside the project"
        )
    validate_digest(digest, "Authority Reference digest")
    return path_value, digest
