#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现货杠杆下单测试脚本

用于测试 cex_spot_place 函数
"""

import os
import sys
from dotenv import load_dotenv

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rest
from rest.ccxt_client import get_ccxt_client
from utils.logger_config import LoggerConfig, get_logger
import logging

# 初始化日志
LoggerConfig.init_logger(
    log_dir='logs',
    log_level=logging.INFO,
    console_output=True,
    file_output=False
)

logger = get_logger(__name__)


def test_spot_place_buy(contract: str = "ETH_USDT", cost: str = "10"):
    """测试买入（做多）下单
    
    Args:
        contract: 交易对名称
        cost: USDT 成本金额
    """
    print("=" * 70)
    print("测试现货杠杆买入（做多）下单")
    print("=" * 70)
    
    # 检查 API 密钥
    client = get_ccxt_client()
    if not client.api_key:
        print("❌ 未配置 API 密钥")
        print("   请设置环境变量: API_KEY, API_SECRET")
        return False
    
    print(f"\n交易对: {contract}")
    print(f"成本金额: {cost} USDT")
    print(f"交易所: {client.exchange_id}")
    
    # 获取当前价格
    print("\n获取当前价格...")
    ticker = rest.get_cex_sticker(contract)
    if ticker and len(ticker) > 0:
        current_price = ticker[0].last
        calculated_size = str(float(cost) / current_price * 0.99)
        print(f"✅ 当前价格: ${current_price:,.2f}")
        print(f"   预计买入数量: {calculated_size}")
    else:
        print("❌ 无法获取价格")
        return False
    
    # 确认下单（非交互式环境自动确认）
    print("\n⚠️ 警告：这将执行真实的交易订单！")
    try:
        confirm = input("确认继续？(yes/no): ").strip().lower()
        if confirm != 'yes':
            print("已取消")
            return False
    except EOFError:
        # 非交互式环境，自动确认
        print("非交互式环境，自动确认继续...")
    
    # 执行下单
    print("\n执行买入下单...")
    try:
        order = rest.cex_spot_place(contract, "buy", cost, calculated_size)
        if order:
            print("✅ 订单创建成功")
            print(f"   订单ID: {order.id}")
            print(f"   成交数量: {order.amount}")
            print(f"   均价: ${order.avg_deal_price:,.2f}")
            print(f"   状态: {order.status}")
            print(f"   手续费: {order.fee}")
            return True
        else:
            print("❌ 订单创建失败")
            return False
    except Exception as e:
        print(f"❌ 下单失败: {e}")
        logger.error(f"下单失败: {e}", exc_info=True)
        return False


def test_spot_place_sell(contract: str = "ETH_USDT", size: str = "0.01"):
    """测试卖出（做空）下单
    
    Args:
        contract: 交易对名称
        size: 卖出数量（币数量）
    """
    print("=" * 70)
    print("测试现货杠杆卖出（做空）下单")
    print("=" * 70)
    
    # 检查 API 密钥
    client = get_ccxt_client()
    if not client.api_key:
        print("❌ 未配置 API 密钥")
        print("   请设置环境变量: API_KEY, API_SECRET")
        return False
    
    print(f"\n交易对: {contract}")
    print(f"卖出数量: {size}")
    print(f"交易所: {client.exchange_id}")
    
    # 获取当前价格以计算成本
    print("\n获取当前价格...")
    ticker = rest.get_cex_sticker(contract)
    if ticker and len(ticker) > 0:
        current_price = ticker[0].last
        cost_value = float(size) * current_price
        print(f"✅ 当前价格: ${current_price:,.2f}")
        print(f"   预计卖出价值: ${cost_value:,.2f} USDT")
    else:
        print("❌ 无法获取价格")
        return False
    
    # 确认下单（非交互式环境自动确认）
    print("\n⚠️ 警告：这将执行真实的交易订单！")
    print("   注意：卖出需要先有持仓或借币")
    try:
        confirm = input("确认继续？(yes/no): ").strip().lower()
        if confirm != 'yes':
            print("已取消")
            return False
    except EOFError:
        # 非交互式环境，自动确认
        print("非交互式环境，自动确认继续...")
    
    # 执行下单
    print("\n执行卖出下单...")
    try:
        # 卖出时 cost 参数用于计算，实际使用 size
        cost_str = str(cost_value)
        order = rest.cex_spot_place(contract, "sell", cost_str, size)
        if order:
            print("✅ 订单创建成功")
            print(f"   订单ID: {order.id}")
            print(f"   成交数量: {order.amount}")
            print(f"   均价: ${order.avg_deal_price:,.2f}")
            print(f"   状态: {order.status}")
            print(f"   手续费: {order.fee}")
            return True
        else:
            print("❌ 订单创建失败")
            return False
    except Exception as e:
        print(f"❌ 下单失败: {e}")
        logger.error(f"下单失败: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='现货杠杆下单测试')
    parser.add_argument('--type', choices=['buy', 'sell', 'test'], default='test',
                       help='测试类型: buy=买入, sell=卖出, test=参数验证测试（默认）')
    parser.add_argument('--contract', default='ETH_USDT', help='交易对名称（默认: ETH_USDT）')
    parser.add_argument('--cost', default='10', help='买入成本金额 USDT（默认: 10）')
    parser.add_argument('--size', default='0.01', help='卖出数量（默认: 0.01）')
    parser.add_argument('--dry-run', action='store_true', help='DRY RUN 模式，不实际下单')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("现货杠杆下单测试")
    print("=" * 70)
    
    # 显示交易所信息
    try:
        client = get_ccxt_client()
        print(f"\n交易所: {client.exchange_id}")
        print(f"测试网: {client.use_testnet}")
    except Exception as e:
        print(f"❌ 无法获取客户端信息: {e}")
        return
    
    if args.dry_run:
        print("\n⚠️ DRY RUN 模式：只进行参数验证，不会实际下单")
    
    # 根据参数执行测试
    if args.type == 'test':
        # 参数验证测试
        print("\n📝 执行参数验证测试...")
        try:
            # 测试无效成本金额
            result = rest.cex_spot_place(args.contract, "buy", "0", "0")
            if result is None:
                print("✅ 参数验证正常（无效金额被拒绝）")
            else:
                print("❌ 参数验证失败（应该拒绝无效金额）")
                return False
        except Exception as e:
            print(f"⚠️ 参数验证测试异常: {e}")
        
        # 测试获取价格
        print("\n📊 测试获取价格...")
        try:
            ticker = rest.get_cex_sticker(args.contract)
            if ticker and len(ticker) > 0:
                print(f"✅ 成功获取价格: ${ticker[0].last:,.2f}")
            else:
                print("❌ 无法获取价格")
                return False
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            return False
        
        print("\n✅ 参数验证测试完成")
        if args.dry_run:
            print("⚠️ DRY RUN 模式：跳过实际下单测试")
        return True
    
    elif args.type == 'buy':
        # 买入测试
        if args.dry_run:
            print("\n⚠️ DRY RUN 模式：跳过实际下单")
            return True
        return test_spot_place_buy(args.contract, args.cost)
    
    elif args.type == 'sell':
        # 卖出测试
        if args.dry_run:
            print("\n⚠️ DRY RUN 模式：跳过实际下单")
            return True
        return test_spot_place_sell(args.contract, args.size)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}", exc_info=True)
        sys.exit(1)

