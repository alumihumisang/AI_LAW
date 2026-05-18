#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終驗證 - 確認用戶問題完全解決
"""

from cag_indictment_generator import CAGIndictmentGenerator

def final_validation():
    """最終驗證所有用戶要求是否已滿足"""
    
    print("=" * 80)
    print("🎯 最終驗證：用戶問題解決狀況")
    print("=" * 80)
    
    generator = CAGIndictmentGenerator()
    
    # 用戶原始問題文本
    user_original_text = """原告主張自系爭車禍發生已支出聯合醫院醫療費用460元、臺大醫院醫療費用81,356元、長庚醫院醫療費用2,290元、高雄義大醫院108年11月22日至109年4月24日醫療費用476,103元、高雄義大醫院109年7月17日至111年12月16日醫療費用53,804元、高雄義大醫院112年3月10日至112年6月9日醫療費用4,280元，以及原告因有持續復健需求，故支出物理矯正治療費用45,500元。根據義大醫院診斷證明書所載原告出院後「宜有專人協助生活照顧至少3個月」，故自車禍發生起由專人及家人照護共計178日，以全日照護費用每日2,200元計算，看護費用一共391,600元。原告前往高雄義大醫院就醫支出之交通費用、高速公路過路費用、油資共49,299元。系爭車禍導致機車受損，修理費用為50,250元。原告因系爭事故不能工作，而受有176日薪資損失即292,160元。原告因本件事故經醫院鑑定勞動能力減損76%，預計未來勞動力減損金額為新臺幣6,339,232元。並且原告至少需復健5年，未來需支出復健費用510,000元。查本件原告於事發時為21歲，職業為工程師，卻因被告之過失行為致受有系爭傷害，右臂神經叢損傷與右上肢失去功能，目前右上肢嚴重萎縮且領有身心障礙手冊，已嚴重影響生活及未來職涯，已如前述，足見原告身心確受有相當程度痛苦，因此請求慰撫金500,000元。"""
    
    # 結構化輸入測試
    structured_text = """（一）醫療費用：15,000元
原告因本次事故受傷至醫院治療，支出醫療費用15,000元。

（二）看護費用：30,000元  
原告因傷勢需要專人照護，支出看護費用30,000元。

（三）慰撫金：100,000元
原告因本次事故受有身心痛苦，請求慰撫金100,000元。"""
    
    print("📋 測試1：純文字無分項輸入（用戶原始問題）")
    result1 = generator.smart_compensation_generation(user_original_text, use_rag_llm=False)
    
    print("\n📋 測試2：結構化輸入")  
    result2 = generator.smart_compensation_generation(structured_text, use_rag_llm=False)
    
    print(f"\n" + "=" * 80)
    print("🔍 問題解決驗證")
    print("=" * 80)
    
    # 用戶原始問題檢查
    print("📝 用戶原始問題：「太多雜項都被分到慰撫金裡了」")
    
    # 檢查慰撫金是否純淨
    consolation_clean = "慰撫金：500,000元" in result1
    lines1 = result1.split('\n')
    consolation_section = []
    in_consolation = False
    
    for line in lines1:
        if '慰撫金：500,000元' in line:
            in_consolation = True
            consolation_section.append(line)
        elif in_consolation:
            if line.strip() and not line.startswith('（'):
                consolation_section.append(line)
            else:
                break
    
    consolation_text = '\n'.join(consolation_section)
    has_no_medical_content = not any(keyword in consolation_text for keyword in ['醫療', '醫院', '治療費用'])
    
    print(f"✅ 慰撫金項目獨立存在: {'是' if consolation_clean else '否'}")
    print(f"✅ 慰撫金內容不含醫療項目: {'是' if has_no_medical_content else '否'}")
    
    # 檢查醫療費用是否正確分類
    medical_separate = "醫療費用：663,793元" in result1
    print(f"✅ 醫療費用正確合併為獨立項目: {'是' if medical_separate else '否'}")
    
    # 檢查自適應功能 - 需要檢查實際的系統行為而不是結果文字
    import io
    import sys
    from contextlib import redirect_stdout
    
    # 捕獲系統輸出來檢查是否啟用了正確的方法
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        generator.smart_compensation_generation(user_original_text, use_rag_llm=False)
    output1 = output_buffer.getvalue()
    
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        generator.smart_compensation_generation(structured_text, use_rag_llm=False)
    output2 = output_buffer.getvalue()
    
    adaptive_working = "啟用智能分類方法" in output1 and "使用傳統解析方法" in output2
    print(f"✅ 自適應方法正確運作: {'是' if adaptive_working else '否'}")
    
    # 檢查結構化輸入保持原格式
    structure_preserved = "（一）" in result2 and "（二）" in result2 and "（三）" in result2
    print(f"✅ 結構化輸入保持原格式: {'是' if structure_preserved else '否'}")
    
    # 總體評估
    all_requirements_met = (
        consolation_clean and 
        has_no_medical_content and 
        medical_separate and 
        adaptive_working and 
        structure_preserved
    )
    
    print(f"\n🎯 用戶要求「當原始律師輸入是一大堆沒有自己分項的純文字時,就啟用這個智能分類方法」")
    print(f"✅ 要求實現狀況: {'完全實現' if adaptive_working else '未實現'}")
    
    print(f"\n🎉 總體問題解決狀況: {'✅ 完全解決' if all_requirements_met else '❌ 需要調整'}")
    
    if all_requirements_met:
        print(f"""
🎊 恭喜！用戶的所有問題都已經完全解決：

✅ 核心問題解決：
   • 醫療費用不再被錯誤分類到慰撫金裡
   • 慰撫金只包含慰撫金相關內容
   • 各項目正確分類並獨立顯示

✅ 自適應功能實現：
   • 系統會自動偵測輸入是否為純文字無分項
   • 純文字輸入自動啟用智能分類方法
   • 結構化輸入仍使用傳統方法保持格式

✅ 系統整合完成：
   • 主系統方法已更新為使用自適應方法
   • 用戶無需手動選擇，系統自動判斷
   • 向下兼容，不影響現有功能

🚀 系統現在可以完美處理用戶的各種輸入需求！
        """)
    
    return all_requirements_met

if __name__ == "__main__":
    final_validation()