# 环境变量配置指南

## 📋 概述

本项目支持多个交易所，可以通过环境变量灵活配置。支持以下配置方式：

1. **交易所特定配置**（推荐）：为每个交易所单独配置 API 密钥
2. **通用配置**：使用统一的 API_KEY 和 API_SECRET
3. **向后兼容配置**：使用 GATE_API_KEY（保持兼容）

## 🔧 配置方式

### 方式一：交易所特定配置（推荐）

为每个交易所单独配置，互不干扰：

```bash
# 选择交易所
EXCHANGE_ID=bitget

# Bitget 专用配置
BITGET_API_KEY=your_bitget_api_key
BITGET_API_SECRET=your_bitget_api_secret
BITGET_USE_TESTNET=false
```

### 方式二：通用配置

使用统一的 API 密钥（适用于只使用一个交易所的情况）：

```bash
# 选择交易所
EXCHANGE_ID=okx

# 通用 API 密钥（适用于所有交易所）
API_KEY=your_api_key
API_SECRET=your_api_secret
USE_TESTNET=false
```

### 方式三：向后兼容配置

保持与旧版本兼容：

```bash
# 选择交易所
EXCHANGE_ID=gate

# 向后兼容配置（名称保持 GATE_ 但可用于任何交易所）
GATE_API_KEY=your_api_key
GATE_API_SECRET=your_api_secret
USE_TESTNET=false
```

## 📝 完整配置示例

### Gate.io 配置

```bash
EXCHANGE_ID=gate
GATE_API_KEY=your_gate_api_key
GATE_API_SECRET=your_gate_api_secret
USE_TESTNET=false
```

### Bitget 配置

```bash
EXCHANGE_ID=bitget
BITGET_API_KEY=your_bitget_api_key
BITGET_API_SECRET=your_bitget_api_secret
BITGET_USE_TESTNET=false
```

### OKX 配置

```bash
EXCHANGE_ID=okx
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_USE_TESTNET=false
```

### Binance 配置

```bash
EXCHANGE_ID=binance
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_USE_TESTNET=false
```

### Bybit 配置

```bash
EXCHANGE_ID=bybit
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
BYBIT_USE_TESTNET=false
```

### Huobi 配置

```bash
EXCHANGE_ID=huobi
HUOBI_API_KEY=your_huobi_api_key
HUOBI_API_SECRET=your_huobi_api_secret
HUOBI_USE_TESTNET=false
```

### Kraken 配置

```bash
EXCHANGE_ID=kraken
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_API_SECRET=your_kraken_api_secret
KRAKEN_USE_TESTNET=false
```

## 🔄 配置优先级

环境变量的读取优先级（从高到低）：

1. **交易所特定配置**：`{EXCHANGE_ID}_API_KEY`（如 `BITGET_API_KEY`）
2. **通用配置**：`API_KEY`
3. **向后兼容配置**：`GATE_API_KEY`

## 📌 注意事项

1. **测试网配置**：每个交易所的测试网配置也是独立的（如 `BITGET_USE_TESTNET`）
2. **安全性**：不要将 `.env` 文件提交到 Git 仓库
3. **多交易所**：如果需要同时使用多个交易所，建议使用交易所特定配置
4. **默认值**：如果不设置 `EXCHANGE_ID`，默认使用 `gate`

## 🚀 快速开始

1. 复制配置模板：
   ```bash
   cp config/env.template .env
   ```

2. 编辑 `.env` 文件，取消对应交易所的注释并填入 API 密钥

3. 运行程序：
   ```bash
   python main.py
   ```

## 📚 支持的交易所

- ✅ **gate** - Gate.io
- ✅ **bitget** - Bitget
- ✅ **okx** - OKX（原 OKEx）
- ✅ **binance** - Binance
- ✅ **bybit** - Bybit
- ✅ **huobi** - Huobi
- ✅ **kraken** - Kraken

查看所有支持的交易所：https://docs.ccxt.com/#/exchanges

