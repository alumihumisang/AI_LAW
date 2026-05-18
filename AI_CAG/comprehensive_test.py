#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多階段CAG系統綜合測試腳本
測試不同類型的事故案例，評估系統性能
"""

import os
import sys
import json
import time
import pandas as pd
from pathlib import Path

# 設定當前目錄為工作目錄
os.chdir('/home/aru/AI_CAG/CAG_backup_20250725_044022')

# 導入CAG模組
from indictment_cag import load_model, prepare_indictment_kv_cache, generate_indictment_from_facts

def load_test_cases():
    """載入多種測試案例"""
    test_cases = [
        {
            "name": "追撞案例1 - 輕微傷害",
            "facts": """一、事故發生緣由：
被告於民國112年3月15日上午10時30分許，駕駛自用小客車沿台北市大安區仁愛路四段往東行駛。行經仁愛路四段與敦化南路一段路口時，因未注意前方車況，追撞原告所駕駛暫停等待號誌之車輛。

二、原告受傷情形：
原告因此車禍受有頸椎扭傷、腰部挫傷等傷害。原告於事故當日及112年3月16日、20日、27日至台大醫院門診就診。根據診斷證明書，原告需休養2週。

三、請求賠償的事實根據：
1. 醫療費用8,500元
2. 車輛修復費用45,000元
3. 交通費用2,800元
4. 工作收入損失21,000元
5. 精神慰撫金50,000元"""
        },
        {
            "name": "機車事故 - 重大傷害",
            "facts": """一、事故發生緣由：
被告於民國112年8月22日下午2時15分許，駕駛重型機車沿新北市板橋區中山路一段往南行駛。行經中山路與民生路交叉路口時，闖紅燈右轉，撞擊正依綠燈直行之原告機車。

二、原告受傷情形：
原告因此車禍受有左腿脛骨骨折、右手橈骨骨折、多處擦挫傷等重傷。原告於112年8月22日至112年10月15日住院治療，並接受2次手術。根據診斷證明書，原告需休養6個月。

三、請求賠償的事實根據：
1. 醫療費用350,000元
2. 機車修復費用28,000元
3. 看護費用180,000元
4. 工作收入損失240,000元
5. 精神慰撫金500,000元"""
        },
        {
            "name": "左轉事故 - 中等傷害",
            "facts": """一、事故發生緣由：
被告於民國112年6月8日晚間7時45分許，駕駛自用小客車沿高雄市左營區博愛二路往北行駛。行經博愛二路與民族一路交叉路口時，未禮讓對向直行車輛，貿然左轉，與原告駕駛之車輛發生碰撞。

二、原告受傷情形：
原告因此車禍受有胸部挫傷、右肩韌帶撕裂傷等傷害。原告於事故後持續至高雄榮總復健科治療，復健期間長達3個月。

