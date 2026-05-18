#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終解決方案測試 - 驗證純文字項目識別能力
"""

from cag_indictment_generator import CAGIndictmentGenerator

def test_pure_text_classification():
    """測試純文字項目分類能力"""
    
    print("=" * 80)
    print("🎯 最終解決方案測試：純文字項目識別")
    print("=" * 80)
    
    # 測試案例1：複雜純文字描述
    complex_case = """原告因本次車禍事故受有腦震盪、右手骨折等傷害，至台大醫院急診治療費用8,500元，後續至長庚醫院復健治療費用15,200元。因傷勢嚴重無法工作，造成薪資損失156,000元。車輛受損嚴重需要修復，花費38,900元。為了就醫往返台北，交通費用累計5,600元。由於右手功能受損，需要看護協助日常生活，看護費用每月25,000元，共需要6個月，總計150,000元。預估未來復健費用需要200,000元。本案造成原告身心極大痛苦，精神受創嚴重，故請求慰撫金300,000元。"""
    
    generator = CAGIndictmentGenerator()
    
    print("📋 測試案例1：複雜純文字描述")
    categorized_items = generator._categorize_amounts_with_context(complex_case)
    
    expected_result = {
        '醫療費用': [8500, 15200],
        '看護費用': [150000],
        '交通費用': [5600], 
        '車輛修理費': [38900],
        '工作損失': [156000],
        '復健費用': [200000],
        '慰撫金': [300000]
    }
    
    print(f"\n✅ 分類結果驗證:")
    all_correct = True
    
    for expected_cat, expected_amounts in expected_result.items():
        actual_items = categorized_items.get(expected_cat, [])
        actual_amounts = [item['amount'] for item in actual_items]
        
        is_correct = set(actual_amounts) == set(expected_amounts)
        status = "✅" if is_correct else "❌"
        print(f"{status} {expected_cat}: 預期{expected_amounts}, 實際{actual_amounts}")
        
        if not is_correct:
            all_correct = False
    
    # 檢查是否有額外的錯誤分類
    all_expected_amounts = []
    for amounts in expected_result.values():
        all_expected_amounts.extend(amounts)
    
    all_actual_amounts = []
    for items in categorized_items.values():
        all_actual_amounts.extend([item['amount'] for item in items])
    
    extra_amounts = set(all_actual_amounts) - set(all_expected_amounts)
    if extra_amounts:
        print(f"❌ 額外錯誤分類: {extra_amounts}")
        all_correct = False
    
    print(f"\n📊 測試案例1結果: {'通過' if all_correct else '失敗'}")
    
    # 測試案例2：用戶原始文本
    original_text = """原告主張自系爭車禍發生已支出聯合醫院醫療費用460元、臺大醫院醫療費用81,356元、長庚醫院醫療費用2,290元、高雄義大醫院108年11月22日至109年4月24日醫療費用476,103元、高雄義大醫院109年7月17日至111年12月16日醫療費用53,804元、高雄義大醫院112年3月10日至112年6月9日醫療費用4,280元，以及原告因有持續復健需求，故支出物理矯正治療費用45,500元。根據義大醫院診斷證明書所載原告出院後「宜有專人協助生活照顧至少3個月」，故自車禍發生起由專人及家人照護共計178日，以全日照護費用每日2,200元計算，看護費用一共391,600元。原告前往高雄義大醫院就醫支出之交通費用、高速公路過路費用、油資共49,299元。系爭車禍導致機車受損，修理費用為50,250元。原告因系爭事故不能工作，而受有176日薪資損失即292,160元。原告因本件事故經醫院鑑定勞動能力減損76%，預計未來勞動力減損金額為新臺幣6,339,232元。並且原告至少需復健5年，未來需支出復健費用510,000元。查本件原告於事發時為21歲，職業為工程師，卻因被告之過失行為致受有系爭傷害，右臂神經叢損傷與右上肢失去功能，目前右上肢嚴重萎縮且領有身心障礙手冊，已嚴重影響生活及未來職涯，已如前述，足見原告身心確受有相當程度痛苦，因此請求慰撫金500,000元。"""
    
    print(f"\n📋 測試案例2：用戶原始文本")
    categorized_items2 = generator._categorize_amounts_with_context(original_text)
    
    # 檢查慰撫金是否只包含慰撫金
    consolation_items = categorized_items2.get('慰撫金', [])
    consolation_amounts = [item['amount'] for item in consolation_items]
    
    medical_items = categorized_items2.get('醫療費用', [])
    medical_amounts = [item['amount'] for item in medical_items]
    
    print(f"✅ 關鍵檢查:")
    print(f"   慰撫金項目: {consolation_amounts} (應該只有[500000])")
    print(f"   醫療費用項目數量: {len(medical_amounts)} (應該是7項)")
    print(f"   是否有雜項被分到慰撫金: {'否' if consolation_amounts == [500000] else '是'}")
    
    consolation_correct = consolation_amounts == [500000]
    medical_correct = len(medical_amounts) == 7
    
    case2_success = consolation_correct and medical_correct
    print(f"\n📊 測試案例2結果: {'通過' if case2_success else '失敗'}")
    
    # 整體結論
    overall_success = all_correct and case2_success
    print(f"\n🎉 整體測試結果: {'完全成功' if overall_success else '需要調整'}")
    
    if overall_success:
        print(f"""
✅ 系統已完全解決用戶問題：
   - 純文字項目能正確識別和分類
   - 各項費用不再混淆
   - 慰撫金只包含慰撫金
   - 醫療費用正確分離為獨立項目
   - 支持複雜的非結構化文本輸入
        """)
    
    return overall_success

if __name__ == "__main__":
    test_pure_text_classification()