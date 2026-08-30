#!/usr/bin/env python3
"""Validate shared runtime contracts and repository boundaries."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
SKILL_NAME_RE = re.compile(r"^sdlc-[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
UTILITY_NAME_RE = re.compile(r"^sdlc-[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONT_MATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
FRONT_MATTER_DESCRIPTION_RE = re.compile(r"^description:\s*(.+)\s*$", re.MULTILINE)
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

REQUIRED = [
    "skills/_shared/README.md",
    "skills/_shared/contracts/registry.json",
    "skills/_shared/contracts/skill-execution.md",
    "skills/_shared/contracts/artifact-runtime.md",
    "skills/_shared/contracts/phase-runtime.md",
    "skills/_shared/schemas/invocation.schema.json",
    "skills/_shared/schemas/result.schema.json",
    "skills/_shared/schemas/source-lock.schema.json",
    "packages/sdlc_artifact_store/CONTRACT.md",
    "packages/sdlc_runtime/CONTRACT.md",
]

FORBIDDEN_REPOSITORY_BINDINGS = [
    "git@github.com:blade-cdn/sdlc-ai-spec.git",
    "git@github.com:ousui/sdlc-ai-spec.git",
    "blade-cdn/sdlc-ai-spec 是唯一",
    "ousui/sdlc-ai-spec 是唯一",
]

RUNTIME_ROOTS = [ROOT / "skills", ROOT / "packages", ROOT / "scripts"]
RUNTIME_DOC_PATTERNS = [
    re.compile(r"docs/v1\.[0-9]+/"),
    re.compile(r"docs/plugin-development/"),
]


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {"AGENTS.md", "README.md", "CONTRACT.md"}:
            continue
        if path.suffix.lower() not in {".md", ".py", ".json", ".yaml", ".yml"}:
            continue
        yield path


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(f"missing required runtime contract: {relative}")

    if (ROOT / "skills/_shared/SKILL.md").exists():
        fail("skills/_shared must not be a callable Skill")

    for relative in (
        "skills/_shared/contracts/registry.json",
        "skills/_shared/schemas/invocation.schema.json",
        "skills/_shared/schemas/result.schema.json",
        "skills/_shared/schemas/source-lock.schema.json",
    ):
        with (ROOT / relative).open("r", encoding="utf-8") as handle:
            json.load(handle)

    old_work_item = ROOT / "docs/plugin-development/work-items/sdlc-project-context"
    if old_work_item.exists():
        fail("legacy sdlc-project-context work item must not exist on main")

    for runtime_root in RUNTIME_ROOTS:
        for path in iter_text_files(runtime_root):
            text = path.read_text(encoding="utf-8")
            for pattern in RUNTIME_DOC_PATTERNS:
                if pattern.search(text):
                    fail(f"runtime dependency on design docs: {path.relative_to(ROOT)}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() == SELF or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".py", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        if "sdlc-project-context" in text:
            fail(f"legacy Skill name remains: {path.relative_to(ROOT)}")
        for forbidden in FORBIDDEN_REPOSITORY_BINDINGS:
            if forbidden in text:
                fail(f"hard-coded repository binding remains: {path.relative_to(ROOT)}")

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "packages"))
    from sdlc_artifact_store import ArtifactCatalog, ArtifactStore, ContextLineageRegistry  # type: ignore
    from sdlc_runtime import registry_sources  # type: ignore

    registry_path = ROOT / "skills/_shared/contracts/registry.json"
    registry = registry_sources(ROOT, registry_path)
    ids = [item.contract_id for item in registry]
    if len(ids) != len(set(ids)):
        fail("runtime contract IDs are not unique")
    if ids != sorted(ids):
        fail("runtime contract registry is not sorted")
    for item in registry:
        if item.contract_version != "1":
            fail(f"unsupported runtime contract version: {item.contract_id}")

    for operation in (
        "initialize",
        "allocate_artifact",
        "allocate_revision",
        "read_revision",
        "write_open_revision",
        "freeze_revision",
        "abandon_revision",
        "resolve_exact_reference",
        "verify_digest",
    ):
        if not hasattr(ArtifactStore, operation):
            fail(f"ArtifactStore missing public operation: {operation}")
    for public_type in (ArtifactCatalog, ContextLineageRegistry):
        if not isinstance(public_type.__name__, str):
            fail("runtime public type is invalid")

    skills_root = ROOT / "skills"
    formal_skills = 0
    for directory in skills_root.iterdir():
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        formal_skills += 1
        if not (
            SKILL_NAME_RE.fullmatch(directory.name)
            or UTILITY_NAME_RE.fullmatch(directory.name)
        ):
            fail(f"invalid formal Skill directory name: {directory.name}")
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            fail(f"formal Skill missing SKILL.md: {directory.name}")
        text = skill_file.read_text(encoding="utf-8")
        name_match = FRONT_MATTER_NAME_RE.search(text)
        description_match = FRONT_MATTER_DESCRIPTION_RE.search(text)
        if not name_match or name_match.group(1) != directory.name:
            fail(f"Skill front matter name mismatch: {directory.name}")
        if not description_match or not CHINESE_RE.search(description_match.group(1)):
            fail(f"Skill description must contain clear Chinese text: {directory.name}")

    print("runtime contract validation: PASS")
    print("runtime contracts:", len(registry))
    print("formal skills:", formal_skills)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"runtime contract validation: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
