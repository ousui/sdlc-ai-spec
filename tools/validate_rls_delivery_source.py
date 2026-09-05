"""Exact final RLS topology, path and syntax guard; no runtime mutation."""
import argparse
import ast
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools.rls_validation_support import git, source_state, write_json
V = "46509eb6688df30e71ed094132b2d10e81ceb2ac"
M = "644218e02876c5649fd87cfca12e1876d3b3b8bf"
OLD_SUBJECT = "076994c1d28438fd3b038f5c928d3ceeda5a7453"
OLD_EVIDENCE = "13e37b100060d714a6b61c26e1ba990edb2dcae3"
REPAIR_SOURCE = "7a00aa04780b7d6b08676042b34f30d558b2a969"
PROPAGATION_HISTORY = (
    "797bde43a31b6e5afdb028de7f8944cea996b460",
    "93e98c577b5c3136df55ee5a7cb7a1c2adfcda30",
    "206c379b77bb47ba0cf7913ea6dc1f8a39ed9bcd",
)
REPAIR_ADDITIONS = {
    "skills/sdlc-600-rls/scripts/rls_confirmation_policy.py",
    "skills/sdlc-600-rls/scripts/rls_human_evidence.py",
    "tests/skill_rls/test_web_repair_confirmation.py",
    "tests/skill_rls/test_web_repair_confirmation_batch.py",
    "tests/skill_rls/test_web_repair_redaction.py",
    "tests/skill_rls/test_web_repair_redaction_propagation.py",
    "tests/skill_rls/test_web_repair_store.py",
}
DESIGN = "docs/plugin-development/work-items/sdlc-600-rls/"
ADDITIVE = {
    "packages/sdlc_lifecycle/__init__.py", "packages/sdlc_lifecycle/models.py", "packages/sdlc_lifecycle/query_rls.py",
    "skills/sdlc-status/scripts/runtime.py", "skills/sdlc-status/references/rls-projection.schema.json",
    "tests/evals/run_sdlc_600_rls_eval.py", "tests/evals/sdlc_600_rls_cases.json", "tests/evals/test_sdlc_600_rls_case_coverage.py",
    "tools/run_rls_provisional_validation.py", "tools/test_sdlc_600_rls_runtime_independence.py", "tools/validate_sdlc_600_rls_source_lock.py",
    "tools/rls_fixture_chain.py", "tools/rls_validation_support.py", "tools/run_rls_test_suite.py",
    "tools/review_rls_effect_boundary.py", "tools/run_external_rls_integration.py",
    "tools/run_rls_delivery_validation.py", "tools/validate_rls_delivery_source.py",
}


def allowed(path):
    return path.startswith(("skills/sdlc-600-rls/", "tests/skill_rls/")) or path in ADDITIVE


def validate(root, source):
    state = source_state(root)
    assert len(source) == 40 and state["sha"] == source and not state["status"], "clean exact Subject is required"
    assert len(state["parents"]) == 1, "S must have exactly one parent D"
    design = state["parents"][0]
    assert design == "c9615cec2da3b39949a3fdd8be32396eae6db3aa", "approved D must be preserved"
    parents = git(root,"show","-s","--format=%P",design).split(); assert len(parents) == 1
    bridge = parents[0]
    assert git(root,"show","-s","--format=%P",bridge).split() == [V,M], "ordered B parents must be accepted V and tree-equivalent M"
    trees = {ref:git(root,"rev-parse",ref+"^{tree}") for ref in (V,M,bridge)}
    assert len(set(trees.values())) == 1, "B/V/M tree equivalence failed"
    git(root,"merge-base","--is-ancestor",M,source)
    design_paths = git(root,"diff","--name-only",bridge,design).splitlines()
    assert design_paths and all(path.startswith(DESIGN) for path in design_paths), "D contains non-RLS design paths"
    migration=json.loads((root/(DESIGN+"goal/17-MIGRATION-MANIFEST.json")).read_bytes())
    planned=[row for row in migration["entries"] if row["disposition"]=="planned_implementation_migration"]
    assert len(planned)==52 and all((root/row["path"]).is_file() for row in planned), "a planned original RLS implementation/test file is missing"
    paths = git(root,"diff","--name-only",design,source).splitlines()
    assert paths and all(allowed(path) for path in paths), "S contains unauthorized paths"
    original_paths = set(git(root,"diff","--name-only",design,OLD_SUBJECT).splitlines())
    assert set(paths) == original_paths | REPAIR_ADDITIONS, "missing or unregistered repair source path"
    assert not git(root,"diff","--name-only",OLD_SUBJECT,source,"--",
                   "packages/sdlc_lifecycle", "skills/sdlc-status"), "approved additive RLS query/status wiring changed"
    assert not git(root,"diff","--name-only",V,source,"--","skills/sdlc-500-vfy","tests/skill_vfy",
                   "tests/evals/run_sdlc_500_vfy_eval.py","tests/evals/sdlc_500_vfy_cases.json",
                   "tools/validate_sdlc_500_vfy_source_lock.py","tools/test_sdlc_500_vfy_runtime_independence.py"), "accepted VFY files changed"
    for old in ("70e6f92fd1644831c836de1e2b8a0aa567c5a979", "8fc15b71e0a90623e6805277fd131dd1f68de0fd",
                OLD_SUBJECT, OLD_EVIDENCE, REPAIR_SOURCE, *PROPAGATION_HISTORY):
        assert git(root,"merge-base",old,source) != old, "old provisional RLS became an ancestor"
    for relative in paths:
        path = root/relative
        if path.suffix == ".py": ast.parse(path.read_text(), filename=relative)
        if path.suffix == ".json": json.loads(path.read_bytes())
    git(root,"diff","--check",design,source)
    return dict(success=True, source=state, design=design, bridge=bridge, upstream=V, main=M, tree_equivalence=trees,
                design_paths=design_paths, implementation_paths=paths, registered_repair_additions=sorted(REPAIR_ADDITIONS),
                excluded_history=[OLD_SUBJECT, OLD_EVIDENCE, REPAIR_SOURCE, *PROPAGATION_HISTORY])


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--source-sha",required=True); parser.add_argument("--json-out",type=Path,required=True)
    args=parser.parse_args()
    try: result=validate(ROOT,args.source_sha)
    except Exception as exc: result=dict(success=False,error_type=type(exc).__name__,error=str(exc))
    write_json(args.json_out,result); print("RLS_SOURCE_GUARD = " + ("PASS" if result["success"] else "FAIL"))
    raise SystemExit(0 if result["success"] else 1)
