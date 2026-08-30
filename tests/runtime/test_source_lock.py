import json
import tempfile
import unittest
from pathlib import Path

from packages.sdlc_runtime import (
    ContractSource,
    SourceLockError,
    build_source_lock,
    load_registry,
    validate_source_lock_shape,
    verify_source_lock,
)


class SourceLockTests(unittest.TestCase):
    def test_registry_and_lock_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("a\n", encoding="utf-8")
            (root / "b.md").write_text("b\n", encoding="utf-8")
            sources = (
                ContractSource("contract/b", "1", "b.md"),
                ContractSource("contract/a", "1", "a.md"),
            )
            lock = build_source_lock(root, sources)
            ids = [item["contract_id"] for item in lock["contracts"]]
            self.assertEqual(ids, ["contract/a", "contract/b"])
            verify_source_lock(root, lock, sources)

    def test_digest_drift_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "a.md"
            path.write_text("a\n", encoding="utf-8")
            sources = (ContractSource("contract/a", "1", "a.md"),)
            lock = build_source_lock(root, sources)
            path.write_text("changed\n", encoding="utf-8")
            with self.assertRaises(SourceLockError):
                verify_source_lock(root, lock, sources)

    def test_source_lock_rejects_extra_field(self):
        with self.assertRaises(SourceLockError):
            validate_source_lock_shape(
                {
                    "contract": "sdlc-ai-spec/runtime-source-lock/v1",
                    "contracts": [],
                    "path": "docs/spec.md",
                }
            )

    def test_registry_requires_sorted_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "registry.json"
            path.write_text(
                json.dumps(
                    {
                        "contract": "sdlc-ai-spec/runtime-contract-registry/v1",
                        "contract_version": "1",
                        "contracts": [
                            {
                                "contract_id": "z",
                                "contract_version": "1",
                                "resource": "z.md",
                            },
                            {
                                "contract_id": "a",
                                "contract_version": "1",
                                "resource": "a.md",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SourceLockError):
                load_registry(path)


if __name__ == "__main__":
    unittest.main()
