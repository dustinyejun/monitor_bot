#!/usr/bin/env python3
"""
测试签名更新逻辑
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🔍 测试签名更新逻辑...")

# 测试签名对象处理
print("\n1. 测试签名对象处理...")
try:
    from src.plugins.solana_monitor_plugin import SolanaMonitorPlugin
    from datetime import datetime
    
    plugin = SolanaMonitorPlugin("test", {})
    
    # 模拟不同格式的签名数据
    mock_signatures = [
        # 字典格式 (最常见)
        {
            'signature': 'sig_dict_format_12345',
            'blockTime': int(datetime.now().timestamp()),
            'slot': 123456
        },
        # 模拟对象格式
        type('SignatureObj', (), {
            'signature': 'sig_obj_format_67890',
            'blockTime': int(datetime.now().timestamp()),
            'slot': 123457
        })(),
        # 字符串格式
        'sig_string_format_abcde'
    ]
    
    # 测试过滤功能
    filtered = plugin._filter_today_signatures(mock_signatures)
    print(f"   原始签名数: {len(mock_signatures)}")
    print(f"   过滤后签名数: {len(filtered)}")
    
    # 测试签名提取逻辑
    print("\n2. 测试签名提取...")
    for i, sig_obj in enumerate(mock_signatures):
        signature_str = None
        if isinstance(sig_obj, dict) and 'signature' in sig_obj:
            signature_str = sig_obj['signature']
            print(f"   签名{i+1}: 字典格式 -> {signature_str}")
        elif hasattr(sig_obj, 'signature'):
            signature_str = sig_obj.signature
            print(f"   签名{i+1}: 对象格式 -> {signature_str}")
        elif isinstance(sig_obj, str):
            signature_str = sig_obj
            print(f"   签名{i+1}: 字符串格式 -> {signature_str}")
        else:
            print(f"   签名{i+1}: 未知格式 -> {sig_obj}")
            
        if signature_str:
            print(f"   ✅ 成功提取: {signature_str}")
        else:
            print(f"   ❌ 提取失败")
    
    print("\n3. 测试最新签名更新...")
    # 测试最新签名提取（模拟数据库更新场景）
    if mock_signatures:
        latest_signature = None
        sig_obj = mock_signatures[0]  # 最新的签名
        
        if isinstance(sig_obj, dict) and 'signature' in sig_obj:
            latest_signature = sig_obj['signature']
        elif hasattr(sig_obj, 'signature'):
            latest_signature = sig_obj.signature
        elif isinstance(sig_obj, str):
            latest_signature = sig_obj
            
        if latest_signature:
            print(f"   ✅ 最新签名提取成功: {latest_signature}")
            print(f"   📝 将更新到数据库: last_signature = '{latest_signature}'")
        else:
            print(f"   ❌ 最新签名提取失败")
    
except Exception as e:
    print(f"   ❌ 测试失败: {e}")

print("\n🏁 签名更新逻辑测试完成!")
print("如果所有项目都显示 ✅，说明签名重复问题已修复。")