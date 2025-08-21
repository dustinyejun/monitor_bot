#!/usr/bin/env python3
"""
企业微信通知curl测试
使用curl命令测试企业微信通知，无需Python依赖
"""
import os
import json
import subprocess
import time
from datetime import datetime


def send_wechat_message_curl(webhook_url: str, title: str, content: str, is_urgent: bool = False):
    """使用curl发送企业微信消息"""
    try:
        # 构造消息内容
        if is_urgent:
            formatted_content = f"## 🚨 {title}\n\n{content}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            formatted_content = f"## {title}\n\n{content}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 企业微信消息格式
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content
            }
        }
        
        # 使用curl发送请求
        curl_command = [
            "curl",
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(message, ensure_ascii=False),
            "--connect-timeout", "10",
            "--max-time", "30",
            webhook_url
        ]
        
        result = subprocess.run(
            curl_command,
            capture_output=True,
            text=True,
            timeout=35
        )
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                if response_data.get("errcode") == 0:
                    print("✅ 企业微信消息发送成功！")
                    return True
                else:
                    print(f"❌ 企业微信API错误: {response_data}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ 响应解析失败: {result.stdout}")
                return False
        else:
            print(f"❌ curl命令失败: {result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 发送消息异常: {e}")
        return False


def test_basic_notification(webhook_url: str):
    """测试基础通知"""
    print("📤 测试基础通知...")
    
    title = "🧪 系统测试通知"
    content = f"""### 📋 企业微信通知测试

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试方式**: curl命令直接调用

这是一条测试通知，用于验证企业微信通知功能。

**测试环境**: 
- 操作系统: macOS
- 工具: curl + Python脚本
- 依赖: 无需额外Python包

如果您收到这条消息，说明企业微信通知功能工作正常！ ✅"""
    
    return send_wechat_message_curl(webhook_url, title, content, False)


def test_urgent_notification(webhook_url: str):
    """测试紧急通知"""
    print("🚨 测试紧急通知...")
    
    title = "🚨 紧急通知测试"
    content = f"""### ⚠️ 紧急通知格式测试

**警报类型**: 测试警报
**触发时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

这是紧急通知格式的测试消息。

**紧急通知特点**:
- 标题带有🚨标识
- 格式更加醒目
- 用于重要事件通知

**测试状态**: 紧急通知格式正常 ✅"""
    
    return send_wechat_message_curl(webhook_url, title, content, True)


def test_monitoring_notification(webhook_url: str):
    """测试监控通知"""
    print("👁️ 测试监控通知...")
    
    title = "📊 监控系统状态报告"
    content = f"""### 🖥️ 系统运行状态

**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**系统版本**: 监控机器人 v2.0

**服务状态**:
- Twitter监控: ✅ 运行正常
- Solana监控: ✅ 运行正常
- 通知系统: ✅ 运行正常

**统计数据**:
- 监控用户: 15个
- 监控钱包: 8个  
- 今日通知: 23条
- 成功率: 98.5%

**下次检查**: {datetime.now().strftime('%H:%M')} (每小时)

系统运行稳定，无需人工干预。"""
    
    return send_wechat_message_curl(webhook_url, title, content, False)


def test_crypto_alert_notification(webhook_url: str):
    """测试加密货币警报通知"""
    print("💎 测试加密货币警报...")
    
    title = "🚨 重要交易警报"
    content = f"""### 🔥 加密货币监控警报

**警报类型**: 大额交易检测
**检测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Twitter推文警报**:
- 用户: @crypto_whale
- 内容: 发现新gem，CA地址已分享
- CA地址: 0x1234...abcd
- 影响力评分: 9/10

**Solana交易警报**:
- 钱包: 鲸鱼钱包A
- 交易类型: 大额买入
- 金额: $500,000 USDC
- 代币: Unknown Token

**建议操作**:
1. 立即查看详细信息
2. 分析市场影响
3. 考虑跟单策略

⚡ 时机敏感，请尽快处理！"""
    
    return send_wechat_message_curl(webhook_url, title, content, True)


def main():
    """主测试函数"""
    print("🚀 企业微信通知curl测试")
    print("=" * 50)
    
    # 检查curl命令是否可用
    try:
        subprocess.run(["curl", "--version"], capture_output=True, check=True)
        print("✅ curl命令可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ curl命令不可用，请先安装curl")
        return
    
    # 检查配置
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 错误: 未设置 WECHAT_WEBHOOK_URL 环境变量")
        print("请在终端中运行:")
        print("export WECHAT_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key'")
        print("或在 .env 文件中配置")
        return
    
    print(f"✅ 企业微信 Webhook URL 已配置")
    print(f"🔗 URL: {webhook_url[:50]}...")
    print()
    
    # 运行测试
    tests = [
        ("基础通知", test_basic_notification),
        ("紧急通知", test_urgent_notification),
        ("监控状态通知", test_monitoring_notification),
        ("加密货币警报", test_crypto_alert_notification),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 运行测试: {test_name}")
        try:
            result = test_func(webhook_url)
            results.append((test_name, result))
            print(f"{'✅ 通过' if result else '❌ 失败'}: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results.append((test_name, False))
        
        print("-" * 30)
        time.sleep(1)  # 避免发送过快
    
    # 总结结果
    print("📋 测试总结:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print()
    print(f"总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！企业微信通知功能正常！")
        print("💡 提示: 请检查您的企业微信群，应该收到了4条测试消息")
    else:
        print("⚠️ 部分测试失败，请检查以下内容：")
        print("  1. 企业微信Webhook URL是否正确")
        print("  2. 网络连接是否正常")
        print("  3. 企业微信机器人是否被移除")
    
    print(f"\n📝 测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # 加载环境变量（如果有.env文件）
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # 没有python-dotenv也没关系，可以用环境变量
        pass
    
    # 运行测试
    main()