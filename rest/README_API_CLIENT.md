# API 客户端管理器使用指南

## 📖 目录

- [概述](#-概述)
- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [配置方式](#-配置方式)
- [使用示例](#-使用示例)
- [常见问题](#-常见问题)

---

## 🎯 概述

`api_client.py` 是一个 Gate.io API 客户端管理模块，负责统一管理所有 API 配置和客户端实例。

### 重构前后对比

#### ❌ 重构前（rest.py 中硬编码）

```python
# API 密钥硬编码在代码中，不安全
config = Configuration(
    key='18c9b6413645f921935f00b0cd405e6e',
    secret='e7d12abf7a8f9240224c57f09ad3f48d1baec366b219054a60331282a8edafc4',
    host='https://api-testnet.gateapi.io/api/v4'
)

# 每次都要重新创建客户端
margin_api = MarginApi(ApiClient(config))
spot_api = SpotApi(ApiClient(config))
# ...
```

#### ✅ 重构后（使用客户端管理器）

```python
# 从客户端管理器获取所有 API
from rest.api_client import get_api_clients

clients = get_api_clients()
margin_api = clients['margin_api']
spot_api = clients['spot_api']
```

---

## 💡 功能特性

### 1. 配置管理

- ✅ **集中管理**：所有 API 配置集中在一个模块
- ✅ **多种配置方式**：支持参数、环境变量、配置文件
- ✅ **环境切换**：轻松切换测试网和正式环境

### 2. 安全性

- ✅ **避免硬编码**：API 密钥不再硬编码在代码中
- ✅ **环境变量支持**：从环境变量加载敏感信息
- ✅ **默认保护**：生产环境强制要求提供密钥

### 3. 性能优化

- ✅ **单例模式**：避免重复创建客户端实例
- ✅ **延迟初始化**：按需创建 API 实例
- ✅ **资源复用**：多处使用同一客户端实例

### 4. 易用性

- ✅ **简洁 API**：一行代码获取所有客户端
- ✅ **类型提示**：完整的类型注解
- ✅ **详细文档**：每个函数都有详细说明

---

## 🚀 快速开始

### 最简单的使用方式

```python
from rest.api_client import get_api_clients

# 获取所有 API 客户端（使用默认测试网配置）
clients = get_api_clients()

# 使用合约 API
futures_api = clients['futures_api']
contracts = futures_api.list_futures_contracts(clients['settle'])

# 使用现货 API
spot_api = clients['spot_api']
tickers = spot_api.list_tickers()
```

---

## ⚙️ 配置方式

### 方式一：使用默认配置（测试网）

适用于开发和测试阶段。

```python
from rest.api_client import get_api_clients

# 使用默认测试网配置
clients = get_api_clients()
```

**特点：**
- 自动使用测试网环境
- 使用预设的测试密钥
- 无需额外配置

---

### 方式二：传入自定义参数

适用于需要动态配置的场景。

```python
from rest.api_client import get_api_clients

# 自定义配置
clients = get_api_clients(
    api_key='your_api_key_here',
    api_secret='your_api_secret_here',
    use_testnet=False,  # 使用正式环境
    settle='usdt'
)

futures_api = clients['futures_api']
```

**参数说明：**
- `api_key`: 您的 API Key
- `api_secret`: 您的 API Secret
- `use_testnet`: `True` 使用测试网，`False` 使用正式环境
- `settle`: 结算货币，`"usdt"` 或 `"btc"`

---

### 方式三：从环境变量加载 ⭐ 推荐

适用于生产环境，最安全的方式。

#### 步骤 1：设置环境变量

**Linux/Mac:**

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export GATE_API_KEY="your_api_key_here"
export GATE_API_SECRET="your_api_secret_here"
export GATE_USE_TESTNET="false"  # true=测试网, false=正式环境
export GATE_SETTLE="usdt"

# 使配置生效
source ~/.bashrc
```

**Windows (PowerShell):**

```powershell
$env:GATE_API_KEY="your_api_key_here"
$env:GATE_API_SECRET="your_api_secret_here"
$env:GATE_USE_TESTNET="false"
$env:GATE_SETTLE="usdt"
```

**Docker:**

```dockerfile
# Dockerfile
ENV GATE_API_KEY="your_api_key_here"
ENV GATE_API_SECRET="your_api_secret_here"
ENV GATE_USE_TESTNET="false"
ENV GATE_SETTLE="usdt"
```

或使用 `docker-compose.yml`:

```yaml
version: '3'
services:
  app:
    environment:
      - GATE_API_KEY=your_api_key_here
      - GATE_API_SECRET=your_api_secret_here
      - GATE_USE_TESTNET=false
      - GATE_SETTLE=usdt
```

#### 步骤 2：使用环境变量

```python
from rest.api_client import init_api_client_from_env

# 自动从环境变量加载配置
clients = init_api_client_from_env()

futures_api = clients['futures_api']
```

---

### 方式四：使用配置文件（可选）

创建 `config/api_config.py`:

```python
# config/api_config.py
import os

# API 配置
GATE_API_KEY = os.getenv('GATE_API_KEY', 'default_test_key')
GATE_API_SECRET = os.getenv('GATE_API_SECRET', 'default_test_secret')
GATE_USE_TESTNET = os.getenv('GATE_USE_TESTNET', 'true').lower() == 'true'
GATE_SETTLE = os.getenv('GATE_SETTLE', 'usdt')
```

然后在代码中使用：

```python
from config.api_config import GATE_API_KEY, GATE_API_SECRET, GATE_USE_TESTNET, GATE_SETTLE
from rest.api_client import get_api_clients

clients = get_api_clients(
    api_key=GATE_API_KEY,
    api_secret=GATE_API_SECRET,
    use_testnet=GATE_USE_TESTNET,
    settle=GATE_SETTLE
)
```

---

## 📚 使用示例

### 示例 1：获取合约列表

```python
from rest.api_client import get_api_clients

clients = get_api_clients()
futures_api = clients['futures_api']
settle = clients['settle']

# 获取所有 USDT 结算的合约
contracts = futures_api.list_futures_contracts(settle)

for contract in contracts[:5]:
    print(f"合约: {contract.name}, 资金费率: {contract.funding_rate}")
```

### 示例 2：查询账户余额

```python
from rest.api_client import get_api_clients

clients = get_api_clients()
wallet_api = clients['wallet_api']

# 获取总资产
balance = wallet_api.get_total_balance()
print(f"总资产: {balance.total}")
print(f"现货: {balance.details['spot'].amount}")
print(f"合约: {balance.details['futures'].amount}")
```

### 示例 3：合约下单

```python
from rest.api_client import get_api_clients
from gate_api import FuturesOrder

clients = get_api_clients()
futures_api = clients['futures_api']
settle = clients['settle']

# 创建合约订单
order = FuturesOrder(
    contract='BTC_USDT',
    size=1,           # 1 张合约
    price='0',        # 市价单
    tif='ioc'         # 立即成交或取消
)

# 下单
result = futures_api.create_futures_order(settle, order)
print(f"订单ID: {result.id}")
```

### 示例 4：现货下单

```python
from rest.api_client import get_api_clients
from gate_api import Order

clients = get_api_clients()
spot_api = clients['spot_api']

# 市价买入
order = Order(
    currency_pair='BTC_USDT',
    type='market',
    side='buy',
    amount='100',      # 100 USDT
    account='unified'
)

result = spot_api.create_order(order)
print(f"订单ID: {result.id}")
```

### 示例 5：在策略中使用

```python
# strategy/my_strategy.py
from rest.api_client import get_api_clients
import time

class MyTradingStrategy:
    def __init__(self):
        # 初始化 API 客户端
        self.clients = get_api_clients()
        self.futures_api = self.clients['futures_api']
        self.spot_api = self.clients['spot_api']
        self.settle = self.clients['settle']
    
    def run(self):
        while True:
            # 获取行情
            contracts = self.futures_api.list_futures_contracts(self.settle)
            
            # 执行策略逻辑
            # ...
            
            time.sleep(1)

# 运行策略
if __name__ == '__main__':
    strategy = MyTradingStrategy()
    strategy.run()
```

---

## ❓ 常见问题

### Q1: 如何切换到正式环境？

**A:** 有三种方式：

```python
# 方式1：参数指定
clients = get_api_clients(use_testnet=False)

# 方式2：环境变量
export GATE_USE_TESTNET="false"
clients = init_api_client_from_env()

# 方式3：创建自定义客户端
from rest.api_client import GateApiClient
client = GateApiClient(
    api_key='your_key',
    api_secret='your_secret',
    use_testnet=False
)
```

### Q2: 如何确认当前使用的是哪个环境？

**A:** 查看日志输出：

```python
from rest.api_client import get_api_clients

clients = get_api_clients()
# 日志会显示: "使用 Gate.io 测试网环境" 或 "使用 Gate.io 正式环境"
```

### Q3: 多个策略可以共享同一个客户端吗？

**A:** 可以！客户端管理器使用单例模式：

```python
# strategy1.py
from rest.api_client import get_api_clients
clients1 = get_api_clients()

# strategy2.py
from rest.api_client import get_api_clients
clients2 = get_api_clients()  # 返回同一实例

# clients1 和 clients2 是同一个对象
```

### Q4: 如何强制创建新的客户端实例？

**A:** 使用 `force_new=True`:

```python
from rest.api_client import GateApiClient

client = GateApiClient.get_instance(force_new=True)
```

### Q5: 生产环境忘记设置 API 密钥会怎样？

**A:** 程序会抛出异常并提示：

```python
ValueError: 生产环境必须提供 API Key！
请通过以下方式之一提供：
1. 传入 api_key 参数
2. 设置环境变量 GATE_API_KEY
3. 在配置文件中设置
```

### Q6: 如何验证 API 密钥是否正确？

**A:** 尝试调用一个简单的 API：

```python
from rest.api_client import get_api_clients

try:
    clients = get_api_clients(
        api_key='your_key',
        api_secret='your_secret',
        use_testnet=False
    )
    
    # 测试 API 调用
    wallet_api = clients['wallet_api']
    balance = wallet_api.get_total_balance()
    print("✅ API 密钥验证成功！")
    print(f"账户余额: {balance.total}")
    
except Exception as e:
    print(f"❌ API 密钥验证失败: {e}")
```

---

## 🔒 安全建议

### 1. 永远不要将 API 密钥提交到 Git

在 `.gitignore` 中添加：

```gitignore
# API 配置文件
config/api_config.py
.env

# 环境变量文件
*.env
*.env.local
```

### 2. 使用只读 API 密钥进行测试

在 Gate.io 创建 API 密钥时：
- ✅ 读取权限：开启
- ⚠️ 交易权限：测试时关闭
- ❌ 提现权限：永远不要开启

### 3. 为不同环境使用不同的 API 密钥

```bash
# 开发环境
export GATE_API_KEY="dev_key"

# 测试环境
export GATE_API_KEY="test_key"

# 生产环境
export GATE_API_KEY="prod_key"
```

### 4. 定期轮换 API 密钥

建议每 30-90 天更换一次 API 密钥。

---

## 📞 技术支持

如有问题，请查看：
- [Gate.io API 官方文档](https://www.gate.io/docs/developers/apiv4/zh_CN/)
- [项目主 README](../README.md)
- [策略使用文档](../strategy/README.md)

---

<div align="center">

**🎉 现在您可以安全、高效地使用 Gate.io API 了！**

</div>

