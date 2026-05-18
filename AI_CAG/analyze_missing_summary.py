#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析為什麼沒有生成綜上所陳段落
"""

def analyze_missing_summary():
    """分析綜上所陳缺失的問題"""
    
    print("=" * 80)
    print("🔍 分析綜上所陳缺失問題")
    print("=" * 80)
    
    # 用戶提供的結果
    user_result = """（一）醫療復健費用：662,640元
原告乙○○、丙○○因被告之過失致受有傷害，為治療上開傷勢而支出醫療費用，

（二）工作損失：249,840元
原告乙○○因傷無法工作達6個月

（三）精神慰撫金：2,300,000元
原告丙○○因被告之侵權行為導致顱內出血及顏面骨折，有頭疼、頭暈且記憶力減退之後遺症等現象，均影響生活、工作及女生外貌甚鉅，導致精神痛苦不堪，爰請求精神賠償新台幣300,000元。原告乙○○因被告之侵權行為而導致下腹部挫傷合併恥骨骨折、卵巢破裂合併內出血等傷害，已切除卵巢百分之50且可能導致終生不孕，生育對多數女性而言乃視為極為重要之天職，若無法生孕，甚至可能造成婚姻之不幸福及家庭之缺憾，因而使原告極其痛苦，爰請求精神撫慰金新台幣2,000,000元。"""
    
    print("📋 用戶提供的結果分析:")
    
    # 檢查項目數量
    items = user_result.count('（')
    print(f"📊 項目數量: {items}個")
    
    # 檢查是否有綜上所陳
    has_summary = '綜上所陳' in user_result or '綜上' in user_result
    print(f"📝 是否有綜上所陳: {'有' if has_summary else '❌ 沒有'}")
    
    # 檢查描述完整性
    incomplete_descriptions = []
    if '為治療上開傷勢而支出醫療費用，' in user_result:
        incomplete_descriptions.append("醫療費用描述不完整 (以逗號結尾)")
    if '無法工作達6個月' in user_result and '元' not in user_result.split('無法工作達6個月')[1][:20]:
        incomplete_descriptions.append("工作損失描述不完整")
    
    print(f"📄 描述完整性問題:")
    for desc in incomplete_descriptions:
        print(f"   ❌ {desc}")
    
    print(f"\n🔍 問題分析:")
    print(f"1. 💰 金額識別問題:")
    print(f"   - 醫療費用: 662,640元 ✅")  
    print(f"   - 工作損失: 249,840元 ✅")
    print(f"   - 慰撫金: 2,300,000元 ✅")
    print(f"   - 但描述中提到: 300,000元 + 2,000,000元 = 2,300,000元")
    
    print(f"\n2. 📝 描述生成問題:")
    print(f"   - 醫療費用描述被截斷")
    print(f"   - 工作損失描述不完整") 
    print(f"   - 缺少總結段落")
    
    print(f"\n3. 🎯 核心問題:")
    print(f"   - 系統沒有生成完整的總結段落")
    print(f"   - 描述生成邏輯在某些情況下會截斷")
    print(f"   - 可能是模板生成邏輯的問題")
    
    print(f"\n💡 可能原因:")
    print(f"   1. 自適應方法對某些輸入格式處理不當")
    print(f"   2. 描述生成函數有bug")
    print(f"   3. 總結段落生成邏輯缺失")
    print(f"   4. 項目數量判斷邏輯有問題")

if __name__ == "__main__":
    analyze_missing_summary()