#!/usr/bin/env python3
"""
調試格式提取過程
"""

def debug_format_extraction():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 包含小額金額的測試文本
    test_text = """
    醫療費用項目如下：
    1. 急診掛號費50元
    2. 門診掛號費460元  
    3. 醫療檢查費用5,000元
    4. 手術費用180,000元
    原告每月工資應為49,791元，以此作為計算基準。
    另原告每日照護費用為2,200元作為計算基準。
    """
    
    print("🔍 調試格式提取過程")
    print("=" * 80)
    
    # 步驟1: 格式檢測
    format_info = handler.detect_format(test_text)
    print(f"1️⃣ 格式檢測: {format_info['primary_format']} (置信度: {format_info['confidence']:.2f})")
    
    # 步驟2: 格式基礎提取
    print(f"\n2️⃣ 格式基礎提取:")
    if format_info['primary_format'] and format_info['confidence'] > 0.3:
        format_items = handler._extract_by_format(test_text, format_info['primary_format'])
        print(f"   格式提取到 {len(format_items)} 個項目:")
        for item in format_items:
            print(f"   - {item.amount}元 ({item.type})")
    else:
        format_items = []
        print(f"   格式置信度不足，跳過格式提取")
    
    # 步驟3: 混合策略提取
    print(f"\n3️⃣ 混合策略提取:")
    mixed_items = handler._extract_by_mixed_strategy(test_text)
    print(f"   混合策略提取到 {len(mixed_items)} 個項目:")
    for item in mixed_items:
        print(f"   - {item.amount}元 ({item.type}) - 置信度: {item.confidence}")
    
    # 步驟4: 合併結果
    print(f"\n4️⃣ 合併結果:")
    all_items = format_items + mixed_items
    print(f"   合併前共 {len(all_items)} 個項目")
    
    # 步驟5: 去重
    print(f"\n5️⃣ 去重處理:")
    deduplicated = handler._deduplicate_items(all_items)
    print(f"   去重後剩餘 {len(deduplicated)} 個項目:")
    for item in deduplicated:
        print(f"   - {item.amount}元 ({item.type}) - 置信度: {item.confidence}")
    
    # 步驟6: 計算基準過濾
    print(f"\n6️⃣ 計算基準過濾:")
    filtered = handler._filter_calculation_bases(deduplicated)
    print(f"   過濾後剩餘 {len(filtered)} 個項目:")
    for item in filtered:
        print(f"   - {item.amount}元 ({item.type}) - 置信度: {item.confidence}")
    
    # 測試條件判斷
    print(f"\n7️⃣ 條件判斷分析:")
    print(f"   len(format_items) = {len(format_items)}")
    print(f"   條件 len(damage_items) < 2: {len(format_items) < 2}")
    print(f"   因此會{'會' if len(format_items) < 2 else '不會'}觸發混合策略補充")

if __name__ == "__main__":
    debug_format_extraction()