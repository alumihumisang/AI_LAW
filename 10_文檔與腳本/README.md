# AI Law - 智能法律文件生成系統

一個基於AI技術的台灣交通事故起訴狀自動生成系統，結合知識圖譜、語義搜索和大型語言模型，為法律專業人士提供高效的文件撰寫解決方案。

## 🎯 專案概述

本系統專門針對台灣交通事故案件，能夠自動分析案件事實、傷害情形和賠償請求，通過檢索相似案例和適用法條，生成結構化的法律文件。系統採用RAG（檢索增強生成）技術，確保生成內容的法律準確性和專業性。

## ✨ 主要功能

- **🔍 智能案例檢索**: 基於語義相似度搜索歷史案例
- **⚖️ 自動法條匹配**: 根據案件特徵自動識別適用法條
- **📝 結構化文件生成**: 生成符合台灣法院格式的起訴狀
- **👥 多當事人支援**: 支援多原告、多被告複雜案件結構
- **🔄 品質控制循環**: 多輪迭代驗證確保輸出品質
- **📊 批量處理**: 支援Excel批量處理大量案件

## 🏗️ 系統架構

### 核心組件

```
AI Law System
├── 檢索系統 (ts_retrieval_system.py)     # 主要協調器
├── 資料存儲層
│   ├── Elasticsearch                      # 向量化法律文本
│   ├── Neo4j                             # 法律知識圖譜
│   └── 嵌入模型 (ts_models.py)           # 文本向量化
├── 提示工程 (ts_prompt.py)               # 模板化提示詞
├── 案件分析
│   ├── ts_define_case_type.py            # 案件類型分類
│   └── ts_input_filter.py                # 當事人資訊提取
└── 文件生成管道
    ├── ts_retrieve_main.py               # 互動式CLI
    ├── KG_800_Run.py                     # Excel批量處理
    └── KG_700_BatchSemanticSearcher_*.py # 進階批量處理
```

### 技術架構

- **🧠 大型語言模型**: Ollama + Llama-3-Taiwan
- **🔍 向量資料庫**: Elasticsearch (餘弦相似度搜索)
- **📊 圖形資料庫**: Neo4j (法律知識關係)
- **🎯 嵌入模型**: 中文text2vec模型
- **⚡ 框架**: LangChain (LLM協調)
- **🐍 程式語言**: Python 3.12+

## 🚀 快速開始

### 環境需求

- Python 3.12+
- Docker (用於Elasticsearch和Neo4j)
- Ollama (用於本地LLM推理)

### 安裝步驟

1. **克隆專案**
```bash
git clone <repository-url>
cd AI_law
```

2. **安裝依賴**
```bash
pip install poetry
poetry install
```

3. **啟動服務**
```bash
# 啟動Elasticsearch
docker run -d --name elasticsearch -p 9201:9200 -e "discovery.type=single-node" elasticsearch:8.8.0

# 啟動Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# 安裝並啟動Ollama
ollama serve
ollama pull kenneth85/llama-3-taiwan:8b-instruct-dpo
```

4. **配置環境變數**
```bash
cp .env.example .env
# 編輯.env文件，設置資料庫連接資訊
```

### 使用方式

#### 1. 互動式單案例處理
```bash
python ts_retrieve_main.py
```

#### 2. Excel批量處理
```bash
python KG_800_Run.py
```
輸入包含「律師輸入」欄位的Excel檔案路徑，系統將自動生成結果。

#### 3. 進階語義搜索
```bash
python KG_700_BatchSemanticSearcher_v6.py
```

## 📖 輸入格式

系統支援結構化輸入，格式如下：

```
一、事故發生緣由：
[描述交通事故發生的經過...]

二、原告受傷情形：
[描述原告的傷害情況...]

三、請求賠償的事實根據：
1. 醫療費用：50,000元
2. 精神慰撫金：100,000元
3. 工作損失：30,000元
...
```

## 🔧 系統配置

### 資料庫連接
在`.env`文件中配置以下參數：
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
ELASTIC_USER=elastic
ELASTIC_PASSWORD=your_password
```

### 模型設定
系統預設使用以下模型：
- **主要LLM**: kenneth85/llama-3-taiwan:8b-instruct-dpo
- **嵌入模型**: shibing624/text2vec-base-chinese
- **備用模型**: gemma2:2b (快速處理)

## 📊 資料處理流程

1. **輸入解析**: 將使用者輸入分解為事故事實、受傷情形、賠償請求三部分
2. **案件分類**: 自動判斷案件類型和當事人結構
3. **語義檢索**: 使用向量搜索找出相似案例
4. **法條檢索**: 從知識圖譜中提取適用法條
5. **品質控制**: 多輪驗證確保生成品質
6. **文件組裝**: 整合各部分生成完整起訴狀

## 🛠️ 核心模組說明

### ts_retrieval_system.py
主要協調器，負責：
- 整合所有子系統
- 管理生成流程
- 品質控制循環

### ts_models.py
模型管理，包含：
- 嵌入模型配置
- LLM連接設定
- 模型切換邏輯

### ts_prompt.py
提示詞工程，提供：
- 結構化提示模板
- 多場景適配
- 品質檢查提示

### Neo4j_manager_utils.py & Elasticsearch_utils.py
資料庫管理工具，負責：
- 資料庫連接管理
- 查詢優化
- 錯誤處理

## 📈 效能最佳化

- **並行處理**: 支援批量案件並行生成
- **快取機制**: 重複查詢結果快取
- **模型切換**: 根據需求自動選擇最適模型
- **記憶體管理**: 大批量處理時的記憶體優化

## 🔍 故障排除

### 常見問題

1. **Elasticsearch連接失敗**
   - 檢查Docker容器是否正常運行
   - 確認連接埠未被佔用

2. **Neo4j連接超時**
   - 驗證認證資訊是否正確
   - 檢查防火牆設定

3. **Ollama模型載入失敗**
   - 確認模型已正確下載
   - 檢查系統記憶體是否充足

### 記錄檔

系統產生的記錄檔：
- `embedding_log_*.txt`: 嵌入處理記錄
- `index_chunks_log_*.txt`: 索引建立記錄
- `neo4j_log_*.txt`: Neo4j操作記錄
- `vectorize_log_*.txt`: 向量化處理記錄

## 🤝 貢獻指南

1. Fork專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟Pull Request

## 📝 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 👥 開發團隊

- 主要開發者: alumihumisang <rita86822002@gmail.com>
- 專案維護: AI Law Development Team

## 📞 聯絡資訊

如有問題或建議，請透過以下方式聯絡：
- 電子郵件: rita86822002@gmail.com
- GitHub Issues: [專案Issues頁面]

## 🗺️ 未來規劃

- [ ] 支援更多法律領域案件
- [ ] 增加多語言支援
- [ ] 開發Web介面
- [ ] 整合更多LLM模型
- [ ] 效能最佳化和擴展性改進

---

**注意**: 本系統僅供法律專業人士參考使用，生成內容仍需人工審核確認。系統不承擔任何法律責任。