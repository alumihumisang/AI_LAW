# 起訴書CAG處理系統

這個腳本專門用於將你的起訴書Excel資料整合到CAG (Cache-Augmented Generation) 系統中，並執行KV-Encode來建立高效的法律問答系統。

## 🎯 主要功能

1. **Excel資料讀取**: 讀取包含事實、法條、賠償、結論四個工作表的Excel檔案
2. **自動問答對生成**: 基於起訴書內容自動生成法律領域問答對
3. **KV-Encode處理**: 將起訴書知識預處理為KV緩存，實現快速推理
4. **測試與評估**: 自動測試系統效能並生成報告

## 📋 系統需求

### 硬體需求
- **GPU**: 建議使用支援CUDA的GPU (8GB+ VRAM)
- **記憶體**: 至少16GB RAM
- **儲存**: 至少10GB可用空間

### 軟體需求
- Python 3.10+
- CUDA 11.8+ (如果使用GPU)

### 依賴套件
```bash
pip install pandas openpyxl torch transformers accelerate bitsandbytes python-dotenv
```

## 🔧 環境配置

1. **設置環境變數**:
   ```bash
   # 創建.env檔案
   echo "HF_TOKEN=your_huggingface_token" >> .env
   ```

2. **確認Excel檔案格式**:
   你的Excel檔案應該包含以下工作表：
   - `事實編輯`: 包含case_id和事實內容
   - `2995法條`: 包含case_id和法條內容
   - `2995賠償`: 包含case_id和賠償內容
   - `2995結論`: 包含case_id和結論內容

## 🚀 使用方法

### 基本使用
```bash
python indictment_cag.py --excel_path "整合_起訴書_2995_CAG用.xlsx"
```

### 完整參數說明
```bash
python indictment_cag.py \
    --excel_path "整合_起訴書_2995_CAG用.xlsx" \
    --max_knowledge 1000 \
    --max_questions 500 \
    --model_name "meta-llama/Llama-3.1-8B-Instruct" \
    --output_dir "./indictment_results" \
    --cache_path "./indictment_kv_cache.pt" \
    --test_questions 20
```

### 參數說明
- `--excel_path`: Excel檔案路徑 (必需)
- `--max_knowledge`: 最大起訴書數量 (預設: 全部)
- `--max_questions`: 最大問題數量 (預設: 100)
- `--model_name`: 使用的LLM模型 (預設: Llama-3.1-8B-Instruct)
- `--output_dir`: 輸出目錄 (預設: ./indictment_results)
- `--cache_path`: KV緩存保存路徑 (預設: 自動生成)
- `--test_questions`: 測試問題數量 (預設: 10)

## 📊 輸出內容

執行完成後，會在輸出目錄中生成以下檔案：

1. **`qa_pairs.json`**: 完整的問答對資料
2. **`test_results.json`**: 測試結果和效能指標
3. **`indictment_kv_cache.pt`**: KV緩存檔案
4. **日誌檔案**: 詳細的執行日誌

## 📈 效能指標

系統會自動評估以下指標：
- **平均回答時間**: 使用KV緩存的回答速度
- **KV緩存大小**: 預處理的token數量
- **問答對品質**: 生成的問答對數量和類型

## 🔍 問答對類型

系統會自動生成以下類型的問答對：

### 1. 事實相關問題
- "案件 XXX 的事故發生經過為何？"
- "請描述案件 XXX 的事實背景。"

### 2. 法條相關問題
- "案件 XXX 引用了哪些法條？"
- "請說明案件 XXX 的法律依據。"

### 3. 賠償相關問題
- "案件 XXX 的賠償項目有哪些？"
- "請列出案件 XXX 的損害賠償內容。"

### 4. 結論相關問題
- "案件 XXX 的結論為何？"
- "請說明案件 XXX 的最終結論。"

### 5. 綜合問題
- "請完整說明案件 XXX 的內容。"
- "案件 XXX 的重點為何？"

## 🎛️ 與原始CAG系統的比較

### 優勢
- **專門化**: 針對法律領域優化
- **自動化**: 自動生成問答對
- **高效**: 利用KV-Encode加速推理
- **獨立**: 不影響原始CAG代碼

### 效能預期
根據你的資料規模：
- **2995份起訴書**: 約164萬tokens
- **預期KV緩存大小**: ~200萬tokens
- **問答對數量**: 每份起訴書約15個問題 = 44,925個問答對
- **平均回答時間**: 預期0.5-2秒 (使用KV緩存)

## 🛠️ 故障排除

### 常見問題

1. **記憶體不足**
   ```bash
   # 減少批次大小
   python indictment_cag.py --excel_path "file.xlsx" --max_knowledge 500
   ```

2. **GPU記憶體不足**
   ```bash
   # 環境變數設置
   export CUDA_VISIBLE_DEVICES=0
   ```

3. **Excel檔案格式問題**
   - 確認工作表名稱正確
   - 確認每個工作表都有case_id欄位
   - 確認資料完整性

### 調試模式
```bash
# 開啟詳細日誌
python indictment_cag.py --excel_path "file.xlsx" --max_knowledge 10 --test_questions 5
```

## 📝 範例輸出

```json
{
  "question": "案件 001 的事故發生經過為何？",
  "expected_answer": "被告於2024年1月15日駕駛車輛...",
  "generated_answer": "根據起訴書內容，案件001的事故經過為...",
  "response_time": 0.85
}
```

## 🔮 進階功能

### 1. 自定義問題模板
你可以修改腳本中的`question_templates`來生成特定類型的問題。

### 2. 批次處理
```bash
# 處理多個Excel檔案
for file in *.xlsx; do
    python indictment_cag.py --excel_path "$file" --output_dir "./results_$(basename $file .xlsx)"
done
```

### 3. 效能調優
- 調整`max_new_tokens`控制回答長度
- 使用不同的模型進行比較
- 調整量化配置以平衡速度和品質

## 📞 支援

如果遇到問題，請檢查：
1. 環境變數是否正確設置
2. Excel檔案格式是否符合要求
3. 系統資源是否充足
4. 模型是否正確下載

## 🎉 完成後的下一步

1. **效能評估**: 比較與原始CAG系統的效能
2. **問答對優化**: 根據需求調整問題生成策略
3. **部署**: 將系統部署到生產環境
4. **擴展**: 添加更多法律領域的特殊功能

---

這個腳本為你的起訴書資料提供了完整的CAG整合解決方案，讓你能夠快速建立高效的法律問答系統！