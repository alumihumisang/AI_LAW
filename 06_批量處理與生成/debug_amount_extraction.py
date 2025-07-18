#!/usr/bin/env python3
"""
調試金額提取問題
"""

def debug_amount_extraction():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    
    generator = HybridCoTGenerator()
    
    # 測試文本 - 使用實際的損害賠償內容
    compensation_text = """
查原告羅靖崴因系爭車禍受有前揭傷害而前往聯新醫院就診，有聯新醫院診斷證明書可作為證據，其因而支出醫療費用2,443元、交通費1,235元。
原告羅靖崴因本件事故受傷，需在家休養16日而無法工作，又原告羅靖崴每月工資應為37,778元，又依聯新醫院診斷證明書分別於110年12月4日及111年1月10日建議原告羅靖崴應休養3日及兩週，是原告羅靖崴應有17日不能工作，但原告羅靖崴僅請求16日工資損失，因此請求不能工作之損失20,148元
原告羅靖崴因本件車禍而受有頭部外傷併輕微腦震盪之傷害，影響日常生活甚鉅，於精神上可能承受之無形痛苦，故請求被告賠償10,000元精神慰撫金。

原告邱品妍因系爭車禍受有前揭傷害同樣前往聯新醫院醫治，有聯新醫院診斷證明書作為證據，其因而支出醫療費用57,550元、交通費22,195元。
另外原告邱品妍因本件事故受傷，需在家休養1月又28日而無法工作，又原告邱品妍每月工資為34,535元，又依聯新醫院診斷證明書分別於110年12月4日、111年12月6日、 110年12月17日、110年12月24日、111年1月10日持續建議休養1週至1個月，總計1個月又28日，其不能工作之損失應為66,768元。
另查系爭車輛，因被告之過失行為，受有交易上價值貶損33,000元及支出鑑定費3,000元，因此原告邱品妍向被告請求賠償之本件車輛交易價值減損及鑑定費共計36,000元。
原告邱品妍因本件車禍受有頭暈及頸部扭傷等傷害，影響其工作、生活之行動，於精神上造成無形痛苦，故請求被告連帶賠償60,000元精神慰撫金。
    """
    
    print("🧪 調試金額提取問題")
    print("=" * 80)
    
    try:
        # 手動計算正確總額
        expected_amounts = [2443, 1235, 20148, 10000, 57550, 22195, 66768, 33000, 3000, 60000]
        expected_total = sum(expected_amounts)
        print(f"📊 期望的金額列表: {expected_amounts}")
        print(f"📊 期望的總計: {expected_total:,}元")
        print()
        
        # 測試金額提取
        extracted_amounts = generator._extract_valid_claim_amounts(compensation_text)
        extracted_total = sum(extracted_amounts)
        print(f"🔍 提取到的金額: {extracted_amounts}")
        print(f"🔍 提取的總計: {extracted_total:,}元")
        print()
        
        # 比較分析
        if extracted_total != expected_total:
            print(f"❌ 金額提取錯誤！")
            print(f"   差額: {expected_total - extracted_total:,}元")
            
            # 找出缺失的金額
            missing = [amt for amt in expected_amounts if amt not in extracted_amounts]
            extra = [amt for amt in extracted_amounts if amt not in expected_amounts]
            
            if missing:
                print(f"   缺失金額: {missing}")
            if extra:
                print(f"   多餘金額: {extra}")
        else:
            print(f"✅ 金額提取正確！")
            
    except Exception as e:
        print(f"❌ 調試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_amount_extraction()