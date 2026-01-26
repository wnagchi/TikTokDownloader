#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Webhook 日志功能测试脚本

用于测试和演示增强的 webhook hooks 日志记录功能。
"""

import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import os


class WebhookTestHandler(BaseHTTPRequestHandler):
    """测试用的 Webhook 接收服务器"""

    def do_POST(self):
        """处理 POST 请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        # 解析 JSON 数据
        try:
            data = json.loads(post_data.decode('utf-8'))
            print(f"\n{'='*60}")
            print(f"[测试服务器] 收到 Webhook 通知")
            print(f"{'='*60}")
            print(f"事件类型: {data.get('event')}")
            print(f"平台: {data.get('platform')}")
            print(f"来源: {data.get('source')}")
            print(f"作品数: {len(data.get('items', []))}")
            print(f"文件总数: {sum(len(item.get('files', [])) for item in data.get('items', []))}")
            print(f"请求体大小: {len(post_data)} bytes")

            # 检查认证
            auth_header = self.headers.get('Authorization')
            if auth_header:
                print(f"认证: {auth_header[:20]}...")

            print(f"{'='*60}\n")

            # 返回成功响应
            response = {"status": "ok", "message": "webhook received"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            print(f"[测试服务器] 错误: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        """禁用默认的访问日志"""
        pass


def start_test_webhook_server(port=8888):
    """启动测试 webhook 服务器"""
    server = HTTPServer(('localhost', port), WebhookTestHandler)
    print(f"\n[测试服务器] 启动在 http://localhost:{port}")
    print(f"[测试服务器] 按 Ctrl+C 停止\n")

    # 在后台线程运行
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def print_test_instructions():
    """打印测试说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           Webhook 日志功能测试指南                            ║
╚══════════════════════════════════════════════════════════════╝

本脚本启动一个测试 webhook 服务器，用于接收和显示下载完成通知。

【测试步骤】

1. 设置环境变量（在另一个终端）：

   Windows (CMD):
   set POST_DOWNLOAD_WEBHOOK_URL=http://localhost:8888/webhook
   set POST_DOWNLOAD_WEBHOOK_TOKEN=test_token_123
   set POST_DOWNLOAD_WEBHOOK_TIMEOUT=5.0

   Windows (PowerShell):
   $env:POST_DOWNLOAD_WEBHOOK_URL="http://localhost:8888/webhook"
   $env:POST_DOWNLOAD_WEBHOOK_TOKEN="test_token_123"
   $env:POST_DOWNLOAD_WEBHOOK_TIMEOUT="5.0"

   Linux/Mac:
   export POST_DOWNLOAD_WEBHOOK_URL=http://localhost:8888/webhook
   export POST_DOWNLOAD_WEBHOOK_TOKEN=test_token_123
   export POST_DOWNLOAD_WEBHOOK_TIMEOUT=5.0

2. 启动 TikTokDownloader API 服务器：
   python main.py

3. 调用下载 API（使用 curl 或 Postman）：

   curl -X POST http://localhost:8000/douyin/download/share \\
     -H "Content-Type: application/json" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -d '{
       "text": "https://v.douyin.com/...",
       "mark": "测试下载"
     }'

【预期日志输出】

在 TikTokDownloader 日志中，你会看到：

  [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 1 | 文件数: 1
  [Hook] 准备发送 webhook 通知到 1 个地址
  [Hook] 使用 Bearer Token 认证
  [Hook] Webhook 请求体大小: 2.45 KB
  [Hook] [1/1] 发送 webhook 到: http://localhost:8888/webhook
  [Hook] [1/1] ✓ 通知成功 | 状态码: 200 | 耗时: 15ms | 响应大小: 45 bytes | URL: http://localhost:8888/webhook

在本测试服务器中，你会看到：

  ============================================================
  [测试服务器] 收到 Webhook 通知
  ============================================================
  事件类型: download.completed
  平台: douyin
  来源: share
  作品数: 1
  文件总数: 1
  请求体大小: 2510 bytes
  认证: Bearer test_token_...
  ============================================================

【测试多个 Webhook URL】

设置多个 URL（用分号分隔）：

  set POST_DOWNLOAD_WEBHOOK_URL=http://localhost:8888/webhook1;http://localhost:8888/webhook2

日志会显示每个 URL 的发送进度：

  [Hook] 准备发送 webhook 通知到 2 个地址
  [Hook] [1/2] 发送 webhook 到: http://localhost:8888/webhook1
  [Hook] [1/2] ✓ 通知成功 | ...
  [Hook] [2/2] 发送 webhook 到: http://localhost:8888/webhook2
  [Hook] [2/2] ✓ 通知成功 | ...

【测试未配置 Webhook】

不设置 POST_DOWNLOAD_WEBHOOK_URL 环境变量，日志会显示：

  [Hook] 下载完成事件触发 | 平台: douyin | 来源: share | 作品数: 1 | 文件数: 1
  [Hook] 未配置 POST_DOWNLOAD_WEBHOOK_URL，跳过 webhook 通知

【测试错误场景】

1. 超时测试：设置很短的超时时间
   set POST_DOWNLOAD_WEBHOOK_TIMEOUT=0.001

2. 错误 URL 测试：
   set POST_DOWNLOAD_WEBHOOK_URL=http://invalid-host-12345.com/webhook

3. HTTP 错误测试：修改测试服务器返回 500 错误

╔══════════════════════════════════════════════════════════════╗
║  测试服务器已启动，等待接收 webhook 通知...                   ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    """主函数"""
    try:
        # 启动测试服务器
        server = start_test_webhook_server(port=8888)

        # 打印测试说明
        print_test_instructions()

        # 保持运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n[测试服务器] 正在关闭...")
        server.shutdown()
        print("[测试服务器] 已停止")


if __name__ == "__main__":
    main()
