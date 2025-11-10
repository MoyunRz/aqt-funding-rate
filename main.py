import os
from strategy.funding import run_funding
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    """程序入口：执行资金费率套利策略"""
    run_funding()