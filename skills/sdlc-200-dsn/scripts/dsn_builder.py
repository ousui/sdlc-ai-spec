"""DSN canonical Artifact Set builder and domain verifier."""

from dsn_common import *
from dsn_analyzer import DsnAnalyzer
from dsn_renderer import DsnRenderer


class DsnBuilder:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.analyzer = DsnAnalyzer()

    def build(
        self,
        *,
        artifact_id: str,
        revision: int,
        upstream: UpstreamScope,
        design: Mapping[str, Any],
        final_confirmation: Mapping[str, Any] | None,
    ) -> BuildResult:
        analysis = self.analyzer.analyze(design, upstream)
        normalized = analysis.normalized
        checks = dict(analysis.checks)
        decision_ids = tuple(
            str(item.get("id") or f"DEC-{index:03d}")
            for index, item in enumerate(normalized["decisions"], start=1)
        )

        domain_members = tuple(
            _domain_member(
                definition=row["definition"],
                artifact_id=artifact_id,
                revision=revision,
                scope_references=upstream.scope_references,
                decisions=decision_ids,
                row=row,
            )
            for row in analysis.domain_rows
            if row["disposition"] == "required"
            and row["completion"] in {"in_progress", "complete"}
            and row["design_result_markdown"]
        )
        supporting = tuple(
            _decode_supporting_member(item, index)
            for index, item in enumerate(
                normalized["supporting_members"], start=1
            )
        )
        member_ids = [item.member_id for item in (*domain_members, *supporting)]
        member_names = [item.canonical_name for item in (*domain_members, *supporting)]
        if len(member_ids) != len(set(member_ids)):
            raise DsnRuntimeError("duplicate DSN Member ID")
        if len(member_names) != len(set(member_names)):
            raise DsnRuntimeError("duplicate DSN Canonical Member Name")
        members = tuple((*domain_members, *supporting))
        manifest = _manifest(members)

        subject = _subject_digest(
            normalized,
            upstream.context_reference,
            upstream.scope_references,
            upstream.control_references,
        )
        final_valid = self._validate_final_confirmation(
            final_confirmation, subject
        )
        checks["CORE-G-009"] = CheckOutcome(
            "pass" if final_valid else "pending",
            "Final Confirmation 已绑定当前 Design"
            if final_valid
            else "需要 Final Confirmation",
        )

        pending_checks = sorted(
            check_id
            for check_id, outcome in checks.items()
            if outcome.result == "pending"
        )
        failed_checks = sorted(
            check_id
            for check_id, outcome in checks.items()
            if outcome.result == "fail"
        )
        open_items = list(analysis.open_items)
        if not final_valid:
            open_items.append(
                {
                    "id": f"OPI-{len(open_items) + 1:03d}",
                    "needed": "确认当前 DSN Artifact",
                    "expected_source": "Design Authority",
                    "blocked_references": "CORE-G-009",
                    "state": "open",
                    "resolution": "N/A",
                }
            )

        if failed_checks:
            status = "failed"
            gate = "fail"
        elif pending_checks or any(item["state"] == "open" for item in open_items):
            status = "waiting_input"
            gate = "pending"
        elif analysis.active_exceptions:
            status = "ready_with_exception"
            gate = "pass_with_exception"
        else:
            status = "ready"
            gate = "pass"

        raw = DsnRenderer.render(
            artifact_id=artifact_id,
            revision=revision,
            status=status,
            upstream=upstream,
            analysis=analysis,
            checks=checks,
            open_items=tuple(open_items),
            members=members,
            final_confirmation=final_confirmation if final_valid else None,
            gate_result=gate,
        )
        if SECRET_RE.search(raw.decode("utf-8", errors="ignore")):
            raise DsnRuntimeError("DSN primary Blob appears to contain a Secret")
        return BuildResult(
            raw_bytes=raw,
            status=status,
            gate_result=gate,
            failed_checks=tuple(failed_checks),
            open_items=tuple(open_items),
            active_exceptions=analysis.active_exceptions,
            final_confirmation_valid=final_valid,
            members=members,
            manifest=manifest,
            subject_digest=subject,
        )

    def _validate_final_confirmation(
        self,
        confirmation: Mapping[str, Any] | None,
        subject_digest: str,
    ) -> bool:
        if confirmation is None:
            return False
        if not isinstance(confirmation, Mapping):
            raise DsnRuntimeError("final_confirmation must be an object")
        mode = confirmation.get("mode")
        if mode not in {"human", "delegated"}:
            raise DsnRuntimeError("Final Confirmation mode must be human or delegated")
        if confirmation.get("subject_digest") != subject_digest:
            return False
        for field in ("confirmer", "role", "authority_reference", "confirmed_at"):
            _text(confirmation.get(field), f"final_confirmation.{field}")
        if not RFC3339_RE.fullmatch(str(confirmation["confirmed_at"])):
            raise DsnRuntimeError("Final Confirmation confirmed_at must use RFC 3339")
        _authority_file(self.project_root, str(confirmation["authority_reference"]))
        return True


__all__ = ("DsnBuilder",)
