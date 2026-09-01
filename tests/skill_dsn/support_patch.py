"""Small fixture corrections kept separate from production DSN runtime."""

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from dsn_handler_final import DsnHandler as FinalDsnHandler

from . import support as base


def _catalog(self):
    return ArtifactCatalog(ArtifactStore.open_read_only(self.root))


def _create_requirement(self, context_reference: str) -> str:
    next_number = getattr(self, "_requirement_sequence", 0) + 1
    self._requirement_sequence = next_number
    artifact_id = f"REQ-20260901090000-{next_number:02d}"
    raw = (
        "---\n"
        "contract: sdlc-ai-spec/artifact/v1\n"
        "phase: REQ\n"
        f"id: {artifact_id}\n"
        "revision: 1\n"
        "status: ready\n"
        f"context: {context_reference}\n"
        "profile: full\n"
        "inputs: []\n"
        "---\n"
        "# Fixture Requirement\n\n"
        "| ID | 类型 Type | 来源或父项引用 Source or Parent References | 需求描述 Requirement Statement |\n"
        "|---|---|---|---|\n"
        "| R-001 | behavior | SRC-001 | 已授权用户可以导出当前筛选结果 |\n\n"
        "| ID | 关联需求 Requirement References | 条件 Condition | 预期结果 Expected Result |\n"
        "|---|---|---|---|\n"
        "| AC-001 | R-001 | 用户具有权限并应用筛选条件 | 导出记录与筛选结果一致 |\n\n"
        + base._gate_summary()
    ).encode("utf-8")
    return self._write_frozen("REQ", raw)


base.DsnHandler = FinalDsnHandler
base.DsnRuntimeFixture.catalog = _catalog
base.DsnRuntimeFixture.create_requirement = _create_requirement
