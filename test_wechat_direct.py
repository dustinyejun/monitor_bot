#!/usr/bin/env python3
"""
直接测试企业微信通知
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 使用项目的aiohttp
try:
    import aiohttp
except ImportError:
    print("❌ aiohttp未安装，尝试使用urllib...")
    import urllib.request
    import urllib.parse
    import json
    aiohttp = None

# 手动加载环境变量（从.env文件）
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    print("⚠️ .env文件未找到")

# 从环境变量获取webhook URL
webhook_url = os.getenv("WECHAT_WEBHOOK_URL", "")

async def test_wechat_direct():
    """直接测试企业微信webhook"""
    print("🔍 直接测试企业微信通知...")
    
    if not webhook_url:
        print("❌ 企业微信webhook URL未配置")
        return
    
    print(f"📡 webhook URL: {webhook_url[:50]}...")
    
    # 构造测试消息
    message_data = {
        "msgtype": "markdown",
        "markdown": {
            "content": """## 🧪 SOL监控测试通知

**测试时间**: 2025-08-21 15:50:00
**测试类型**: SOL转账
**测试金额**: 1.5 SOL ($150.0)

> 这是一条测试消息，用于验证企业微信通知是否正常工作。"""
        }
    }
    
    try:
        if aiohttp:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=message_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    status = response.status
                    text = await response.text()
                    
                    print(f"📊 响应状态: {status}")
                    print(f"📄 响应内容: {text}")
                    
                    if status == 200 and '"errcode":0' in text:
                        print("✅ 企业微信通知发送成功!")
                    else:
                        print("❌ 企业微信通知发送失败!")
        else:
            # 使用urllib发送请求
            import urllib.request
            import urllib.parse
            import json
            
            data = json.dumps(message_data).encode('utf-8')
            req = urllib.request.Request(
                webhook_url, 
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.getcode()
                text = response.read().decode('utf-8')
                
                print(f"📊 响应状态: {status}")
                print(f"📄 响应内容: {text}")
                
                if status == 200 and '"errcode":0' in text:
                    print("✅ 企业微信通知发送成功!")
                else:
                    print("❌ 企业微信通知发送失败!")
                    
    except Exception as e:
        if "timeout" in str(e).lower():
            print("❌ 请求超时 - 检查网络连接")
        else:
            print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_wechat_direct())