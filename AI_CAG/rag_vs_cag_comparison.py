#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG vs CAG 賠償項目解析技術對比分析
"""

import re

def demonstrate_cag_rule_based_approach():
    """展示CAG規則式方法的限制"""
    
    # CAG系統使用的典型regex模式
    care_patterns = [
        r'看護費用(\d+萬\d{1,3}(?:,\d{3})*|\d+萬|\d{1,3}(?:,\d{3})*|\d+)元',
        r'照護費用(\d+萬\d{1,3}(?:,\d{3})*|\d+萬|\d{1,3}(?:,\d{3})*|\d+)元',
        r'請求看護費用(\d+萬\d{1,3}(?:,\d{3})*|\d+萬|\d{1,3}(?:,\d{3})*|\d+)元'
    ]
    
    # 測試案例
    test_cases = [
        # 簡單標準格式 - CAG能處理
        "看護費用50,000元",
        
        # 複雜描述 - CAG難以處理  
        "故自車禍發生起由專人及家人照護共計178日，以全日照護費用每日2,200元計算，看護費用一共391,600元",
        
        # 非標準表達 - CAG無法處理
        "原告因傷勢嚴重，需要24小時專人協助日常生活，支出照顧費用總計80,000元",
        
        # 嵌入在長句中 - CAG容易遺漏
        "經醫院診斷需休養3個月，期間無法自理生活起居，家屬雇請看護人員協助，累計支出費用為120,000元，此有收據可證"
    ]
    
    print("=" * 80)
    print("🔧 CAG規則式方法測試")
    print("=" * 80)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n📝 測試案例 {i}: {text}")
        
        found = False
        for pattern in care_patterns:
            match = re.search(pattern, text)
            if match:
                print(f"✅ CAG找到: {match.group(1)}元")
                found = True
                break
        
        if not found:
            print("❌ CAG無法識別")

def demonstrate_rag_contextual_approach():
    """展示RAG上下文理解方法的優勢"""
    
    # RAG系統的關鍵詞+上下文分析
    valid_keywords = ['費用', '損失', '賠償', '支出', '花費', '照護', '看護', '協助']
    exclude_keywords = ['日薪', '收據', '可證', '每日', '計算式']
    
    test_cases = [
        "故自車禍發生起由專人及家人照護共計178日，以全日照護費用每日2,200元計算，看護費用一共391,600元",
        "原告因傷勢嚴重，需要24小時專人協助日常生活，支出照顧費用總計80,000元", 
        "經醫院診斷需休養3個月，期間無法自理生活起居，家屬雇請看護人員協助，累計支出費用為120,000元，此有收據可證"
    ]
    
    print("\n" + "=" * 80)
    print("🧠 RAG上下文理解方法測試")
    print("=" * 80)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n📝 測試案例 {i}: {text}")
        
        # 找出所有金額
        amounts = re.findall(r'(\d+(?:,\d{3})*)\s*元', text)
        
        for amt_str in amounts:
            amount = int(amt_str.replace(',', ''))
            
            # 找到金額在文本中的位置
            amount_pos = text.find(amt_str + '元')
            
            # 提取前後50字符的上下文
            start = max(0, amount_pos - 50)
            end = min(len(text), amount_pos + 50)
            context = text[start:end]
            
            # 檢查上下文
            has_valid_keyword = any(keyword in context for keyword in valid_keywords)
            has_exclude_keyword = any(keyword in context for keyword in exclude_keywords)
            
            # 特殊處理：看護相關即使有排除詞也接受
            if has_exclude_keyword and ('看護' in context or '照護' in context):
                has_exclude_keyword = False
            
            if has_valid_keyword and not has_exclude_keyword:
                print(f"✅ RAG識別: {amount:,}元 - 上下文: ...{context}...")
            elif has_exclude_keyword:
                print(f"🔍 RAG排除: {amount:,}元 - 包含排除詞: ...{context}...")
            else:
                print(f"❌ RAG跳過: {amount:,}元 - 無明確求償關鍵詞")

def demonstrate_llm_semantic_understanding():
    """展示LLM語義理解的最大優勢"""
    
    complex_text = """原告主張自系爭車禍發生已支出聯合醫院醫療費用460元、臺大醫院醫療費用81,356元、長庚醫院醫療費用2,290元、高雄義大醫院108年11月22日至109年4月24日醫療費用476,103元、高雄義大醫院109年7月17日至111年12月16日醫療費用53,804元，以及原告因有持續復健需求，故支出物理矯正治療費用45,500元。根據義大醫院診斷證明書所載原告出院後「宜有專人協助生活照顧至少3個月」，故自車禍發生起由專人及家人照護共計178日，以全日照護費用每日2,200元計算，看護費用一共391,600元。"""
    
    print("\n" + "=" * 80)
    print("🤖 LLM語義理解優勢展示")
    print("=" * 80)
    
    print("📝 複雜長段落文本:")
    print(complex_text[:200] + "...")
    
    print("\n🔧 CAG規則式方法會遇到的問題:")
    print("❌ 無法理解「宜有專人協助生活照顧至少3個月」與391,600元的關聯")
    print("❌ 可能錯誤識別「每日2,200元」為獨立項目")
    print("❌ 難以區分已支出vs預估費用")
    print("❌ 無法理解複雜的計算邏輯")
    
    print("\n🧠 RAG/LLM方法的優勢:")
    print("✅ 理解整個句子的語義結構")
    print("✅ 識別「每日2,200元」是計算基礎，391,600元才是實際求償")
    print("✅ 理解因果關係：診斷證明→需要照護→產生費用")
    print("✅ 能區分不同性質的費用（醫療、看護、復健）")

if __name__ == "__main__":
    demonstrate_cag_rule_based_approach()
    demonstrate_rag_contextual_approach()
    demonstrate_llm_semantic_understanding()