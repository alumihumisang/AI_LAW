#!/usr/bin/env python3
"""
調試工作損失提取問題
"""

def debug_work_loss():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    import re
    
    # 包含工作損失的句子
    test_sentence = "（四）工作損失：350,000元\n原告因本次事故無法工作，受有薪資損失共計350,000元。"
    
    processor = HybridCoTGenerator()
    
    print("🔍 調試工作損失提取問題")
    print("=" * 60)
    print(f"測試句子: {test_sentence}")
    print()
    
    # 步驟1: 檢查原告識別
    sentences = re.split(r'[。]', test_sentence)
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
            
        amounts = re.findall(r'(\d+(?:,\d{3})*)\s*元', sentence)
        if amounts:
            print(f"句子 {i+1}: {sentence.strip()}")
            print(f"金額: {amounts}")
            
            # 檢查原告識別
            plaintiff = None
            if '原告' in sentence and ('因' in sentence or '支出' in sentence or '受有' in sentence or '產生' in sentence):
                plaintiff = "原告"
            
            print(f"原告: {plaintiff}")
            
            # 檢查工作損失關鍵詞
            keywords = ['工資損失', '薪資損失', '工作損失', '不能工作', '無法工作', '收入損失']
            found_keywords = []
            for keyword in keywords:
                if keyword in sentence:
                    found_keywords.append(keyword)
            
            print(f"工作損失關鍵詞: {found_keywords}")
            
            if found_keywords:
                # 檢查正則表達式
                pattern = r'(?:損失|請求|受有)\s*(\d+(?:,\d{3})*)\s*元'
                amount_match = re.search(pattern, sentence)
                print(f"正則匹配: {amount_match.group(1) if amount_match else None}")
            
            print()
    
    # 實際提取測試
    print("實際提取結果:")
    result = processor._extract_damage_items_from_text(test_sentence)
    print(f"結果: {result}")

if __name__ == "__main__":
    debug_work_loss()