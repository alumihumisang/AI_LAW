# Web Handoff

本檔給負責網頁的協作者使用。網頁端只需要串接 API，不需要碰研究批次腳本或原始起訴書資料。

## Recommended Division

研究端負責：

- 維護 SDKG/XRAG 生成 pipeline。
- 提供 `/generate` API。
- 提供去識別化測試輸入與範例輸出。
- 確認模型、資料庫與檢索資料已在後端機器上準備好。

網頁端負責：

- 建立使用者輸入表單。
- 呼叫 `/generate`。
- 顯示生成中的 loading/error state。
- 顯示起訴書草稿，並提供複製或下載功能。

## Backend Setup

1. 確認 Ollama server 已啟動。

```bash
curl http://localhost:11434/api/tags
```

2. 確認模型已存在。

```bash
ollama pull gemma3:27b
```

3. 安裝 API 依賴。

```bash
pip install fastapi uvicorn numpy requests openpyxl
```

4. 從 repo root 啟動 API。

```bash
uvicorn new_kg.api_server:app --host 0.0.0.0 --port 8000
```

## Request

`POST /generate`

```json
{
  "query_text": "一、事故發生緣由：...\n二、原告受傷情形：...\n三、請求賠償的事實根據：...",
  "category": "",
  "query_id": "web-demo-001",
  "experiment": "FC-H",
  "top_k": 8,
  "model": "gemma3:27b",
  "llm_url": "http://localhost:11434/api/generate"
}
```

## Response

```json
{
  "generated_text": "完整起訴書草稿",
  "sections": {
    "facts": "一、...",
    "laws": "二、...",
    "damages": "（一）...",
    "conclusion": "（四）..."
  },
  "parties": {
    "原告": "原告",
    "被告": "被告",
    "原告數量": 1,
    "被告數量": 1
  },
  "retrieval": {
    "mode": "dual_tree",
    "experiment": "FC-H",
    "top_k": 8,
    "anchor_case_id": "123",
    "anchor_distance": 0.1,
    "similar_cases": []
  },
  "model": "gemma3:27b"
}
```

## Frontend Notes

- `generated_text` 是主要顯示內容。
- `sections` 可用於分段預覽或編輯。
- `retrieval.similar_cases` 只給除錯或研究展示，不一定要顯示給一般使用者。
- 第一次 request 會載入 corpus，可能比較慢；後續 request 會重用 cache。
- 若 API 回傳 500，多半是 Ollama/model 未啟動、檢索資料缺失或 GPU/記憶體問題。

## Data Sharing

請不要把完整真實資料交給前端開發。網頁開發階段只需要：

- 2 到 5 筆假資料或去識別化 query。
- 欄位格式。
- API response 範例。

真實 Excel、判決 PDF、起訴書原文、`.env`、生成批次輸出都應留在後端研究環境。
