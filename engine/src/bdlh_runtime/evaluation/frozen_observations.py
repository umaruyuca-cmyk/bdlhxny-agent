"""A/B 评测冻结工具返回（唯一真源：data 服务 → PostgreSQL fixture 表）。

数据集 ``ab-eval`` 由 seed（08）写入 ``fixture_tool_responses``；engine 启动
评测时一次拉取、运行期内存查找。三组对照共用同一份冻结数据，隔离工具执行
质量差异——唯一变量是编排形态。

call_key 规则：基准返回为工具名；标的覆盖为「工具名:标的代码」（如
``market.get_valuation:600519``）。查找先精确（带 symbol 覆盖键）再回退基准。
"""

from __future__ import annotations

from typing import Any

#: 评测使用的冻结数据集编号（对应 db seed 08 的 fixture_sets.id）。
FIXTURE_SET_ID = "ab-eval"


class FrozenObservations:
    """从 data 服务 payload 构建的冻结返回查找表（无代码内兜底数据）。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        responses = payload.get("responses") or []
        if not isinstance(responses, list) or not responses:
            raise ValueError("tool fixture payload has no responses")
        self._by_key: dict[str, dict[str, Any]] = {}
        for item in responses:
            call_key = str(item["call_key"])
            if item.get("response_status") != "SUCCESS":
                continue
            self._by_key[call_key] = dict(item["response"])
        if not self._by_key:
            raise ValueError("tool fixture payload has no SUCCESS responses")

    def get(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """按 (tool_name, symbol) 查找冻结返回；覆盖键优先，未命中回失败桩。"""
        symbol = str((arguments or {}).get("symbol") or "")
        if symbol and f"{tool_name}:{symbol}" in self._by_key:
            return self._by_key[f"{tool_name}:{symbol}"]
        if tool_name in self._by_key:
            return self._by_key[tool_name]
        return {"status": "FAILED", "error": f"unknown tool: {tool_name}"}
