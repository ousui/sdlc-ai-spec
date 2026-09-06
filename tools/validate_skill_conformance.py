#!/usr/bin/env python3
"""Validate the maintained eight-Skill inventory, without native-client certification."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SKILLS = tuple([f"sdlc-{number:03d}-{name}" for number, name in
                ((0,"ctx"),(100,"req"),(200,"dsn"),(300,"pln"),(400,"imp"),(500,"vfy"),(600,"rls"))] + ["sdlc-status"])
SURFACES = ("codex-cli", "codex-app", "claude-code-cli", "cursor-ide", "cursor-cli")
DIMENSIONS = ("installation", "discovery", "explicit_invocation", "negative_invocation", "behavior", "permissions", "installed_independence")
INDEX = "docs/plugin-development/SKILL-INVENTORY.json"


def require(condition, message):
    if not condition: raise ValueError(message)


def file_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and relative, "missing path")
    value = PurePosixPath(relative)
    require(not value.is_absolute() and ".." not in value.parts and "\\" not in relative and str(value) == relative, "unsafe path")
    path = root / relative
    require(all(not part.is_symlink() for part in (path, *path.parents) if part != root.parent), "symlink is not evidence")
    require(path.is_file(), "missing file: " + relative)
    return path


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path = ROOT):
    from packages.sdlc_runtime import load_skill_interface, parse_skill_command
    actual = sorted(path.name for path in (root / "skills").iterdir() if path.is_dir() and not path.name.startswith("_"))
    require(actual == sorted(SKILLS), "formal Skill inventory differs")
    require(not (root / "skills/_shared/SKILL.md").exists(), "shared resources became callable")
    inventory = json.loads(file_path(root, INDEX).read_bytes())
    require([row["skill"] for row in inventory["skills"]] == list(SKILLS), "inventory incomplete")
    checked = []
    for row in inventory["skills"]:
        name = row["skill"]; base = "skills/" + name
        for path in (base+"/SKILL.md", base+"/references/interface.json", base+"/references/contract.md", base+"/references/source-lock.json", base+"/agents/openai.yaml", row["runtime_entry"], row["design"], row["eval_plan"]): file_path(root, path)
        skill = (root / base / "SKILL.md").read_text()
        require(re.search(r"^name:\s*"+re.escape(name)+r"\s*$",skill,re.M), "Skill name mismatch")
        require(re.search(r"^disable-model-invocation:\s*true\s*$",skill,re.M), "implicit invocation enabled")
        require(re.search(r"^\s+allow_implicit_invocation:\s*false\s*$", (root / base / "agents/openai.yaml").read_text(), re.M), "Codex implicit policy missing")
        spec = load_skill_interface(root / base / "references/interface.json")
        require(spec.skill == name and spec.default_command == "auto", "wrong interface identity/default")
        for command in ("help", "version", "commands", "examples"):
            require(parse_skill_command([command], spec).command == command, "meta command mismatch")
        require(parse_skill_command([], spec).command == "auto", "bare invocation missing")
        for field in ("runtime_entry", "design", "eval_plan"):
            require(isinstance(row[field], str), "invalid inventory path")
        for path in row["test_roots"]: require((root / path).exists(), "test source missing")
        checked.append({"skill": name, "declared_commands": list(spec.command_names), "layout": "PASS"})
    return {"contract": "sdlc-ai-spec/skill-conformance-result/v1", "success": True,
            "portable_structure": "PASS", "skills": checked,
            "native_certification": "OUT_OF_SCOPE_MANUAL_FEEDBACK_NO_RECORDED_ATTESTATION"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"success": False, "error": str(exc)}
    from tools.rls_validation_support import write_json
    write_json(args.json_out, result)
    print("SKILL_CONFORMANCE =", "PASS" if result["success"] else "FAIL")
    raise SystemExit(0 if result["success"] else 1)
