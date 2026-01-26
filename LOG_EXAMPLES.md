# Hook 日志输出示例

本文档展示了不同场景下的 hook 日志输出示例，帮助您理解和调试 webhook 功能。

## 场景 1: 成功发送单个 Webhook

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
POST_DOWNLOAD_WEBHOOK_TOKEN=secret_token_123
POST_DOWNLOAD_WEBHOOK_TIMEOUT=2.0
```

### 日志输出
```
[2026-01-26 10:30:45] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 1 | 文件数: 1
[2026-01-26 10:30:45] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 10:30:45] [INFO] [Hook] 使用 Bearer Token 认证
[2026-01-26 10:30:45] [INFO] [Hook] Webhook 请求体大小: 2.45 KB
[2026-01-26 10:30:45] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 10:30:45] [INFO] [Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 156ms | 响应大小: 64 bytes | URL: https://api.example.com/webhook
```

---

## 场景 2: 成功发送多个 Webhook

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://hook1.example.com/api;https://hook2.example.com/api;https://hook3.example.com/api
POST_DOWNLOAD_WEBHOOK_TOKEN=secret_token_123
```

### 日志输出
```
[2026-01-26 10:35:12] [INFO] [Hook] 下载完成事件触发 | 平台: tiktok | 来源: favorite | 作品数: 5 | 文件数: 12
[2026-01-26 10:35:12] [INFO] [Hook] 准备发送 webhook 通知到 3 个地址
[2026-01-26 10:35:12] [INFO] [Hook] 使用 Bearer Token 认证
[2026-01-26 10:35:12] [INFO] [Hook] Webhook 请求体大小: 8.76 KB
[2026-01-26 10:35:12] [INFO] [Hook] [1/3] 发送 webhook 到: https://hook1.example.com/api
[2026-01-26 10:35:12] [INFO] [Hook] [1/3] ✓ 通知成功 | 状态码: 200 | 耗时: 145ms | 响应大小: 32 bytes | URL: https://hook1.example.com/api
[2026-01-26 10:35:12] [INFO] [Hook] [2/3] 发送 webhook 到: https://hook2.example.com/api
[2026-01-26 10:35:12] [INFO] [Hook] [2/3] ✓ 通知成功 | 状态码: 200 | 耗时: 203ms | 响应大小: 32 bytes | URL: https://hook2.example.com/api
[2026-01-26 10:35:12] [INFO] [Hook] [3/3] 发送 webhook 到: https://hook3.example.com/api
[2026-01-26 10:35:13] [INFO] [Hook] [3/3] ✓ 通知成功 | 状态码: 200 | 耗时: 189ms | 响应大小: 32 bytes | URL: https://hook3.example.com/api
```

---

## 场景 3: 未配置 Webhook URL

### 配置
```bash
# 未设置 POST_DOWNLOAD_WEBHOOK_URL
```

### 日志输出
```
[2026-01-26 10:40:30] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: account | 作品数: 10 | 文件数: 25
[2026-01-26 10:40:30] [INFO] [Hook] 未配置 POST_DOWNLOAD_WEBHOOK_URL，跳过 webhook 通知
```

---

## 场景 4: 请求超时

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://slow-server.example.com/webhook
POST_DOWNLOAD_WEBHOOK_TIMEOUT=2.0
```

### 日志输出
```
[2026-01-26 10:45:15] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 3 | 文件数: 7
[2026-01-26 10:45:15] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 10:45:15] [INFO] [Hook] Webhook 请求体大小: 5.32 KB
[2026-01-26 10:45:15] [INFO] [Hook] [1/1] 发送 webhook 到: https://slow-server.example.com/webhook
[2026-01-26 10:45:17] [ERROR] [Hook] [1/1] ✗ 请求超时 | 超时设置: 2.0s | 已耗时: 2001ms | URL: https://slow-server.example.com/webhook
```

---

## 场景 5: HTTP 错误（500 服务器错误）

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
```

### 日志输出
```
[2026-01-26 10:50:22] [INFO] [Hook] 下载完成事件触发 | 平台: tiktok | 来源: share | 作品数: 2 | 文件数: 4
[2026-01-26 10:50:22] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 10:50:22] [INFO] [Hook] Webhook 请求体大小: 3.21 KB
[2026-01-26 10:50:22] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 10:50:22] [ERROR] [Hook] [1/1] ✗ HTTP 错误 | 状态码: 500 | 耗时: 89ms | URL: https://api.example.com/webhook | 错误: Server Error: Internal Server Error
```

