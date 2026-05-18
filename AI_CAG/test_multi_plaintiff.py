#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試多名原告按人分組功能
"""

from cag_indictment_generator import CAGIndictmentGenerator

def test_multi_plaintiff_grouping():
    """測試多名原告按人分組功能"""
    
    print("=" * 80)
    print("👥 測試多名原告按人分組功能")
    print("=" * 80)
    
    generator = CAGIndictmentGenerator()
    
    # 測試案例：仿照您提供的格式
    test_input = """一、事故發生緣由:
被告於111年10月28日駕駛汽車與原告林肜宇、原告吳彩雲發生交通事故。

二、原告受傷情形：
原告林肜宇受有頭部、左側手肘、膝部、足部、雙側手部挫擦傷、左側第六肋骨及肩胛骨閉鎖性骨折等傷害，需專人照顧2個月，薪資162,000元每月，足部受傷需搭乘計程車，機車受損。原告吳彩雲受有左側肩膀、手部、髖部及足部挫擦傷等傷害，任職於台鼎有限公司每月薪資30,000元，需請假3日。

三、請求賠償的事實根據：
原告林肜宇醫療費用20,185元、看護費用132,000元、工作損失324,000元、交通費用1,335元、車輛修復費用7,970元、慰撫金200,000元。原告吳彩雲醫療費用3,200元、工作損失3,000元、慰撫金50,000元。"""
    
    similar_cases = []
    legal_basis = "按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」民法第184條第1項前段定有明文。"
    
    print("📝 測試案例：雙原告車禍案件（林肜宇、吳彩雲）")
    print("-" * 60)
    
    try:
        result, gen_time = generator.generate_complete_indictment(
            test_input, similar_cases, legal_basis
        )
        
        print(f"\n✅ 生成成功 ({gen_time:.2f}秒)")
        print("\n📄 生成結果：")
        print("=" * 60)
        print(result)
        
        # 檢查格式是否符合要求
        print("\n🔍 格式檢查：")
        print("-" * 40)
        
        # 檢查關鍵格式要素
        has_plaintiff_grouping = "原告林肜宇之損害" in result or "原告吳彩雲之損害" in result
        has_numbered_items = "1. " in result and "2. " in result
        has_both_plaintiffs = "林肜宇" in result and "吳彩雲" in result
        has_individual_amounts = "20,185" in result and "3,200" in result  # 各自的醫療費用
        has_summary = "綜上所陳" in result
        
        print(f"   ✅ 按原告分組: {'是' if has_plaintiff_grouping else '❌ 否'}")
        print(f"   ✅ 項目編號格式: {'是' if has_numbered_items else '❌ 否'}")
        print(f"   ✅ 包含兩名原告: {'是' if has_both_plaintiffs else '❌ 否'}")
        print(f"   ✅ 個別金額正確: {'是' if has_individual_amounts else '❌ 否'}")
        print(f"   ✅ 包含總結: {'是' if has_summary else '❌ 否'}")
        
        score = sum([has_plaintiff_grouping, has_numbered_items, has_both_plaintiffs, has_individual_amounts, has_summary])
        print(f"\n📊 格式符合度: {score}/5 ({'優秀' if score >= 4 else '良好' if score >= 3 else '需改進'})")
        
        # 檢查是否符合您要求的具體格式
        print(f"\n🎯 格式對比分析：")
        print("-" * 40)
        
        expected_patterns = [
            "（一）原告.*之損害：",
            "（二）原告.*之損害：", 
            "1\\. 醫療費用：.*元",
            "2\\. .*費用：.*元",
            "原告.*因本次事故"
        ]
        
        import re
        pattern_matches = 0
        for pattern in expected_patterns:
            if re.search(pattern, result):
                pattern_matches += 1
                print(f"   ✅ 符合模式: {pattern}")
            else:
                print(f"   ❌ 缺少模式: {pattern}")
        
        print(f"\n📈 模式匹配: {pattern_matches}/{len(expected_patterns)}")
        
        return score >= 4 and pattern_matches >= 3
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_single_plaintiff_compatibility():
    """測試單一原告案件的向後相容性"""
    
    print("\n" + "=" * 80)
    print("👤 測試單一原告案件的向後相容性")
    print("=" * 80)
    
    generator = CAGIndictmentGenerator()
    
    test_input = """一、事故發生緣由:
被告駕駛車輛與原告發生交通事故。

二、原告受傷情形：
原告受有外傷。

三、請求賠償的事實根據：
原告主張醫療費用50,000元、慰撫金300,000元，總計350,000元。"""
    
    similar_cases = []
    legal_basis = "按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」民法第184條第1項前段定有明文。"
    
    print("📝 測試案例：單一原告案件")
    print("-" * 60)
    
    try:
        result, gen_time = generator.generate_complete_indictment(
            test_input, similar_cases, legal_basis
        )
        
        print(f"✅ 生成成功 ({gen_time:.2f}秒)")
        
        # 檢查是否使用標準格式（不是按原告分組）
        uses_standard_format = "（一）醫療費用" in result and "原告因本次事故" in result
        not_grouped_by_plaintiff = "原告之損害" not in result
        has_summary = "綜上所陳" in result
        
        print(f"🔍 相容性檢查：")
        print(f"   ✅ 使用標準格式: {'是' if uses_standard_format else '❌ 否'}")
        print(f"   ✅ 未誤用分組格式: {'是' if not_grouped_by_plaintiff else '❌ 否'}")
        print(f"   ✅ 包含總結: {'是' if has_summary else '❌ 否'}")
        
        compatibility_score = sum([uses_standard_format, not_grouped_by_plaintiff, has_summary])
        print(f"📊 相容性評分: {compatibility_score}/3")
        
        return compatibility_score >= 2
        
    except Exception as e:
        print(f"❌ 相容性測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 開始多名原告分組功能測試")
    
    # 測試1：多名原告分組
    test1_success = test_multi_plaintiff_grouping()
    
    # 測試2：單一原告相容性
    test2_success = test_single_plaintiff_compatibility()
    
    # 總結
    print("\n" + "=" * 80)
    print("🎉 測試總結")
    print("=" * 80)
    
    overall_success = test1_success and test2_success
    
    print(f"✅ 多名原告分組: {'通過' if test1_success else '失敗'}")
    print(f"✅ 單一原告相容性: {'通過' if test2_success else '失敗'}")
    print(f"🎯 總體結果: {'成功' if overall_success else '需要改進'}")
    
    if overall_success:
        print("\n🎊 恭喜！多名原告分組功能已成功實現！")
        print("   系統現在可以:")
        print("   • 自動檢測多名原告案件")
        print("   • 按照（一）原告XXX之損害格式分組")
        print("   • 為每個原告生成編號項目（1. 2. 3...）")
        print("   • 保持單一原告案件的標準格式")
        print("   • 生成完整的總結段落")
    else:
        print("\n⚠️ 功能仍需完善，建議檢查:")
        print("   • LLM 損害項目分析準確性")
        print("   • 格式輸出的一致性")
        print("   • 向後相容性保證")