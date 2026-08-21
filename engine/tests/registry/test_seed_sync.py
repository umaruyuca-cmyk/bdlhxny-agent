"""工具目录种子同步守卫。

数据库 seed（07 SQL）是工具目录唯一真源；``tests/registry/seeded_store.py``
是单测注入的替身。两者漂移（改了一处忘另一处）即失败。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.registry.seeded_store import build_seeded_store

_SEED_SQL = Path(__file__).resolve().parents[3] / "db" / "postgresql" / "setup" / "07-create-tool-catalog-tables.sql"

_CAP_RE = re.compile(
    r"\('([a-z_.]+)', '[^']*', '[a-z]+', '(mcp|java|web|local)', (true|false),\s*"
    r"'(\[[^\]]*\])',\s*'(\[[^\]]*\])',\s*'(\[[^\]]*\])',\s*'(\[[^\]]*\])'\)"
)


def _section(marker: str) -> str:
    text = _SEED_SQL.read_text(encoding="utf-8")
    start = text.index(marker)
    return text[start : text.index(";", start)]


def _sql_rows(marker: str, pattern: str) -> list[tuple[str, ...]]:
    return re.findall(pattern, _section(marker), re.MULTILINE)


def test_operations_match_seed():
    sql_ops = set(_sql_rows("INSERT INTO touchstone.tool_operations", r"^\('([A-Z_]+)', '[^']*'\)"))
    store_ops = {op.code for op in build_seeded_store().operations}
    assert sql_ops == store_ops, "操作证清单与数据库 seed 不一致"


def test_toolsets_match_seed():
    sql_sets = set(_sql_rows("INSERT INTO touchstone.toolsets", r"^\('([a-z_]+)', '[^']*'\)"))
    store_sets = {ts.name for ts in build_seeded_store().toolsets}
    assert sql_sets == store_sets, "工具集清单与数据库 seed 不一致"


def test_capabilities_match_seed():
    rows = _CAP_RE.findall(_section("INSERT INTO touchstone.tool_capabilities"))
    sql_caps = {
        name: {
            "adapter": adapter,
            "auth": auth == "true",
            "required_arguments": frozenset(json.loads(required)),
            "depends_on": frozenset(json.loads(depends)),
            "operations": frozenset(json.loads(ops)),
            "toolsets": frozenset(json.loads(toolsets)),
        }
        for name, adapter, auth, required, depends, ops, toolsets in rows
    }
    store_caps = {cap.name: cap for cap in build_seeded_store().capabilities}
    assert set(sql_caps) == set(store_caps), "工具能力清单与数据库 seed 不一致"
    for name, expected in sql_caps.items():
        cap = store_caps[name]
        assert cap.adapter == expected["adapter"], f"{name} adapter 漂移"
        assert cap.requires_authenticated_user == expected["auth"], f"{name} auth 漂移"
        assert cap.required_arguments == expected["required_arguments"], f"{name} 参数漂移"
        assert cap.depends_on == expected["depends_on"], f"{name} 依赖漂移"
        assert cap.operations == expected["operations"], f"{name} operations 漂移"
        assert cap.toolsets == expected["toolsets"], f"{name} toolsets 漂移"


def test_skills_match_seed():
    sql_skills = {
        skill: (status, enabled == "true")
        for skill, status, enabled in _sql_rows(
            "INSERT INTO touchstone.tool_skills", r"^\('([a-z0-9-]+)', '[^']*', '[a-z]+', '([A-Z]+)', (true|false)\)"
        )
    }
    sql_skill_ops: dict[str, set[tuple[str, bool]]] = {}
    for skill, code, required in _sql_rows(
        "INSERT INTO touchstone.tool_skill_operations", r"^\('([a-z0-9-]+)', '([A-Z_]+)', (true|false)\)"
    ):
        sql_skill_ops.setdefault(skill, set()).add((code, required == "true"))
    sql_skill_caps: dict[str, set[tuple[str, bool]]] = {}
    for skill, capability, required in _sql_rows(
        "INSERT INTO touchstone.tool_skill_capabilities", r"^\('([a-z0-9-]+)', '([a-z_.]+)', (true|false)\)"
    ):
        sql_skill_caps.setdefault(skill, set()).add((capability, required == "true"))

    store_skills = {skill.skill_id: skill for skill in build_seeded_store().skills}
    assert set(sql_skills) == set(store_skills), "技能清单与数据库 seed 不一致"
    for skill_id, (status, enabled) in sql_skills.items():
        skill = store_skills[skill_id]
        assert skill.status == status, f"{skill_id} status 漂移"
        assert skill.enabled == enabled, f"{skill_id} enabled 漂移"
        assert skill.operations == sql_skill_ops.get(skill_id, set()), f"{skill_id} operations 漂移"
        assert skill.capabilities == sql_skill_caps.get(skill_id, set()), f"{skill_id} capabilities 漂移"
