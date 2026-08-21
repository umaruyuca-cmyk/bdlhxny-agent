"""启动加载 + fail-fast 校验（最终八表目录）。

校验失败抛 ``ConfigurationError``，进程退出；禁止任何代码兜底目录。
资格上限来自 Settings，不在快照内。
"""

from __future__ import annotations

from typing import Any

from bdlh_runtime.infra.errors import ConfigurationError

from .defaults import DEFAULT_RUNTIME_ALLOWED_OPERATIONS
from .models import (
    CapabilityRecord,
    OperationRecord,
    RegistrySnapshot,
    SkillRecord,
    ToolsetRecord,
)
from .store import InMemoryRegistryStore, RegistryStore


def load_and_validate(
    store: RegistryStore,
    *,
    runtime_allowed_operations: frozenset[str] | None = None,
) -> RegistrySnapshot:
    """加载目录行并执行全部启动校验；任一失败即拒绝启动。"""
    snapshot = store.load()
    allowed = frozenset(runtime_allowed_operations or DEFAULT_RUNTIME_ALLOWED_OPERATIONS)
    _validate_capabilities(snapshot)
    _validate_skills(snapshot, runtime_allowed=allowed)
    return snapshot


def load_and_validate_payload(payload: dict[str, Any]) -> RegistrySnapshot:
    """从 data 服务返回的工具目录 JSON 构建快照并执行与启动一致的校验。

    JSON 结构与 ``GET /internal/v1/tool-catalog`` 一致；结构异常按
    ``ConfigurationError`` fail-fast，不做兜底目录。
    """
    store = InMemoryRegistryStore()
    try:
        store.operations = [
            OperationRecord(str(item["code"]), str(item["description"])) for item in payload["operations"]
        ]
        store.toolsets = [ToolsetRecord(str(item["name"]), str(item["description"])) for item in payload["toolsets"]]
        store.capabilities = [
            CapabilityRecord(
                name=str(item["name"]),
                description=str(item["description"]),
                domain=str(item["domain"]),
                adapter=str(item["adapter"]),
                read_only=bool(item["read_only"]),
                requires_authenticated_user=bool(item["requires_authenticated_user"]),
                required_arguments=frozenset(str(arg) for arg in item.get("required_arguments") or []),
                depends_on=frozenset(str(dep) for dep in item.get("depends_on") or []),
                timeout_seconds=int(item.get("timeout_seconds") or 20),
                enabled=bool(item.get("enabled", True)),
                operations=frozenset(str(op) for op in item.get("operations") or []),
                toolsets=frozenset(str(toolset) for toolset in item.get("toolsets") or []),
            )
            for item in payload["capabilities"]
        ]
        store.skills = [
            SkillRecord(
                skill_id=str(item["skill_id"]),
                skill_version=str(item["skill_version"]),
                domain=str(item["domain"]),
                status=str(item["status"]),
                enabled=bool(item["enabled"]),
                operations=frozenset((str(row["code"]), bool(row["required"])) for row in item.get("operations") or []),
                capabilities=frozenset(
                    (str(row["capability"]), bool(row["required"])) for row in item.get("capabilities") or []
                ),
            )
            for item in payload["skills"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"tool catalog payload is invalid: {exc}") from exc
    return load_and_validate(store)


def _validate_capabilities(snapshot: RegistrySnapshot) -> None:
    if not snapshot.capabilities:
        raise ConfigurationError("registry: zero capability rows; refusing to start without catalog")
    known = {cap.name for cap in snapshot.capabilities}
    for cap in snapshot.capabilities:
        if not cap.operations:
            raise ConfigurationError(f"registry: capability {cap.name} has no operation")
        if not cap.toolsets:
            raise ConfigurationError(f"registry: capability {cap.name} has no toolset")
        missing = cap.depends_on - known
        if missing:
            raise ConfigurationError(f"registry: capability {cap.name} depends_on unknown capability {sorted(missing)}")
        unknown_ops = cap.operations - {op.code for op in snapshot.operations}
        if unknown_ops:
            raise ConfigurationError(
                f"registry: capability {cap.name} references unknown operations {sorted(unknown_ops)}"
            )
        if not cap.read_only and cap.enabled:
            raise ConfigurationError(f"registry: capability {cap.name} is writable and enabled")


def _validate_skills(snapshot: RegistrySnapshot, *, runtime_allowed: frozenset[str]) -> None:
    known_caps = {cap.name for cap in snapshot.capabilities}
    known_ops = {op.code for op in snapshot.operations}
    for skill in snapshot.skills:
        missing_caps = {name for name, _ in skill.capabilities} - known_caps
        if missing_caps:
            raise ConfigurationError(
                f"registry: skill {skill.skill_id} references unknown capabilities {sorted(missing_caps)}"
            )
        missing_ops = {code for code, _ in skill.operations} - known_ops
        if missing_ops:
            raise ConfigurationError(
                f"registry: skill {skill.skill_id} references unknown operations {sorted(missing_ops)}"
            )
        if skill.enabled:
            required_ops = {code for code, required in skill.operations if required}
            outside = required_ops - set(runtime_allowed)
            if outside:
                raise ConfigurationError(
                    f"registry: enabled skill {skill.skill_id} required operations "
                    f"outside RUNTIME_ALLOWED_OPERATIONS: {sorted(outside)}"
                )
