#!/usr/bin/env python3
"""
調試遺漏金額問題
"""

def debug_missing_amounts():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    import re
    
    test_case = """
（一）原告陳碧翔之損害：
1. 醫療費用：13,180元
原告陳碧翔因本次事故受傷就醫，支出醫療費用共計13,180元。
2. 假牙裝置費用：24,000元
原告陳碧翔因頭部受擊導致假牙脫落，需重新安裝假牙裝置，費用為24,000元。
3. 慰撫金：200,000元
原告陳碧翔因本次事故受傷及治療，造成生活不便，請求精神慰撫金200,000元。
（二）原告吳麗娟之損害：
1. 醫療費用：8,720元
原告吳麗娟因本次事故受傷就醫，支出醫療費用共計8,720元。
2. 腰椎手術預估費用：264,379元
原告吳麗娟因事故導致腰椎滑脫，預估未來手術費用為264,379元。
3. 慰撫金：200,000元
原告吳麗娟因本次事故受傷及治療，造成身心痛苦，請求精神慰撫金200,000元。
（三）原告陳碧翔、吳麗娟共同損害：
1. 看護費用：305,000元
原告陳碧翔、吳麗娟因事故導致生活無法自理，需支付看護費用共計305,000元。
2. 交通費用：39,370元
原告陳碧翔、吳麗娟因就醫及復健，支出計程車費用共計39,370元。
"""
    
    processor = HybridCoTGenerator()
    
    print("🔍 調試遺漏金額問題")
    print("=" * 60)
    
    # 步驟1: 找出文本中所有的金額
    all_amounts_in_text = re.findall(r'(\d+(?:,\d{3})*)\s*元', test_case)
    print("1. 文本中所有金額:")
    for amount in all_amounts_in_text:
        print(f"   {amount}元")
    print(f"   共 {len(all_amounts_in_text)} 個金額")
    print()
    
    # 步驟2: 按句子分析原告識別
    sentences = re.split(r'[。]', test_case)
    print("2. 按句子分析原告識別:")
    
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
            
        # 檢查是否包含金額
        amounts = re.findall(r'(\d+(?:,\d{3})*)\s*元', sentence)
        if amounts:
            print(f"\n句子 {i+1}: {sentence.strip()}")
            print(f"金額: {amounts}")
            
            # 檢查原告識別
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
            for pattern in plaintiff_patterns:
                plaintiff_match = re.search(pattern, sentence)
                if plaintiff_match:
                    potential_plaintiff = plaintiff_match.group(1)
                    if processor._is_valid_plaintiff_name(potential_plaintiff):
                        plaintiff = potential_plaintiff
                        break
            
            print(f"識別到的原告: {plaintiff if plaintiff else '未識別'}")
            
            if not plaintiff:
                print("❌ 這個金額會被跳過（無原告）")
    
    print("\n" + "=" * 60)
    
    # 步驟3: 實際提取結果對比
    print("3. 實際提取結果:")
    result = processor._extract_damage_items_from_text(test_case)
    extracted_amounts = []
    for plaintiff, items in result.items():
        for item in items:
            extracted_amounts.append(item['amount'])
            print(f"   {plaintiff}: {item['name']} {item['amount']:,}元")
    
    print(f"\n4. 統計:")
    print(f"   文本中的金額: {[amount for amount in all_amounts_in_text]}")
    print(f"   提取到的金額: {extracted_amounts}")
    
    missing_amounts = []
    for amount_str in all_amounts_in_text:
        amount = int(amount_str.replace(',', ''))
        if amount not in extracted_amounts:
            missing_amounts.append(amount)
    
    print(f"   遺漏的金額: {missing_amounts}")

if __name__ == "__main__":
    debug_missing_amounts()