from __future__ import annotations

from .support import ArtifactStore, PlnFixture, resolve_inputs


class PlnVfoObligationTests(PlnFixture):
    """Regression for frozen DOM-510 VFY Objectives consumed by PLN.

    VFO is a DSN-produced VFY target. VFM/VPC/VEC are details owned by that
    objective and must not become independent Plan obligations.
    """

    def create_vfo_scope(self, count: int = 2) -> str:
        design = self.complete_design()
        objective_rows = []
        method_rows = []
        pass_rows = []
        evidence_rows = []
        for index in range(1, count + 1):
            suffix = f"{index:03d}"
            objective_rows.append(
                f"| VFO-{suffix} | both | {self.ac_item} | DOM-510 | None | "
                f"objective {suffix} produces a reviewable result | regression coverage | "
                f"VFM-{suffix} | VPC-{suffix} | VEC-{suffix} |"
            )
            method_rows.append(
                f"| VFM-{suffix} | test | required | level=integration, mode=automated | "
                f"objective-{suffix} | deterministic fixture method | regression coverage | VFY | N/A |"
            )
            pass_rows.append(
                f"| VPC-{suffix} | VFO-{suffix} | fixture input | objective result is recorded | "
                f"none | result is missing |"
            )
            evidence_rows.append(
                f"| VEC-{suffix} | VFO-{suffix} | report | VFY | objective result | internal | "
                f"test run | artifact reference |"
            )
        design["domains"]["DOM-510"]["design_result_markdown"] = (
            "## 设计结果 Design Result\n\n"
            "### VFY 目标 VFY Objectives\n\n"
            "| ID | Kind | Requirement, AC, Goal or Intended-use References | Design or Decision References | Domain VFY Point References | 可观察结果 Observable Result | 风险或重要性 Risk or Importance | Method References | Pass Criteria References | Evidence Contract References |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            + "\n".join(objective_rows)
            + "\n\n### 方法选择 VFY Methods\n\n"
            "| ID | 类型 Type | Disposition | 方法明细 Method Detail | 适用范围 Scope | 方法 Method | 选择依据 Selection Basis | 承载位置 Host | Exception Reference |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            + "\n".join(method_rows)
            + "\n\n### 通过条件 Pass Criteria\n\n"
            "| ID | VFY Objective | 输入或条件 Input or Condition | 预期结果 Expected Result | 容差 Tolerance | 失败条件 Failure Condition |\n"
            "|---|---|---|---|---|---|\n"
            + "\n".join(pass_rows)
            + "\n\n### Evidence Contract\n\n"
            "| ID | VFY Objective | Evidence Type | 生成方或来源 Producer or Source | 必要内容 Required Content | 敏感性与处理 Sensitivity and Handling | 保留要求 Retention Requirement | 保存或引用位置 Storage or Reference |\n"
            "|---|---|---|---|---|---|---|---|\n"
            + "\n".join(evidence_rows)
        )
        design["traceability"][0]["vfy_references"] = [
            f"VFO-{index:03d}" for index in range(1, count + 1)
        ]
        result = self.execute(self.invocation(design=design))
        self.assertTrue(result["ok"], result)
        return result["artifact"]["reference"]

    def phase_inputs(self, reference: str):
        return resolve_inputs(
            ArtifactStore.open_read_only(self.root),
            {"scope_inputs": [reference], "control_inputs": []},
        )

    def plan_for(self, reference: str, vfos: tuple[str, ...]):
        change = reference + "#CHG-001"
        refs = [reference + "#" + identity for identity in vfos]
        plan = self.plan()
        plan["delivery_scope"][0]["source_references"] = [change]
        plan["obligations"] = [change, *refs]
        plan["work_items"][0]["source_references"] = [change]
        plan["work_items"][1]["source_references"] = refs
        return plan

    def test_dom510_vfo_is_authoritative_and_method_details_are_not(self):
        reference = self.create_vfo_scope(count=9)
        obligations = self.phase_inputs(reference).metadata["authoritative_obligations"]
        self.assertEqual(
            obligations,
            (
                reference + "#CHG-001",
                reference + "#VFO-001",
                reference + "#VFO-002",
                reference + "#VFO-003",
                reference + "#VFO-004",
                reference + "#VFO-005",
                reference + "#VFO-006",
                reference + "#VFO-007",
                reference + "#VFO-008",
                reference + "#VFO-009",
            ),
        )
        self.assertFalse(any("#VFM-" in item for item in obligations))
        self.assertFalse(any("#VPC-" in item for item in obligations))
        self.assertFalse(any("#VEC-" in item for item in obligations))

    def test_complete_vfo_plan_does_not_fail_obligation_or_scope_checks(self):
        reference = self.create_vfo_scope(count=9)
        plan = self.plan_for(reference, tuple(f"VFO-{index:03d}" for index in range(1, 10)))
        result = self.execute_pln(plan=plan, scope=(reference,), final=False)
        self.assertNotIn("PLN-G-002", result["gate"]["failed_checks"], result)
        self.assertNotIn("PLN-G-006", result["gate"]["failed_checks"], result)

    def test_missing_vfo_still_fails_exact_obligation_coverage(self):
        reference = self.create_vfo_scope(count=9)
        plan = self.plan_for(reference, tuple(f"VFO-{index:03d}" for index in range(1, 9)))
        plan["obligations"] = [
            reference + "#CHG-001",
            *(reference + f"#VFO-{index:03d}" for index in range(1, 9)),
        ]
        result = self.execute_pln(plan=plan, scope=(reference,), final=False)
        self.assertIn("PLN-G-002", result["gate"]["failed_checks"], result)


if __name__ == "__main__":
    import unittest

    unittest.main()
