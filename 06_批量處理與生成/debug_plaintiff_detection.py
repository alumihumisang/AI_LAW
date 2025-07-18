#!/usr/bin/env python3
"""
調試原告檢測邏輯
"""

def debug_plaintiff_detection():
    from universal_format_handler import UniversalFormatHandler, DamageItem
    
    handler = UniversalFormatHandler()
    
    # 創建測試項目
    test_items = [
        DamageItem(
            type="精神慰撫金",
            amount=300000,
            description="3. 精神慰撫金：",
            raw_text="（一）原告陳慶華之損害：\n3. 精神慰撫金：300,000元",
            confidence=0.8
        ),
        DamageItem(
            type="精神慰撫金",
            amount=300000,
            description="請求精神慰撫金",
            raw_text="原告陳慶華因被告拒絕承認肇事責任及誣指肇事逃逸，遭受精神痛苦，請求精神慰撫金300,000元。",
            confidence=0.8
        ),
        DamageItem(
            type="精神慰撫金",
            amount=300000,
            description="3. 精神慰撫金：",
            raw_text="（二）原告朱庭慧之損害：\n3. 精神慰撫金：300,000元",
            confidence=0.8
        ),
        DamageItem(
            type="精神慰撫金",
            amount=300000,
            description="請求精神慰撫金",
            raw_text="原告朱庭慧因臉部留下疤痕、自信受創、業績下降，以及被告拒絕承認肇事責任，遭受精神痛苦，請求精神慰撫金300,000元。",
            confidence=0.8
        )
    ]
    
    print("🔍 調試原告檢測邏輯")
    print("=" * 60)
    
    # 測試原告檢測
    for i, item in enumerate(test_items):
        plaintiff_key = handler._extract_plaintiff_context(item)
        group_key = f"{item.amount}_{plaintiff_key}"
        
        print(f"\n項目 {i+1}:")
        print(f"  描述: {item.description}")
        print(f"  原始文本: {item.raw_text[:80]}...")
        print(f"  檢測到的原告: {plaintiff_key}")
        print(f"  分組鍵: {group_key}")
    
    # 測試去重邏輯
    print(f"\n🔄 測試去重邏輯:")
    deduplicated = handler._deduplicate_items(test_items)
    
    print(f"去重前: {len(test_items)} 個項目")
    print(f"去重後: {len(deduplicated)} 個項目")
    
    for i, item in enumerate(deduplicated):
        plaintiff_key = handler._extract_plaintiff_context(item)
        print(f"  保留項目 {i+1}: {item.amount}元 - 原告: {plaintiff_key}")
        print(f"    描述: {item.description}")
    
    # 預期結果
    expected_count = 2  # 應該保留2個（每個原告1個）
    if len(deduplicated) == expected_count:
        print(f"\n✅ 去重邏輯正確：保留了{expected_count}個慰撫金（每個原告1個）")
    else:
        print(f"\n❌ 去重邏輯錯誤：預期{expected_count}個，實際{len(deduplicated)}個")

if __name__ == "__main__":
    debug_plaintiff_detection()