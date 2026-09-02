"""Small fixture corrections kept separate from production DSN runtime."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills/sdlc-200-dsn/scripts"
for candidate in (ROOT, ROOT / "packages", SCRIPT_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from dsn_handler_final import DsnHandler as FinalDsnHandler

from . import support as base


def _catalog(self):
    return ArtifactCatalog(ArtifactStore.open_read_only(self.root))


def _create_requirement(
    self,
    context_reference: str,
    dsn_disposition: str = "required",
) -> str:
    next_number = getattr(self, "_requirement_sequence", 0) + 1
    self._requirement_sequence = next_number
    artifact_id = f"REQ-20260901090000-{next_number:02d}"
    basis = {
        "required": "Requirement changes product behavior and needs design",
        "n/a": "Requirement is documentation-only and introduces no design obligation",
        "waived": "Approved upstream exception waives the design phase",
        "pending": "Pending — applicability decision is unresolved",
    }[dsn_disposition]
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
        "| Phase | Disposition | Host | 判断依据 Basis |\n"
        "|---|---|---|---|\n"
        f"| DSN | {dsn_disposition} | N/A | {basis} |\n"
        "| PLN | pending | N/A | Pending — OPI-001 |\n"
        "| IMP | pending | N/A | Pending — OPI-001 |\n"
        "| VFY | required | N/A | VFY is the mandatory control point |\n"
        "| RLS | pending | N/A | Pending — OPI-001 |\n\n"
        + base._gate_summary()
    ).encode("utf-8")
    return self._write_frozen("REQ", raw)


base.DsnHandler = FinalDsnHandler
base.DsnRuntimeFixture.catalog = _catalog
base.DsnRuntimeFixture.create_requirement = _create_requirement
