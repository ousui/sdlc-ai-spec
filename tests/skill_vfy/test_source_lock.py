"""Negative and final-mode tests for the exact VFY Source Lock."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.validate_sdlc_500_vfy_source_lock import (
    EXPECTED_CONTRACTS,
    EXPECTED_DESIGN_SOURCES,
    LOCK_RELATIVE,
    ROOT,
    validate,
)


class VfySourceLockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="vfy-source-lock-")
        self.root = Path(self.temporary.name)
        paths = {path for _, _, path in EXPECTED_CONTRACTS}
        paths.update(path for _, path in EXPECTED_DESIGN_SOURCES)
        paths.add(str(LOCK_RELATIVE))
        for relative in sorted(paths):
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        self.lock_path = self.root / LOCK_RELATIVE
        self.payload = json.loads(self.lock_path.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, payload: dict[str, object]) -> None:
        self.lock_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _rejects(self, payload: dict[str, object]) -> None:
        self._write(payload)
        with self.assertRaises(ValueError):
            validate(require_final=True, root=self.root)

    def test_final_source_lock_passes(self) -> None:
        result = validate(require_final=True, root=self.root)
        self.assertEqual("PASS", result["status"])
        self.assertFalse(result["provisional"])
        self.assertEqual(len(EXPECTED_CONTRACTS), result["contract_count"])

    def test_missing_contract_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["contracts"].pop()
        self._rejects(payload)

    def test_extra_contract_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["contracts"].append(deepcopy(payload["contracts"][-1]))
        self._rejects(payload)

    def test_duplicate_contract_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["contracts"][1] = deepcopy(payload["contracts"][0])
        self._rejects(payload)

    def test_unsorted_contracts_are_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["contracts"][0], payload["contracts"][1] = (
            payload["contracts"][1],
            payload["contracts"][0],
        )
        self._rejects(payload)

    def test_digest_drift_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["contracts"][0]["sha256"] = "0" * 64
        self._rejects(payload)

    def test_design_source_set_and_identity_drift_are_rejected(self) -> None:
        mutations = []
        missing = deepcopy(self.payload)
        missing["design_sources"].pop()
        mutations.append(missing)
        extra = deepcopy(self.payload)
        extra["design_sources"].append(deepcopy(extra["design_sources"][-1]))
        mutations.append(extra)
        duplicate = deepcopy(self.payload)
        duplicate["design_sources"][1] = deepcopy(duplicate["design_sources"][0])
        mutations.append(duplicate)
        unsorted = deepcopy(self.payload)
        unsorted["design_sources"].reverse()
        mutations.append(unsorted)
        blob_drift = deepcopy(self.payload)
        blob_drift["design_sources"][0]["git_blob"] = "0" * 40
        mutations.append(blob_drift)
        digest_drift = deepcopy(self.payload)
        digest_drift["design_sources"][0]["sha256"] = "0" * 64
        mutations.append(digest_drift)
        for index, payload in enumerate(mutations):
            with self.subTest(mutation=index):
                self._rejects(payload)


if __name__ == "__main__":
    unittest.main()
