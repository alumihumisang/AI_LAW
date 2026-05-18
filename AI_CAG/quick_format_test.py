#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速格式測試 - 驗證新的法律文書格式
"""

import os
import sys
import json
import time
import pandas as pd

# 設定當前目錄為工作目錄
os.chdir('/home/aru/AI_CAG/CAG_backup_20250725_044022')

# 導入CAG模組
from indictment_cag import load_model, prepare_indictment_kv_cache, generate_indictment_from_facts

def quick_format_test():
    """快速測試新格式"""
    print("=== 新格式快速測試 ===\n")
    
    # 載入模型
    try:
        load_model("gemma3:27b", use_ollama=True)
        print("✅ 模型載入成功")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return

    # 簡化的KV-Cache (只用前50個案例以加快速度)
    try:
        excel_path = "整合_起訴書_2995_CAG用.xlsx"
        main_df = pd.read_excel(excel_path, sheet_name='事實編輯')
        
        documents = []
        for i in range(min(50, len(main_df))):  # 只取前50個案例加快測試
            full_document = str(main_df.iloc[i, 1]) if pd.notna(main_df.iloc[i, 1]) else ""
            if full_document.strip() and full_document != "nan":
                documents.append(full_document)
        
        print(f"✅ 載入 {len(documents)} 個案例進行測試")
        
        kv_cache = prepare_indictment_kv_cache(documents, model_name="gemma3:27b")
        print(f"✅ KV緩存準備完成")
        
    except Exception as e:
        print(f"❌ 資料庫載入失敗: {e}")
        return

    # 測試案例
    test_facts = """一、事故發生緣由：
被告於民國105年4月12日13時27分許，駕駛租賃小客車沿新北市某區某路往富國路方向行駛。行經福營路342號前時，被告跨越分向限制線欲繞越前方由原告所駕駛併排於路邊臨時停車後適欲起駛之車輛。被告為閃避對向來車，因而駕車自後追撞原告駕駛車輛左後車尾。

二、原告受傷情形：
原告因此車禍受有左膝挫傷、半月軟骨受傷等傷害。原告於105年5月2日、7日、7月16日、8月13日、8月29日至醫院門診就診。根據醫院開立的診斷證明書，原告需休養1個月。

三、請求賠償的事實根據：
1. 醫療復健費用190元
2. 車輛修復費用181,144元
3. 交通費用4,500元
4. 休養期間工作收入損失33,000元
5. 慰撫金99,000元"""

    print("🧪 開始生成測試...")
    start_time = time.time()
    
    try:
        result = generate_indictment_from_facts(
            accident_facts=test_facts,
            kv_cache=kv_cache,
            model_name="gemma3:27b"
        )
        
        generation_time = time.time() - start_time
        print(f"✅ 生成完成 (耗時: {generation_time:.1f}秒)\n")
        
        # 分析格式
        full_text = result.get("full_indictment", "")
        
        print("📋 格式檢查結果:")
        print("-" * 50)
        
        # 檢查關鍵格式標記
        format_checks = [
            ("使用「一、」開頭", "一、" in full_text),
            ("使用「二、」標記", "二、" in full_text),
            ("使用賠償括號格式", "（一）" in full_text and "（二）" in full_text),
            ("使用「綜上所陳」結論", "綜上所陳" in full_text),
            ("沒有markdown符號", "**" not in full_text and "##" not in full_text)
        ]
        
        for check_name, passed in format_checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
        
        # 檢查事實保護
        print("\n💾 事實保護檢查:")
        print("-" * 50)
        amounts = ["190元", "181,144元", "4,500元", "33,000元", "99,000元"]
        
        for amount in amounts:
            preserved = amount in full_text
            status = "✅" if preserved else "❌"
            print(f"{status} {amount}: {'保留' if preserved else '遺失'}")
        
        # 顯示生成內容片段
        print("\n📄 生成內容預覽:")
        print("=" * 60)
        print(full_text[:800] + ("..." if len(full_text) > 800 else ""))
        print("=" * 60)
        
        # 保存結果
        with open("format_test_result.json", "w", encoding="utf-8") as f:
            json.dump({
                "test_facts": test_facts,
                "result": result,
                "generation_time": generation_time,
                "format_analysis": {name: passed for name, passed in format_checks}
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 詳細結果已保存至 format_test_result.json")
        
    except Exception as e:
        print(f"❌ 生成測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_format_test()