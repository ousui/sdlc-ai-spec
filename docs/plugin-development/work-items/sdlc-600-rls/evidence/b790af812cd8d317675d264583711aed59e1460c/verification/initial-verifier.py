"""Read-only verification of new RLS repair evidence and exact archived bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def read(path):
    return json.loads(path.read_bytes())


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def schema_check(value, schema):
    assert set(schema) <= {"type", "properties", "required", "const", "pattern", "minimum", "additionalProperties", "items", "$schema", "$id", "description"}, "unsupported schema keyword"
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    if "type" in schema:
        assert type(value) is kinds[schema["type"]], "schema type mismatch"
    if "const" in schema:
        assert value == schema["const"], "schema const mismatch"
    if "pattern" in schema:
        assert re.fullmatch(schema["pattern"], value), "schema pattern mismatch"
    if "minimum" in schema:
        assert value >= schema["minimum"], "schema minimum mismatch"
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= set(value), "missing required field"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(props), "unexpected field"
        for key, item in value.items():
            if key in props:
                schema_check(item, props[key])
    if isinstance(value, list) and "items" in schema:
        for item in value:
            schema_check(item, schema["items"])


def verify_propagation(repo, evidence, result, archived, reports):
    policy = 'sdlc-ai-spec/validation-redaction/v2'
    subject = result['implementation_subject_sha']
    assert result['redaction_policy'] == policy
    assert result['web_repair_tests'] == 120
    assert result['propagation_tests'] == 56 and result['original_web_repair_tests'] == 64
    assert result['rls_private'] == 435 and result['full_regression'] == 1068
    for name, report in reports.items():
        assert report['redaction_policy'] == policy
        assert report['real_target_effects'] == report['remote_writes'] == report['installations'] == 0
    unique_receipts = set()
    bindings = 0
    def inspect(value):
        nonlocal bindings
        if isinstance(value, dict):
            if value.get('stream_hashes_bind') == 'ARCHIVED_REDACTED_UTF8_BYTES':
                assert value['redaction_policy'] == policy
                for stream in ('stdout', 'stderr'):
                    path = archived[value[stream + '_log']]
                    raw = path.read_bytes()
                    assert raw == value[stream].encode('utf-8')
                    assert digest(raw) == value[stream + '_sha256']
                receipt_path = value['stdout_log'].removesuffix('.stdout.log') + '.receipt.json'
                assert read(archived[receipt_path]) == value, 'embedded and persisted receipt differ'
                if value.get('source_before'):
                    assert value['source_before'] == value['source_after']
                    assert value['source_unchanged']
                unique_receipts.add(receipt_path)
                bindings += 1
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    for path in evidence.rglob('*.json'):
        inspect(read(path))
    git = lambda *args: subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
    migration = read(evidence / 'migration.json')
    assert migration['count'] == len(migration['entries']) == 85
    expected = set(git('diff', '--name-only', result['design_head_sha'], subject).splitlines())
    assert {row['path'] for row in migration['entries']} == expected
    for row in migration['entries']:
        mode, kind, blob, _ = git('ls-tree', subject, '--', row['path']).split()
        assert kind == 'blob' and mode == row['mode'] and blob == row['result_blob']
        assert git('rev-parse', result['repair_source_sha'] + ':' + row['path']) == row['source_blob']
        assert row['result_blob'] == row['source_blob'], 'unrecorded local source repair'
    assert git('show', '-s', '--format=%P', result['design_head_sha']) == result['bridge_sha']
    assert git('show', '-s', '--format=%P', result['bridge_sha']).split() == [result['accepted_vfy_sha'], result['main_sha']]
    assert len({git('rev-parse', ref + '^{tree}') for ref in (result['bridge_sha'], result['accepted_vfy_sha'], result['main_sha'])}) == 1
    for old in result['superseded_objects']:
        assert git('merge-base', old, subject) != old
    raw = evidence / 'raw'
    for prefix, stem in ((raw, ''), (raw / 'attest-steps', 'fresh-')):
        for filename, count in (('rls-private.json', 435), ('repository.json', 1068)):
            suite = read(prefix / (stem + 'full-steps') / filename)
            passed = re.findall(r'^test_\w+ \(([^)]+)\) \.\.\. ok$', suite['log'], re.M)
            assert len(passed) == len(set(passed)) == suite['tests_run'] == count
            assert all(suite[key] == 0 for key in ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'))
            assert suite['redaction_policy'] == policy
        source = read(prefix / (stem + 'quick-steps') / 'source.json')
        assert source['success'] and source['source']['sha'] == subject
        assert len(source['implementation_paths']) == 85
    for collection in (reports, reports['attest']['profiles']):
        for profile in collection.values():
            assert profile['redaction_policy'] == policy
        external = collection['external']['external']
        assert external['real_target_effects'] == external['remote_writes'] == external['installations'] == 0
        for project in external['projects']:
            assert project['expected_sha'] == {'springgear':'e855096ff19dcdb303dc4250ba19c30acd743ac7','gin-vue-admin':'a6882210a80bb27e3aa5dff0b4c21aa4afe8988a'}[project['name']]
            assert project['before']['head'] == project['expected_sha']
            assert project['rls_state']['artifact_gate'] == 'pass'
            assert project['rls_state']['release_conclusion'] == 'success'
            assert all(key in project['chain'] for key in ('context', 'requirement', 'design', 'plan', 'vfy')) and project['imp_subjects']
            assert digest(archived[project['store_export']['path']].read_bytes()) == project['store_export']['sha256']
            if 'cache_before' in project:
                assert project['cache_before'] == project['cache_after']
    for name in ('focused-independent', 'subject-independent'):
        probes = read(evidence / name / 'result.json')
        assert probes['success'] and len(probes['probes']) == 12 and all(row['success'] for row in probes['probes'])
        assert probes['policy'] == policy and probes['synthetic_only'] and not probes['sensitive_context_persisted']
        assert probes['source']['sha'] == (subject if name == 'subject-independent' else result['repair_source_sha'])
    summary = read(evidence / 'focused' / 'summary.json')
    assert [row['tests_run'] for row in summary] == [74,46] and all(row['success'] and row['exit_code'] == 0 for row in summary)
    fresh_root = Path(reports['attest']['fresh_source']['root'])
    assert not fresh_root.exists(), 'fresh checkout still exists'
    assert str(fresh_root) not in git('worktree', 'list', '--porcelain')
    return dict(policy=policy, unique_process_receipts=len(unique_receipts), nested_bindings_verified=bindings,
                propagation_tests=56, original_web_repair_tests=64, source_paths=85, independent_probes=12)


def verify(repository, directory):
    repo = Path(repository).resolve(); evidence = repo / directory
    manifest = read(evidence / "MANIFEST.sha256.json")
    result = read(evidence / "final-result.json")
    assert manifest['subject_sha'] == result['implementation_subject_sha']
    assert manifest['subject_tree'] == result['subject_tree']
    schema_check(result, read(evidence / "final-result.schema.json"))
    entries = manifest["files"]
    assert len(entries) == len({row["path"] for row in entries})
    expected = {path.relative_to(repo).as_posix() for path in evidence.rglob("*") if path.is_file() and path.name != "MANIFEST.sha256.json"}
    expected |= {"docs/plugin-development/work-items/sdlc-600-rls/goal/" + name for name in ("26-REDACTION-PROPAGATION-REPAIR.md", "27-LOCAL-CODEX-GOAL-REDACTION-PROPAGATION.md", "28-PROPAGATION-REPAIR-HANDOFF.md", "29-WEB-PROPAGATION-REVIEW.md")}
    assert {row["path"] for row in entries} == expected, "manifest coverage differs"
    for row in entries:
        path = repo / row["path"]
        assert not path.is_symlink() and path.resolve().is_relative_to(repo)
        raw = path.read_bytes()
        assert digest(raw) == row["sha256"] and len(raw) == row["bytes"], row["path"]
    archived = {row["source_path"]: repo / row["archive_path"] for row in read(evidence / "archive-map.json")["files"]}
    receipts = 0
    for path in evidence.rglob("*.receipt.json"):
        value = read(path)
        if "stdout_log" not in value:
            continue
        for stream in ("stdout", "stderr"):
            raw = archived[value[stream + "_log"]].read_bytes()
            assert digest(raw) == value[stream + "_sha256"], str(path)
            assert raw == value[stream].encode("utf-8"), str(path)
        assert value["stream_hashes_bind"] == "ARCHIVED_REDACTED_UTF8_BYTES"
        receipts += 1
    subject = result["implementation_subject_sha"]
    git = lambda *args: subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    assert git("show", "-s", "--format=%P", subject) == result["design_head_sha"]
    assert git("rev-parse", subject + "^{tree}") == result["subject_tree"]
    raw = evidence / "raw"
    reports = {name: read(raw / (name + ".json")) for name in ("quick", "phase", "full", "external", "attest")}
    fresh = reports["attest"]
    assert fresh["fresh_cleanup"] and fresh["fresh_source"]["sha"] == subject
    assert not fresh["fresh_source"]["branch"] and not fresh["fresh_source"]["status"]
    for collection in (reports, fresh["profiles"]):
        for name, report in collection.items():
            assert report["success"] and report["source_sha"] == subject
            assert report["source_before"] == report["source_after"]
            assert report["source_before"]["tree"] == result["subject_tree"]
            assert not report["source_before"]["status"]
            assert report["steps"] and all(step["success"] and step["exit_code"] == 0 for step in report["steps"])
        fixed = collection["phase"]["fixed_eval"]
        assert fixed["success"] and fixed["tests_run"] == 87
        assert fixed["executed_case_ids"] == [f"RLS-E{i:03d}" for i in range(1, 88)]
        vfy = collection["full"]["vfy_regression"]
        assert vfy["passed"] == 80 and vfy["failed"] == vfy["skipped"] == 0
        for case in vfy["results"]:
            if case["case_id"] in {"VFY-E041", "VFY-E046"}:
                observed = json.loads(case["result"]["actual_result"])
                assert observed["containment"] == "os-sandbox" and observed["network"] == "disabled"
        full = collection["full"]["full_regression"]
        assert full["success"] and full["tests_run"] == result["full_regression"]
        assert full["failures"] == full["errors"] == full["skipped"] == full["expected_failures"] == 0
        external = collection["external"]["external"]
        assert external["success"] and external["passed"] == 2
        for project in external["projects"]:
            assert project["success"] and project["before"] == project["after_cleanup"]
            assert project["target_cleanup"] and project["temporary_root_removed"]
            assert "tracked_bytes_modes" in project["before"] and "untracked_bytes_modes" in project["before"]
    ledger = read(evidence / "A01-A12.json")
    assert [row["id"] for row in ledger["rows"]] == [f"A{i:02d}" for i in range(1, 13)]
    private = read(raw / "full-steps/rls-private.json")
    fresh_private = read(raw / "attest-steps/fresh-full-steps/rls-private.json")
    for prefix in (raw, raw / "attest-steps"):
        stem = "fresh-" if prefix != raw else ""
        lock = read(prefix / (stem + "quick-steps") / "source-lock.json")
        assert lock["result"] == "PASS" and lock["entries"] == 14
        independence = read(prefix / (stem + "full-steps") / "rls-independence.json")
        assert independence["result"] == independence["cleanup"] == "PASS"
        assert independence["network_reads"] == independence["installations"] == independence["real_target_effects"] == 0
        assert len(independence["commands"]) == 12
        for receipt in independence["receipts"]:
            assert receipt["exit_code"] == 0
            for stream in ("stdout", "stderr"):
                assert digest(receipt[stream].encode("utf-8")) == receipt[stream + "_sha256"]
        effect = read(prefix / (stem + "full-steps") / "effect-review.json")
        assert effect["success"] and not effect["violations"] and effect["behavior"]["success"]
    for row in ledger["rows"]:
        assert row["status"] == "CLOSED" and row["source_sha"] == subject
        for test in row["tests"]:
            assert test + ") ... ok" in private["log"] and test + ") ... ok" in fresh_private["log"], test
    for report in (private, fresh_private):
        assert report["success"] and report["tests_run"] == result["rls_private"]
        repaired = re.findall(r"^test_\w+ \((tests\.skill_rls\.test_web_repair_\w+\.\w+\.test_\w+)\) \.\.\. ok$", report["log"], re.M)
        assert len(repaired) == len(set(repaired)) == 120
        assert sum(".test_web_repair_store." in test for test in repaired) == 10
        assert sum(".test_web_repair_redaction_propagation." in test for test in repaired) == 56
        assert sum(".test_web_repair_redaction." in test for test in repaired) == 18
        assert report["failures"] == report["errors"] == report["skipped"] == report["expected_failures"] == report["unexpected_successes"] == 0
    extended = verify_propagation(repo, evidence, result, archived, reports)
    return {"success": True, "source_sha": subject, "schema": "PASS", "propagation_integrity": extended, "manifest_files": len(entries),
            "archived_process_receipts": receipts, "fixed_eval": 87, "vfy_regression": 80,
            "full_regression": result["full_regression"], "web_review": "REQUIRED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.repository, args.directory), ensure_ascii=False))
