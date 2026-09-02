#!/usr/bin/env python3
"""Recover the most complete historical remaining-phase source candidate.

This is an internal development utility. It never updates formal branches and
only emits a candidate after the recovered source passes the IMP gate and the
complete repository regression against the frozen PLN base.
"""
from __future__ import annotations

import base64
import bz2
import gzip
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = Path(sys.argv[1]).resolve()
DESTINATION = Path(sys.argv[2]).resolve()
WORK = DESTINATION.parent / "recovery-work"
REPORT_PATH = DESTINATION.parent / "recovery-report.json"


def run(command: list[str], cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONWARNINGS": "default"},
    )


def extract_nested_archives(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    queue = list(source.rglob("*.zip"))
    seen: set[tuple[str, str]] = set()
    while queue:
        archive = queue.pop(0)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        key = (archive.name, digest)
        if key in seen:
            continue
        seen.add(key)
        destination = target / f"zip-{len(seen):04d}-{archive.stem}"
        try:
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(destination)
        except Exception:
            continue
        queue.extend(destination.rglob("*.zip"))


def repository_roots(root: Path) -> list[Path]:
    result: list[Path] = []
    for marker in root.rglob("skills/sdlc-400-imp/SKILL.md"):
        candidate = marker.parents[2]
        if (candidate / "skills/sdlc-400-imp/scripts/runtime.py").is_file():
            result.append(candidate)
    return sorted(set(result), key=str)


def decode_layers(raw: bytes):
    yield "raw", raw
    compact = re.sub(rb"\s+", b"", raw)
    compact += b"=" * ((4 - len(compact) % 4) % 4)
    for label, decoder in (("base64", base64.b64decode), ("urlsafe-base64", base64.urlsafe_b64decode)):
        try:
            decoded = decoder(compact)
        except Exception:
            continue
        yield label, decoded


def decompress_layers(raw: bytes):
    yield "identity", raw
    for label, decoder in (
        ("xz", lambda value: lzma.decompress(value, format=lzma.FORMAT_AUTO)),
        ("lzma-alone", lambda value: lzma.decompress(value, format=lzma.FORMAT_ALONE)),
        ("gzip", gzip.decompress),
        ("bz2", bz2.decompress),
        ("zlib", zlib.decompress),
    ):
        try:
            yield label, decoder(raw)
        except Exception:
            continue


def materialize(payload: bytes, destination: Path) -> Path | None:
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as handle:
            handle.extractall(destination / "archive")
        return destination / "archive"
    except Exception:
        pass
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as handle:
            handle.extractall(destination / "archive")
        return destination / "archive"
    except Exception:
        pass
    if b"diff --git " in payload[:65536]:
        patch = destination / "candidate.patch"
        patch.write_bytes(payload)
        return patch
    return None


def restore_base(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
    subprocess.run(["git", "config", "user.name", "SHUAI.W"], cwd=destination, check=True)
    subprocess.run(["git", "config", "user.email", "x@ousui.org"], cwd=destination, check=True)
    subprocess.run(["git", "add", "-A"], cwd=destination, check=True)
    subprocess.run(["git", "commit", "-qm", "frozen PLN base"], cwd=destination, check=True)


def overlay_tree(source: Path, destination: Path) -> bool:
    roots = repository_roots(source)
    if not roots:
        return False
    recovered = roots[0]
    for item in recovered.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(recovered)
        if ".git" in relative.parts or relative.as_posix().startswith(".github/workflows/"):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
    return True


def apply_materialized(materialized: Path, destination: Path) -> bool:
    if materialized.is_file():
        for command in (
            ["git", "apply", "--index", "--whitespace=nowarn", str(materialized)],
            ["git", "apply", "--index", "--3way", "--whitespace=nowarn", str(materialized)],
        ):
            completed = run(command, destination)
            if completed.returncode == 0:
                return True
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=destination, check=True)
        return False
    return overlay_tree(materialized, destination)


def validate_imp(candidate: Path) -> tuple[bool, list[dict[str, object]]]:
    required = (
        "skills/sdlc-400-imp/SKILL.md",
        "skills/sdlc-400-imp/scripts/runtime.py",
        "skills/sdlc-400-imp/references/source-lock.json",
        "tools/validate_sdlc_400_imp_source_lock.py",
        "tools/test_sdlc_400_imp_runtime_independence.py",
        "tests/evals/run_sdlc_400_imp_eval.py",
    )
    missing = [path for path in required if not (candidate / path).is_file()]
    if missing:
        return False, [{"missing": missing}]
    commands = [
        ["python3", "-m", "compileall", "-q", "packages", "scripts", "skills"],
        ["python3", "tools/validate_runtime_contracts.py"],
        ["python3", "tools/validate_skill_interfaces.py"],
        ["python3", "tools/validate_lifecycle_query.py"],
        ["python3", "tools/validate_sdlc_status.py"],
        ["python3", "tools/validate_sdlc_300_pln_source_lock.py"],
        ["python3", "tools/test_sdlc_300_pln_runtime_independence.py"],
        ["python3", "tests/evals/run_sdlc_300_pln_eval.py"],
        ["python3", "tools/validate_sdlc_400_imp_source_lock.py"],
        ["python3", "tools/test_sdlc_400_imp_runtime_independence.py"],
        ["python3", "tests/evals/run_sdlc_400_imp_eval.py"],
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    ]
    logs: list[dict[str, object]] = []
    for command in commands:
        completed = run(command, candidate, timeout=3600)
        logs.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-5000:],
                "stderr": completed.stderr[-5000:],
            }
        )
        if completed.returncode != 0:
            return False, logs
    return True, logs


