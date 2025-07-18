# 06_批量處理與生成 腳本整理指南

## 📋 腳本分類與用途

### 🔥 **核心主要腳本** (建議保留)

| 腳本名稱 | 用途 | 狀態 | 優先級 |
|---------|------|------|--------|
| `KG_700_CoT_Final.py` | **最終版CoT生成器** - 整合所有功能 | ✅ 最新 | 🔥 必須 |
| `structured_legal_amount_processor.py` | **結構化金額處理器** - 解決計算問題 | ✅ 最新 | 🔥 必須 |
| `legal_amount_standardizer.py` | **金額標準化器** - 基礎金額處理 | ✅ 穩定 | 🔥 必須 |
| `robust_case_type_updater.py` | **案件分類批量更新器** - 已完成2995案例 | ✅ 完成 | 🔥 必須 |
| `auto_updater.py` | **自動重啟監控器** - 斷點續傳 | ✅ 實用 | 🔥 必須 |
| `quick_status.py` | **快速狀態檢查** - 監控進度 | ✅ 實用 | 🔥 必須 |

### 📊 **批量處理腳本** (選擇性保留)

| 腳本名稱 | 用途 | 建議 |
|---------|------|------|
| `KG_690_Patch_Compensation_To_Chunks.py` | 賠償金額補丁 | 🟡 保留 - 可能需要 |
| `KG_695_Patch_CaseType_FromLawyerInput_Optimized.py` | 案件類型補丁(優化版) | 🟡 保留 - 主要版本 |
| `KG_700_BatchExcel_v9_clean.py` | Excel批量處理 | 🟡 保留 - 如需Excel功能 |
| `enhanced_compensation_updater.py` | 增強版賠償更新器 | 🟡 保留 - 可能有用 |

### 🧪 **測試和分析腳本** (可刪除)

| 腳本名稱 | 用途 | 建議 |
|---------|------|------|
| `analyze_calculation_error.py` | 分析計算錯誤 | ❌ 可刪 - 臨時分析 |
| `compare_cot_versions.py` | 版本比較 | ❌ 可刪 - 臨時測試 |
| `test_amount_solutions.py` | 金額解決方案測試 | ❌ 可刪 - 臨時測試 |
| `test_classification_accuracy.py` | 分類準確性測試 | ❌ 可刪 - 臨時測試 |
| `test_hybrid_integration.py` | 混合集成測試 | ❌ 可刪 - 臨時測試 |
| `test_imports.py` | 導入測試 | ❌ 可刪 - 臨時測試 |
| `test_legal_provisions.py` | 法條測試 | ❌ 可刪 - 臨時測試 |
| `test_reclassify.py` | 重分類測試 | ❌ 可刪 - 臨時測試 |
| `test_reclassify_100.py` | 100案例測試 | ❌ 可刪 - 臨時測試 |
| `test_updater.py` | 更新器測試 | ❌ 可刪 - 臨時測試 |

### 🗂️ **舊版本腳本** (可刪除)

| 腳本名稱 | 用途 | 建議 |
|---------|------|------|
| `KG_700_CoT_Enhanced.py` | CoT增強版 | ❌ 可刪 - 已被Final版取代 |
| `KG_700_CoT_Hybrid.py` | CoT混合版 | ❌ 可刪 - 已被Final版取代 |
| `KG_700_CoT_Standalone.py` | CoT獨立版 | ❌ 可刪 - 舊版本 |
| `KG_700_CoT_Debug.py` | CoT調試版 | ❌ 可刪 - 調試用 |
| `KG_700_CoT_SingleTest.py` | CoT單一測試 | ❌ 可刪 - 測試用 |
| `KG_700_CoT_BatchProcessor.py` | CoT批量處理器 | ❌ 可刪 - 被Final版取代 |
| `KG_700_v8_CoT_Integration.py` | CoT集成v8版 | ❌ 可刪 - 舊版本 |
| `KG_700_BatchSemanticSearcher_v5_with_dual_prompt_and_case_type.py` | 語義搜索v5 | ❌ 可刪 - 舊版本 |
| `KG_700_BatchSemanticSearcher_v6.py` | 語義搜索v6 | ❌ 可刪 - 舊版本 |
| `KG_700_BatchSemanticSearcher_v7_for_excel.py` | 語義搜索v7 | ❌ 可刪 - 舊版本 |
| `KG_695_Simple_CaseType_Patcher.py` | 簡單案件分類補丁 | ❌ 可刪 - 被優化版取代 |
| `robust_amount_processor.py` | 強健金額處理器 | ❌ 可刪 - 被結構化版本取代 |
| `improved_compensation_calculator.py` | 改進版賠償計算器 | ❌ 可刪 - 被Final版取代 |

