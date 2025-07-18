#!/usr/bin/env python3
"""
調試過濾步驟
"""

def debug_filtering_step():
    from universal_format_handler import UniversalFormatHandler, DamageItem
    
    handler = UniversalFormatHandler()
    
    # 創建測試項目 - 模擬2200元的情況
    test_item = DamageItem(
        type="看護費用",
        amount=2200,
        description="另原告每日照護費用",
        raw_text="另原告每日照護費用為2,200元作為計算基準。",
        confidence=0.6
    )
    
    print("🔍 調試過濾步驟")
    print("=" * 60)
    print(f"測試項目: {test_item.amount}元")
    print(f"描述: {test_item.description}")
    print(f"原始文本: {test_item.raw_text}")
    print("=" * 60)
    
    # 手動執行過濾邏輯
    is_calculation_base = False
    
    # 檢查當前金額本身是否是計算基準
    amount_str_with_comma = f"{test_item.amount:,}元"
    amount_str_no_comma = f"{test_item.amount}元"
    
    print(f"金額格式:")
    print(f"  帶逗號: {amount_str_with_comma}")
    print(f"  不帶逗號: {amount_str_no_comma}")
    
    prefix_context = test_item.description  # 默認使用描述
    
    # 先嘗試在原始文本中找到金額位置 - 擴大檢查範圍
    full_text = test_item.raw_text if test_item.raw_text else ""
    
    for amount_format in [amount_str_with_comma, amount_str_no_comma]:
        if amount_format in full_text:
            pos = full_text.find(amount_format)
            prefix_start = max(0, pos - 100)
            prefix_context = full_text[prefix_start:pos + len(amount_format)]
            print(f"在原始文本中找到 {amount_format}，位置: {pos}")
            print(f"上下文: {prefix_context}")
            break
        elif amount_format in test_item.description:
            prefix_context = test_item.description
            print(f"在描述中找到 {amount_format}")
            print(f"上下文: {prefix_context}")
    
    # 檢查金額前面是否直接包含計算基準關鍵詞
    calculation_base_indicators = [
        '每個月月薪', '月薪', '日薪', '時薪', '基本工資',
        '每日照護費用', '每日.*作為計算基準', '作為計算基準',
        '每月.*計算', '依每月.*計算', '每月.*減少',
        '勞動能力.*減少', '勞動能力.*損失.*計算',
        '每月工資.*為', '月工資.*為', '每日.*元作為計算基準'
    ]
    
    print(f"\n檢測計算基準關鍵詞:")
    for base_keyword in calculation_base_indicators:
        import re as regex_module
        if '.*' in base_keyword:
            # 正則表達式模式
            if regex_module.search(base_keyword, prefix_context):
                is_calculation_base = True
                print(f"✅ 匹配正則模式: {base_keyword}")
                break
        else:
            # 精確文本匹配
            if base_keyword in prefix_context:
                print(f"✅ 找到關鍵詞: {base_keyword}")
                base_pos = prefix_context.find(base_keyword)
                
                # 檢查多種金額格式
                amount_patterns = [
                    f'{test_item.amount:,}元',
                    f'{test_item.amount}元',
                    test_item.raw_text  # 原始格式
                ]
                
                amount_pos = -1
                for pattern in amount_patterns:
                    pos = prefix_context.find(pattern)
                    if pos != -1:
                        amount_pos = pos
                        print(f"   金額位置: {pos} (模式: {pattern})")
                        break
                
                if amount_pos > base_pos and (amount_pos - base_pos) < 30:
                    # 檢查中間文字
                    between_text = prefix_context[base_pos:amount_pos]
                    exclusion_words = ['請求', '賠償', '損害', '損失', '支出', '費用']
                    has_exclusion = any(word in between_text for word in exclusion_words)
                    
                    print(f"   基準詞位置: {base_pos}")
                    print(f"   金額位置: {amount_pos}")
                    print(f"   距離: {amount_pos - base_pos}")
                    print(f"   中間文字: '{between_text}'")
                    print(f"   包含排除詞: {has_exclusion}")
                    
                    if not has_exclusion:
                        is_calculation_base = True
                        print(f"   => 確認為計算基準")
                        break
    
    # 特殊檢查：如果金額後面緊跟"計算"
    calc_pattern = f"{test_item.amount}元計算"
    if calc_pattern in prefix_context.replace(',', ''):
        is_calculation_base = True
        print(f"✅ 匹配計算模式: {calc_pattern}")
    
    print(f"\n最終結果: {'是計算基準' if is_calculation_base else '不是計算基準'}")
    
    # 測試實際過濾函數
    print(f"\n測試實際過濾函數:")
    filtered = handler._filter_calculation_bases([test_item])
    print(f"過濾前: 1 個項目")
    print(f"過濾後: {len(filtered)} 個項目")
    
    if len(filtered) == 0:
        print("✅ 項目被正確過濾掉")
    else:
        print("❌ 項目沒有被過濾掉")

if __name__ == "__main__":
    debug_filtering_step()