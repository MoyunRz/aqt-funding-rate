# CCXT 快速开始指南 🚀

## 📦 安装

CCXT 已经在 `requirements.txt` 中，如果没安装：

```bash
pip install ccxt>=4.5.0
```

## ⚡ 3步启用 CCXT

### 步骤 1：配置环境变量

编辑 `.env` 文件（或复制 `env.template`）：

```bash
# 启用 CCXT
USE_CCXT=true

# 配置 API（从 Gate.io 获取）
GATE_API_KEY=your_api_key_here
GATE_API_SECRET=your_api_secret_here

# 可选：使用测试网
USE_TESTNET=false
```

### 步骤 2：测试 CCXT

```bash
# 运行测试脚本
python3 test_ccxt.py
```

期望输出：

```
╔====================================================================╗
║                    CCXT 功能测试                                    ║
╚====================================================================╝

==================================================
  0. CCXT 客户端信息
==================================================

交易所信息:
   ID: gate
   名称: Gate.io
   测试网: False
   速率限制: True

API 配置:
   API Key: ✅ 已配置
   API Secret: ✅ 已配置

==================================================
  1. 测试市场数据 API
==================================================

📋 获取合约列表...
✅ 成功获取 150 个合约

前5个合约:
   1. BTC_USDT
      资金费率: 0.0100%
      标记价格: $95,234.50
      结算间隔: 8小时

💹 获取 BTC_USDT 现货行情...
✅ 成功获取行情
   最新价: $95,234.50
   买一价: $95,233.00
   卖一价: $95,235.00

... (更多测试输出)

🎉 所有测试通过！CCXT 功能正常！
```

### 步骤 3：启动策略

```bash
python3 main.py
```

就这么简单！现在你的程序已经在使用 CCXT 了！

## 🎯 代码示例

### 基本使用

```python
# 导入 REST API（会自动使用 CCXT）
import rest

# 获取合约列表
contracts = rest.get_cex_contracts()
for contract in contracts[:5]:
    print(f"{contract.name}: {contract.funding_rate*100:.4f}%")

# 获取行情
ticker = rest.get_cex_sticker("BTC_USDT")
print(f"BTC 价格: ${ticker[0].last:,.2f}")

# 获取持仓（需要 API 密钥）
positions = rest.get_cex_all_position()
if positions:
    for pos in positions:
        print(f"{pos.contract}: {pos.size} 张")
```

### 直接使用 CCXT 客户端

```python
from rest.ccxt_client import get_ccxt_client

# 获取客户端
client = get_ccxt_client()
exchange = client.exchange

# 使用原生 CCXT API
markets = exchange.load_markets()
ticker = exchange.fetch_ticker('BTC/USDT')
print(f"BTC: ${ticker['last']}")

# 查看支持的交易所
print(f"支持的交易所: {len(exchange.exchanges)}")
```

## 🔄 切换交易所

想切换到其他交易所？超级简单！

### 方法 1：修改配置

编辑 `rest/ccxt_client.py`：

```python
def get_ccxt_client():
    global _ccxt_client
    if _ccxt_client is None:
        # 将 'gate' 改为你想要的交易所
        _ccxt_client = CCXTClient(exchange_id='binance')  # 或 'okx', 'bybit'
    return _ccxt_client
```

### 方法 2：环境变量

```bash
export EXCHANGE_ID=binance
```

然后修改代码读取环境变量：

```python
exchange_id = os.getenv('EXCHANGE_ID', 'gate')
_ccxt_client = CCXTClient(exchange_id=exchange_id)
```

### 支持的主流交易所

- ✅ **gate** - Gate.io
- ✅ **binance** - Binance
- ✅ **okx** - OKX  
- ✅ **bybit** - Bybit
- ✅ **huobi** - Huobi
- ✅ **coinbase** - Coinbase Pro
- ✅ **kraken** - Kraken
- ✅ **bitfinex** - Bitfinex

查看所有支持的交易所：https://docs.ccxt.com/#/exchanges

## 📊 功能对照

