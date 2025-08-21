#!/usr/bin/env python3
"""
快速通知测试脚本
快速验证通知系统是否正常工作
"""
import asyncio
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.notification_service import notification_service
from src.schemas.notification import NotificationCreate, NotificationType, NotificationChannel


async def quick_test():
    """快速测试"""
    print("🚀 快速通知测试")
    print("=" * 40)
    
    # 检查配置
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 未配置 WECHAT_WEBHOOK_URL")
        print("请在 .env 文件中添加:")
        print("WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key")
        return False
    
    print(f"✅ Webhook URL: {webhook_url[:50]}...")
    
    # 创建测试通知
    notification = NotificationCreate(
        type=NotificationType.SYSTEM,
        title="⚡ 快速测试",
        content=f"""### 🧪 系统快速测试

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

这是一条快速测试通知，用于验证企业微信通知功能。

如果您收到这条消息，说明通知系统工作正常！ ✅""",
        is_urgent=False,
        channel=NotificationChannel.WECHAT,
        data={"test": "quick_test"}
    )
    
    print("📤 发送测试通知...")
    
    try:
        result = await notification_service.send_notification(notification)
        
        if result:
            print("✅ 测试通知发送成功！")
            print("请检查您的企业微信群是否收到消息")
            return True
        else:
            print("❌ 测试通知发送失败！")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False


if __name__ == "__main__":
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    # 运行测试
    success = asyncio.run(quick_test())
    
    if success:
        print("\n🎉 快速测试完成！通知系统正常工作！")
    else:
        print("\n⚠️ 快速测试失败，请检查配置和网络连接")
        sys.exit(1)