#!/usr/bin/env python3
"""
調試2200元為什麼沒有被排除
"""

def debug_2200_issue():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 專門測試2200元的上下文
    test_text = """另原告每日照護費用為2,200元作為計算基準。"""
    
    print("🔍 調試2200元計算基準檢測")
    print("=" * 60)
    print(f"測試文本: {test_text}")
    print("=" * 60)
    
    # 提取項目
    items = handler.extract_damage_items(test_text)
    print(f"提取到的項目:")
    for item in items:
        print(f"- {item.amount}元 - {item.description}")
        print(f"  原始文本: {item.raw_text}")
        print(f"  分類: {item.type}")
        print()
    
    # 手動測試計算基準檢測
    if items:
        item = items[0]  # 取第一個項目
        print(f"手動測試計算基準檢測:")
        print(f"金額: {item.amount}元")
        print(f"描述: {item.description}")
        print(f"原始文本: {item.raw_text}")
        
        # 模擬檢測邏輯
        prefix_context = item.raw_text if item.raw_text else item.description
        print(f"檢測上下文: {prefix_context}")
        
        calculation_base_indicators = [
            '每個月月薪', '月薪', '日薪', '時薪', '基本工資',
            '每日照護費用', '每日.*作為計算基準', '作為計算基準',
            '每月.*計算', '依每月.*計算', '每月.*減少',
            '勞動能力.*減少', '勞動能力.*損失.*計算',
            '每月工資.*為', '月工資.*為', '每日.*元作為計算基準'
        ]
        
        found_matches = []
        for keyword in calculation_base_indicators:
            import re
            if '.*' in keyword:
                if re.search(keyword, prefix_context):
                    found_matches.append(keyword)
            else:
                if keyword in prefix_context:
                    found_matches.append(keyword)
        
        print(f"匹配的關鍵詞: {found_matches}")

if __name__ == "__main__":
    debug_2200_issue()