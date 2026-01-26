# Webhook Hooks 使用指南

## 快速开始

### 1. 配置环境变量

```bash
# Windows CMD
set POST_DOWNLOAD_WEBHOOK_URL=https://your-server.com/webhook
set POST_DOWNLOAD_WEBHOOK_TOKEN=your_secret_token
set POST_DOWNLOAD_WEBHOOK_TIMEOUT=5.0

# Windows PowerShell
$env:POST_DOWNLOAD_WEBHOOK_URL="https://your-server.com/webhook"
$env:POST_DOWNLOAD_WEBHOOK_TOKEN="your_secret_token"
$env:POST_DOWNLOAD_WEBHOOK_TIMEOUT="5.0"

# Linux/Mac
export POST_DOWNLOAD_WEBHOOK_URL=https://your-server.com/webhook
export POST_DOWNLOAD_WEBHOOK_TOKEN=your_secret_token
export POST_DOWNLOAD_WEBHOOK_TIMEOUT=5.0
```

### 2. 启动服务

```bash
python main.py
```

### 3. 调用下载 API

当任何下载 API 完成后，会自动触发 webhook 通知。

## 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `POST_DOWNLOAD_WEBHOOK_URL` | 是 | - | Webhook 通知地址，支持多个（用 `;` 分隔） |
| `POST_DOWNLOAD_WEBHOOK_TOKEN` | 否 | - | Bearer Token 认证令牌 |
| `POST_DOWNLOAD_WEBHOOK_TIMEOUT` | 否 | 2.0 | 请求超时时间（秒） |

## 多 Webhook 配置

支持同时通知多个 webhook 地址：

```bash
# 配置 3 个 webhook 地址
set POST_DOWNLOAD_WEBHOOK_URL=https://hook1.com/api;https://hook2.com/api;https://hook3.com/api
```

## Webhook 接收端实现示例

### Node.js (Express)

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhook', (req, res) => {
  const { event, platform, source, items } = req.body;

  // 验证 Token（可选）
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (token !== process.env.EXPECTED_TOKEN) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  console.log(`收到下载完成通知: ${platform}/${source}`);
  console.log(`作品数: ${items.length}`);

  // 处理下载完成事件
  items.forEach(item => {
    console.log(`- 作品 ${item.id}: ${item.files.length} 个文件`);
    item.files.forEach(file => {
      console.log(`  文件: ${file.url}`);
    });
  });

  res.json({ status: 'ok', message: 'received' });
});

app.listen(3000, () => {
  console.log('Webhook 服务器运行在 http://localhost:3000');
});
```

### Python (Flask)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    # 验证 Token（可选）
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token != 'your_secret_token':
        return jsonify({'error': 'Unauthorized'}), 401

    event = data.get('event')
    platform = data.get('platform')
    source = data.get('source')
    items = data.get('items', [])

    print(f"收到下载完成通知: {platform}/{source}")
    print(f"作品数: {len(items)}")

    for item in items:
        print(f"- 作品 {item['id']}: {len(item['files'])} 个文件")
        for file in item['files']:
            print(f"  文件: {file['url']}")

    return jsonify({'status': 'ok', 'message': 'received'})

if __name__ == '__main__':
    app.run(port=3000)
```

### Python (FastAPI)

```python
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class FileInfo(BaseModel):
    path: str
    url: str

class ItemInfo(BaseModel):
    id: str
    type: str
    files: List[FileInfo]

class WebhookPayload(BaseModel):
    event: str
    platform: str
    source: str
    resolved_url: str
    root: str
    items: List[ItemInfo]
    params: dict

@app.post('/webhook')
async def webhook(
    payload: WebhookPayload,
    authorization: Optional[str] = Header(None)
):
    # 验证 Token（可选）
    if authorization:
        token = authorization.replace('Bearer ', '')
        if token != 'your_secret_token':
            raise HTTPException(status_code=401, detail='Unauthorized')

    print(f"收到下载完成通知: {payload.platform}/{payload.source}")
    print(f"作品数: {len(payload.items)}")

    for item in payload.items:
        print(f"- 作品 {item.id}: {len(item.files)} 个文件")
        for file in item.files:
            print(f"  文件: {file.url}")

    return {'status': 'ok', 'message': 'received'}
```

## Webhook 事件数据结构