### 🔍 **檢查和診斷腳本** (可刪除)

| 腳本名稱 | 用途 | 建議 |
|---------|------|------|
| `check_actual_es_status.py` | ES狀態檢查 | ❌ 可刪 - 功能重複 |
| `check_es_case_types.py` | ES案件類型檢查 | ❌ 可刪 - 功能重複 |
| `check_es_status.py` | ES狀態檢查 | ❌ 可刪 - 功能重複 |
| `check_missing_values.py` | 缺失值檢查 | ❌ 可刪 - 臨時分析 |
| `check_special_types.py` | 特殊類型檢查 | ❌ 可刪 - 臨時分析 |
| `diagnose_embedding_space.py` | 嵌入空間診斷 | ❌ 可刪 - 臨時分析 |
| `diagnose_es.py` | ES診斷 | ❌ 可刪 - 臨時分析 |
| `detailed_es_check.py` | 詳細ES檢查 | ❌ 可刪 - 臨時分析 |

### 📂 **日誌和進度檔案** (可保留或清理)

| 檔案類型 | 建議 |
|---------|------|
| `*.log`, `*.txt` | 🟡 看需要 - 保留最新的幾個 |
| `*.pkl` | 🟡 看需要 - 保留重要的進度檔案 |
| `*.json` | 🟡 看需要 - 保留統計資料 |

## 🗑️ **建議刪除清單**

```bash
# 測試腳本
rm analyze_calculation_error.py
rm compare_cot_versions.py
rm test_amount_solutions.py
rm test_classification_accuracy.py
rm test_hybrid_integration.py
rm test_imports.py
rm test_legal_provisions.py
rm test_reclassify.py
rm test_reclassify_100.py
rm test_updater.py

# 舊版本腳本
rm KG_700_CoT_Enhanced.py
rm KG_700_CoT_Hybrid.py
rm KG_700_CoT_Standalone.py
rm KG_700_CoT_Debug.py
rm KG_700_CoT_SingleTest.py
rm KG_700_CoT_BatchProcessor.py
rm KG_700_v8_CoT_Integration.py
rm KG_700_BatchSemanticSearcher_v5_with_dual_prompt_and_case_type.py
rm KG_700_BatchSemanticSearcher_v6.py
rm KG_700_BatchSemanticSearcher_v7_for_excel.py
rm KG_695_Simple_CaseType_Patcher.py
rm robust_amount_processor.py
rm improved_compensation_calculator.py

# 檢查腳本
rm check_actual_es_status.py
rm check_es_case_types.py
rm check_es_status.py
rm check_missing_values.py
rm check_special_types.py
rm diagnose_embedding_space.py
rm diagnose_es.py
rm detailed_es_check.py

# 舊日誌（保留最新的）
rm test_100_cases_log.txt
rm test_reclassify_100_20250617_085758.txt
rm test_reclassify_100_20250617_090111.txt
rm reclassify_errors_20250617_091014.txt
rm reclassify_log_20250617_091014.txt
rm reclassify_log_20250617_093036.txt
rm robust_reclassify_20250617_100626.txt
rm special_reclassify_20250617_093824.txt
```

## 🎯 **最終建議保留的核心腳本**

1. `KG_700_CoT_Final.py` - 主要起訴狀生成器
2. `structured_legal_amount_processor.py` - 金額處理核心
3. `legal_amount_standardizer.py` - 金額標準化基礎
4. `robust_case_type_updater.py` - 案件分類更新
5. `auto_updater.py` - 自動監控重啟
6. `quick_status.py` - 狀態檢查
7. `KG_690_Patch_Compensation_To_Chunks.py` - 賠償補丁（如需要）
8. `KG_695_Patch_CaseType_FromLawyerInput_Optimized.py` - 案件類型補丁
9. `PROJECT_STATUS.md` - 項目狀態文檔
10. `continue_remaining_cases_progress.pkl` - 重要進度檔案

這樣可以從 64 個檔案減少到約 15-20 個核心檔案。