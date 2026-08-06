# Codebase Map

本檔用來快速判斷目前 AI_LAW 資料夾中哪些檔案是正式主線、哪些是歷史方法或實驗輸出。

## Recommended Entry Points

| Purpose | File |
| --- | --- |
| 網頁單筆生成 wrapper | `new_kg/web_indictment_generator.py` |
| 網頁 HTTP API | `new_kg/api_server.py` |
| SDKG/XRAG 批次生成實驗 | `new_kg/XRAG_query_generate.py` |
| SDKG 批次 top-k 實驗 runner | `new_kg/SDKG_run_50q_18exp_topk1to8.py` |
| 生成結果評估 | `new_kg/XRAG_evaluate_generation.py` |
| Phase 1 布林特徵與嚴重度 | `new_kg/XRAG_phase1_boolean_severity.py` |
| Phase 2 嚴重度雙樹 | `new_kg/XRAG_phase2_build_severity_trees.py` |

## Current Research Pipeline

1. `new_kg/XRAG_phase1_boolean_encode.py`
   - 從案件資料建立布林特徵。
2. `new_kg/XRAG_phase1_boolean_severity.py`
   - 依 Fact / Injury / Compensation 分級，輸出 `phase1_boolean_severity_v1.jsonl`。
3. `new_kg/XRAG_phase2_build_severity_trees.py`
   - 建立 LH/HL 嚴重度方向樹。
4. `new_kg/XRAG_query_generate.py`
   - 讀取 query、做 SDKG 檢索、呼叫 Ollama、產生起訴書。
5. `new_kg/XRAG_evaluate_generation.py`
   - 評估生成結果。

## Web Integration Layer

網頁不要直接呼叫 `XRAG_query_generate.py` 的 CLI。請改用：

- Python function: `new_kg.web_indictment_generator.generate_indictment`
- HTTP endpoint: `POST /generate` from `new_kg.api_server`

這樣前端只需要知道輸入文字與回傳 JSON，不需要理解實驗批次參數。

## Historical or Secondary Areas

| Folder | Status |
| --- | --- |
| `AI_CAG/` | 早期 CAG 研究與測試。保留作比較，不作為目前網頁主線。 |
| `03_知識圖譜建構/` | 舊版 Neo4j 知識圖譜建構流程。 |
| `04_向量化與索引/` | 舊版語義摘要與向量索引。 |
| `05_語義檢索與分析/` | 舊版 Elasticsearch 查詢與分析。 |
| `06_批量處理與生成/` | 起訴書格式化、金額處理、批次修正工具。可視需求抽部分邏輯。 |
| `07_測試與驗證/` | 測試與視覺化工具。 |
| `08_日誌與記錄/` | 執行紀錄，不應作為程式入口。 |
| `09_輸入輸出資料/` | 原始資料與中間 Excel，對外協作前需去識別化。 |

## Privacy Rules

- 不上傳新的 `.env`。
- 不上傳未去識別化起訴書、律師輸入、判決、Excel、PDF、Word、PPT。
- 不上傳大型生成結果、模型 cache、`.pt`、`.pkl`。
- 給網頁開發者的資料應使用 `docs/sample_generate_request.json` 類似格式，內容改成假資料或去識別化資料。
