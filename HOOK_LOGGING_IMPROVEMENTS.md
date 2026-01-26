# Hook 日志增强说明文档

## 概述

本次更新增强了下载 API 的 webhook hooks 功能日志记录，提供更详细的调试和监控信息。

## 主要改进

### 1. 无条件记录下载事件

**改进前：** 只有配置了 webhook URL 才会有日志输出

**改进后：** 无论是否配置 webhook URL，每次下载完成都会记录事件信息

```
[Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 5 | 文件数: 12
```

**记录信息包括：**
- 平台类型（douyin/tiktok）
- 下载来源（share/favorite/post）
- 下载的作品数量
- 下载的文件总数

### 2. 详细的 Webhook 发送日志

#### 2.1 发送前准备信息

```
[Hook] 准备发送 webhook 通知到 2 个地址
[Hook] 使用 Bearer Token 认证
[Hook] Webhook 请求体大小: 15.32 KB
```

#### 2.2 发送过程追踪

每个 webhook URL 都会显示发送进度：

```
[Hook] [1/2] 发送 webhook 到: https://example.com/hook1
```

#### 2.3 成功响应详情

```
[Hook] [1/2] ✓ 通知成功 | 状态码: 200 | 耗时: 245ms | 响应大小: 128 bytes | URL: https://example.com/hook1
```

**记录信息包括：**
- ✓ 成功标记
- HTTP 状态码
- 请求耗时（毫秒）
- 响应体大小
- 目标 URL

#### 2.4 响应内容记录（DEBUG 级别）

如果 webhook 服务器返回了响应内容，会在 DEBUG 级别记录：

```
[Hook] [1/2] 响应内容: {"status": "ok", "message": "received"}
```

### 3. 详细的错误处理

#### 3.1 超时错误

```
[Hook] [1/2] ✗ 请求超时 | 超时设置: 2.0s | 已耗时: 2001ms | URL: https://slow-server.com/hook
```

#### 3.2 HTTP 错误

```
[Hook] [1/2] ✗ HTTP 错误 | 状态码: 500 | 耗时: 156ms | URL: https://example.com/hook | 错误: Server Error
```

#### 3.3 其他错误

```
[Hook] [1/2] ✗ 通知失败 | 耗时: 89ms | URL: https://invalid.com/hook | 错误类型: ConnectionError | 错误: Connection refused
```

**错误日志包括：**
- ✗ 失败标记
- 错误类型（超时/HTTP错误/其他）
- 具体错误信息
- 请求耗时
- 目标 URL

### 4. 未配置提示

当没有配置 webhook URL 时，会明确提示：

```
[Hook] 未配置 POST_DOWNLOAD_WEBHOOK_URL，跳过 webhook 通知
```

### 5. 异常情况处理

如果无法创建异步任务（极少见），会记录警告：

```
[Hook] 无法创建异步任务：没有运行中的 event loop
```

## 日志级别说明

| 级别 | 用途 | 示例 |
|------|------|------|
| **INFO** | 正常流程信息 | 下载完成、发送通知、成功响应 |
| **DEBUG** | 详细调试信息 | Webhook 响应内容 |
| **WARNING** | 警告信息 | 无法创建异步任务 |
| **ERROR** | 错误信息 | 超时、HTTP 错误、连接失败 |

## 配置说明

### 环境变量

```bash
# Webhook 通知地址（必需，支持多个用 ; 分隔）
POST_DOWNLOAD_WEBHOOK_URL=https://example.com/hook1;https://example.com/hook2

# 认证令牌（可选）
POST_DOWNLOAD_WEBHOOK_TOKEN=your_secret_token

# 请求超时时间（可选，默认 2.0 秒）
POST_DOWNLOAD_WEBHOOK_TIMEOUT=5.0
```

### 多 Webhook 支持

可以配置多个 webhook URL，用分号分隔：

```bash
POST_DOWNLOAD_WEBHOOK_URL=https://hook1.com/api;https://hook2.com/api;https://hook3.com/api
```

日志会显示每个 URL 的发送进度：

```
[Hook] 准备发送 webhook 通知到 3 个地址
[Hook] [1/3] 发送 webhook 到: https://hook1.com/api
[Hook] [1/3] ✓ 通知成功 | ...
[Hook] [2/3] 发送 webhook 到: https://hook2.com/api
[Hook] [2/3] ✓ 通知成功 | ...
[Hook] [3/3] 发送 webhook 到: https://hook3.com/api
[Hook] [3/3] ✗ 请求超时 | ...
```

