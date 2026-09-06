#!/usr/bin/env python3
"""Check all eight Skills and exact-scope native evidence; never invent host results."""
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
LEDGER = "docs/plugin-development/COMPATIBILITY.json"
INDEX = "docs/plugin-development/work-items/post-integration-conformance/SKILL-INVENTORY.json"


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


def runtime_snapshot(root: Path, skill: str, surface: str, *, source_sha: str | None = None):
    """Bind installed runtime bytes/modes, not docs, test results or the ledger itself."""
    require(skill in SKILLS and surface in SURFACES, "unknown certification target")
    platform = ".codex-plugin" if surface.startswith("codex") else ".cursor-plugin" if surface.startswith("cursor") else ".claude-plugin"
    dirs = ["packages", "scripts", "skills/_shared", "skills/" + skill, platform]
    if surface.startswith("codex"): dirs.append(".agents/plugins")
    rows = []
    if source_sha:
        listing = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-z", source_sha, "--", *dirs], capture_output=True, timeout=10)
        require(listing.returncode == 0, "native source tree unavailable")
        objects = {}
        for entry in listing.stdout.split(b"\0"):
            if not entry: continue
            meta, path = entry.split(b"\t", 1); mode, kind, blob = meta.decode().split()
            relative = path.decode()
            parts = PurePosixPath(relative).parts
            if "__pycache__" in parts or "evals" in parts or relative.endswith(".pyc") or parts[-1] in {"AGENTS.md", "CLAUDE.md", "README.md"}: continue
            require(kind == "blob" and mode in {"100644", "100755"}, "non-file native deployment component")
            objects[relative] = (mode, blob)
    else: objects = None
    for directory in dirs:
        require((root / directory).is_dir(), "missing deployment component: " + directory)
        for path in sorted((root / directory).rglob("*")):
            if "__pycache__" in path.parts or "evals" in path.parts or path.suffix == ".pyc" or path.name in {"AGENTS.md", "CLAUDE.md", "README.md"}: continue
            if path.is_file():
                relative = path.relative_to(root).as_posix(); file_path(root, relative)
                raw = path.read_bytes()
                mode = "100755" if path.stat().st_mode & 0o111 else "100644"
                blob = hashlib.sha1(("blob " + str(len(raw)) + "\0").encode() + raw).hexdigest()
                if objects is not None: require(objects.pop(relative, None) == (mode, blob), "native source bytes/modes differ")
                rows.append([relative, mode, hashlib.sha256(raw).hexdigest()])
    require(rows, "empty runtime snapshot")
    if objects is not None: require(not objects, "native deployment omits source files")
    return hashlib.sha256(json.dumps(sorted(rows), separators=(",", ":")).encode()).hexdigest()


def verify_native_receipt(root: Path, relative: str, skill: str, surface: str):
    data = json.loads(file_path(root, relative).read_bytes())
    require(data.get("contract") == "sdlc-ai-spec/native-skill-receipt/v1", "wrong native receipt contract")
    require(data.get("observation_source") == "native_host", "Python/static checks are not native host behavior")
    require(data.get("skill") == skill and data.get("surface") == surface, "wrong Skill or Client/surface")
    require(data.get("runtime_snapshot_sha256") == runtime_snapshot(root, skill, surface), "native evidence is stale")
    require(re.fullmatch(r"[0-9a-f]{40}", str(data.get("source_sha", ""))) is not None, "missing exact source identity")
    require(isinstance(data.get("client_version"), str) and data["client_version"].strip() not in ("", "Unknown", "NOT_RUN"), "missing tested Client version")
    require(all(isinstance(data.get(k), str) and data[k].strip() for k in ("source_sha", "observed_at", "operator")), "missing execution identity/time")
    from datetime import datetime
    timestamp = datetime.fromisoformat(data["observed_at"].replace("Z", "+00:00"))
    require(timestamp.tzinfo is not None, "native timestamp must carry a timezone")
    # Bind the claimed source commit to the exact same installed byte set. A
    # correctly-shaped receipt for some other commit is insufficient.
    source = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", data["source_sha"] + "^{commit}"],
                            capture_output=True, text=True, timeout=10)
    require(source.returncode == 0 and source.stdout.strip() == data["source_sha"], "native source object unavailable")
    require(runtime_snapshot(root, skill, surface, source_sha=data["source_sha"]) == data["runtime_snapshot_sha256"], "native source binding mismatch")
    review = data.get("independent_review", {})
    require(review.get("verdict") == "ACCEPTED" and review.get("reviewer") and review["reviewer"] != data["operator"], "independent review required")
    checks = data.get("checks", [])
    require([row.get("id") for row in checks] == list(DIMENSIONS), "native case coverage incomplete or reordered")
    for check in checks:
        require(check.get("result") == "PASS" and check.get("evidence"), "unexecuted native check")
        for entry in check["evidence"]:
            path = file_path(root, entry["path"])
            require(path.stat().st_size > 0 and digest(path) == entry.get("sha256"), "native raw evidence mismatch")
    return data


