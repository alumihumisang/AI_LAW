# AI_LAW

此專案保存交通事故民事起訴書生成研究程式與實驗資料。最新主線是
`new_kg` 內的 SDKG/XRAG 流程；其他資料夾多為早期知識圖譜、CAG、
批次格式修正、論文章節與口試材料。

## Current Main Path

- `new_kg/`: 目前論文主線，包含布林特徵、嚴重度分數、雙向樹檢索、
  批次生成與評估。
- `new_kg/web_indictment_generator.py`: 給網頁後端呼叫的單筆起訴書生成
  wrapper。
- `new_kg/api_server.py`: 可選 FastAPI server，提供 `/generate` endpoint。
- `06_批量處理與生成/`: 舊版起訴書批次格式化與金額修正工具。
- `AI_CAG/`: 早期 CAG 實驗與測試，非目前網頁串接主線。
- `09_輸入輸出資料/`: 原始與中間資料。此類資料可能含個資或案件內容，
  對外協作前需去識別化。

## Local Requirements

主要 pipeline 目前依賴：

- Python 3.10+
- `numpy`
- `requests`
- `openpyxl`
- Ollama server: `http://localhost:11434/api/generate`
- 預設模型: `gemma3:27b`

若要啟動 API server，另需：

- `fastapi`
- `uvicorn`

## Single-Case Generation

```python
from new_kg.web_indictment_generator import generate_indictment

result = generate_indictment(
    query_text="一、事故發生緣由...\n二、受傷情形...\n三、請求賠償的事實根據...",
    category="",
    experiment="FC-H",
    top_k=8,
)

print(result["generated_text"])
```

## API Server

```bash
uvicorn new_kg.api_server:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Generate:

```bash
curl -X POST http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d @docs/sample_generate_request.json
```

## Collaboration Notes

不要直接把完整起訴書 Excel、`.env`、大型生成輸出或模型 cache 給前端協作者。
網頁開發只需要：

- API endpoint 規格
- 去識別化測試輸入
- 範例輸出 JSON
- 本 repo 中的 wrapper/API server 程式

更多說明見 `docs/WEB_HANDOFF.md` 與 `docs/CODEBASE_MAP.md`。