---

## 场景 6: HTTP 错误（401 未授权）

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
POST_DOWNLOAD_WEBHOOK_TOKEN=wrong_token
```

### 日志输出
```
[2026-01-26 10:55:10] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: favorite | 作品数: 8 | 文件数: 20
[2026-01-26 10:55:10] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 10:55:10] [INFO] [Hook] 使用 Bearer Token 认证
[2026-01-26 10:55:10] [INFO] [Hook] Webhook 请求体大小: 12.45 KB
[2026-01-26 10:55:10] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 10:55:10] [ERROR] [Hook] [1/1] ✗ HTTP 错误 | 状态码: 401 | 耗时: 45ms | URL: https://api.example.com/webhook | 错误: Client Error: Unauthorized
```

---

## 场景 7: 连接失败（无效域名）

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://invalid-domain-12345.com/webhook
```

### 日志输出
```
[2026-01-26 11:00:05] [INFO] [Hook] 下载完成事件触发 | 平台: tiktok | 来源: account | 作品数: 15 | 文件数: 35
[2026-01-26 11:00:05] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 11:00:05] [INFO] [Hook] Webhook 请求体大小: 18.92 KB
[2026-01-26 11:00:05] [INFO] [Hook] [1/1] 发送 webhook 到: https://invalid-domain-12345.com/webhook
[2026-01-26 11:00:05] [ERROR] [Hook] [1/1] ✗ 通知失败 | 耗时: 123ms | URL: https://invalid-domain-12345.com/webhook | 错误类型: ConnectError | 错误: [Errno 11001] getaddrinfo failed
```

---

## 场景 8: 混合场景（部分成功，部分失败）

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://good.example.com/webhook;https://slow.example.com/webhook;https://error.example.com/webhook
POST_DOWNLOAD_WEBHOOK_TIMEOUT=2.0
```

### 日志输出
```
[2026-01-26 11:05:30] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 6 | 文件数: 15
[2026-01-26 11:05:30] [INFO] [Hook] 准备发送 webhook 通知到 3 个地址
[2026-01-26 11:05:30] [INFO] [Hook] Webhook 请求体大小: 10.23 KB
[2026-01-26 11:05:30] [INFO] [Hook] [1/3] 发送 webhook 到: https://good.example.com/webhook
[2026-01-26 11:05:30] [INFO] [Hook] [1/3] ✓ 通知成功 | 状态码: 200 | 耗时: 145ms | 响应大小: 64 bytes | URL: https://good.example.com/webhook
[2026-01-26 11:05:30] [INFO] [Hook] [2/3] 发送 webhook 到: https://slow.example.com/webhook
[2026-01-26 11:05:32] [ERROR] [Hook] [2/3] ✗ 请求超时 | 超时设置: 2.0s | 已耗时: 2001ms | URL: https://slow.example.com/webhook
[2026-01-26 11:05:32] [INFO] [Hook] [3/3] 发送 webhook 到: https://error.example.com/webhook
[2026-01-26 11:05:32] [ERROR] [Hook] [3/3] ✗ HTTP 错误 | 状态码: 503 | 耗时: 78ms | URL: https://error.example.com/webhook | 错误: Server Error: Service Unavailable
```

---

## 场景 9: 大量作品下载

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
```

### 日志输出
```
[2026-01-26 11:10:15] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: account | 作品数: 50 | 文件数: 120
[2026-01-26 11:10:15] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 11:10:15] [INFO] [Hook] Webhook 请求体大小: 156.78 KB
[2026-01-26 11:10:15] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 11:10:16] [INFO] [Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 456ms | 响应大小: 128 bytes | URL: https://api.example.com/webhook
```

---

