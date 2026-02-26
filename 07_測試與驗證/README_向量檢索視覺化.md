# 向量檢索視覺化工具使用說明

## 📊 功能說明

這個工具可以幫你視覺化 **query 向量在高維空間中如何找到最相似的 sentence embeddings**。

### 視覺化內容

1. **🎯 Query 點** (紅色星星) - 你輸入的查詢案情
2. **✅ Top-K 相似句子** (綠色圓點) - 從 ES 檢索到的最相似句子
3. **⚪ 背景資料點** (灰色小點) - 隨機抽樣的其他句子，用來對比
4. **🔗 箭頭連線** (橙色箭頭) - Query → Top-K 的相似度關係

### 降維方法

由於原始 embedding 是 **768 維**，無法直接視覺化，所以需要降維到 2D：

- **t-SNE**: 保留局部結構，適合觀察聚類效果
- **PCA**: 保留全局結構，適合觀察整體分布

---

## 🚀 使用方法

### 基本使用

```bash
cd /home/aru/AI_LAW/07_測試與驗證
python visualize_vector_retrieval.py
```

### 自訂 Query

編輯腳本最下方的 `example_query`，替換成你要測試的案情：

```python
example_query = """
你的案情描述...
"""

visualize_retrieval(
    query_text=example_query,
    top_k=5,              # 檢索前幾筆相似句子
    label="Facts",        # 檢索哪種類型 (Facts, Laws, Compensation...)
    method="tsne",        # 降維方法 ("tsne" 或 "pca")
    include_background=100  # 背景資料點數量
)
```

### 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `query_text` | 查詢的案情文字 | 必填 |
| `top_k` | 檢索前 K 筆相似句子 | 3 |
| `label` | ES 中的段落類型 | "Facts" |
| `method` | 降維方法 | "tsne" |
| `include_background` | 背景對比點數量 | 50 |

### 可用的 label 類型

- `"Facts"` - 事實段落
- `"Laws"` - 法條段落
- `"Compensation"` - 賠償段落
- `"Conclusion"` - 結論段落
- `"LawyerInput"` - 律師輸入段落
- `"LawyerInput_Cause"` - 事故原因段落
- `"LawyerInput_Effect"` - 事故結果段落

---

## 📈 輸出結果

### 1. 視覺化圖表

生成 `vector_retrieval_visualization_tsne.png` 或 `vector_retrieval_visualization_pca.png`

圖表包含：
- **座標軸**: t-SNE/PCA 降維後的 2D 座標
- **標註**: Query 和 Top-K 相似句子的文字片段
- **圖例**: 說明各種點的含義

### 2. 終端輸出

```
🔍 Query: 被告於民國110年8月18日晚間9時26分許...
📊 計算 query embedding...
🔎 從 ES 檢索 top-5 相似句子...
🎲 隨機抽樣 100 筆背景資料點...
📐 降維中... (使用 TSNE)
✅ 圖表已儲存至: vector_retrieval_visualization_tsne.png

================================================================================
📋 檢索結果詳情:
================================================================================

【Top-1】
案例 ID: 123
相似度分數: 1.8523
段落類型: Facts
內容: 緣被告雖持有車號000-0000號重型機車駕駛執照，惟該執照業因酒後駕車案件遭註銷...
--------------------------------------------------------------------------------

【Top-2】
案例 ID: 456
相似度分數: 1.7891
段落類型: Facts
內容: ...
```

---

## 🎨 視覺化範例解讀

### 理想的檢索結果

```
                背景點 ⚪
        背景點 ⚪      ⚪ 背景點
    ⚪
         Top-3 🟢 ←---- 🔴 Query
    ⚪    Top-2 🟢 ←----/
         Top-1 🟢 ←----/
    ⚪          ⚪ 背景點
        背景點 ⚪
```

**說明**：
- Top-K 相似句子應該距離 Query 很近（箭頭短）
- 背景點應該分散在較遠的地方
- 如果 Top-K 和背景點混在一起，表示檢索效果不佳

---

## 🔬 進階用法：比較降維方法

如果想同時看 t-SNE 和 PCA 的結果：

```python
compare_reduction_methods(example_query, top_k=3)
```

這會生成兩張圖，方便比較：
- `vector_retrieval_visualization_tsne.png`
- `vector_retrieval_visualization_pca.png`

### t-SNE vs PCA 選擇建議

| 場景 | 推薦方法 | 原因 |
|------|----------|------|
| 觀察相似句子的聚類效果 | t-SNE | 保留局部鄰近關係 |
| 觀察整體資料分布 | PCA | 保留全局變異方向 |
| 資料量很大 (>1000點) | PCA | t-SNE 計算較慢 |
| 需要可重複的結果 | PCA | t-SNE 有隨機性 |

---

## 🛠️ 依賴套件

腳本會自動使用 `.env` 中的設定，需要確保以下套件已安裝：

```bash
pip install numpy matplotlib scikit-learn transformers torch elasticsearch python-dotenv
```

---

## 📝 注意事項

1. **字體問題**: 如果中文顯示為方塊，需安裝中文字體：
   ```bash
   # macOS
   brew install font-noto-sans-cjk

   # Ubuntu/Debian
   sudo apt-get install fonts-noto-cjk
   ```

2. **ES 連線**: 確保 `.env` 中的 Elasticsearch 設定正確

3. **GPU 加速**: 如果有 CUDA GPU，模型會自動使用 GPU 加速

4. **記憶體**: 如果 `include_background` 設太大 (>500)，可能會消耗較多記憶體

---

## 🎯 使用場景

### 場景 1: 檢查檢索品質

當你想確認「系統是否真的找到相似案例」時，可以視覺化觀察：
- Top-K 句子是否真的靠近 Query
- 相似度分數是否反映實際距離

### 場景 2: 調整檢索策略

比較不同 `label` 類型的檢索效果：
```python
# 比較檢索 Facts vs LawyerInput
visualize_retrieval(query, label="Facts")
visualize_retrieval(query, label="LawyerInput")
```

### 場景 3: 偵錯向量化問題

如果發現檢索結果不佳，可以視覺化檢查：
- Query 向量是否異常孤立
- 相似句子是否形成明確的聚類

---

## 📧 問題排查

### 問題 1: "未找到相似句子"

**原因**: ES 中沒有對應 label 的資料

**解決**:
```python
# 檢查 ES 中有哪些 label
# 在 visualize_vector_retrieval.py 中加入:
body = {"size": 0, "aggs": {"labels": {"terms": {"field": "label"}}}}
response = requests.post(f"{ES_HOST}/{CHUNK_INDEX}/_search", auth=ES_AUTH, json=body, verify=False)
print(response.json()["aggregations"]["labels"]["buckets"])
```

### 問題 2: 圖表空白

**原因**: 降維失敗或資料點太少

**解決**: 增加 `include_background` 數量，確保至少有 50 個資料點

### 問題 3: 相似度分數都很低

**原因**: Query 向量與 ES 中的向量不在同一分布

**解決**: 確認 embedding 模型一致（都使用 `shibing624/text2vec-base-chinese`）

---

## 🚀 擴展功能建議

### 擴展 1: 3D 視覺化

修改降維參數為 `n_components=3`，使用 Plotly 繪製互動式 3D 圖

### 擴展 2: 動態探索

使用 Plotly Dash 創建 Web UI，讓使用者輸入 query 即時查看結果

### 擴展 3: 多 Query 比較

同時視覺化多個不同 query 的檢索結果，觀察向量空間的分布
