#!/usr/bin/env python3
"""
詳細調試交通費提取問題
"""

def debug_transportation_extraction():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    import re
    
    processor = HybridCoTGenerator()
    
    # 簡單測試案例
    test_case = "原告陳小明因本次事故就醫產生交通費500元。"
    
    print("🔍 詳細調試交通費提取")
    print("=" * 60)
    print(f"測試文本: {test_case}")
    print()
    
    # 步驟1: 檢查句子分割
    sentences = re.split(r'[。]', test_case)
    print(f"1. 句子分割結果: {sentences}")
    print()
    
    # 步驟2: 檢查原告識別
    sentence = sentences[0] if sentences else ""
    plaintiff_patterns = [
        r'原告([^，。；、\s因由就支出產生之]{2,4})',     # 標準格式，避免抓取動詞
        r'([^，。；、\s]{2,4})之醫療費用',              # 從損害項目反推原告
        r'([^，。；、\s]{2,4})之交通費',                # 從損害項目反推原告  
        r'([^，。；、\s]{2,4})之工資損失',              # 從損害項目反推原告
        r'([^，。；、\s]{2,4})之慰撫金',                # 從損害項目反推原告
        r'原告([^，。；、\s]{2,4})因',                  # 原告XX因格式
        r'原告([^，。；、\s]{2,4})[支受]',               # 原告XX支出/受有格式
    ]
    
    plaintiff = None
    for i, pattern in enumerate(plaintiff_patterns):
        plaintiff_match = re.search(pattern, sentence)
        print(f"2.{i+1} 模式 '{pattern}': {plaintiff_match.group(1) if plaintiff_match else None}")
        if plaintiff_match:
            potential_plaintiff = plaintiff_match.group(1)
            # 檢查是否為有效姓名
            print(f"     檢查姓名 '{potential_plaintiff}' 長度: {len(potential_plaintiff)}")
            chinese_char_count = sum(1 for char in potential_plaintiff if '\u4e00' <= char <= '\u9fff')
            print(f"     中文字符數: {chinese_char_count}")
            
            # 檢查無效關鍵詞
            invalid_keywords = [
                '醫療', '交通', '工資', '損失', '費用', '慰撫', '精神',
                '車輛', '貶值', '鑑定', '賠償', '元', '因', '受', '支出',
                '就醫', '事故', '本次', '所', '之', '等', '共', '計',
                '包含', '總', '合', '金額', '項目'
            ]
            for keyword in invalid_keywords:
                if keyword in potential_plaintiff:
                    print(f"     包含無效關鍵詞: {keyword}")
            
            if processor._is_valid_plaintiff_name(potential_plaintiff):
                plaintiff = potential_plaintiff
                print(f"     ✅ 有效原告: {plaintiff}")
                break
            else:
                print(f"     ❌ 無效原告: {potential_plaintiff}")
    
    if not plaintiff:
        print("❌ 未找到有效原告，將跳過處理")
        return
    
    print()
    
    # 步驟3: 檢查交通費關鍵詞匹配
    keywords = ['交通費用', '交通費', '往返費用', '來回費用', '車費', '油費', '停車費', '過路費', '通行費']
    print("3. 交通費關鍵詞檢查:")
    for keyword in keywords:
        if keyword in sentence:
            print(f"   ✅ 找到關鍵詞: {keyword}")
        else:
            print(f"   ❌ 未找到: {keyword}")
    
    # 檢查是否有任何關鍵詞匹配
    has_keyword = any(keyword in sentence for keyword in keywords)
    print(f"   總結: {'有' if has_keyword else '無'}交通費關鍵詞")
    print()
    
    # 步驟4: 檢查正則表達式匹配
    if has_keyword:
        pattern = r'(?:交通費用|交通費|往返費用|來回費用|車費|油費|停車費|過路費|通行費).*?(\d+(?:,\d{3})*)\s*元'
        amount_match = re.search(pattern, sentence)
        print(f"4. 正則表達式匹配:")
        print(f"   模式: {pattern}")
        print(f"   結果: {amount_match.group(1) if amount_match else None}")
        if amount_match:
            amount = int(amount_match.group(1).replace(',', ''))
            print(f"   金額: {amount}元")
        print()
    
    # 步驟5: 調用實際的提取方法
    print("5. 實際提取結果:")
    result = processor._extract_damage_items_from_text(test_case)
    print(f"   結果: {result}")
    
    if result:
        for plaintiff, items in result.items():
            print(f"   原告 {plaintiff}:")
            for item in items:
                print(f"     - {item}")

if __name__ == "__main__":
    debug_transportation_extraction()