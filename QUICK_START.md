# 🚀 快速开始指南

## 📦 项目概述

本项目是一个**资金费率套利交易系统**，通过合约和现货对冲方式收取资金费率收益。

现已集成**统一日志管理系统**，所有操作都会被详细记录。

## ⚡ 快速启动

### 1. 启动主程序

```bash
python3 main.py
```

程序启动后将：
- ✅ 自动初始化日志系统
- ✅ 创建 `logs/` 目录
- ✅ 开始监控市场和执行交易
- ✅ 记录所有操作到日志文件

### 2. 查看实时日志

在另一个终端窗口中运行：

```bash
# 查看今天的日志
tail -f logs/funding_rate_$(date +%Y-%m-%d).log

# 或者查看总日志
tail -f logs/funding_rate_all.log
```

### 3. 查看错误日志

```bash
tail -f logs/error.log
```

## 📁 日志文件说明

运行程序后，`logs/` 目录将包含：

| 文件名 | 说明 | 保留策略 |
|--------|------|---------|
| `funding_rate_YYYY-MM-DD.log` | 每日日志 | 30天 |
| `funding_rate_all.log` | 总日志 | 最大10MB，5个备份 |
| `error.log` | 错误日志 | 最大5MB，3个备份 |

## 🎓 在代码中使用日志

```python
from utils.logger_config import get_logger

logger = get_logger(__name__)

# 记录不同级别的日志
logger.info("这是一条普通信息")
logger.warning("这是一条警告")
logger.error("这是一条错误", exc_info=True)
```

## 📚 完整文档

| 文档 | 说明 |
|------|------|
| `README.md` | 项目主文档 |
| `docs/LOG_USAGE.md` | 日志系统完整使用手册 |
| `strategy/README.md` | 策略说明文档 |

## 🔧 常用命令

### 日志查看

```bash
# 实时查看所有日志
tail -f logs/funding_rate_all.log

# 查看最后100行
tail -n 100 logs/funding_rate_all.log

# 搜索关键词
grep "ERROR" logs/funding_rate_all.log

# 统计错误数量
grep -c "ERROR" logs/funding_rate_all.log
```

### 日志管理

```bash
# 查看日志文件大小
ls -lh logs/

# 清理30天前的日志
find logs/ -name "*.log" -mtime +30 -delete

# 压缩旧日志
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

## 💡 最佳实践

### ✅ 推荐做法

1. **定期查看日志**：了解策略运行状况
2. **监控错误日志**：及时发现和解决问题
3. **备份重要日志**：保存关键交易记录
4. **适当的日志级别**：生产环境使用 INFO 或 WARNING

### ❌ 避免的做法

1. **不要忽略错误日志**：可能导致资金损失
2. **不要删除运行中的日志**：可能导致程序异常
3. **不要记录敏感信息**：如 API 密钥、密码等
4. **不要使用过低的日志级别**：DEBUG 级别会产生大量日志

## 🎯 日志示例

### 程序启动日志

```
2025-11-10 14:30:25 - __main__ - INFO - 资金费率套利程序启动
2025-11-10 14:30:25 - utils.logger_config - INFO - 日志系统初始化成功
2025-11-10 14:30:26 - strategy.gate_funding - INFO - 资金费率套利策略启动，开始监控市场...
```

### 策略运行日志

```
2025-11-10 14:30:26 - strategy.gate_funding - INFO - 交易配置 - 单边余额: 200 USDT, 杠杆倍数: 3x
2025-11-10 14:30:30 - strategy.gate_funding - INFO - BTC_USDT 资金费率(%): 0.75
2025-11-10 14:30:35 - strategy.gate_funding - INFO - 找到高资金费率合约: BTC_USDT
```

### 交易执行日志

```
2025-11-10 14:31:00 - strategy.gate_funding - INFO - 开始执行对冲交易: BTC_USDT
2025-11-10 14:31:05 - strategy.gate_funding - INFO - 合约开仓成功: 订单ID 123456
2025-11-10 14:31:10 - strategy.gate_funding - INFO - 现货开仓成功: 订单ID 789012
```

### 平仓日志

```
2025-11-10 15:00:00 - strategy.gate_funding - INFO - ==================== 交易对 BTC_USDT ====================
2025-11-10 15:00:00 - strategy.gate_funding - INFO - 合约方向：short 持仓数量：-10 持仓收益：2.5
2025-11-10 15:00:00 - strategy.gate_funding - INFO - 现货方向：buy 持仓数量：0.002 持仓收益：0.8
2025-11-10 15:00:00 - strategy.gate_funding - INFO - 预计总收益：3.3
2025-11-10 15:00:00 - strategy.gate_funding - INFO - 平仓交易对：BTC_USDT 总收益：3.3
```

## 🔍 故障排查

### 问题1：程序启动但没有日志文件

**解决方案：**
- 检查磁盘空间是否充足
- 检查是否有写入权限
- 查看控制台是否有错误提示

### 问题2：日志文件过大

**解决方案：**
- 日志会自动轮转，无需担心
- 如需手动清理：`rm -f logs/*.log.backup*`
- 调整日志级别：在 `main.py` 中改为 `logging.WARNING`

### 问题3：找不到某些日志

**解决方案：**
- 检查日志级别设置
- 查看是否被轮转到备份文件
- 使用 `grep` 搜索所有日志文件

## 📞 获取帮助

| 需求 | 操作 |
|------|------|
| 了解日志系统使用 | 查看 `docs/LOG_USAGE.md` |
| 查看技术实现 | 查看 `utils/logger_config.py` |
| 查看策略说明 | 查看 `strategy/README.md` |
| 查看API文档 | 查看 `rest/README_API_CLIENT.md` |

## 🎉 开始使用

现在你已经了解了基本操作，可以开始使用了：

```bash
# 1. 启动程序
python3 main.py

# 2. 在另一个终端查看日志
tail -f logs/funding_rate_all.log

# 3. 监控错误（可选）
tail -f logs/error.log
```

祝交易顺利！ 💰📈

---

**提示：** 查看 `docs/LOG_USAGE.md` 了解日志系统的详细使用方法。

