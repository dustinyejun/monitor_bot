#!/usr/bin/env python3
"""
调试 before 参数的行为
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🔍 调试 before 参数行为...")

def test_before_logic():
    """
    测试 before 参数的逻辑
    
    根据 Solana API 文档：
    - before: 从此签名之前开始搜索（不包含此签名本身）
    - 返回结果按时间倒序排列（最新的在前）
    """
    
    # 模拟的签名列表（按时间倒序）
    all_signatures = [
        {"signature": "newest_sig_1", "blockTime": 1692600000, "slot": 100},    # 最新
        {"signature": "sig_12_36", "blockTime": 1692599400, "slot": 99},       # 12:36 (你看到的重复消息)
        {"signature": "older_sig_1", "blockTime": 1692598800, "slot": 98},     # 更早的
        {"signature": "older_sig_2", "blockTime": 1692598200, "slot": 97},     # 更早的
    ]
    
    print("\n1. 模拟第一次检查（last_signature = None）:")
    last_signature = None
    signatures_1st = get_signatures_with_before(all_signatures, last_signature, limit=2)
    print(f"   获取到签名: {[s['signature'] for s in signatures_1st]}")
    
    # 模拟更新 last_signature
    if signatures_1st:
        last_signature = signatures_1st[0]['signature']  # newest_sig_1
        print(f"   更新 last_signature = {last_signature}")
    
    print("\n2. 模拟第二次检查:")
    signatures_2nd = get_signatures_with_before(all_signatures, last_signature, limit=2)
    print(f"   获取到签名: {[s['signature'] for s in signatures_2nd]}")
    
    if any(s['signature'] == 'sig_12_36' for s in signatures_2nd):
        print("   ❌ 问题：12:36的消息又出现了！")
        print("   📝 原因分析：")
        if last_signature == "newest_sig_1":
            print("      - last_signature 正确更新为 newest_sig_1")
            print("      - before=newest_sig_1 应该排除 newest_sig_1")
            print("      - 但是 sig_12_36 仍然被返回")
            print("      - 这说明可能有新的交易在 newest_sig_1 之后产生")
    else:
        print("   ✅ 正常：12:36的消息没有重复")

def get_signatures_with_before(all_signatures, before_signature, limit):
    """
    模拟 get_signatures_for_address 的 before 参数行为
    """
    if before_signature is None:
        # 没有 before 参数，返回最新的 limit 个
        return all_signatures[:limit]
    
    # 找到 before_signature 的位置
    before_index = None
    for i, sig in enumerate(all_signatures):
        if sig['signature'] == before_signature:
            before_index = i
            break
    
    if before_index is None:
        # before_signature 不存在，返回所有最新的
        return all_signatures[:limit]
    
    # 返回 before_signature 之前的签名（不包含 before_signature 本身）
    return all_signatures[before_index + 1:before_index + 1 + limit]

print("\n3. 测试 before 参数逻辑:")
test_before_logic()

print("\n4. 可能的问题原因:")
print("   1. 在两次检查之间，有新的交易产生")
print("   2. last_signature 没有正确保存到数据库")
print("   3. 数据库读取的 last_signature 不是最新的")
print("   4. before 参数传递有问题")

print("\n🔧 建议调试步骤:")
print("   1. 添加更详细的日志，显示每次的 before 参数值")
print("   2. 检查数据库中 last_signature 的实际值")
print("   3. 验证两次检查之间的时间间隔")
print("   4. 确认没有并发检查的问题")