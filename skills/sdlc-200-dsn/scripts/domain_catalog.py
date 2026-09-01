"""Fixed DSN Domain catalog and generic Domain Member validation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

DOMAIN_DISPOSITIONS = frozenset({"required", "n/a", "waived", "pending"})
DOMAIN_COMPLETIONS = {
    "required": frozenset({"not_started", "in_progress", "complete"}),
    "n/a": frozenset({"not_applicable"}),
    "waived": frozenset({"waived"}),
    "pending": frozenset({"not_started"}),
}
REFERENCE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@%+#-]*$")


@dataclass(frozen=True)
class DomainDefinition:
    code: str
    group: str
    zh_name: str
    en_name: str
    filename: str
    check_ids: tuple[str, ...]
    always_required: bool = False

    @property
    def display_name(self) -> str:
        return f"{self.zh_name} {self.en_name}"

    @property
    def canonical_name(self) -> str:
        return f"domains/{self.filename}"


def _checks(number: str, count: int) -> tuple[str, ...]:
    return tuple(
        f"DSN-DG-{number}-{index:03d}" for index in range(1, count + 1)
    )


DOMAIN_CATALOG = (
    DomainDefinition("DOM-110", "行为设计 Behavior", "流程与状态", "Workflow and State", "110-workflow-state.md", _checks("110", 3)),
    DomainDefinition("DOM-120", "行为设计 Behavior", "用户体验与交互", "UX and Interaction", "120-ux-interaction.md", _checks("120", 3)),
    DomainDefinition("DOM-130", "行为设计 Behavior", "界面与内容", "UI and Content", "130-ui-content.md", _checks("130", 3)),
    DomainDefinition("DOM-140", "行为设计 Behavior", "可访问性与国际化", "Accessibility and Internationalization", "140-accessibility-i18n.md", _checks("140", 3)),
    DomainDefinition("DOM-210", "技术设计 Technical", "系统与架构", "System and Architecture", "210-system-architecture.md", _checks("210", 3)),
    DomainDefinition("DOM-220", "技术设计 Technical", "组件与模块", "Components and Modules", "220-components-modules.md", _checks("220", 3)),
    DomainDefinition("DOM-230", "技术设计 Technical", "接口与集成", "Interfaces and Integration", "230-interfaces-integration.md", _checks("230", 3)),
    DomainDefinition("DOM-240", "技术设计 Technical", "数据设计", "Data Design", "240-data-design.md", _checks("240", 3)),
    DomainDefinition("DOM-310", "质量属性 Quality", "安全、隐私与合规", "Security, Privacy and Compliance", "310-security-privacy-compliance.md", _checks("310", 4)),
    DomainDefinition("DOM-320", "质量属性 Quality", "性能与容量", "Performance and Capacity", "320-performance-capacity.md", _checks("320", 3)),
    DomainDefinition("DOM-330", "质量属性 Quality", "可靠性与恢复", "Reliability and Recovery", "330-reliability-recovery.md", _checks("330", 3)),
    DomainDefinition("DOM-340", "质量属性 Quality", "兼容与迁移", "Compatibility and Migration", "340-compatibility-migration.md", _checks("340", 3)),
    DomainDefinition("DOM-350", "质量属性 Quality", "可维护性与扩展性", "Maintainability and Extensibility", "350-maintainability-extensibility.md", _checks("350", 3)),
    DomainDefinition("DOM-410", "运行设计 Operations", "部署与配置", "Deployment and Configuration", "410-deployment-configuration.md", _checks("410", 3)),
    DomainDefinition("DOM-420", "运行设计 Operations", "可观测性与可运维性", "Observability and Operability", "420-observability-operability.md", _checks("420", 3)),
    DomainDefinition("DOM-510", "验证设计 Verification", "可验证性与 VFY 策略", "Verifiability and VFY Strategy", "510-verifiability-vfy-strategy.md", _checks("510", 5), True),
)
DOMAIN_BY_CODE = {item.code: item for item in DOMAIN_CATALOG}
DOMAIN_ORDER = tuple(item.code for item in DOMAIN_CATALOG)
COMPOSITE_SUBDOMAINS = (
    ("DOM-140", "可访问性 Accessibility"),
    ("DOM-140", "国际化 Internationalization"),
    ("DOM-310", "安全 Security"),
    ("DOM-310", "隐私 Privacy"),
    ("DOM-310", "合规 Compliance"),
)


class DomainContractError(ValueError):
    code = "DSN_DOMAIN_INVALID"


def _text(value: Any, name: str, *, allow_na: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainContractError(f"{name} must be a non-empty string")
    result = value.strip()
    if not allow_na and result in {"N/A", "None", "Pending"}:
        raise DomainContractError(f"{name} must contain a concrete value")
    return result


def _refs(value: Any, name: str, *, required: bool = True) -> tuple[str, ...]:
    if value is None:
        values: list[str] = []
    elif isinstance(value, str):
        values = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = [str(part).strip() for part in value if str(part).strip()]
    else:
        raise DomainContractError(f"{name} must be a reference array")
    if required and not values:
        raise DomainContractError(f"{name} must not be empty")
    if len(values) != len(set(values)):
        raise DomainContractError(f"{name} contains duplicate references")
    if any(not REFERENCE_TOKEN_RE.fullmatch(item) for item in values):
        raise DomainContractError(f"{name} contains an invalid reference token")
    return tuple(values)


def normalize_domain_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Mapping):
        raise DomainContractError("design.domains must be an object keyed by DOM code")
    extra = sorted(set(value) - set(DOMAIN_ORDER))
    if extra:
        raise DomainContractError("unregistered DSN Domain: " + ", ".join(extra))
    rows: list[Mapping[str, Any]] = []
    for definition in DOMAIN_CATALOG:
        raw = value.get(definition.code)
        if raw is None:
            raw = {
                "disposition": "required" if definition.always_required else "pending",
                "completion": "not_started",
                "reason": (
                    "Pending — required Domain content is not started"
                    if definition.always_required
                    else f"Pending — OPI-{len(rows) + 1:03d}"
                ),
                "basis_references": [],
            }
        if not isinstance(raw, Mapping):
            raise DomainContractError(f"{definition.code} must be an object")
        disposition = raw.get("disposition", "pending")
        completion = raw.get(
            "completion",
            {
                "required": "not_started",
                "n/a": "not_applicable",
                "waived": "waived",
                "pending": "not_started",
            }.get(str(disposition), "not_started"),
        )
        if disposition not in DOMAIN_DISPOSITIONS:
            raise DomainContractError(
                f"{definition.code} has invalid disposition: {disposition}"
            )
        if completion not in DOMAIN_COMPLETIONS[disposition]:
            raise DomainContractError(
                f"{definition.code} completion {completion} conflicts with {disposition}"
            )
        if definition.always_required and disposition != "required":
            raise DomainContractError("DOM-510 is required whenever a DSN exists")
        basis = _refs(
            raw.get("basis_references"),
            f"{definition.code}.basis_references",
            required=(
                disposition in {"n/a", "waived"}
                or (disposition == "required" and completion == "complete")
            ),
        )
        normalized: dict[str, Any] = {
            "code": definition.code,
            "definition": definition,
            "disposition": disposition,
            "completion": completion,
            "responsible_role": str(raw.get("responsible_role") or "").strip(),
            "basis_references": basis,
            "reason": str(raw.get("reason") or "").strip(),
            "exception_reference": str(raw.get("exception_reference") or "").strip(),
            "design_result_markdown": str(raw.get("design_result_markdown") or "").strip(),
            "constraints_impacts": tuple(raw.get("constraints_impacts") or ()),
            "vfy_points": tuple(raw.get("vfy_points") or ()),
            "evidence_references": tuple(raw.get("evidence_references") or ()),
        }
        if disposition == "required":
            if completion != "not_started":
                normalized["responsible_role"] = _text(
                    normalized["responsible_role"],
                    f"{definition.code}.responsible_role",
                )
            if completion == "complete":
                markdown = _text(
                    normalized["design_result_markdown"],
                    f"{definition.code}.design_result_markdown",
                )
                if "## 设计结果 Design Result" not in markdown:
                    raise DomainContractError(
                        f"{definition.code} content must start with Design Result"
                    )
                if definition.code == "DOM-510":
                    for marker in (
                        "### VFY 目标 VFY Objectives",
                        "### 方法选择 VFY Methods",
                        "### 通过条件 Pass Criteria",
                        "### Evidence Contract",
                    ):
                        if marker not in markdown:
                            raise DomainContractError(
                                f"DOM-510 content is missing required section: {marker}"
                            )
                elif not normalized["vfy_points"]:
                    raise DomainContractError(
                        f"{definition.code} requires at least one VFY Point"
                    )
            else:
                normalized["reason"] = normalized["reason"] or (
                    f"Pending — {definition.code} required content is incomplete"
                )
        elif disposition == "n/a":
            normalized["reason"] = _text(
                normalized["reason"], f"{definition.code}.n/a reason"
            )
        elif disposition == "waived":
            normalized["reason"] = _text(
                normalized["reason"], f"{definition.code}.waiver reason"
            )
            normalized["exception_reference"] = _text(
                normalized["exception_reference"],
                f"{definition.code}.exception_reference",
            )
        else:
            normalized["reason"] = _text(
                normalized["reason"], f"{definition.code}.pending reason"
            )
            if "OPI-" not in normalized["reason"]:
                raise DomainContractError(
                    f"{definition.code} pending reason must reference an Open Item"
                )
        rows.append(normalized)
    return tuple(rows)


def normalize_composite_rows(value: Any) -> tuple[Mapping[str, str], ...]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise DomainContractError("design.composite_subdomains must be an array")
    by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in value:
        if not isinstance(row, Mapping):
            raise DomainContractError("composite subdomain row must be an object")
        key = (str(row.get("domain_code")), str(row.get("subdomain")))
        if key in by_key:
            raise DomainContractError(f"duplicate composite subdomain: {key}")
        by_key[key] = row
    normalized: list[Mapping[str, str]] = []
    for domain_code, subdomain in COMPOSITE_SUBDOMAINS:
        row = by_key.get((domain_code, subdomain))
        if row is None:
            row = {
                "disposition": "pending",
                "basis_references": [],
                "reason": "Pending — OPI-001",
                "exception_references": [],
            }
        disposition = str(row.get("disposition"))
        if disposition not in DOMAIN_DISPOSITIONS:
            raise DomainContractError(
                f"{domain_code}/{subdomain} has invalid disposition"
            )
        basis = _refs(
            row.get("basis_references"),
            f"{domain_code}/{subdomain}.basis_references",
            required=disposition != "pending",
        )
        reason = str(row.get("reason") or "").strip()
        exceptions = _refs(
            row.get("exception_references"),
            f"{domain_code}/{subdomain}.exception_references",
            required=disposition == "waived",
        )
        if disposition == "required":
            reason = "N/A"
            exceptions = ()
        elif disposition == "n/a":
            reason = _text(reason, f"{domain_code}/{subdomain}.n/a reason")
            exceptions = ()
        elif disposition == "waived":
            reason = _text(reason, f"{domain_code}/{subdomain}.waiver reason")
        else:
            reason = _text(reason, f"{domain_code}/{subdomain}.pending reason")
            if "OPI-" not in reason:
                raise DomainContractError(
                    f"{domain_code}/{subdomain} pending reason must reference OPI"
                )
            exceptions = ()
        normalized.append(
            {
                "domain_code": domain_code,
                "subdomain": subdomain,
                "disposition": disposition,
                "basis_references": ", ".join(basis) if basis else "None",
                "reason": reason,
                "exception_references": ", ".join(exceptions) if exceptions else (
                    "N/A" if disposition == "n/a" else "None"
                ),
            }
        )
    extra = sorted(set(by_key) - set(COMPOSITE_SUBDOMAINS))
    if extra:
        raise DomainContractError(f"unregistered composite subdomain: {extra}")
    return tuple(normalized)


def aggregate_composite_disposition(
    rows: Sequence[Mapping[str, str]], domain_code: str
) -> str:
    dispositions = [
        row["disposition"] for row in rows if row["domain_code"] == domain_code
    ]
    for candidate in ("pending", "required", "waived", "n/a"):
        if candidate in dispositions:
            return candidate
    raise DomainContractError(f"composite rows missing for {domain_code}")
