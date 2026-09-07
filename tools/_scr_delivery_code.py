from pathlib import Path
r=Path.cwd()
def change(rel, old, new, count=1):
 p=r/rel;s=p.read_text();assert s.count(old)==count,(rel,s.count(old),old[:80]);p.write_text(s.replace(old,new))
# The command parser is the authority for aliases; meta commands never touch stdin.
change('skills/sdlc-200-dsn/scripts/runtime.py',
'''        payload: Mapping[str, Any] = {}
        if not sys.stdin.isatty():''',
'''        payload: Mapping[str, Any] = {}
        command = parse_skill_command_with_inputs(arguments, load_skill_interface(INTERFACE_PATH))
        if command.command not in {"help", "version", "commands", "examples"} and not sys.stdin.isatty():''')
change('skills/sdlc-300-pln/scripts/runtime.py',
'''        payload={}
        if not sys.stdin.isatty():''',
'''        arguments = list(sys.argv[1:] if argv is None else argv)
        command = parse_skill_command_with_inputs(arguments, load_skill_interface(INTERFACE_PATH))
        payload={}
        if command.command not in {"help", "version", "commands", "examples"} and not sys.stdin.isatty():''')
change('skills/sdlc-300-pln/scripts/runtime.py',
'result,output=run_cli(list(sys.argv[1:] if argv is None else argv),payload)',
'result,output=run_cli(arguments,payload)')
# Provisional IDs are not allocated identities. Target semantics decide lineage.
change('skills/sdlc-600-rls/scripts/rls_service.py',
'''        if target.target_id == state["release_contract"]["release_target"]:
            self._target(state, target)
        new = domain.revise(state, candidate, target=target.target_id, target_baseline=target.baseline(), retry=retry)
        if new["artifact"]["reference"] == reference:''',
'''        same_artifact = target.target_id == state["release_contract"]["release_target"]
        if same_artifact:
            self._target(state, target)
        new = domain.revise(state, candidate, target=target.target_id, target_baseline=target.baseline(), retry=retry)
        # build_provisional has no Store reservation. Its clock-based ID may equal
        # an existing ID; that must never suppress allocation for a new Target.
        if same_artifact and new["artifact"]["reference"] == reference:''')
change('skills/sdlc-600-rls/scripts/rls_service.py',
'''        same_artifact = new["artifact"]["id"] == state["artifact"]["id"]
        if same_artifact:''','''        if same_artifact:''')
# Validate scalar types before set membership; JSON arrays/objects must not crash.
change('packages/sdlc_runtime/envelopes.py','if operation not in OPERATIONS:',
       'if not isinstance(operation, str) or operation not in OPERATIONS:', count=2)
change('skills/sdlc-000-ctx/scripts/runtime.py',
       'safe_operation = operation if operation in {"create", "revise", "check"} else "check"',
       'safe_operation = operation if isinstance(operation, str) and operation in {"create", "revise", "check"} else "check"')
# The existing REQ public entry must serialize shared envelope errors as well.
change('skills/sdlc-100-req/scripts/runtime.py','    ControlInputError,\n    ControlInputResolver,',
       '    ControlInputError,\n    ControlInputResolver,\n    EnvelopeValidationError,')
change('skills/sdlc-100-req/scripts/runtime.py',
       'except (json.JSONDecodeError, OSError, RequirementRuntimeError, CanonicalFormatError) as exc:',
       'except (json.JSONDecodeError, OSError, RequirementRuntimeError, CanonicalFormatError, EnvelopeValidationError) as exc:')
change('skills/sdlc-100-req/scripts/runtime.py',
       'if "request" in locals() and request.get("operation") in {"create", "revise", "check"}:',
       'if "request" in locals() and isinstance(request.get("operation"), str) and request.get("operation") in {"create", "revise", "check"}:')
