#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試僱傭關係偵測"""

import re

# 測試文本
test_text = """
被告楊進傳於110年6月18日上午10時34分許，駕駛二牙堆高機（下稱系爭堆高機，為動力機械）一部，
在臺中市豐原區豐原大道6段外側車道行駛至該段地下道後，不當慢速行駛地下道路段，未開啟燈光，
無警示措施，適有原告莊士紘駕駛車牌號碼000-0000號自用小客車（下稱系爭汽車）搭載其母即原告
林淑玲在該地下道內同向在後，亦未注意車前狀況、未開啟頭燈、未與前車保持安全距離，撞擊前方
系爭堆高機尾部，致系爭堆高機往前旋轉後二根牙杈插入莊士紘所駕駛系爭汽車之車底，並將系爭汽
車推向地下道牆壁（下稱本件車禍），又被告楊進傳於本件車禍發生時（110年6月18日）係在執行其
駕駛堆高機之職務，且其係受雇於被告韓昇忠，被告韓昇忠對於被告楊進傳之駕駛行為，具有指揮、
監督之責任，應同負連帶賠償責任。
"""

# 僱傭關係模式
employment_patterns = [
    r'被告.*?僱用',
    r'被告.*?雇主',
    r'被告.*?受僱',
    r'受僱.*?被告',
    r'受雇.*?被告',  # 「受雇」也要支援
    r'僱用.*?被告',
    r'執行.*?職務',  # 支援「執行...職務」
    r'職務上.*?行為',
    r'公司車',
    r'被告.*?員工',
    r'被告公司.*?員工',
    r'係在執行',  # 「係在執行」
    r'指揮.*?監督',  # 「指揮、監督」
]

print("=" * 80)
print("測試僱傭關係偵測")
print("=" * 80)

matched_patterns = []
for pattern in employment_patterns:
    match = re.search(pattern, test_text)
    if match:
        matched_patterns.append((pattern, match.group(0)))
        print(f"✓ 匹配：{pattern}")
        print(f"  內容：{match.group(0)}")
        print()

if matched_patterns:
    print("=" * 80)
    print(f"✅ 偵測結果：有僱傭關係（匹配了 {len(matched_patterns)} 個模式）")
    print("=" * 80)
else:
    print("=" * 80)
    print("❌ 偵測結果：沒有僱傭關係")
    print("=" * 80)
