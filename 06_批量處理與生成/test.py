#!/usr/bin/env python3
"""
測試理由完整性的後處理機制
驗證每個損害項目都有完整的理由說明
"""

def test_reason_completeness():
    """測試理由完整性"""
    print("📝 測試理由完整性後處理機制")
    print("=" * 80)
    
    # 導入修復後的生成器
    import re
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    
    # 測試案例：包含詳細理由的損害描述
    test_comp_facts = """
    1. 醫療費用182,690元：
    原告因本件車禍受傷，於南門醫院、雲林基督教醫院就醫治療，支出醫療費用共計182,690元。
    
    2. 看護費用246,000元：
    原告因本件車禍受有重傷，需專人看護，支出看護費用246,000元。
    
    3. 交通費用10,380元：
    原告因本件車禍受傷就醫期間，支出交通費用10,380元。
    
    4. 醫療用品費用4,464元：
    原告因本件車禍受傷，需購買醫療用品，支出費用4,464元。
    
    5. 無法工作損失485,000元：
    原告於車禍發生時任職於凱撒大飯店股份有限公司房務部領班，工作內容為整理客房清潔衛生、更換床單棉被、打掃客房浴室廁所等。因本件車禍受傷，依雲林基督教醫院及南門醫院診斷書記載，需休養一年，致無法工作一年，依原告108年度薪資所得合計485,922元計算，請求無法工作損失485,000元。
    
    6. 精神慰撫金1,559,447元：
    原告因本件車禍受有上開重傷，且需多次手術治療，造成生活上極大不便及身心痛苦。原告為國中畢業，於車禍發生前從事凱撒大飯店房務部領班之工作，名下僅有房屋、土地各1筆，考量原告所受傷勢非輕、需長期治療及休養，且對其日常生活造成重大影響。
    """
    
    # 單一原告案例（1原告，2被告）
    parties = {
        "原告": "原告", 
        "被告": "徐金坤、尤彰寶", 
        "原告數量": 1, 
        "被告數量": 2
    }
    
    try:
        # 初始化生成器
        generator = HybridCoTGenerator()
        
        print("🧪 測試單一原告損害項目格式和理由完整性（含後處理）")
        print("-" * 60)
        
        result = generator._generate_llm_based_compensation(test_comp_facts, parties)
        
        print("生成結果：")
        print(result)
        
        # 分析結果
        lines = result.split('\n')
        damage_items = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 找到損害項目行
            if re.match(r'^[（(][一二三四五六七八九十][）)].*：.*元', line):
                item = {
                    'line': line,
                    'has_reason': False,
                    'reason_lines': []
                }
                
                # 檢查後續行是否有理由
                j = i + 1
                while j < len(lines) and not re.match(r'^[（(][一二三四五六七八九十][）)]', lines[j].strip()):
                    if lines[j].strip() and len(lines[j].strip()) > 10:
                        item['has_reason'] = True
                        item['reason_lines'].append(lines[j].strip())
                    j += 1
                
                damage_items.append(item)
            i += 1
        
        print(f"\n📊 分析結果：")
        print(f"總損害項目數：{len(damage_items)}")
        
        items_with_reason = [item for item in damage_items if item['has_reason']]
        items_without_reason = [item for item in damage_items if not item['has_reason']]
        
        print(f"有理由說明的項目：{len(items_with_reason)}")
        print(f"缺少理由的項目：{len(items_without_reason)}")
        
        if items_without_reason:
            print("\n❌ 缺少理由的項目：")
            for item in items_without_reason:
                print(f"   - {item['line']}")
        else:
            print("\n✅ 所有損害項目都有理由說明")
        
        # 檢查詳細資訊保留
        detail_keywords = ["南門醫院", "雲林基督教醫院", "凱撒大飯店", "房務部領班", "需休養一年"]
        found_details = [kw for kw in detail_keywords if kw in result]
        
        print(f"\n📋 詳細資訊保留檢查：")
        for keyword in detail_keywords:
            if keyword in result:
                print(f"✅ 找到：{keyword}")
            else:
                print(f"❌ 遺失：{keyword}")
        
        # 檢查格式問題
        format_issues = []
        if "（一）原告" in result and "損害：" in result:
            format_issues.append("❌ 發現錯誤的多原告格式")
        
        # 更精確地檢測被告損害錯誤格式
        import re
        defendant_damage_pattern = r'[（(][一二三四五六七八九十][）)].*被告.*[之的]損害：'
        if re.search(defendant_damage_pattern, result):
            format_issues.append("❌ 發現被告損害錯誤格式")
        
        print(f"\n🔍 格式檢查：")
        if format_issues:
            for issue in format_issues:
                print(issue)
        else:
            print("✅ 格式正確")
        
        # 綜合評估
        success = (len(items_without_reason) == 0 and 
                  len(found_details) >= 3 and 
                  len(format_issues) == 0)
        
        print(f"\n🎯 測試結果：")
        if success:
            print("🎉 理由完整性後處理機制測試通過！")
            print("✅ 格式簡潔且每項都有理由")
            print("✅ 保留了重要的詳細資訊")
            return True
        else:
            print("⚠️ 後處理機制需要調整")
            if items_without_reason:
                print(f"- {len(items_without_reason)}個項目缺少理由")
            if len(found_details) < 3:
                print(f"- 遺失了重要的詳細資訊")
            if format_issues:
                print(f"- 格式問題：{len(format_issues)}個")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_reason_completeness()