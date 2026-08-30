import unittest

from packages.sdlc_runtime import (
    EnvelopeValidationError,
    error_result,
    validate_invocation,
    validate_result,
)


class EnvelopeTests(unittest.TestCase):
    def test_valid_invocation_is_normalized(self):
        value = validate_invocation(
            {
                "contract": "sdlc-ai-spec/runtime-invocation/v1",
                "operation": "create",
                "project_root": "/tmp/project",
                "inputs": {},
            }
        )
        self.assertEqual(value["artifact_reference"], None)
        self.assertEqual(value["confirmations"], [])
        self.assertEqual(value["options"]["dry_run"], False)

    def test_relative_project_root_is_rejected(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_invocation(
                {
                    "contract": "sdlc-ai-spec/runtime-invocation/v1",
                    "operation": "check",
                    "project_root": "relative",
                    "inputs": {},
                }
            )

    def test_extra_top_level_field_is_rejected(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_invocation(
                {
                    "contract": "sdlc-ai-spec/runtime-invocation/v1",
                    "operation": "check",
                    "project_root": "/tmp/project",
                    "inputs": {},
                    "phase": "CTX",
                }
            )

    def test_error_result_matches_contract(self):
        result = error_result(
            operation="check",
            status="failed",
            code="STORE_NOT_FOUND",
            message="Store does not exist",
            next_action_code="PROVIDE_PROJECT_WITH_EXISTING_STORE",
            next_action_message="请选择已有 Store 的项目",
            requires_user=True,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "STORE_NOT_FOUND")

    def test_success_with_errors_is_rejected(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_result(
                {
                    "contract": "sdlc-ai-spec/runtime-result/v1",
                    "ok": True,
                    "operation": "create",
                    "status": "completed",
                    "artifact": None,
                    "gate": {"result": "pending", "failed_checks": []},
                    "open_items": [],
                    "warnings": [],
                    "errors": [{"code": "X", "message": "bad"}],
                    "next_action": None,
                }
            )


if __name__ == "__main__":
    unittest.main()