## 日志示例

### 完整的成功流程

```
[Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 3 | 文件数: 8
[Hook] 准备发送 webhook 通知到 2 个地址
[Hook] 使用 Bearer Token 认证
[Hook] Webhook 请求体大小: 12.45 KB
[Hook] [1/2] 发送 webhook 到: https://api.example.com/webhook
[Hook] [1/2] ✓ 通知成功 | 状态码: 200 | 耗时: 156ms | 响应大小: 64 bytes | URL: https://api.example.com/webhook
[Hook] [2/2] 发送 webhook 到: https://backup.example.com/webhook
[Hook] [2/2] ✓ 通知成功 | 状态码: 200 | 耗时: 203ms | 响应大小: 64 bytes | URL: https://backup.example.com/webhook
```

### 未配置 Webhook

```
[Hook] 下载完成事件触发 | 平台: tiktok | 来源: favorite | 作品数: 10 | 文件数: 25
[Hook] 未配置 POST_DOWNLOAD_WEBHOOK_URL，跳过 webhook 通知
```

### 部分失败场景

```
[Hook] 下载完成事件触发 | 平台: douyin | 来源: account | 作品数: 5 | 文件数: 15
[Hook] 准备发送 webhook 通知到 3 个地址
[Hook] Webhook 请求体大小: 18.76 KB
[Hook] [1/3] 发送 webhook 到: https://primary.com/hook
[Hook] [1/3] ✓ 通知成功 | 状态码: 200 | 耗时: 145ms | 响应大小: 32 bytes | URL: https://primary.com/hook
[Hook] [2/3] 发送 webhook 到: https://slow.com/hook
[Hook] [2/3] ✗ 请求超时 | 超时设置: 2.0s | 已耗时: 2001ms | URL: https://slow.com/hook
[Hook] [3/3] 发送 webhook 到: https://error.com/hook
[Hook] [3/3] ✗ HTTP 错误 | 状态码: 503 | 耗时: 89ms | URL: https://error.com/hook | 错误: Service Unavailable
```

## 性能影响

- **异步执行：** Webhook 通知在后台异步执行，不会阻塞下载 API 响应
- **失败不影响主流程：** Webhook 发送失败不会影响下载任务的成功返回
- **超时控制：** 默认 2 秒超时，可通过环境变量调整

## 调试建议

### 1. 查看基本信息

设置日志级别为 INFO（默认），可以看到：
- 下载事件触发
- Webhook 发送状态
- 成功/失败统计

### 2. 查看详细响应

设置日志级别为 DEBUG，可以额外看到：
- Webhook 服务器的响应内容
- 更详细的请求/响应信息

### 3. 排查问题

根据日志中的错误类型：
- **请求超时：** 检查网络连接，考虑增加 `POST_DOWNLOAD_WEBHOOK_TIMEOUT`
- **HTTP 错误：** 检查 webhook 服务器状态和日志
- **连接失败：** 检查 URL 是否正确，服务器是否可达

## 受影响的 API 端点

所有下载 API 端点都会触发 webhook：

### 抖音平台
- `POST /douyin/download/share` - 分享链接下载
- `POST /douyin/download/favorite` - 喜欢作品下载
- `POST /douyin/download/account` - 账号作品下载

### TikTok 平台
- `POST /tiktok/download/share` - 分享链接下载
- `POST /tiktok/download/favorite` - 喜欢作品下载
- `POST /tiktok/download/account` - 账号作品下载

## Webhook 事件数据格式

```json
{
  "event": "download.completed",
  "platform": "douyin",
  "source": "share",
  "resolved_url": "https://...",
  "root": "/path/to/downloads",
  "earliest": "2024-01-01",
  "latest": "2024-12-31",
  "items": [
    {
      "id": "7123456789",
      "type": "视频",
      "files": [
        {
          "path": "/absolute/path/to/file.mp4",
          "url": "http://localhost:8000/files/relative/path/file.mp4"
        }
      ]
    }
  ],
  "params": {
    // 已清理敏感信息的请求参数
  }
}
```

## 更新日期

2026-01-26

## 相关文件

- `src/application/main_server.py` - 主要修改文件
  - `_trigger_post_download_hook()` - 第 175-200 行
  - `_send_post_download_webhook()` - 第 202-273 行
