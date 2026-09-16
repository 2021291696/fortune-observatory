"""奇门遁甲（时家转盘，mainline-cn-v1）确定性排盘。

第一实现：本包是网站排盘唯一计算源（apps/api 调用）。
第二实现 = skills/qimen-dunjia/scripts/qimen_cli.py（仓库内 skill 副本），
两者由 tests/differential/test_qimen_skill_parity.py 逐字段对拍；
修改任一侧必须跑差分并在另一侧同步。
"""

from fortune_core.qimen.engine import build_output

__all__ = ["build_output"]
