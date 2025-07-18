#!/usr/bin/env python3
"""
調試去重過程，找出慰撫金被誤刪的原因
"""

def debug_deduplication_process():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 測試文本 - 兩個原告的慰撫金
    test_text = """（一）原告陳慶華之損害：
3. 精神慰撫金：300,000元
原告陳慶華因被告拒絕承認肇事責任及誣指肇事逃逸，遭受精神痛苦，請求精神慰撫金300,000元。

（二）原告朱庭慧之損害：
3. 精神慰撫金：300,000元
原告朱庭慧因臉部留下疤痕、自信受創、業績下降，以及被告拒絕承認肇事責任，遭受精神痛苦，請求精神慰撫金300,000元。"""
    
    print("🔍 調試去重過程 - 慰撫金案例")
    print("=" * 80)
    
    # 步驟1: 格式檢測
    format_info = handler.detect_format(test_text)
    print(f"1️⃣ 格式檢測: {format_info['primary_format']} (置信度: {format_info['confidence']:.2f})")
    
    # 步驟2: 格式基礎提取
    print(f"\n2️⃣ 格式基礎提取:")
    if format_info['primary_format'] and format_info['confidence'] > 0.3:
        format_items = handler._extract_by_format(test_text, format_info['primary_format'])
        print(f"   格式提取到 {len(format_items)} 個項目:")
        for i, item in enumerate(format_items):
            print(f"   {i+1}. {item.amount}元 - {item.description[:50]}...")
            print(f"      原始文本: {item.raw_text[:60]}...")
    else:
        format_items = []
        print(f"   格式置信度不足，跳過格式提取")
    
    # 步驟3: 混合策略提取
    print(f"\n3️⃣ 混合策略提取:")
    mixed_items = handler._extract_by_mixed_strategy(test_text)
    print(f"   混合策略提取到 {len(mixed_items)} 個項目:")
    for i, item in enumerate(mixed_items):
        print(f"   {i+1}. {item.amount}元 - {item.description[:50]}... (置信度: {item.confidence})")
    
    # 步驟4: 合併結果
    print(f"\n4️⃣ 合併結果:")
    all_items = format_items + mixed_items
    print(f"   合併前共 {len(all_items)} 個項目")
    
    # 統計300,000元的項目
    consolation_items_before = [item for item in all_items if item.amount == 300000]
    print(f"   其中300,000元項目: {len(consolation_items_before)} 個")
    for i, item in enumerate(consolation_items_before):
        print(f"     {i+1}. 描述: {item.description[:50]}...")
        print(f"        原始: {item.raw_text[:60]}...")
        print(f"        置信度: {item.confidence}")
    
    # 步驟5: 去重處理
    print(f"\n5️⃣ 去重處理:")
    deduplicated = handler._deduplicate_items(all_items)
    print(f"   去重後剩餘 {len(deduplicated)} 個項目")
    
    # 統計去重後的300,000元項目
    consolation_items_after = [item for item in deduplicated if item.amount == 300000]
    print(f"   其中300,000元項目: {len(consolation_items_after)} 個")
    for i, item in enumerate(consolation_items_after):
        print(f"     {i+1}. 描述: {item.description[:50]}...")
    
    # 分析去重原因
    if len(consolation_items_before) > len(consolation_items_after):
        print(f"\n❌ 去重步驟錯誤刪除了 {len(consolation_items_before) - len(consolation_items_after)} 個慰撫金項目")
        print(f"   這是錯誤的，因為不同原告的慰撫金應該分別計算")
    else:
        print(f"\n✅ 去重步驟正確保留了所有慰撫金項目")

if __name__ == "__main__":
    debug_deduplication_process()