def chunk_sequences(root: Path):
    matcher = re.compile(r"chunk[-_](\d+)(?:[-_](\d+))?$", re.IGNORECASE)
    groups: dict[Path, list[tuple[int, int, Path]]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        match = matcher.search(path.name)
        if not match:
            continue
        first = int(match.group(1))
        last = int(match.group(2) or first)
        groups.setdefault(path.parent, []).append((first, last, path))
    for directory, entries in groups.items():
        by_start: dict[int, list[tuple[int, int, Path]]] = {}
        for entry in entries:
            by_start.setdefault(entry[0], []).append(entry)
        start = 0 if 0 in by_start else min(by_start)
        sequences: list[list[tuple[int, int, Path]]] = []

        def walk(index: int, selected: list[tuple[int, int, Path]]) -> None:
            if len(sequences) >= 512:
                return
            options = by_start.get(index)
            if not options:
                sequences.append(selected.copy())
                return
            options = sorted(options, key=lambda item: (-(item[1] - item[0]), str(item[2])))[:12]
            for option in options:
                walk(option[1] + 1, selected + [option])

        walk(start, [])
        for sequence in sequences:
            if sequence:
                yield directory, sequence


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    expanded = WORK / "expanded"
    extract_nested_archives(MATERIALS, expanded)
    report: dict[str, object] = {"direct": [], "chunks": [], "success": None}

    direct_candidates = repository_roots(MATERIALS) + repository_roots(expanded)
    for index, source in enumerate(direct_candidates):
        trial = WORK / f"direct-{index:04d}"
        restore_base(trial)
        overlay_tree(source, trial)
        workflows = ROOT / ".github/workflows"
        if (trial / ".github/workflows").exists():
            shutil.rmtree(trial / ".github/workflows")
        shutil.copytree(workflows, trial / ".github/workflows")
        ok, logs = validate_imp(trial)
        report["direct"].append({"source": str(source), "ok": ok, "logs": logs})
        if ok:
            if DESTINATION.exists():
                shutil.rmtree(DESTINATION)
            shutil.copytree(trial, DESTINATION, ignore=shutil.ignore_patterns(".git"))
            report["success"] = {"kind": "direct", "source": str(source)}
            REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 0

    for index, (directory, sequence) in enumerate(chunk_sequences(MATERIALS)):
        raw = b"".join(path.read_bytes() for _, _, path in sequence)
        for encoding, encoded in decode_layers(raw):
            for compression, payload in decompress_layers(encoded):
                materialized = materialize(payload, WORK / f"payload-{index:04d}-{encoding}-{compression}")
                if materialized is None:
                    continue
                trial = WORK / f"chunk-{index:04d}-{encoding}-{compression}"
                restore_base(trial)
                if not apply_materialized(materialized, trial):
                    continue
                if (trial / ".github/workflows").exists():
                    shutil.rmtree(trial / ".github/workflows")
                shutil.copytree(ROOT / ".github/workflows", trial / ".github/workflows")
                ok, logs = validate_imp(trial)
                report["chunks"].append(
                    {
                        "directory": str(directory),
                        "sequence": [(first, last, str(path)) for first, last, path in sequence],
                        "encoding": encoding,
                        "compression": compression,
                        "ok": ok,
                        "logs": logs,
                    }
                )
                if ok:
                    if DESTINATION.exists():
                        shutil.rmtree(DESTINATION)
                    shutil.copytree(trial, DESTINATION, ignore=shutil.ignore_patterns(".git"))
                    report["success"] = {
                        "kind": "chunks",
                        "directory": str(directory),
                        "encoding": encoding,
                        "compression": compression,
                    }
                    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    return 0

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