```json
{
  "event": "download.completed",
  "platform": "douyin",
  "source": "share",
  "resolved_url": "https://www.douyin.com/video/...",
  "root": "D:\\Downloads\\TikTok",
  "earliest": "2024-01-01",
  "latest": "2024-12-31",
  "items": [
    {
      "id": "7123456789012345678",
      "type": "视频",
      "files": [
        {
          "path": "D:\\Downloads\\TikTok\\share\\作品标题_7123456789012345678.mp4",
          "url": "http://localhost:8000/files/share/作品标题_7123456789012345678.mp4"
        }
      ]
    }
  ],
  "params": {
    "text": "https://v.douyin.com/...",
    "mark": "测试下载",
    "cookie": null,
    "proxy": null
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `event` | string | 事件类型，固定为 `download.completed` |
| `platform` | string | 平台：`douyin` 或 `tiktok` |
| `source` | string | 来源：`share`（分享）、`favorite`（喜欢）、`post`（发布） |
| `resolved_url` | string | 解析后的完整 URL |
| `root` | string | 下载根目录的绝对路径 |
| `earliest` | string | 最早日期（仅 favorite/post） |
| `latest` | string | 最晚日期（仅 favorite/post） |
| `items` | array | 下载的作品列表 |
| `items[].id` | string | 作品 ID |
| `items[].type` | string | 作品类型：`视频`、`图集`、`实况` |
| `items[].files` | array | 文件列表 |
| `items[].files[].path` | string | 文件的绝对路径 |
| `items[].files[].url` | string | 文件的 HTTP 访问 URL |
| `params` | object | 请求参数（已清理敏感信息） |

## 日志示例

### 成功场景

```
[Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 3 | 文件数: 8
[Hook] 准备发送 webhook 通知到 1 个地址
[Hook] 使用 Bearer Token 认证
[Hook] Webhook 请求体大小: 12.45 KB
[Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 156ms | 响应大小: 64 bytes | URL: https://api.example.com/webhook
```

### 未配置 Webhook

```
[Hook] 下载完成事件触发 | 平台: tiktok | 来源: favorite | 作品数: 10 | 文件数: 25
[Hook] 未配置 POST_DOWNLOAD_WEBHOOK_URL，跳过 webhook 通知
```

### 超时场景

```
[Hook] 下载完成事件触发 | 平台: douyin | 来源: account | 作品数: 5 | 文件数: 15
[Hook] 准备发送 webhook 通知到 1 个地址
[Hook] Webhook 请求体大小: 18.76 KB
[Hook] [1/1] 发送 webhook 到: https://slow-server.com/webhook
[Hook] [1/1] ✗ 请求超时 | 超时设置: 2.0s | 已耗时: 2001ms | URL: https://slow-server.com/webhook
```

### HTTP 错误场景

```
[Hook] [1/1] 发送 webhook 到: https://api.example.com/webhook
[Hook] [1/1] ✗ HTTP 错误 | 状态码: 500 | 耗时: 89ms | URL: https://api.example.com/webhook | 错误: Internal Server Error
```

## 常见问题

### Q1: Webhook 通知失败会影响下载吗？

**不会。** Webhook 通知在后台异步执行，失败不会影响下载任务的正常完成。

### Q2: 如何调试 Webhook？

1. 使用测试脚本：`python test_webhook_logging.py`
2. 查看日志中的详细错误信息
3. 使用 webhook 测试工具（如 webhook.site）

### Q3: 支持重试机制吗？

目前不支持自动重试。如果需要重试，建议在 webhook 接收端实现幂等性处理。

### Q4: 如何保护 Webhook 安全？

1. 使用 HTTPS 协议
2. 配置 `POST_DOWNLOAD_WEBHOOK_TOKEN` 进行认证
3. 在接收端验证 Token
4. 限制 IP 白名单（在接收端实现）

### Q5: Webhook 请求体太大怎么办？

如果下载的作品数量很多，请求体可能较大。建议：
1. 增加接收端的请求体大小限制
2. 在接收端异步处理数据
3. 考虑分批下载

## 测试工具

### 使用内置测试脚本

```bash
# 启动测试 webhook 服务器
python test_webhook_logging.py

# 在另一个终端设置环境变量
set POST_DOWNLOAD_WEBHOOK_URL=http://localhost:8888/webhook

# 启动 TikTokDownloader 并测试下载
```

### 使用在线测试工具

1. **Webhook.site**
   - 访问 https://webhook.site
   - 复制生成的 URL
   - 设置为 `POST_DOWNLOAD_WEBHOOK_URL`

2. **RequestBin**
   - 访问 https://requestbin.com
   - 创建一个 bin
   - 使用生成的 URL

## 实际应用场景

### 1. 自动化工作流

下载完成后自动触发后续处理：
- 视频转码
- 上传到云存储
- 发送通知给用户
- 更新数据库记录

### 2. 监控和统计

收集下载统计信息：
- 下载成功率
- 文件大小统计
- 平台分布
- 时间分析

### 3. 集成第三方服务

- 发送到 Slack/Discord/钉钉
- 触发 CI/CD 流程
- 更新项目管理工具
- 同步到其他系统

### 4. 内容审核

下载完成后自动进行：
- 内容安全检测
- 版权检查
- 质量评估
- 分类标签

## 更新日志

### 2026-01-26
- ✨ 增加详细的 hook 调用日志
- ✨ 无论是否配置 URL 都记录下载事件
- ✨ 增加请求耗时、响应大小等详细信息
- ✨ 改进错误处理和分类（超时、HTTP错误、其他错误）
- ✨ 支持多 webhook URL 的进度显示
- ✨ 增加 Bearer Token 认证日志
- ✨ 增加请求体大小统计

## 相关文档

- [详细改进说明](./HOOK_LOGGING_IMPROVEMENTS.md)
- [测试脚本](./test_webhook_logging.py)
- [API 文档](./README.md)
