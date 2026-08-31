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
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/marketplace.json",
    ".cursor-plugin/plugin.json",
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
    "git@github.com:goedgecloud/sdlc-ai-spec.git",
    "git@github.com:ousui/sdlc-ai-spec.git",
    "goedgecloud/sdlc-ai-spec 是唯一",
    "ousui/sdlc-ai-spec 是唯一",
]

DISTRIBUTION_METADATA_PATHS = {
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/marketplace.json",
    ".cursor-plugin/plugin.json",
}

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


def single_marketplace_entry(
    marketplace: dict, plugin_name: str, platform: str
) -> dict:
    entries = marketplace.get("plugins")
    matching_entries = (
        [entry for entry in entries if entry.get("name") == plugin_name]
        if isinstance(entries, list)
        and all(isinstance(entry, dict) for entry in entries)
        else []
    )
    if len(matching_entries) != 1:
        fail(f"{platform} marketplace must contain exactly one {plugin_name} entry")
    return matching_entries[0]


def main() -> int:
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(f"missing required runtime contract: {relative}")

    if (ROOT / "skills/_shared/SKILL.md").exists():
        fail("skills/_shared must not be a callable Skill")

    for relative in (
        ".agents/plugins/marketplace.json",
        ".claude-plugin/marketplace.json",
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
        ".cursor-plugin/marketplace.json",
        ".cursor-plugin/plugin.json",
        "skills/_shared/contracts/registry.json",
        "skills/_shared/schemas/invocation.schema.json",
        "skills/_shared/schemas/result.schema.json",
        "skills/_shared/schemas/source-lock.schema.json",
    ):
        with (ROOT / relative).open("r", encoding="utf-8") as handle:
            json.load(handle)

    with (ROOT / ".codex-plugin/plugin.json").open("r", encoding="utf-8") as handle:
        codex_manifest = json.load(handle)
    with (ROOT / ".agents/plugins/marketplace.json").open(
        "r", encoding="utf-8"
    ) as handle:
        codex_marketplace = json.load(handle)
    with (ROOT / ".cursor-plugin/plugin.json").open("r", encoding="utf-8") as handle:
        cursor_manifest = json.load(handle)
    with (ROOT / ".cursor-plugin/marketplace.json").open(
        "r", encoding="utf-8"
    ) as handle:
        cursor_marketplace = json.load(handle)
    with (ROOT / ".claude-plugin/plugin.json").open("r", encoding="utf-8") as handle:
        claude_manifest = json.load(handle)
    with (ROOT / ".claude-plugin/marketplace.json").open(
        "r", encoding="utf-8"
    ) as handle:
        claude_marketplace = json.load(handle)

    plugin_name = codex_manifest.get("name")
    if plugin_name != "sdlc-ai-spec":
        fail("Codex plugin name must remain sdlc-ai-spec")
    if not CHINESE_RE.search(str(codex_manifest.get("description", ""))):
        fail("Codex plugin description must contain clear Chinese text")
    interface = codex_manifest.get("interface")
    if not isinstance(interface, dict):
        fail("Codex plugin interface metadata is required")
    for field in ("shortDescription", "longDescription"):
        if not CHINESE_RE.search(str(interface.get(field, ""))):
            fail(f"Codex plugin interface.{field} must contain clear Chinese text")

    if codex_marketplace.get("name") != plugin_name:
        fail("Codex marketplace name must match Codex plugin name")
    codex_entry = single_marketplace_entry(
        codex_marketplace, plugin_name, "Codex"
    )
    source = codex_entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "url":
        fail("Codex marketplace plugin source must use the url adapter")
    if source.get("url") != codex_manifest.get("repository"):
        fail("Codex marketplace source url must match plugin repository metadata")
    if source.get("ref") != "main":
        fail("Codex marketplace plugin source ref must be main")
    if codex_entry.get("policy") != {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }:
        fail("Codex marketplace plugin policy must use the distributable defaults")
    if codex_entry.get("category") != interface.get("category"):
        fail("Codex marketplace category must match plugin interface category")

    common_manifest_fields = (
        "name",
        "version",
        "description",
        "homepage",
        "repository",
        "keywords",
        "skills",
    )
    for platform, manifest in (
        ("Cursor", cursor_manifest),
        ("Claude Code", claude_manifest),
    ):
        for field in common_manifest_fields:
            if manifest.get(field) != codex_manifest.get(field):
                fail(f"{platform} plugin {field} must match Codex")
    codex_author = codex_manifest.get("author")
    if not isinstance(codex_author, dict):
        fail("Codex plugin author metadata is required")
    if cursor_manifest.get("author") != {"name": codex_author.get("name")}:
        fail("Cursor plugin author must use the Cursor-supported Codex projection")
    if claude_manifest.get("author") != codex_author:
        fail("Claude Code plugin author must match Codex")
    if claude_manifest.get("displayName") != interface.get("displayName"):
        fail("Claude Code displayName must match Codex interface.displayName")

    if cursor_marketplace.get("name") != plugin_name:
        fail("Cursor marketplace name must match Codex plugin name")
    if cursor_marketplace.get("owner") != {"name": codex_author.get("name")}:
        fail("Cursor marketplace owner must use the Cursor-supported Codex projection")
    if cursor_marketplace.get("metadata") != {
        "description": codex_manifest.get("description")
    }:
        fail("Cursor marketplace description must match Codex")
    cursor_entry = single_marketplace_entry(
        cursor_marketplace, plugin_name, "Cursor"
    )
    if cursor_entry.get("source") != ".":
        fail("Cursor marketplace source must resolve to the repository root")

    if claude_marketplace.get("name") != plugin_name:
        fail("Claude Code marketplace name must match Codex plugin name")
    if claude_marketplace.get("owner") != codex_author:
        fail("Claude Code marketplace owner must match Codex author")
    if claude_marketplace.get("description") != codex_manifest.get("description"):
        fail("Claude Code marketplace description must match Codex")
    claude_entry = single_marketplace_entry(
        claude_marketplace, plugin_name, "Claude Code"
    )
    if claude_entry.get("source") != source:
        fail("Claude Code marketplace source must match Codex")

    marketplace_projection_fields = (
        "name",
        "version",
        "description",
        "homepage",
        "repository",
        "keywords",
    )
    for platform, entry in (
        ("Cursor", cursor_entry),
        ("Claude Code", claude_entry),
    ):
        for field in marketplace_projection_fields:
            if entry.get(field) != codex_manifest.get(field):
                fail(f"{platform} marketplace plugin {field} must match Codex")
        expected_author = (
            {"name": codex_author.get("name")}
            if platform == "Cursor"
            else codex_author
        )
        if entry.get("author") != expected_author:
            fail(f"{platform} marketplace plugin author must match its native manifest")
        if entry.get("category") != interface.get("category"):
            fail(f"{platform} marketplace category must match Codex")

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
        allows_repository_binding = (
            path.relative_to(ROOT).as_posix() in DISTRIBUTION_METADATA_PATHS
        )
        for forbidden in FORBIDDEN_REPOSITORY_BINDINGS:
            if forbidden in text and not allows_repository_binding:
                fail(f"hard-coded repository binding remains: {path.relative_to(ROOT)}")

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "packages"))
    from sdlc_artifact_store import ArtifactStore  # type: ignore
    from sdlc_artifact_store.catalog import ArtifactCatalog  # type: ignore
    from sdlc_artifact_store.context_lineage import ContextLineageRegistry  # type: ignore
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