# Baseline representation is not proof of resolution or authorization. Keep the
# documented legacy generic VCS form, and reject mutable names / observation time.
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''def _collection_row_problem(name: str, row: Mapping[str, str]) -> str | None:''',
'''def _immutable_baseline(value: str) -> bool:
    """Recognize explicit version/content identities, not provenance truth.

    Generic vcs: revisions retain the existing abbreviated hexadecimal form.
    New git: inputs require full object IDs. Content references bind a snapshot
    digest (including a dirty-worktree manifest), never an observation timestamp.
    Resolution/observation Evidence remains a separate domain obligation.
    """
    return bool(
        re.fullmatch(r"vcs:[^\\s@]+@[0-9a-f]{7,64}(?:\\+sha256:[0-9a-f]{64})?", value)
        or re.fullmatch(r"git:(?:[^\\s@]+@)?(?:[0-9a-f]{40}|[0-9a-f]{64})(?:\\+sha256:[0-9a-f]{64})?", value)
        or re.fullmatch(r"(?:[^\\s@]+@)?sha256:[0-9a-f]{64}", value)
    )


def _collection_row_problem(name: str, row: Mapping[str, str]) -> str | None:''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''    required_typed = {
        "resources": ("type", "name", "role", "locator"),''',
'''    if name == "resources":
        baseline = row["baseline_reference"]
        versioned = row["type"] == "repository" or row["locator"].startswith(("vcs:", "git:"))
        if not _immutable_baseline(baseline) and (versioned or baseline not in {"None", "N/A"}):
            return "resources.baseline_reference requires an immutable version or content digest, not a timestamp or mutable name"

    required_typed = {
        "resources": ("type", "name", "role", "locator"),''')
# Missing/invalid input is not a failed evaluation of every Artifact Check.
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''    if errors:
        return {check_id: ("fail", errors[0]["message"]) for check_id in (*CORE_CHECKS, *CTX_CHECKS)}''',
'''    if errors:
        return {check_id: ("pending", "Not evaluated: invalid request") for check_id in (*CORE_CHECKS, *CTX_CHECKS)}''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''"gate_result": "fail" if errors else "pending",''','''"gate_result": "pending",''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''            checks = _pending_checks([], errors)
        else:
            checks = complete_checks''',
'''            checks = complete_checks
            checks["CORE-G-009"] = ("fail", "Final Confirmation rejected this Revision")
        else:
            checks = complete_checks''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''    if errors:
        gate_result = "fail"
        status = "failed"''',
'''    if errors:
        gate_result = "fail" if any(outcome == "fail" for outcome, _ in checks.values()) else "pending"
        status = "failed"''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''                "create", ok=True, status="completed", artifact=None, gate_result=product.gate_result,''',
'''                "create", ok=not product.errors, status="failed" if product.errors else "completed", artifact=None, gate_result=product.gate_result,''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''                errors=[], next_action=_action("REVIEW_DRY_RUN", "检查候选结果；需要持久化时另行明确写入授权", user=True),''',
'''                errors=product.errors,
                next_action=(_action("CORRECT_CTX_INPUT", "修正结构化 CTX 输入后重试", user=True) if product.errors
                             else _action("REVIEW_DRY_RUN", "检查候选结果；需要持久化时另行明确写入授权", user=True)),''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''                "create", ok=False, status="failed", artifact=None, gate_result="fail",
                failed_checks=preliminary.failed_checks,''',
'''                "create", ok=False, status="failed", artifact=None, gate_result=preliminary.gate_result,
                failed_checks=preliminary.failed_checks,''')
change('skills/sdlc-000-ctx/scripts/runtime.py',
'''                    gate_result="fail", failed_checks=preview_product.failed_checks, open_items=preview_product.open_items,''',
'''                    gate_result=preview_product.gate_result, failed_checks=preview_product.failed_checks, open_items=preview_product.open_items,''')
# This existing assertion concerned an invalid request, not an evaluated Artifact.
# Keep its exact ID and error code, adding stronger no-write assertions.
change('tests/skills/test_ctx_preconfirmation.py',
'''        self.assertEqual(result['gate']['result'],'fail')
        self.assertTrue(any(e['code']=='INVALID_PREPARE_CONFIRMATION' for e in result['errors']))''',
'''        self.assertEqual(result['gate'], {'result': 'pending', 'failed_checks': []})
        self.assertTrue(any(e['code']=='INVALID_PREPARE_CONFIRMATION' for e in result['errors']))
        self.assertIsNone(result['artifact'])
        self.assertFalse((self.fixture.project_root / '.sdlc').exists())''')
print('critical fixes applied')
