# AI_LAW 系統改進計畫

> 本文件記錄所有待實現的改進項目和想法
>
> 最後更新：2025-10-16

---

## 📋 待辦事項列表

### 🔴 高優先級

#### 1. 程式碼重構：模組化拆分（新增 2025-10-16）

**問題描述：**
- KG_700_CoT_Hybrid.py 已達 3,443 行，156KB
- 程式碼太長太亂，未來引進分群器會更難 debug
- 需要重構，拆分成多個模組

**建議的目錄結構：**

```
06_批量處理與生成/
├── main.py                          # 主程式（互動式界面）
│
├── modules/                         # 功能模組
│   ├── __init__.py
│   │
│   ├── party_extraction.py          # 當事人提取（優先級1）
│   │   ├── extract_parties()
│   │   ├── extract_parties_with_llm()
│   │   ├── parse_llm_parties_result()
│   │   └── verify_and_fix_party_names()
│   │
│   ├── case_retrieval.py            # 案例檢索（優先級1）
│   │   ├── embed()
│   │   ├── es_search()
│   │   ├── rerank_case_ids_by_paragraphs()
│   │   └── get_complete_cases_content()
│   │
│   ├── legal_analysis.py            # 法律關係分析（優先級1）
│   │   ├── detect_special_relationships()  ← 僱傭關係、動物案型偵測
│   │   ├── determine_case_type()
│   │   ├── determine_applicable_laws()     ← 法條選擇邏輯
│   │   └── normalize_article_number()
│   │
│   ├── text_processing.py           # 文字處理工具（優先級2）
│   │   ├── extract_sections()
│   │   ├── _preprocess_chinese_numbers()
│   │   ├── _split_compensation_facts_into_items()  ← 列表格式拆分
│   │   └── _fix_incomplete_sentences()             ← 修復「據。」
│   │
│   └── lawsuit_generator.py         # 起訴狀生成器（優先級3）
│       └── class HybridCoTGenerator  (~2000 行，保留完整)
│           ├── generate_standard_facts()
│           ├── generate_standard_laws()
│           ├── generate_smart_compensation()
│           └── generate_cot_conclusion_*()
│
└── utils/                           # 輔助工具（優先級2）
    ├── __init__.py
    ├── llm_client.py                # LLM 調用
    └── amount_utils.py              # 金額處理工具
```

**拆分的好處：**
1. 易於測試（可單獨測試每個模組）
2. 易於除錯（不用在 3443 行中找程式碼）
3. 易於擴展（未來引進分群器時更容易整合）
4. 程式碼重用（其他專案也可以使用）

**執行步驟：**

**階段 1：立即拆分（容易且影響大）** - 預估 2-3 小時
1. 創建目錄結構 `modules/` 和 `utils/`
2. 拆分 `party_extraction.py`（~200 行）
3. 拆分 `legal_analysis.py`（~200 行）← 最近修復的核心邏輯
4. 拆分 `case_retrieval.py`（~150 行）
5. 測試確保沒有破壞功能

**階段 2：中期拆分** - 預估 3-4 小時
6. 拆分 `text_processing.py`（~300 行）
7. 拆分 `llm_client.py`（~100 行）

**階段 3：保留在主文件（暫時不拆）**
8. `lawsuit_generator.py`（~2000 行）保留完整

**行動清單：**
- [ ] 決定採用方案 A（分階段）還是方案 B（一次性重構）
- [ ] Git commit 當前穩定版本
- [ ] 拆分 `party_extraction.py`
- [ ] 拆分 `legal_analysis.py`
- [ ] 拆分 `case_retrieval.py`
- [ ] 測試階段 1 的改動
- [ ] 拆分 `text_processing.py`
- [ ] 拆分 `llm_client.py`
- [ ] 測試階段 2 的改動

---

#### 2. 段落對稱性匹配問題

**問題描述：**
- 目前資料庫中的案例是以**段落級別** (paragraphs) 切分並向量化
- 但用戶輸入是**整段文本**直接向量化
- 造成不對稱的比對：長文本 vs 短段落

**目前流程：**
```
用戶輸入（整段） → 向量化 → 比對資料庫段落
```

**應改進為：**
```
用戶輸入（整段） → 切割段落 → 每段向量化 → 段落級比對
```

