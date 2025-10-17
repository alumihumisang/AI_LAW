#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試完整工作流程：姓名修正、僱傭關係偵測、細項保留"""

import sys
import os

# 將主程式加入路徑
sys.path.insert(0, os.path.dirname(__file__))

from KG_700_CoT_Hybrid import (
    extract_parties,
    detect_special_relationships,
    determine_applicable_laws
)

# 測試文本 - 來自使用者的實際案例
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

# 另一個測試案例：羅靖崴（測試姓名截斷修正）
test_text_truncation = """
原告羅靖崴於110年6月18日駕駛車輛，遭被告撞擊受傷。原告邱品妍亦在車上受傷。
被告應負賠償責任。
"""

print("=" * 80)
print("測試1：僱傭關係偵測與法條適用")
print("=" * 80)

# 測試當事人提取
print("\n1. 提取當事人...")
parties = extract_parties(test_text)
print(f"原告：{parties.get('原告', [])}")
print(f"被告：{parties.get('被告', [])}")

# 測試關係偵測
print("\n2. 偵測特殊關係...")
relationships = detect_special_relationships(test_text, parties)
for rel_type, detected in relationships.items():
    status = "✅" if detected else "❌"
    print(f"{status} {rel_type}: {detected}")

# 測試法條判定
print("\n3. 判定適用法條...")
applicable_laws = determine_applicable_laws(test_text, "", "", parties)
print(f"適用法條：{applicable_laws}")

if "民法第188條第1項本文" in applicable_laws:
    print("✅ 正確適用僱傭關係法條（188條）")
else:
    print("❌ 錯誤：應適用188條但實際適用了其他法條")

print("\n" + "=" * 80)
print("測試2：姓名截斷修正（羅靖崴）")
print("=" * 80)

parties_truncation = extract_parties(test_text_truncation)
print(f"原告：{parties_truncation.get('原告', [])}")

if "羅靖崴" in parties_truncation.get('原告', []):
    print("✅ 姓名修正成功：'羅靖崴' 正確提取")
else:
    print(f"❌ 姓名修正失敗：預期 '羅靖崴'，實際 {parties_truncation.get('原告', [])}")

print("\n" + "=" * 80)
print("測試完成")
print("=" * 80)
