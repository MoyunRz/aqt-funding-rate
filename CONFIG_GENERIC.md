# 通用配置方式使用指南

## 📋 概述

通用配置方式使用统一的 `API_KEY` 和 `API_SECRET` 环境变量，适用于只使用一个交易所的情况。这是最简单、最直接的配置方式。

## 🔧 配置步骤

### 1. 创建 `.env` 文件

在项目根目录创建 `.env` 文件：

```bash
# Windows PowerShell
New-Item -Path .env -ItemType File

# Linux/Mac
touch .env
```

### 2. 编辑 `.env` 文件

在 `.env` 文件中添加以下配置：

```bash
# ==================== 选择交易所 ====================
# 支持的交易所: gate, bitget, okx, binance, bybit, huobi, kraken
EXCHANGE_ID=gate

# ==================== API 密钥（通用配置）====================
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here

# ==================== 测试网配置 ====================
USE_TESTNET=false
```

### 3. 填入你的 API 密钥

将 `your_api_key_here` 和 `your_api_secret_here` 替换为你的实际 API 密钥。

## 📝 配置示例

### Gate.io 配置示例

```bash
EXCHANGE_ID=gate
API_KEY=18c9b6413645f921935f00b0cd405e6e
API_SECRET=e7d12abf7a8f9240224c57f09ad3f48d1baec366b219054a60331282a8edafc4
USE_TESTNET=false
```

### Bitget 配置示例

```bash
EXCHANGE_ID=bitget
API_KEY=your_bitget_api_key
API_SECRET=your_bitget_api_secret
USE_TESTNET=false
```

### OKX 配置示例

```bash
EXCHANGE_ID=okx
API_KEY=your_okx_api_key
API_SECRET=your_okx_api_secret
USE_TESTNET=false
```

### Binance 配置示例

```bash
EXCHANGE_ID=binance
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret
USE_TESTNET=false
```

### Bybit 配置示例

```bash
EXCHANGE_ID=bybit
API_KEY=your_bybit_api_key
API_SECRET=your_bybit_api_secret
USE_TESTNET=false
```

## ✅ 优势

1. **简单明了**：只需配置三个环境变量
2. **易于切换**：只需修改 `EXCHANGE_ID` 即可切换交易所
3. **统一管理**：所有交易所使用相同的环境变量名

## ⚠️ 注意事项

1. **安全性**：
   - 不要将 `.env` 文件提交到 Git 仓库
   - 确保 `.env` 文件在 `.gitignore` 中

2. **多交易所**：
   - 如果需要在多个交易所之间切换，建议使用交易所特定配置（方式一）
   - 通用配置适合只使用一个交易所的情况

3. **配置优先级**：
   - 如果同时设置了交易所特定配置和通用配置，会优先使用交易所特定配置
   - 例如：如果设置了 `BITGET_API_KEY` 和 `API_KEY`，会使用 `BITGET_API_KEY`

## 🚀 快速开始

1. **创建 `.env` 文件**：
   ```bash
   # 复制模板（如果存在）
   cp config/env.template .env
   ```

2. **编辑 `.env` 文件**，添加：
   ```bash
   EXCHANGE_ID=gate
   API_KEY=your_api_key
   API_SECRET=your_api_secret
   USE_TESTNET=false
   ```

3. **运行程序**：
   ```bash
   python main.py
   ```

## 🔍 验证配置

运行程序后，你应该看到类似以下的日志：

```
✅ CCXT 客户端初始化完成 - 交易所: gate, 测试网: False
```

如果看到错误，请检查：
- `.env` 文件是否存在
- `EXCHANGE_ID` 是否正确
- `API_KEY` 和 `API_SECRET` 是否已填入
- API 密钥是否正确

## 📚 相关文档

- [完整配置指南](./README_ENV_CONFIG.md)
- [配置模板](./config/env.template)

