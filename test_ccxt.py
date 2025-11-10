#!/usr/bin/env python3
"""
CCXT 功能测试脚本

用于验证 CCXT API 是否正常工作
"""

import os
import sys

# 强制使用 CCXT
os.environ['USE_CCXT'] = 'true'

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 现在 rest 模块已经从 ccxt_client 导入所有函数
import rest
from rest.ccxt_client import get_ccxt_client
from utils.logger_config import LoggerConfig, get_logger
import logging

# 初始化日志
LoggerConfig.init_logger(
    log_dir='logs',
    log_level=logging.INFO,
    console_output=True,
    file_output=False  # 测试时不写文件
)

logger = get_logger(__name__)


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_market_data():
    """测试市场数据 API（无需 API 密钥）"""
    print_section("1. 测试市场数据 API")
    
    # 测试获取合约列表
    print("\n📋 获取合约列表...")
    try:
        contracts = rest.get_cex_contracts()
        if contracts:
            print(f"✅ 成功获取 {len(contracts)} 个合约")
            
            # 显示前5个合约
            print("\n前5个合约:")
            for i, contract in enumerate(contracts[:5], 1):
                print(f"   {i}. {contract.name}")
                print(f"      资金费率: {contract.funding_rate*100:.4f}%")
                print(f"      标记价格: ${contract.mark_price:,.2f}")
                print(f"      结算间隔: {contract.funding_interval//3600}小时")
        else:
            print("❌ 获取合约列表失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 测试获取现货行情
    print("\n💹 获取 BTC_USDT 现货行情...")
    try:
        ticker = rest.get_cex_sticker("BTC_USDT")
        if ticker and len(ticker) > 0:
            t = ticker[0]
            print(f"✅ 成功获取行情")
            print(f"   最新价: ${t.last:,.2f}")
            print(f"   买一价: ${t.highest_bid:,.2f}")
            print(f"   卖一价: ${t.lowest_ask:,.2f}")
            print(f"   24h成交量: {t.base_volume:,.2f} BTC")
        else:
            print("❌ 获取行情失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 测试获取合约行情
    print("\n📊 获取 BTC_USDT 合约行情...")
    try:
        fticker = rest.get_cex_fticker("BTC_USDT")
        if fticker and len(fticker) > 0:
            t = fticker[0]
            print(f"✅ 成功获取合约行情")
            print(f"   合约价格: ${t.last:,.2f}")
            print(f"   买一价: ${t.highest_bid:,.2f}")
            print(f"   卖一价: ${t.lowest_ask:,.2f}")
        else:
            print("❌ 获取合约行情失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 测试获取K线数据
    print("\n📈 获取 BTC_USDT K线数据（1分钟，最近10根）...")
    try:
        candles = rest.get_cex_spot_candle("BTC_USDT", "1m", 10)
        if candles:
            print(f"✅ 成功获取 {len(candles)} 根K线")
            if len(candles) > 0:
                latest = candles[-1]
                print(f"   最新K线: 时间={latest[0]}, 开={latest[1]}, 高={latest[2]}, 低={latest[3]}, 收={latest[4]}, 量={latest[5]}")
        else:
            print("❌ 获取K线失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    return True


def test_account_api():
    """测试账户 API（需要 API 密钥）"""
    print_section("2. 测试账户 API（需要 API 密钥）")
    
    # 检查是否配置了 API 密钥
    api_key = os.getenv('GATE_API_KEY', '') or os.getenv('API_KEY', '')
    if not api_key:
        print("⚠️ 未配置 API 密钥，跳过账户 API 测试")
        print("   设置方法: export API_KEY='your_key'")
        print("            export API_SECRET='your_secret'")
        return True
    
    # 测试获取余额
    print("\n💰 获取账户余额...")
    try:
        balance = rest.get_cex_wallet_balance()
        if balance:
            print(f"✅ 成功获取余额")
            print(f"   币种: {balance.currency}")
            print(f"   可用: ${balance.available:,.2f}")
            print(f"   总额: ${balance.total:,.2f}")
        else:
            print("❌ 获取余额失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("   请检查 API 密钥是否正确")
        return False
    
    # 测试获取持仓
    print("\n📦 获取当前持仓...")
    try:
        positions = rest.get_cex_all_position()
        if positions:
            print(f"✅ 当前持仓数: {len(positions)}")
            for pos in positions:
                print(f"   {pos.contract}:")
                print(f"      数量: {pos.size} 张")
                print(f"      杠杆: {pos.leverage}x")
                print(f"      未实现盈亏: ${pos.unrealised_pnl:,.2f}")
        else:
            print("✅ 当前无持仓")
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    return True


def test_spot_place_order(dry_run: bool = True, contract: str = "ETH_USDT", cost: str = "10", size: str = "0.01"):
    """测试现货杠杆下单
    
    Args:
        dry_run: 如果为 True，只测试参数验证，不下单
        contract: 交易对名称
        cost: 买入时的 USDT 成本金额
        size: 卖出时的币数量
    """
    print_section("3. 测试现货杠杆下单")
    
    # 检查是否配置了 API 密钥
    api_key = os.getenv('API_KEY', '') or os.getenv('BITGET_API_KEY', '')
    if not api_key:
        print("⚠️ 未配置 API 密钥，跳过下单测试")
        print("   设置方法: export API_KEY='your_key'")
        print("            export API_SECRET='your_secret'")
        if os.getenv('EXCHANGE_ID', '').lower() in ['bitget', 'okx']:
            print("            export API_PASSWORD='your_passphrase'")
        return True
    
    if dry_run:
        print("⚠️ 当前为 DRY RUN 模式，不会实际下单")
        print("   要实际下单，请设置 dry_run=False")
    
    # 测试参数验证
    print("\n📝 测试参数验证...")
    try:
        # 测试无效成本金额
        result = rest.cex_spot_place(contract, "buy", "0", "0")
        if result is None:
            print("✅ 参数验证正常（无效金额被拒绝）")
        else:
            print("❌ 参数验证失败（应该拒绝无效金额）")
            return False
    except Exception as e:
        print(f"⚠️ 参数验证测试异常: {e}")
    
    if dry_run:
        print("\n⚠️ DRY RUN 模式：跳过实际下单测试")
        print("   如果要测试实际下单，请修改代码设置 dry_run=False")
        return True
    
    # 测试买入（做多）
    print("\n📈 测试买入（做多）下单...")
    print(f"   交易对: {contract}")
    print(f"   成本: {cost} USDT")
    
    try:
        # 获取当前价格以计算 size（用于卖出测试）
        ticker = rest.get_cex_sticker(contract)
        if ticker and len(ticker) > 0:
            current_price = ticker[0].last
            calculated_size = str(float(cost) / current_price * 0.99)  # 留1%余量
            print(f"   当前价格: ${current_price:,.2f}")
            print(f"   预计买入数量: {calculated_size}")
        else:
            calculated_size = size
        
        # 确认是否继续
        print("\n⚠️ 警告：这将执行真实的交易订单！")
        confirm = input("   确认继续？(yes/no): ").strip().lower()
        if confirm != 'yes':
            print("   已取消下单测试")
            return True
        
        order = rest.cex_spot_place(contract, "buy", cost, calculated_size)
        if order:
            print(f"✅ 买入订单创建成功")
            print(f"   订单ID: {order.id}")
            print(f"   成交数量: {order.amount}")
            print(f"   均价: ${order.avg_deal_price:,.2f}")
            print(f"   状态: {order.status}")
            print(f"   手续费: {order.fee}")
        else:
            print("❌ 买入订单创建失败")
            return False
    except Exception as e:
        print(f"❌ 买入下单测试失败: {e}")
        logger.error(f"买入下单测试失败: {e}", exc_info=True)
        return False
    
    # 测试卖出（做空）- 可选，需要先有持仓
    print("\n📉 测试卖出（做空）下单（可选）...")
    print("   注意：卖出需要先有持仓或借币")
    test_sell = input("   是否测试卖出？(yes/no): ").strip().lower()
    
    if test_sell == 'yes':
        print(f"   交易对: {contract}")
        print(f"   卖出数量: {size}")
        
        try:
            confirm = input("   确认继续？(yes/no): ").strip().lower()
            if confirm != 'yes':
                print("   已取消卖出测试")
                return True
            
            order = rest.cex_spot_place(contract, "sell", cost, size)
            if order:
                print(f"✅ 卖出订单创建成功")
                print(f"   订单ID: {order.id}")
                print(f"   成交数量: {order.amount}")
                print(f"   均价: ${order.avg_deal_price:,.2f}")
                print(f"   状态: {order.status}")
                print(f"   手续费: {order.fee}")
            else:
                print("❌ 卖出订单创建失败")
                return False
        except Exception as e:
            print(f"❌ 卖出下单测试失败: {e}")
            logger.error(f"卖出下单测试失败: {e}", exc_info=True)
            return False
    
    return True


def test_client_info():
    """测试客户端信息"""
    print_section("0. CCXT 客户端信息")
    
    try:
        client = get_ccxt_client()
        exchange = client.exchange
        
        print(f"\n交易所信息:")
        print(f"   ID: {exchange.id}")
        print(f"   名称: {exchange.name}")
        print(f"   版本: {exchange.version if hasattr(exchange, 'version') else 'N/A'}")
        print(f"   测试网: {client.use_testnet}")
        print(f"   速率限制: {exchange.enableRateLimit}")
        
        # 检查 API 密钥配置
        has_key = bool(client.api_key)
        has_secret = bool(client.api_secret)
        
        print(f"\nAPI 配置:")
        print(f"   API Key: {'✅ 已配置' if has_key else '❌ 未配置'}")
        print(f"   API Secret: {'✅ 已配置' if has_secret else '❌ 未配置'}")
        
        if has_key:
            # 隐藏显示
            key_display = client.api_key[:8] + "..." + client.api_key[-4:] if len(client.api_key) > 12 else "***"
            print(f"   Key 预览: {key_display}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取客户端信息失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "CCXT 功能测试" + " " * 36 + "║")
    print("╚" + "=" * 68 + "╝")
    
    results = []
    
    # 测试客户端信息
    results.append(("客户端信息", test_client_info()))
    
    # 测试市场数据
    results.append(("市场数据API", test_market_data()))
    
    # 测试账户API
    results.append(("账户API", test_account_api()))
    
    # 测试现货杠杆下单（默认 DRY RUN 模式）
    results.append(("现货杠杆下单", test_spot_place_order(dry_run=True)))
    
    # 汇总结果
    print_section("测试结果汇总")
    
    print()
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed + failed} 个测试")
    print(f"   ✅ 通过: {passed}")
    print(f"   ❌ 失败: {failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！CCXT 功能正常！")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查配置")
    
    print("\n" + "=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}", exc_info=True)
        sys.exit(1)

