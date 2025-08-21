#!/usr/bin/env python3
"""
测试运行脚本
提供不同级别的测试选项
"""
import os
import sys
import subprocess
import argparse


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🚀 {description}")
    print("=" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="监控机器人测试运行器")
    parser.add_argument("--quick", action="store_true", help="运行快速通知测试")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--notification", action="store_true", help="运行通知功能测试")
    parser.add_argument("--real-api", action="store_true", help="包括真实API测试")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--coverage", action="store_true", help="生成测试覆盖率报告")
    
    args = parser.parse_args()
    
    # 如果没有指定任何参数，显示帮助
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    success_count = 0
    total_count = 0
    
    # 检查环境变量
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
    if args.real_api and not webhook_url:
        print("⚠️ 警告: 要运行真实API测试，请设置 WECHAT_WEBHOOK_URL 环境变量")
    
    # 快速通知测试
    if args.quick or args.all:
        total_count += 1
        if run_command("python quick_test_notification.py", "快速通知测试"):
            success_count += 1
    
    # 单元测试
    if args.unit or args.all:
        total_count += 1
        cmd = "uv run pytest tests/test_notification_services.py -v"
        if args.coverage:
            cmd += " --cov=src/services --cov-report=html"
        if run_command(cmd, "通知服务单元测试"):
            success_count += 1
    
    # 企业微信通知测试
    if args.notification or args.all:
        total_count += 1
        cmd = "uv run pytest tests/test_wechat_notification.py -v"
        if args.real_api:
            cmd += " --run-real-api"
        if run_command(cmd, "企业微信通知测试"):
            success_count += 1
    
    # 完整通知功能测试
    if args.notification or args.all:
        if webhook_url:  # 只有配置了webhook才运行
            total_count += 1
            if run_command("python test_wechat_real.py", "完整通知功能测试"):
                success_count += 1
    
    # 其他核心测试
    if args.all:
        test_files = [
            ("tests/test_twitter_services.py", "Twitter服务测试"),
            ("tests/test_solana_services.py", "Solana服务测试"),
            ("tests/test_monitor_plugins.py", "监控插件测试"),
        ]
        
        for test_file, description in test_files:
            if os.path.exists(test_file):
                total_count += 1
                cmd = f"uv run pytest {test_file} -v"
                if args.coverage:
                    cmd += " --cov=src --cov-append"
                if run_command(cmd, description):
                    success_count += 1
    
    # 总结结果
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    
    if total_count == 0:
        print("⚠️ 没有运行任何测试")
    else:
        print(f"✅ 通过: {success_count}/{total_count} 个测试套件")
        
        if success_count == total_count:
            print("🎉 所有测试都通过了！")
        else:
            print("⚠️ 部分测试失败，请检查上述输出")
    
    # 显示覆盖率报告位置
    if args.coverage and os.path.exists("htmlcov/index.html"):
        print(f"\n📊 测试覆盖率报告: file://{os.path.abspath('htmlcov/index.html')}")


if __name__ == "__main__":
    main()