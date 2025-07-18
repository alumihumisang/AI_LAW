#!/usr/bin/env python3
"""
Debug理由完整性函數
"""

from KG_700_CoT_Hybrid import HybridCoTGenerator

def test_reason_function():
    generator = HybridCoTGenerator()
    
    # 測試輸入
    test_text = """（一）醫療費用：182,690元
（二）看護費用：246,000元
原告因本件車禍受有重傷，需專人看護，支出看護費用246,000元。
（三）交通費用：10,380元
（四）醫療用品費用：4,464元
（五）無法工作損失：485,000元
（六）精神慰撫金：1,559,447元"""

    original_facts = """1. 醫療費用182,690元：
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
原告因本件車禍受有上開重傷，且需多次手術治療，造成生活上極大不便及身心痛苦。原告為國中畢業，於車禍發生前從事凱撒大飯店房務部領班之工作，名下僅有房屋、土地各1筆，考量原告所受傷勢非輕、需長期治療及休養，且對其日常生活造成重大影響。"""

    print("🧪 測試理由完整性函數")
    print("=" * 60)
    print("輸入文本：")
    print(test_text)
    print("\n" + "=" * 60)
    
    result = generator._ensure_reason_completeness(test_text, original_facts)
    
    print("第一步（理由完整性）結果：")
    print(result)
    print("\n" + "-" * 60)
    
    # 測試_remove_conclusion_phrases
    cleaned_result = generator._remove_conclusion_phrases(result)
    
    print("第二步（清理結論語言）結果：")
    print(cleaned_result)
    print("\n" + "=" * 60)
    
    # 檢查是否有改進
    input_lines = test_text.split('\n')
    output_lines = result.split('\n')
    
    print(f"輸入行數：{len(input_lines)}")
    print(f"輸出行數：{len(output_lines)}")
    print(f"增加行數：{len(output_lines) - len(input_lines)}")

if __name__ == "__main__":
    test_reason_function()