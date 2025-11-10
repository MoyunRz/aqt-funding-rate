# 日志系统使用指南

## 概述

本项目使用统一的日志管理系统，所有日志自动存储在 `logs/` 目录下，支持多种日志轮转策略。

## 功能特性

✅ **控制台 + 文件双重输出**：同时输出到控制台和文件
✅ **自动按日期分文件**：每天自动生成新的日志文件
✅ **按大小自动轮转**：单个日志文件超过限制自动创建新文件
✅ **错误日志单独记录**：ERROR 级别日志单独存储
✅ **统一日志格式**：包含时间、模块、级别、函数、行号、消息
✅ **自动创建目录**：日志目录不存在时自动创建

## 日志文件说明

### 目录结构

```
logs/
├── funding_rate_2025-11-10.log    # 每日日志（按日期命名）
├── funding_rate_all.log           # 总日志（按大小轮转）
├── error.log                      # 错误日志（仅 ERROR 及以上）
└── ...                            # 其他备份文件
```

### 日志文件类型

1. **每日日志** - `funding_rate_YYYY-MM-DD.log`
   - 每天午夜自动创建新文件
   - 保留最近 30 天的日志
   - 包含所有级别的日志

2. **总日志** - `funding_rate_all.log`
   - 单个文件最大 10MB
   - 超过大小自动轮转，保留 5 个备份
   - 包含所有级别的日志

3. **错误日志** - `error.log`
   - 单个文件最大 5MB
   - 仅记录 ERROR 和 CRITICAL 级别
   - 保留 3 个备份

## 使用方法

### 1. 在主程序中初始化（main.py）

```python
from utils.logger_config import LoggerConfig
import logging

# 初始化全局日志
LoggerConfig.init_logger(
    log_dir='logs',              # 日志目录
    log_level=logging.INFO,      # 日志级别
    console_output=True,         # 控制台输出
    file_output=True             # 文件输出
)
```

### 2. 在其他模块中使用

```python
from utils.logger_config import get_logger

# 获取当前模块的日志记录器
logger = get_logger(__name__)

# 使用不同级别的日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 记录异常堆栈
try:
    # 你的代码
    pass
except Exception as e:
    logger.error(f"发生异常: {e}", exc_info=True)
```

## 日志级别

从低到高依次为：

| 级别 | 数值 | 用途 |
|------|------|------|
| DEBUG | 10 | 详细的调试信息，通常仅在诊断问题时使用 |
| INFO | 20 | 一般信息，程序正常运行的日志 |
| WARNING | 30 | 警告信息，程序仍能正常运行但可能存在问题 |
| ERROR | 40 | 错误信息，程序某些功能无法正常执行 |
| CRITICAL | 50 | 严重错误，程序可能无法继续运行 |

## 动态调整日志级别

```python
from utils.logger_config import LoggerConfig
import logging

# 调整为 DEBUG 级别（更详细）
LoggerConfig.set_level(logging.DEBUG)

# 调整为 WARNING 级别（更简洁）
LoggerConfig.set_level(logging.WARNING)
```

## 日志格式

默认日志格式：

```
2025-11-10 14:30:25 - strategy.gate_funding - INFO - watch_history_funding:189 - 找到高资金费率合约: BTC_USDT
```

格式说明：
- `2025-11-10 14:30:25`：时间戳
- `strategy.gate_funding`：模块名
- `INFO`：日志级别
- `watch_history_funding:189`：函数名和行号
- `找到高资金费率合约: BTC_USDT`：日志消息

## 最佳实践

### 1. 使用合适的日志级别

```python
# ❌ 不好的做法
logger.info("变量 x 的值是: " + str(x))  # 这应该是 DEBUG

# ✅ 好的做法
logger.debug(f"变量 x 的值是: {x}")  # 使用 DEBUG 记录详细信息
logger.info("用户登录成功")           # 使用 INFO 记录重要事件
logger.warning("API 响应时间过长")    # 使用 WARNING 记录潜在问题
logger.error("数据库连接失败")        # 使用 ERROR 记录错误
```

### 2. 使用 f-string 格式化

```python
# ❌ 不好的做法
logger.info("用户 " + username + " 执行了 " + action)

# ✅ 好的做法
logger.info(f"用户 {username} 执行了 {action}")
```

### 3. 记录异常时包含堆栈信息

```python
# ❌ 不好的做法
except Exception as e:
    logger.error(f"错误: {e}")

# ✅ 好的做法
except Exception as e:
    logger.error(f"错误: {e}", exc_info=True)
```

### 4. 避免记录敏感信息

```python
# ❌ 不好的做法
logger.info(f"用户密码: {password}")
logger.info(f"API密钥: {api_key}")

# ✅ 好的做法
logger.info(f"用户 {username} 登录成功")
logger.info("API 初始化完成")
```

## 日志文件管理

### 自动清理

- 每日日志：自动保留最近 30 天
- 总日志：自动保留 5 个备份文件
- 错误日志：自动保留 3 个备份文件

### 手动清理

如需手动清理旧日志：

```bash
# 删除 30 天前的日志
find logs/ -name "*.log" -mtime +30 -delete

# 删除所有日志（谨慎操作）
rm -rf logs/
```

## 常见问题

### Q: 日志文件太大怎么办？

A: 日志系统已配置自动轮转，无需担心。如需调整限制：

```python
LoggerConfig.init_logger(log_dir='logs')
# 修改 logger_config.py 中的 maxBytes 参数
```

### Q: 如何查看实时日志？

A: 使用 `tail` 命令：

```bash
# 查看今天的日志
tail -f logs/funding_rate_$(date +%Y-%m-%d).log

# 查看总日志
tail -f logs/funding_rate_all.log
```

### Q: 如何只输出到文件不输出到控制台？

A: 初始化时设置：

```python
LoggerConfig.init_logger(
    console_output=False,  # 关闭控制台输出
    file_output=True
)
```

## 技术细节

### 日志处理器

系统使用以下三种处理器：

1. **StreamHandler**：控制台输出
2. **TimedRotatingFileHandler**：按时间轮转（每日日志）
3. **RotatingFileHandler**：按大小轮转（总日志、错误日志）

### 线程安全

Python 的 logging 模块是线程安全的，可在多线程环境下放心使用。

### 性能考虑

- 日志写入是异步的，不会阻塞主程序
- 避免在高频循环中使用 DEBUG 级别日志
- 生产环境建议使用 INFO 或 WARNING 级别

## 参考资源

- [Python logging 官方文档](https://docs.python.org/zh-cn/3/library/logging.html)
- [Logging HOWTO](https://docs.python.org/zh-cn/3/howto/logging.html)

