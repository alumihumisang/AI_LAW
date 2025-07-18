#!/usr/bin/env python3
"""
調試未來醫療費用問題
"""

def debug_future_medical():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    import re
    
    # 包含未來醫療費用的具體句子
    test_sentence = "原告主張因本件交通事故發生後，因受到系爭傷害，而前往淡水馬偕紀念醫院、新光吳火獅紀念醫院、大順中醫診所就醫，支出相關就醫費用共130,698元，另外因診斷證明書稱宜門診持續追蹤治療，因此預估仍有將來醫療費用共15萬元。"
    
    processor = HybridCoTGenerator()
    
    print("🔍 調試未來醫療費用提取")
    print("=" * 60)
    print(f"測試句子: {test_sentence}")
    print()
    
    # 步驟1: 檢查原告識別
    plaintiff_patterns = [
        r'原告([^，。；、\s因由就支出產生之]{2,4})',
        r'([^，。；、\s]{2,4})之醫療費用',
        r'([^，。；、\s]{2,4})之交通費',
        r'([^，。；、\s]{2,4})之工資損失',
        r'([^，。；、\s]{2,4})之慰撫金',
        r'原告([^，。；、\s]{2,4})因',
        r'原告([^，。；、\s]{2,4})[支受]',
    ]
    
    plaintiff = None
    print("1. 原告識別檢查:")
    for i, pattern in enumerate(plaintiff_patterns):
        plaintiff_match = re.search(pattern, test_sentence)
        print(f"   模式 {i+1}: {pattern}")
        if plaintiff_match:
            potential_plaintiff = plaintiff_match.group(1)
            print(f"     匹配: {potential_plaintiff}")
            if processor._is_valid_plaintiff_name(potential_plaintiff):
                plaintiff = potential_plaintiff
                print(f"     ✅ 有效: {plaintiff}")
                break
            else:
                print(f"     ❌ 無效: {potential_plaintiff}")
        else:
            print(f"     無匹配")
    
    # 檢查通用原告
    if not plaintiff:
        if '原告' in test_sentence and ('因' in test_sentence or '支出' in test_sentence or '受有' in test_sentence or '產生' in test_sentence):
            plaintiff = "原告"
            print(f"   通用原告: {plaintiff}")
    
    print(f"\n最終原告: {plaintiff}")
    
    # 步驟2: 檢查未來醫療費用關鍵詞
    print(f"\n2. 未來醫療費用關鍵詞檢查:")
    keywords = ['未來醫療', '將來醫療', '預估.*醫療', '15萬', '十五萬']
    for keyword in keywords:
        if re.search(keyword, test_sentence):
            print(f"   ✅ 找到關鍵詞: {keyword}")
        else:
            print(f"   ❌ 未找到: {keyword}")
    
    # 檢查是否有任何關鍵詞匹配
    has_keyword = any(re.search(keyword, test_sentence) for keyword in keywords)
    print(f"   總結: {'有' if has_keyword else '無'}未來醫療關鍵詞")
    
    # 步驟3: 檢查正則表達式匹配
    if has_keyword:
        print(f"\n3. 正則表達式匹配:")
        pattern = r'(?:未來醫療|將來醫療|預估.*醫療).*?(\d+(?:,\d{3})*)\s*元|15萬|十五萬'
        amount_match = re.search(pattern, test_sentence)
        print(f"   模式: {pattern}")
        
        if amount_match:
            if '15萬' in test_sentence or '十五萬' in test_sentence:
                amount = 150000
                print(f"   匹配到中文數字: 15萬 → {amount}元")
            else:
                amount = int(amount_match.group(1).replace(',', ''))
                print(f"   匹配到金額: {amount}元")
        else:
            print(f"   ❌ 無匹配")
    
    # 步驟4: 實際提取測試
    print(f"\n4. 實際提取測試:")
    result = processor._extract_damage_items_from_text(test_sentence)
    print(f"   結果: {result}")

if __name__ == "__main__":
    debug_future_medical()