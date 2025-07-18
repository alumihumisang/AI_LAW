#!/usr/bin/env python3
"""
調試單一原告案例問題
"""

def debug_single_plaintiff():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    import re
    
    test_case = """
三、損害項目：

（一）醫療費用：12,372元
原告因本次事故就醫，支出住院及物理治療費用共計12,372元。
（二）交通費：86,800元
原告因本次事故行動不便，往返醫院復健產生交通費用共計86,800元。
（三）看護費用：500,000元
原告因本次事故行動不便，需僱用幫傭照護，產生看護費用共計500,000元。
（四）財物損失：38,000元
原告因本次事故造成衣物及牙齒損壞，財物損失共計38,000元。
（五）精神慰撫金：500,000元
原告因本次事故受有嚴重傷害及精神痛苦，請求精神慰撫金500,000元。
"""
    
    processor = HybridCoTGenerator()
    
    print("🔍 調試單一原告案例")
    print("=" * 60)
    
    # 步驟1: 分句分析
    sentences = re.split(r'[。]', test_case)
    print("1. 句子分析:")
    
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
                    print(f"     模式 '{pattern}' 匹配: {potential_plaintiff}")
                    if processor._is_valid_plaintiff_name(potential_plaintiff):
                        plaintiff = potential_plaintiff
                        print(f"     ✅ 有效原告: {plaintiff}")
                        break
                    else:
                        print(f"     ❌ 無效原告: {potential_plaintiff}")
            
            if not plaintiff:
                print("     ❌ 未識別到原告，此句會被跳過")
    
    print(f"\n2. 實際提取結果:")
    result = processor._extract_damage_items_from_text(test_case)
    print(f"   結果: {result}")

if __name__ == "__main__":
    debug_single_plaintiff()