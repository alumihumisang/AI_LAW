#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試案件分類器整合到 CAG 系統
"""

from cag_indictment_generator import CAGIndictmentGenerator

def test_integrated_system():
    """測試整合案件分類器的 CAG 系統"""
    
    print("=" * 80)
    print("🧪 測試案件分類器整合到 CAG 系統")
    print("=" * 80)
    
    generator = CAGIndictmentGenerator()
    
    # 測試案例：多名原告案件
    test_input = """一、事故發生緣由:
被告於108年9月12日早上8時36分許，騎乘車牌號碼000-000號普通重型機車，沿新北市中和區華中橋行駛時，本應注意變換車道時，應讓直行車先行，並注意安全距離，竟疏未注意而貿然變換車道，致擦撞右側原告所騎乘之車牌000-0000號普通重型機車（下稱系爭車輛），造成原告人車倒地。

二、原告受傷情形：
原告乙○○、丙○○因被告之過失致受有傷害，為治療上開傷勢而支出醫療費用，原告乙○○因傷無法工作達6個月。原告丙○○因被告之侵權行為導致顱內出血及顏面骨折，有頭疼、頭暈且記憶力減退之後遺症等現象，均影響生活、工作及女生外貌甚鉅，導致精神痛苦不堪，爰請求精神賠償新台幣300,000元。原告乙○○因被告之侵權行為而導致下腹部挫傷合併恥骨骨折、卵巢破裂合併內出血等傷害，已切除卵巢百分之50且可能導致終生不孕，生育對多數女性而言乃視為極為重要之天職，若無法生孕，甚至可能造成婚姻之不幸福及家庭之缺憾，因而使原告極其痛苦，爰請求精神撫慰金新台幣2,000,000元。

三、請求賠償的事實根據：
原告主張醫療復健費用662,640元、工作損失249,840元、精神慰撫金2,300,000元，總計3,212,480元。"""
    
    similar_cases = []
    legal_basis = "按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」民法第184條第1項前段定有明文。"
    
    print("📝 測試案例：多名原告車禍案件")
    print("-" * 60)
    
    try:
        result, gen_time = generator.generate_complete_indictment(
            test_input, similar_cases, legal_basis
        )
        
        print(f"\n✅ 生成成功 ({gen_time:.2f}秒)")
        print("\n📄 生成結果：")
        print("-" * 40)
        print(result)
        
        # 檢查案件分類效果
        print("\n🔍 案件分類效果檢查：")
        print("-" * 40)
        
        # 檢查是否包含案件分類信息
        contains_case_type = "案件類型" in result or "當事人" in result
        contains_multiple_plaintiffs = "乙○○" in result and "丙○○" in result
        contains_compensation = "醫療" in result and "工作" in result and "慰撫金" in result
        contains_summary = "綜上所陳" in result
        
        print(f"   ✅ 包含案件分類信息: {'是' if contains_case_type else '否'}")
        print(f"   ✅ 正確處理多名原告: {'是' if contains_multiple_plaintiffs else '否'}")
        print(f"   ✅ 完整賠償項目: {'是' if contains_compensation else '否'}")
        print(f"   ✅ 包含綜上所陳: {'是' if contains_summary else '否'}")
        
        score = sum([contains_case_type, contains_multiple_plaintiffs, contains_compensation, contains_summary])
        print(f"\n📊 整合效果評分: {score}/4 ({'優秀' if score >= 3 else '需改進'})")
        
        return score >= 3
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_case_types():
    """測試不同類型的案件"""
    
    print("\n" + "=" * 80)
    print("🎯 測試不同類型案件的分類效果")
    print("=" * 80)
    
    generator = CAGIndictmentGenerator()
    
    # 測試案例集合
    test_cases = [
        {
            "name": "單純車禍案件",
            "input": """一、事故發生緣由:
被告駕駛汽車與原告機車發生碰撞。

二、原告受傷情形：
原告受有外傷。

三、請求賠償的事實根據：
原告主張醫療費用50,000元、慰撫金300,000元。"""
        },
        {
            "name": "僱用人責任案件", 
            "input": """一、事故發生緣由:
被告公司之受僱人張三在執行職務中駕駛公司貨車發生事故。

二、原告受傷情形：
原告受有重傷。

三、請求賠償的事實根據：
原告主張醫療費用100,000元、看護費用200,000元。"""
        },
        {
            "name": "未成年案件",
            "input": """一、事故發生緣由:
被告（未成年人，16歲）騎乘機車發生事故，其法定代理人為其父母。

二、原告受傷情形：
原告受有傷害。

三、請求賠償的事實根據：
原告主張損害賠償150,000元。"""
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 測試案例 {i}：{test_case['name']}")
        print("-" * 50)
        
        try:
            # 直接測試案件分類
            case_analysis = generator.case_classifier.analyze_case(test_case['input'])
            
            print(f"   案件類型: {case_analysis['case_type']}")
            print(f"   特殊特徵: {', '.join(case_analysis['special_characteristics'])}")
            print(f"   當事人數: 原告{case_analysis['parties']['原告數量']}人、被告{case_analysis['parties']['被告數量']}人")
            
            results.append({
                'name': test_case['name'],
                'case_type': case_analysis['case_type'],
                'success': True
            })
            
        except Exception as e:
            print(f"   ❌ 分類失敗: {e}")
            results.append({
                'name': test_case['name'],
                'case_type': 'ERROR',
                'success': False
            })
    
    # 總結
    success_count = sum(1 for r in results if r['success'])
    print(f"\n📊 案件分類測試總結:")
    print(f"   成功案例: {success_count}/{len(test_cases)}")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"   {status} {result['name']}: {result['case_type']}")
    
    return success_count == len(test_cases)

if __name__ == "__main__":
    print("🚀 開始案件分類器整合測試")
    
    # 測試1：整合效果
    test1_success = test_integrated_system()
    
    # 測試2：不同案件類型
    test2_success = test_different_case_types()
    
    # 總結
    print("\n" + "=" * 80)
    print("🎉 測試總結")
    print("=" * 80)
    
    overall_success = test1_success and test2_success
    
    print(f"✅ 整合測試: {'通過' if test1_success else '失敗'}")
    print(f"✅ 分類測試: {'通過' if test2_success else '失敗'}")
    print(f"🎯 總體結果: {'成功' if overall_success else '需要改進'}")
    
    if overall_success:
        print("\n🎊 恭喜！案件分類器已成功整合到 CAG 系統中！")
        print("   系統現在可以:")
        print("   • 自動識別案件類型（單純、多名原告/被告、特殊案型）")
        print("   • 提取當事人信息")
        print("   • 根據案件特徵優化生成策略")
    else:
        print("\n⚠️ 整合仍需完善，建議檢查:")
        print("   • LLM 連接狀態")
        print("   • 案件分類邏輯")
        print("   • 生成方法整合")