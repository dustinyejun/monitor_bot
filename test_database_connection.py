#!/usr/bin/env python3
"""
数据库连接测试
验证数据库配置是否正确
"""
import sys
import os
from sqlalchemy import create_engine, text

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config.settings import settings
    from src.config.database import engine, SessionLocal
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


def test_database_connection():
    """测试数据库连接"""
    print("🔗 测试数据库连接...")
    print(f"📊 数据库URL: {settings.database_url}")
    
    try:
        # 测试基础连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ 数据库连接成功!")
            print(f"📝 PostgreSQL版本: {version}")
            
        # 测试SessionLocal
        db = SessionLocal()
        try:
            result = db.execute(text("SELECT current_database(), current_user"))
            database_info = result.fetchone()
            print(f"📂 当前数据库: {database_info[0]}")
            print(f"👤 当前用户: {database_info[1]}")
        finally:
            db.close()
            
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def test_database_tables():
    """检查数据库表是否存在"""
    print("\n🗃️ 检查数据库表...")
    
    try:
        db = SessionLocal()
        try:
            # 检查表是否存在
            tables_to_check = [
                'twitter_users',
                'tweets', 
                'solana_wallets',
                'solana_transactions',
                'notifications',
                'notification_templates',
                'notification_rules'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table_name in tables_to_check:
                try:
                    result = db.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                    existing_tables.append(table_name)
                except Exception:
                    missing_tables.append(table_name)
            
            if existing_tables:
                print("✅ 已存在的表:")
                for table in existing_tables:
                    print(f"  - {table}")
            
            if missing_tables:
                print("⚠️ 缺失的表:")
                for table in missing_tables:
                    print(f"  - {table}")
                print("\n💡 提示: 运行数据库迁移命令创建缺失的表:")
                print("  uv run alembic upgrade head")
            else:
                print("🎉 所有数据库表都已存在!")
            
            return len(missing_tables) == 0
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 检查数据库表失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 数据库配置测试")
    print("=" * 50)
    
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ 未安装 python-dotenv")
    
    # 显示配置信息
    print(f"🔧 数据库配置:")
    print(f"  主机: 192.168.1.222")
    print(f"  端口: 5432") 
    print(f"  数据库: monitor_bot")
    print(f"  用户: postgres")
    print()
    
    # 测试连接
    connection_ok = test_database_connection()
    
    if connection_ok:
        # 检查表
        tables_ok = test_database_tables()
        
        print("\n" + "=" * 50)
        print("📋 测试总结:")
        print(f"  数据库连接: {'✅ 正常' if connection_ok else '❌ 失败'}")
        print(f"  数据库表: {'✅ 完整' if tables_ok else '⚠️ 需要迁移'}")
        
        if connection_ok and tables_ok:
            print("\n🎉 数据库配置完全正确! 现在可以运行完整的通知测试了:")
            print("  python quick_test_notification.py")
        elif connection_ok:
            print("\n⚠️ 数据库连接正常，但需要运行迁移创建表:")
            print("  uv run alembic upgrade head")
    else:
        print("\n❌ 数据库连接失败，请检查:")
        print("  1. 数据库服务是否运行")
        print("  2. IP地址和端口是否正确")
        print("  3. 用户名和密码是否正确") 
        print("  4. 数据库 'monitor_bot' 是否存在")
        print("  5. 网络连接是否正常")


if __name__ == "__main__":
    main()