#!/usr/bin/env python3
"""
調試小額金額檢測問題
"""

def debug_small_amounts():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 簡化測試文本 - 專注於小額金額
    simple_text = """
    醫療費用項目如下：
    1. 急診掛號費50元
    2. 門診掛號費460元  
    3. 醫療檢查費用5,000元
    """
    
    print("🔍 調試小額金額檢測")
    print("=" * 60)
    print(f"測試文本:\n{simple_text}")
    print("=" * 60)
    
    # 檢測格式
    format_info = handler.detect_format(simple_text)
    print(f"格式檢測結果: {format_info}")
    
    # 提取損害項目
    items = handler.extract_damage_items(simple_text)
    print(f"\n提取到的項目:")
    for item in items:
        print(f"- {item.amount}元 ({item.type}) - 置信度: {item.confidence}")
        print(f"  描述: {item.description}")
        print(f"  原始: {item.raw_text}")
        print()
    
    # 測試混合策略
    print("\n🔄 測試混合策略:")
    mixed_items = handler._extract_by_mixed_strategy(simple_text)
    print(f"混合策略提取到 {len(mixed_items)} 個項目:")
    for item in mixed_items:
        print(f"- {item.amount}元 ({item.type}) - 置信度: {item.confidence}")
        print(f"  描述: {item.description}")
        print()

if __name__ == "__main__":
    debug_small_amounts()