**實施方案：**
1. 在 `interactive_generate_lawsuit()` 中，對 `accident_facts` 進行段落切分
2. 對每個段落分別向量化
3. 用段落向量去檢索資料庫
4. 可選：使用 LLM 對每個段落生成 summary 後再向量化（提升語義理解）

**相關檔案：**
- `KG_700_CoT_Hybrid.py:2066` - 查詢向量化
- `KG_700_CoT_Hybrid.py:2084` - Rerank 函數
- `KG_700_CoT_Hybrid.py:402` - `rerank_case_ids_by_paragraphs()`

**預期效果：**
- ✅ 提升檢索精準度
- ✅ 更公平的相似度比對
- ✅ 更好的段落級語義匹配

---

### 🟡 中優先級

#### 3. 知識圖譜深度利用（老師建議）

**問題描述：**
老師指出「目前 RAG 中知識圖譜的善用，以及跟語意推理的關係應該要更深入設計，目前太薄弱」

**現狀分析：**

**已實現的知識圖譜功能：**
- ✅ 基礎圖譜查詢（1-2跳）
  - `Case -> Facts`
  - `Case -> Laws -> LawDetail`
- ✅ 法條使用頻率統計
- ✅ 向量檢索 + 圖譜結合

**已實現的語意推理：**
- ✅ 規則推理（案件分類、法條適用）
- ✅ Chain of Thought (CoT) 雙輪生成
- ✅ 條件判斷邏輯

**不足之處：**
- ❌ 缺乏深層圖譜推理（多跳推理）
- ❌ 圖譜資訊孤立，沒有充分利用拓樸結構
- ❌ 靜態查詢模式，無動態調整
- ❌ 知識融合不足（圖譜知識 + LLM 知識）

**改進方案（小改動、高效果）：**

##### 3.1 賠償生成加入同案型損害模式
```python
def get_case_type_damage_patterns(case_type: str, top_k: int = 5) -> List[str]:
    """查詢同案型的典型損害模式"""
    query = """
    MATCH (c:Case {case_type: $case_type})-[:包含]->(damage:Damage)
    RETURN damage.item_name, count(*) as frequency
    ORDER BY frequency DESC LIMIT $top_k
    """
    # 返回: ["醫療費", "車損", "工損", "慰撫金", "交通費"]
```
- 修改函數：`generate_smart_compensation()`
- 效果：賠償生成 = 個案事實 + 同類案例模式

##### 3.2 法條推理加入共現模式
```python
def get_law_co_occurrence(primary_laws: List[str]) -> Dict[str, int]:
    """查詢法條共現模式"""
    query = """
    MATCH (c:Case)-[:適用]->(l1:Laws), (c)-[:適用]->(l2:Laws)
    WHERE l1.name IN $primary_laws AND l1 <> l2
    RETURN l2.name, count(*) as co_count
    ORDER BY co_count DESC
    """
```
- 修改函數：`determine_applicable_laws()`
- 效果：如果適用184條，還能推薦常搭配的法條

##### 3.3 相似案例加入結構化得分
```python
def calculate_structural_similarity(case_id1: str, case_id2: str) -> float:
    """計算兩案例的結構相似度"""
    # 法條重疊度 + 案件類型 + 當事人結構 + 損害類型
    return (law_overlap * 0.4 +
            case_type_match * 0.3 +
            party_similarity * 0.2 +
            damage_similarity * 0.1)
```
- 修改函數：`rerank_case_ids_by_paragraphs()`
- 最終得分：`vector_score * 0.7 + structural_score * 0.3`
- 效果：混合向量相似度和圖譜結構相似度

**實施順序（漸進式）：**
1. 第一週：賠償模式注入（效果最明顯）
2. 第二週：法條共現推理
3. 第三週：結構化相似度

---

#### 4. 引進損害項目分群器（未來計畫）

**問題描述：**
- 目前依賴 prompt 和規則處理損害項目分類
- 不同輸入格式（列表 vs 段落）需要不同處理策略
- Prompt 優化是「無底洞」

**未來架構：**
```
輸入
  ↓
段落拆分 (text_processing.py)
  ↓
損害項目分類 (damage_classifier.py) ← 新模組（ML 模型）
  ↓
根據類別選擇模板 (template_selector.py) ← 新模組
  ↓
生成描述 (lawsuit_generator.py)
  ↓
後處理 (text_processing.py)
  ↓
輸出
```