| 功能 | Gate API | CCXT | 状态 |
|------|----------|------|------|
| 获取合约列表 | ✅ | ✅ | ✅ 已实现 |
| 获取行情 | ✅ | ✅ | ✅ 已实现 |
| 合约下单 | ✅ | ✅ | ✅ 已实现 |
| 现货下单 | ✅ | ✅ | ✅ 已实现 |
| 查询持仓 | ✅ | ✅ | ✅ 已实现 |
| 查询余额 | ✅ | ✅ | ✅ 已实现 |
| 设置杠杆 | ✅ | ✅ | ✅ 已实现 |
| 获取K线 | ✅ | ✅ | ✅ 已实现 |
| 查询订单 | ✅ | ✅ | ✅ 已实现 |
| 平仓 | ✅ | ✅ | ✅ 已实现 |

✅ **100% 功能兼容！**

## 🐛 故障排查

### 问题 1：ImportError: No module named 'ccxt'

**解决方案：**

```bash
pip install ccxt
```

### 问题 2：API 密钥错误

**解决方案：**

1. 检查 `.env` 文件配置
2. 确保 API 密钥正确
3. 检查 API 权限（需要交易权限）

```bash
# 验证环境变量
python3 -c "import os; print(os.getenv('GATE_API_KEY'))"
```

### 问题 3：测试网不工作

**解决方案：**

Gate.io 测试网需要单独申请：
- 正式网：https://www.gate.io/
- 测试网：https://www.gate.io/testnet/

```bash
# 切换到正式网
export USE_TESTNET=false
```

### 问题 4：速率限制错误

**解决方案：**

CCXT 已内置速率限制，但如果仍然遇到：

```python
# 增加请求间隔
exchange.rateLimit = 2000  # 毫秒
```

## 💡 常见用例

### 1. 监控资金费率

```python
import rest

# 获取所有合约
contracts = rest.get_cex_contracts()

# 筛选高资金费率
high_rate = [c for c in contracts if abs(c.funding_rate) > 0.005]

for contract in high_rate:
    print(f"{contract.name}: {contract.funding_rate*100:.4f}%")
```

### 2. 自动交易

```python
import rest

# 检查余额
balance = rest.get_cex_wallet_balance()
if balance.available < 100:
    print("余额不足")
    exit()

# 下单
order = rest.cex_futures_place("BTC_USDT", "0", 10)  # 10张合约
if order:
    print(f"下单成功: {order.id}")
```

### 3. 监控持仓

```python
import rest
import time

while True:
    positions = rest.get_cex_all_position()
    if positions:
        for pos in positions:
            pnl = pos.unrealised_pnl
            print(f"{pos.contract}: 盈亏 ${pnl:,.2f}")
            
            # 止盈
            if pnl > 100:
                rest.cex_futures_close_position(pos.contract)
                print(f"止盈平仓: {pos.contract}")
    
    time.sleep(10)
```

## 📚 更多资源

### 官方资源

- **CCXT 官网：** https://ccxt.com
- **完整文档：** https://docs.ccxt.com
- **GitHub：** https://github.com/ccxt/ccxt
- **示例代码：** https://github.com/ccxt/ccxt/tree/master/examples

### 项目文档

- **完整迁移指南：** `CCXT_MIGRATION.md`
- **API 参考：** `rest/ccxt_client.py`
- **清理报告：** `CLEANUP_REPORT.md`

### 社区支持

- **Discord：** https://discord.gg/ccxt
- **Telegram：** https://t.me/ccxt_announcements

## ✅ 下一步

1. ✅ 已安装 CCXT
2. ✅ 已配置 API 密钥
3. ✅ 已测试功能
4. ✅ 已启动策略

现在你可以：

- 🔧 自定义策略参数
- 📊 添加更多监控指标
- 🔄 切换到其他交易所
- 🚀 部署到生产环境

## 🎉 恭喜！

你已经成功迁移到 CCXT！享受统一 API 带来的便利吧！

---

**有问题？** 查看 `CCXT_MIGRATION.md` 或提交 Issue。