三、請求賠償的事實根據：
1. 醫療復健費用95,000元
2. 車輛修復費用120,000元
3. 計程車費用15,000元
4. 工作收入損失90,000元
5. 精神慰撫金150,000元"""
        }
    ]
    return test_cases

def analyze_result(test_name, result, original_facts):
    """分析生成結果的品質"""
    analysis = {
        "test_name": test_name,
        "success": True,
        "issues": [],
        "strengths": [],
        "fact_preservation": {},
        "structure_check": {},
        "format_check": {}
    }
    
    # 檢查基本結構
    required_sections = ["similar_cases", "facts_section", "legal_section", 
                        "compensation_section", "conclusion_section"]
    
    for section in required_sections:
        if section in result and result[section] and "生成失敗" not in result[section]:
            analysis["structure_check"][section] = "✅ 正常"
        else:
            analysis["structure_check"][section] = "❌ 失敗"
            analysis["success"] = False
            analysis["issues"].append(f"{section} 段落生成失敗")
    
    # 檢查新格式要求
    full_text = result.get("full_indictment", "")
    
    # 檢查是否使用標準法律文書格式
    if "一、" in full_text and "二、" in full_text:
        analysis["format_check"]["standard_numbering"] = "✅ 使用標準編號格式"
        analysis["strengths"].append("符合標準法律文書編號格式")
    else:
        analysis["format_check"]["standard_numbering"] = "❌ 未使用標準編號"
        analysis["issues"].append("未使用標準「一、二、」編號格式")
    
    # 檢查賠償項目是否使用括號格式
    if "（一）" in full_text and "（二）" in full_text:
        analysis["format_check"]["compensation_format"] = "✅ 使用標準賠償格式"
        analysis["strengths"].append("賠償項目使用標準（一）（二）格式")
    else:
        analysis["format_check"]["compensation_format"] = "❌ 賠償格式不標準"
        analysis["issues"].append("賠償項目未使用標準括號格式")
    
    # 檢查是否以「綜上所陳」結尾
    if "綜上所陳" in full_text:
        analysis["format_check"]["conclusion_format"] = "✅ 使用標準結論開頭"
        analysis["strengths"].append("使用標準「綜上所陳」結論格式")
    else:
        analysis["format_check"]["conclusion_format"] = "❌ 結論格式不標準"
        analysis["issues"].append("未使用標準「綜上所陳」結論格式")
    
    # 檢查事實保護 - 提取原始金額
    import re
    original_amounts = re.findall(r'(\d+(?:,\d{3})*元)', original_facts)
    generated_text = str(result)
    
    for amount in original_amounts:
        if amount in generated_text:
            analysis["fact_preservation"][amount] = "✅ 保留"
        else:
            analysis["fact_preservation"][amount] = "❌ 遺失"
            analysis["issues"].append(f"金額 {amount} 未正確保留")
    
    # 檢查法條引用
    legal_text = result.get("legal_section", "")
    expected_laws = ["184", "191", "193", "195"]
    found_laws = [law for law in expected_laws if law in legal_text]
    
    if found_laws:
        analysis["strengths"].append(f"正確引用法條: {', '.join(found_laws)}")
    else:
        analysis["issues"].append("未找到標準法條引用")
    
    return analysis

def run_comprehensive_test():
    """運行綜合測試"""
    print("=== CAG系統綜合測試開始 ===\n")
    
    # 1. 載入模型
    print("🔧 載入模型...")
    try:
        load_model("gemma3:27b", use_ollama=True)
        print("✅ 模型載入成功\n")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return False
    
    # 2. 載入案例資料庫
    print("📚 載入案例資料庫...")
    try:
        excel_path = "整合_起訴書_2995_CAG用.xlsx"
        main_df = pd.read_excel(excel_path, sheet_name='事實編輯')
        
        documents = []
        for i in range(len(main_df)):
            full_document = str(main_df.iloc[i, 1]) if pd.notna(main_df.iloc[i, 1]) else ""
            if full_document.strip() and full_document != "nan":
                documents.append(full_document)
        
        print(f"✅ 載入 {len(documents)} 個案例")
        
        # 準備KV緩存
        kv_cache = prepare_indictment_kv_cache(documents, model_name="gemma3:27b")
        cache_size = len(str(kv_cache)) if isinstance(kv_cache, str) else "非字符串緩存"
        print(f"✅ KV緩存準備完成，大小: {cache_size} 字符\n")
        
    except Exception as e:
        print(f"❌ 資料庫載入失敗: {e}")
        return False
    
    # 3. 載入測試案例
    test_cases = load_test_cases()
    results = []
    
    print(f"🧪 開始測試 {len(test_cases)} 個案例...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 測試案例 {i}: {test_case['name']}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # 生成起訴書
            result = generate_indictment_from_facts(
                accident_facts=test_case["facts"],
                kv_cache=kv_cache,
                model_name="gemma3:27b"
            )
            
            generation_time = time.time() - start_time
            
            # 分析結果
            analysis = analyze_result(test_case["name"], result, test_case["facts"])
            analysis["generation_time"] = generation_time
            
            # 顯示結果摘要
            status = "✅ 成功" if analysis["success"] else "❌ 失敗"
            print(f"結果: {status} (耗時: {generation_time:.1f}秒)")
            
            # 顯示關鍵分析
            if analysis["strengths"]:
                print("💪 優點:")
                for strength in analysis["strengths"]:
                    print(f"   - {strength}")
            
            if analysis["issues"]:
                print("⚠️ 問題:")
                for issue in analysis["issues"]:
                    print(f"   - {issue}")
            
            # 顯示事實保護情況
            preservation_status = []
            for fact, status in analysis["fact_preservation"].items():
                preservation_status.append(f"{fact}: {status}")
            if preservation_status:
                print("💾 事實保護:", " | ".join(preservation_status))
            
            print()
            
            # 保存詳細結果
            result_with_analysis = {
                "test_case": test_case,
                "result": result,
                "analysis": analysis
            }
            results.append(result_with_analysis)
            
        except Exception as e:
            print(f"❌ 測試失敗: {e}")
            results.append({
                "test_case": test_case,
                "result": None,
                "analysis": {"success": False, "error": str(e)}
            })
            print()
    
    # 4. 保存結果並生成總結
    output_dir = Path("comprehensive_test_results")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "full_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 生成總結報告
    generate_summary_report(results, output_dir)
    
    print("=" * 60)
    print("🎯 測試完成！詳細結果已保存至 comprehensive_test_results/")
    return True

def generate_summary_report(results, output_dir):
    """生成總結報告"""
    successful_tests = [r for r in results if r["analysis"].get("success", False)]
    total_tests = len(results)
    success_rate = len(successful_tests) / total_tests * 100 if total_tests > 0 else 0
    
    # 統計平均時間
    avg_time = sum(r["analysis"].get("generation_time", 0) for r in results) / total_tests
    
    # 統計常見問題
    all_issues = []
    all_strengths = []
    for r in results:
        all_issues.extend(r["analysis"].get("issues", []))
        all_strengths.extend(r["analysis"].get("strengths", []))
    
    report = f"""# CAG系統綜合測試總結報告

