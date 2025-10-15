#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試結論段落生成 - 驗證不會使用錯誤的原告姓名
"""

from KG_700_CoT_Hybrid import HybridCoTGenerator

def test_conclusion_generation():
    """測試單一原告案件的結論不會出現錯誤姓名"""

    # 讀取測試案例
    with open('test_outsider_case.txt', 'r', encoding='utf-8') as f:
        lawyer_input = f.read()

    print("=" * 80)
    print("開始測試結論生成...")
    print("=" * 80)

    # 創建生成器
    generator = HybridCoTGenerator()

    # 生成完整起訴狀
    result = generator.generate_cot(lawyer_input)

    # 顯示結果
    print("\n" + "=" * 80)
    print("生成結果 - 結論段落:")
    print("=" * 80)

    # 提取結論段落（通常在最後）
    lines = result.split('\n')
    in_conclusion = False
    conclusion_lines = []

    for line in lines:
        if '綜上所陳' in line:
            in_conclusion = True
        if in_conclusion:
            conclusion_lines.append(line)
            if '利息' in line:
                break

    conclusion_text = '\n'.join(conclusion_lines)
    print(conclusion_text)

    # 驗證
    print("\n" + "=" * 80)
    print("驗證結果:")
    print("=" * 80)

    # 檢查是否出現錯誤的原告姓名
    wrong_names = ['林肜宇', '林彤宇', '吳彩雲']
    found_errors = []

    for name in wrong_names:
        if name in conclusion_text:
            found_errors.append(name)
            print(f"❌ 錯誤：發現不應出現的姓名 '{name}'")

    # 檢查單一原告案件是否使用了「就原告XXX部分」格式
    if '就原告' in conclusion_text and '部分' in conclusion_text:
        # 檢查是否為多原告情況
        if '；就原告' not in conclusion_text:  # 如果只有一個「就原告」
            print("❌ 錯誤：單一原告案件使用了多原告格式（就原告XXX部分）")
            found_errors.append("格式錯誤")

    if not found_errors:
        print("✅ 通過：結論段落格式正確，沒有錯誤的原告姓名")

    print("\n" + "=" * 80)
    print("完整起訴狀:")
    print("=" * 80)
    print(result)

    return len(found_errors) == 0

if __name__ == "__main__":
    success = test_conclusion_generation()
    exit(0 if success else 1)