**未來可能的新模組：**
- `modules/damage_classifier.py` - 損害項目分群器（ML 模型）
- `modules/template_selector.py` - 根據輸入格式選擇 prompt 模板
- `modules/evidence_analyzer.py` - 證據文件分析
- `utils/validation.py` - 輸出驗證工具

**Prompt 優化方向（等分群器後再處理）：**
1. **雙模板系統**
   - 結構化列表 → 使用「補充描述」模板
   - 非結構化段落 → 使用「完整保留」模板

2. **自適應 Prompt**
   - 先分析輸入特徵（簡短 vs 詳細）
   - 根據特徵動態調整 prompt

3. **為每種損害類型設計專門模板**
   - 醫療費用模板
   - 看護費用模板
   - 慰撫金模板

**⚠️ 注意**：建議先完成「程式碼重構」，再引進分群器

---

### 🟢 低優先級 / 優化項目

#### 5. 案件分類優化

**現狀：**
- 使用關鍵字規則判斷案件類型
- 當事人提取使用 LLM

**可選改進：**
- 擴展關鍵字庫（涵蓋更多同義詞）
- 分級關鍵字系統（高/中/低信心度）
- 組合條件判斷
- 模糊案例使用 LLM 輔助

**相關檔案：**
- `KG_700_CoT_Hybrid.py:523` - `detect_special_relationships()`
- `KG_700_CoT_Hybrid.py:563` - `determine_case_type()`

---

## 💡 想法池

> 這裡記錄尚未分類或待討論的想法

- [ ] 考慮加入時間、地點等 case_info 的提取
- [ ] 評估是否在生成階段也參考相似案例的賠償項目寫法
- [ ] 研究不同 LLM 模型的適用性（目前使用 Gemma3）

---

## ✅ 已完成項目

### 2025-10-16 修復
- [x] 僱傭關係偵測強化
  - 支援「受僱於XX即YY」格式
  - 支援「僱用人責任」關鍵字
  - 支援「執行業務」關鍵字
  - 修復：原告任職資訊不再干擾被告僱傭關係偵測

- [x] 動物案型法條選擇修復
  - 動物案型正確適用 §190（動物占有人責任）
  - 動物案型正確排除 §191-2（車輛責任）
  - 原因：動物不是車輛，侵權主體是動物而非車輛

- [x] 慰撫金拆分優化
  - 偵測「元。末查」等模式，確保慰撫金獨立拆分
  - 二次拆分邏輯：即使原文已分段，仍檢查慰撫金是否需要拆分
  - 確保慰撫金不會與其他項目混在一起

- [x] 列表格式處理
  - 自動偵測「1. 2. 3.」列表格式
  - 按照數字編號自動拆分成獨立項目
  - Prompt 加入簡短列表項的處理指引
  - 修復：損害項目描述不再全部混在一起

- [x] 不完整句子修復
  - 自動修復「據。」截斷 → 「有相關證明文件可資佐證。」
  - 自動修復「作為證。」截斷 → 「作為證據。」
  - 保留正確的「為證。」法律用語

### 2025-10-02 系統維護
- [x] 修復 Claude Code 自動更新問題
  - 升級從 1.0.123 → 2.0.1
  - 解決權限問題
  - 清理舊版本

---

## 📌 備註

### 重構注意事項
1. **先 Commit 穩定版**
   ```bash
   git add .
   git commit -m "重構前穩定版本 - 3443行單文件版本"
   ```

2. **每拆一個模組就測試**
   - 不要一次拆太多
   - 每拆完一個模組，就跑測試案例確認功能正常

3. **更新 Import**
   ```python
   # main.py
   from modules.party_extraction import extract_parties
   from modules.legal_analysis import detect_special_relationships, determine_applicable_laws
   from modules.lawsuit_generator import HybridCoTGenerator
   ```

4. **保留向後兼容**
   - 如果有其他腳本依賴 `KG_700_CoT_Hybrid.py`
   - 可以暫時保留舊文件，讓它 import 新模組
   - 等所有依賴都更新後，再刪除舊文件

### 當前狀態
- 本文件持續更新
- 新想法請直接加入對應優先級區塊
- 完成的項目移至「已完成項目」區
- 當前系統已經「可用」（金額正確、項目完整、法條正確）
- 重構目的是為了「可維護性」和「未來擴展性」
- 不急於一次完成，可以分階段進行

---

**最後更新**：2025-10-16
