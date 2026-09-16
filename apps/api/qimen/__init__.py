"""奇门遁甲 API 模块：解读口径来源与端点实现。

排盘计算 = src/fortune_core/qimen（确定性引擎）；
解读口径 = skills/qimen-dunjia/references（仓库内 skill 副本，与本地
~/.agents/skills/qimen-dunjia 实体相互独立）。
"""

from qimen.service import build_qimen_chart, stream_qimen_events

__all__ = ["build_qimen_chart", "stream_qimen_events"]
