# ==================== 程序入口 ====================
import os

from strategy.gate_funding import run_funding
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    """
    程序入口

    执行资金费率套利策略：
    - 自动扫描市场上资金费率最高的合约
    - 在资金费率结算前开仓（合约+现货对冲）
    - 收取资金费率后，等待盈利平仓

    使用方法：
        python gate_funding.py

    退出方法：
        按 Ctrl+C 中断程序
    """
    run_funding()