## 场景 10: 无 Token 认证

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
# 未设置 POST_DOWNLOAD_WEBHOOK_TOKEN
```

### 日志输出
```
[2026-01-26 11:15:20] [INFO] [Hook] 下载完成事件触发 | 平台: tiktok | 来源: favorite | 作品数: 3 | 文件数: 8
[2026-01-26 11:15:20] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 11:15:20] [INFO] [Hook] Webhook 请求体大小: 6.12 KB
[2026-01-26 11:15:20] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 11:15:20] [INFO] [Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 123ms | 响应大小: 32 bytes | URL: https://api.example.com/webhook
```

注意：没有 "使用 Bearer Token 认证" 这一行日志。

---

## 场景 11: 图集下载（多文件）

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
```

### 日志输出
```
[2026-01-26 11:20:45] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 1 | 文件数: 9
[2026-01-26 11:20:45] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 11:20:45] [INFO] [Hook] Webhook 请求体大小: 4.56 KB
[2026-01-26 11:20:45] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 11:20:45] [INFO] [Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 167ms | 响应大小: 64 bytes | URL: https://api.example.com/webhook
```

说明：1 个图集作品包含 9 张图片。

---

## 场景 12: 调试模式（DEBUG 级别日志）

### 配置
```bash
POST_DOWNLOAD_WEBHOOK_URL=https://api.example.com/webhook
# 日志级别设置为 DEBUG
```

### 日志输出
```
[2026-01-26 11:25:10] [INFO] [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 2 | 文件数: 5
[2026-01-26 11:25:10] [INFO] [Hook] 准备发送 webhook 通知到 1 个地址
[2026-01-26 11:25:10] [INFO] [Hook] Webhook 请求体大小: 7.89 KB
[2026-01-26 11:25:10] [INFO] [Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[2026-01-26 11:25:10] [INFO] [Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 134ms | 响应大小: 85 bytes | URL: https://api.example.com/webhook
[2026-01-26 11:25:10] [DEBUG] [Hook] [1/1] 响应内容: {'status': 'ok', 'message': 'webhook received', 'processed': 2}
```

注意：DEBUG 级别会额外显示响应内容。

---

## 日志字段说明

### 基本信息
- **时间戳**: `[2026-01-26 11:25:10]`
- **日志级别**: `[INFO]` / `[ERROR]` / `[WARNING]` / `[DEBUG]`
- **标识**: `[Hook]` - 所有 hook 相关日志的统一前缀

### 下载事件信息
- **平台**: `douyin` 或 `tiktok`
- **来源**: `share`（分享）、`favorite`（喜欢）、`account`（发布）
- **作品数**: 下载的作品数量
- **文件数**: 下载的文件总数（包括视频、图片等）

### Webhook 发送信息
- **地址数量**: 配置的 webhook URL 数量
- **认证方式**: 是否使用 Bearer Token
- **请求体大小**: JSON 数据的大小（KB）
- **进度**: `[1/3]` 表示第 1 个，共 3 个

### 成功响应信息
- **✓ 标记**: 表示成功
- **状态码**: HTTP 响应状态码（200、201 等）
- **耗时**: 请求总耗时（毫秒）
- **响应大小**: 响应体大小（bytes）
- **URL**: 目标 webhook 地址

### 错误信息
- **✗ 标记**: 表示失败
- **错误类型**: 超时、HTTP 错误、连接错误等
- **错误详情**: 具体的错误信息
- **耗时**: 失败前的耗时

---

## 日志过滤技巧

### 查看所有 Hook 日志
```bash
# Linux/Mac
grep "\[Hook\]" app.log

# Windows PowerShell
Select-String -Pattern "\[Hook\]" -Path app.log
```

### 只查看错误
```bash
# Linux/Mac
grep "\[Hook\].*✗" app.log

# Windows PowerShell
Select-String -Pattern "\[Hook\].*✗" -Path app.log
```

### 只查看成功
```bash
# Linux/Mac
grep "\[Hook\].*✓" app.log

# Windows PowerShell
Select-String -Pattern "\[Hook\].*✓" -Path app.log
```

### 统计成功率
```bash
# Linux/Mac
echo "成功: $(grep -c '\[Hook\].*✓' app.log)"
echo "失败: $(grep -c '\[Hook\].*✗' app.log)"
```

---

## 性能分析

### 平均响应时间
从日志中提取耗时信息，计算平均值：
```
156ms, 203ms, 189ms, 145ms, 134ms
平均: 165.4ms
```

### 请求体大小分布
```
小型 (< 5 KB):   40%
中型 (5-20 KB):  45%
大型 (> 20 KB):  15%
```

### 成功率统计
```
总请求数: 100
成功: 95 (95%)
超时: 3 (3%)
HTTP 错误: 2 (2%)
```

---

**更新日期**: 2026-01-26