def validate_ledger(root: Path, value, required_surface: str | None = None):
    require(value.get("contract") == "sdlc-ai-spec/skill-client-matrix/v1", "matrix contract mismatch")
    rows = value.get("skills", [])
    require([row.get("skill") for row in rows] == list(SKILLS), "missing, duplicate or reordered Skill")
    verified = []
    for row in rows:
        for entry in row.get("historical_evidence", []):
            require(digest(file_path(root, entry["path"])) == entry["sha256"], "historical evidence changed")
        cells = row.get("surfaces", [])
        require([cell.get("surface") for cell in cells] == list(SURFACES), "missing, duplicate or reordered surface")
        for cell in cells:
            state = cell.get("status")
            require(state in {"NOT_RUN", "VERIFIED"}, "unsupported current native state")
            if state == "VERIFIED":
                require(cell.get("receipt"), "Verified needs a native receipt")
                verify_native_receipt(root, cell["receipt"], row["skill"], cell["surface"])
                verified.append((row["skill"], cell["surface"]))
            else: require(cell.get("receipt") is None, "unreviewed receipt must not masquerade as accepted evidence")
    missing = [[skill, required_surface] for skill in SKILLS if required_surface and (skill, required_surface) not in verified]
    return {"verified": len(verified), "total": len(SKILLS)*len(SURFACES), "required_native_missing": missing}


def verify_summary(text: str, ledger):
    """The human-readable table must not silently drift from the machine ledger."""
    for row in ledger["skills"]:
        line = "| " + row["skill"] + " | " + " | ".join(cell["status"] for cell in row["surfaces"]) + " |"
        require(text.splitlines().count(line) == 1, "compatibility Markdown/JSON drift: " + row["skill"])


def validate(root: Path = ROOT, *, required_surface: str | None = None):
    from packages.sdlc_runtime import load_skill_interface, parse_skill_command
    require(required_surface is None or required_surface in SURFACES, "unknown required surface")
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
    ledger = json.loads(file_path(root, LEDGER).read_bytes())
    native = validate_ledger(root, ledger, required_surface)
    verify_summary(file_path(root, "docs/plugin-development/COMPATIBILITY.md").read_text(), ledger)
    return {"contract":"sdlc-ai-spec/skill-conformance-result/v1", "success":not native["required_native_missing"],
            "portable_structure":"PASS", "skills":checked, "native":native, "native_certification":"NOT_CLAIMED_BY_STATIC_VALIDATION"}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--require-client", choices=SURFACES); parser.add_argument("--json-out", type=Path, required=True)
    args=parser.parse_args()
    try: result=validate(required_surface=args.require_client)
    except Exception as exc: result={"success":False, "error":str(exc)}
    from tools.rls_validation_support import write_json
    write_json(args.json_out, result)
    print("SKILL_CONFORMANCE =", "PASS" if result["success"] else "FAIL")
    raise SystemExit(0 if result["success"] else 1)