## 🎯 測試概況
- **總測試數**: {total_tests}
- **成功率**: {success_rate:.1f}% ({len(successful_tests)}/{total_tests})
- **平均生成時間**: {avg_time:.1f}秒

## 📊 性能表現

### ✅ 系統優勢
"""
    
    # 統計最常見的優勢
    from collections import Counter
    strength_counts = Counter(all_strengths)
    for strength, count in strength_counts.most_common(5):
        report += f"- {strength} (出現 {count} 次)\n"
    
    report += "\n### ⚠️ 需要改善的問題\n"
    
    # 統計最常見的問題
    issue_counts = Counter(all_issues)
    for issue, count in issue_counts.most_common(5):
        report += f"- {issue} (出現 {count} 次)\n"
    
    report += "\n## 📋 各測試案例詳細結果\n\n"
    
    for i, result in enumerate(results, 1):
        test_name = result["test_case"]["name"]
        analysis = result["analysis"]
        status = "✅ 成功" if analysis.get("success", False) else "❌ 失敗"
        time_taken = analysis.get("generation_time", 0)
        
        report += f"### {i}. {test_name}\n"
        report += f"- **狀態**: {status}\n"
        report += f"- **耗時**: {time_taken:.1f}秒\n"
        
        if analysis.get("fact_preservation"):
            report += "- **事實保護**:\n"
            for fact, status in analysis["fact_preservation"].items():
                report += f"  - {fact}: {status}\n"
        
        if analysis.get("structure_check"):
            report += "- **結構檢查**:\n"
            for section, status in analysis["structure_check"].items():
                report += f"  - {section}: {status}\n"
        
        report += "\n"
    
    report += """
## 🎯 總結與建議

基於本次綜合測試，CAG系統整體表現：
"""
    
    if success_rate >= 80:
        report += "**優秀** - 系統穩定，可以投入實際使用"
    elif success_rate >= 60:
        report += "**良好** - 系統基本可用，需要針對性優化"
    else:
        report += "**需要改善** - 建議優先解決核心問題"
    
    # 保存報告
    with open(output_dir / "summary_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print("📊 測試總結:")
    print(f"   成功率: {success_rate:.1f}% ({len(successful_tests)}/{total_tests})")
    print(f"   平均時間: {avg_time:.1f}秒")
    if issue_counts:
        print(f"   主要問題: {issue_counts.most_common(1)[0][0]}")

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        if success:
            print("🎉 綜合測試順利完成！")
        else:
            print("❌ 測試過程中發生錯誤")
    except KeyboardInterrupt:
        print("\n⚠️ 測試被用戶中斷")
    except Exception as e:
        print(f"\n💥 測試發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc()