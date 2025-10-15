#!/usr/bin/env python3
"""測試金額驗證和修正功能"""
import re

def verify_and_fix_amount_calculations(result: str) -> str:
    """驗證並修正損害項目中的金額計算錯誤"""
    lines = result.split('\n')
    output_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 檢測包含細項明細的醫療費用行
        item_match = re.match(r'^(\d+)\.\s*(醫療費用|看護費用)：([\d,]+)元\s*$', line.strip())

        if item_match:
            item_num = item_match.group(1)
            item_name = item_match.group(2)
            claimed_amount = int(item_match.group(3).replace(',', ''))

            # 檢查下一行的描述中是否包含細項金額
            if i + 1 < len(lines):
                description = lines[i + 1]

                # 提取描述中的所有金額
                detail_amounts = re.findall(r'(\d+(?:,\d{3})*)元', description)

                if len(detail_amounts) > 1:  # 有多個細項金額
                    # 計算實際總額
                    actual_total = sum(int(amt.replace(',', '')) for amt in detail_amounts)

                    if actual_total != claimed_amount:
                        print(f"⚠️  發現金額計算錯誤：{item_name}")
                        print(f"   聲稱總額：{claimed_amount:,}元")
                        print(f"   實際總額：{actual_total:,}元（細項：{detail_amounts}）")
                        print(f"   差異：{abs(actual_total - claimed_amount):,}元")

                        # 修正標題行的金額
                        corrected_line = f"{item_num}. {item_name}：{actual_total:,}元"
                        output_lines.append(corrected_line)
                        print(f"✅ 已修正為：{actual_total:,}元")
                        i += 1
                        continue

        output_lines.append(line)
        i += 1

    return '\n'.join(output_lines)


# 測試案例
test_input = """（一）原告賴秀雲之損害：
1. 醫療費用：90,638元
原告賴秀雲因系爭車禍事故就醫，支出包含臺中榮民總醫院9,160元、高堂中醫診所44,628元、蕭永明骨科診所15,350元、新奇美診所4,100元等醫療費用。
2. 藥品及耗材費用：4,050元
原告賴秀雲因本次事故受有藥品及耗材費用4,050元。"""

print("測試案例：賴秀雲醫療費用")
print("="*60)
result = verify_and_fix_amount_calculations(test_input)

print("\n修正後結果：")
print("="*60)
for line in result.split('\n'):
    if '醫療費用' in line:
        print(f">>> {line}")

print("\n手動驗算：")
print("9,160 + 44,628 + 15,350 + 4,100 = 73,238元")
print("系統原本顯示：90,638元（錯誤）")
print("應修正為：73,238元")
