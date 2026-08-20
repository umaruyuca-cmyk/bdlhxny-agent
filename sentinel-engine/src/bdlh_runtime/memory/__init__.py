"""记忆层包入口。

对外暴露统一接口 MemoryStore。Touchstone 精简：仅保留 ``memory.base``
（MemoryStore 端口）与 ``memory.recall``（语义召回）；写入链（writer /
remote）已随会话与看护系统移除（见 main 分支）。
"""

from .base import MemoryRecord, MemoryStore
from .recall import MemoryRecallResult, recall_semantic_memory

__all__ = [
    "MemoryRecord",
    "MemoryRecallResult",
    "MemoryStore",
    "recall_semantic_memory",
]
