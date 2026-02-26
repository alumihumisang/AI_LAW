# AI_LAW 系統改進計畫

> 本文件記錄所有待實現的改進項目和想法
>
> 最後更新：2025-10-02

---

## 📋 待辦事項列表

### 🔴 高優先級

#### 1. 雙層級檢索架構與結構化信息提取 ⭐ NEW

**問題描述：**
- 目前的向量檢索是直接將所有文本句子級切分並向量化
- 缺乏段落級的完整語義
- 缺乏結構化信息的提取與利用
- 無法精準匹配特定類型的信息（如時間、地點、車輛信息等）

**新架構設計：**

**層級1：段落級索引** (`legal_kg_paragraphs_v2`)
```
7種段落類型：
1. indictment_fact (起訴書事實)
2. indictment_laws (起訴書法條)
3. indictment_compensation (起訴書賠償)
4. indictment_conclusion (起訴書結論)
5. lawyer_input_fact (律師輸入事實)
6. lawyer_input_injury (律師輸入傷害)
7. lawyer_input_compensation (律師輸入賠償)

每個段落包含：
- original_text: 完整原文
- paragraph_embedding: 段落向量
- structured_info: LLM提取的結構化信息（JSON）
```

**層級2：句子級結構化信息** (`legal_kg_sentences_v2`)
```
Facts段落提取：
- time_info: 時間資訊
- location_info: 地點資訊
- vehicle_info: 車輛資訊（含車牌）
- consequence_info: 傷害後果
- action_info: 行為描述
- witnesses: 證人
- weather_road_conditions: 天候路況

Compensation段落提取（動態列表）：
- expenses: [{category, item, amount, supporting_text}]
- total_claimed: 請求總額
- deductions: 扣除項目

Laws段落提取：
- applicable_laws: 適用法條列表
- law_reasoning: 法律推論
- liability_basis: 責任基礎

Conclusion段落提取：
- final_amount: 最終金額
- interest_rate: 利息
- litigation_costs: 訴訟費用
```

**檢索流程：**
```
階段1：段落級粗檢索
  用戶輸入 → 向量化 → 檢索相關段落（top-20）
  ↓
階段2：結構化過濾
  根據structured_info進行智能匹配
  例如：只取有nursing_expense的案例
  ↓
階段3：句子級精檢索
  從top-20的段落中，提取關鍵句子（top-10）
  結合structured_info進行排序
  ↓
階段4：混合rerank
  vector_score * 0.5 +
  structured_match_score * 0.3 +
  kg_similarity_score * 0.2
```

**實施步驟：**

1. **[已完成]** 設計ES索引mapping結構
   - 段落級索引設計
   - 句子級索引設計

2. **[已完成]** 實作LLM結構化信息提取
   - 腳本：`KG_560_extract_structured_info.py`
   - Facts提取（時間、地點、車輛等）
   - Compensation提取（動態列表避免null）
   - Laws提取（適用法條、推論）
   - Conclusion提取（金額、利息等）

3. **[進行中]** 向量化流程重構
   - 腳本：`KG_620_vectorize_paragraphs_v2.py`
   - 腳本：`KG_630_vectorize_sentences_v2.py`

4. **[待實作]** 智能匹配檢索函數
   ```python
   def retrieve_with_structured_filter(
       lawyer_input: str,
       paragraph_type: str,
       required_categories: List[str] = None
   ):
       """
       使用structured_info進行智能匹配的檢索

       Args:
           lawyer_input: 律師輸入文本
           paragraph_type: 段落類型（如"indictment_compensation"）
           required_categories: 必須包含的類別（如["medical", "nursing"]）

       Returns:
           過濾後的檢索結果
       """
       # 1. 段落級向量檢索（top-20）
       paragraph_results = es_search_paragraphs(
           query_text=lawyer_input,
           paragraph_type=paragraph_type,
           top_k=20
       )

       # 2. 結構化過濾
       if required_categories and paragraph_type == "indictment_compensation":
           filtered_results = []
           for result in paragraph_results:
               expenses = result["structured_info"].get("expenses", [])
               # 檢查是否包含所需的category
               result_categories = {exp["category"] for exp in expenses}
               if required_categories.issubset(result_categories):
                   filtered_results.append(result)
           paragraph_results = filtered_results

       # 3. 提取相關句子（從structured_info）
       sentences = []
       for result in paragraph_results:
           if paragraph_type == "indictment_compensation":
               for expense in result["structured_info"]["expenses"]:
                   if not required_categories or expense["category"] in required_categories:
                       sentences.append({
                           "case_id": result["case_id"],
                           "text": expense["supporting_text"],
                           "category": expense["category"],
                           "amount": expense["amount"]
                       })
           elif paragraph_type == "indictment_fact":
               info = result["structured_info"]
               # 提取關鍵信息句子
               for key in ["time_info", "location_info", "consequence_info"]:
                   if key in info and info[key]:
                       sentences.extend(info[key])

       # 4. 句子級rerank
       reranked = rerank_sentences_by_relevance(sentences, lawyer_input)

       return reranked[:10]  # 返回top-10
   ```

5. **[待實作]** 生成階段的prompt改進
   ```python
   generation_prompt = f"""
   請根據以下檢索結果撰寫起訴書。

   **嚴格規則**：
   1. 只使用檢索結果中實際出現的項目
   2. 不要添加檢索結果沒有的內容
   3. 不要猜測任何數字或事實

   檢索到的結構化信息：
   {structured_results}

   請撰寫：
   """
   ```

**相關檔案：**
- `04_向量化與索引/KG_560_extract_structured_info.py` - 結構化提取
- `04_向量化與索引/KG_620_vectorize_paragraphs_v2.py` - 段落向量化
- `04_向量化與索引/KG_630_vectorize_sentences_v2.py` - 句子向量化
- `KG_700_CoT_Hybrid.py` - 需修改檢索與生成邏輯

**預期效果：**
- ✅ 真正的雙層級檢索（段落+句子）
- ✅ 精準的結構化信息匹配
- ✅ 避免生成階段的hallucination
- ✅ 更靈活的檢索策略（可按category過濾）
- ✅ 更好的可解釋性（知道為何檢索到這個案例）

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

#### 2. 知識圖譜深度利用（老師建議）

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

##### 2.1 賠償生成加入同案型損害模式
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

##### 2.2 法條推理加入共現模式
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

##### 2.3 相似案例加入結構化得分
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

**相關檔案：**
- `KG_700_CoT_Hybrid.py:851` - `generate_smart_compensation()`
- `KG_700_CoT_Hybrid.py:585` - `determine_applicable_laws()`
- `KG_700_CoT_Hybrid.py:402` - `rerank_case_ids_by_paragraphs()`

---

#### 3. LawCluster - 法律領域感知的損害賠償項目分群演算法 ⭐ 創新研究

**研究動機：**
- 律師輸入通常是一大段無結構化文字，沒有明確分點
- 傳統分群方法（KMeans/GMM/DBSCAN）不理解法律領域特性
- 需要自動從文字中"發現"有哪些賠償項目，並精準分群

**核心創新點：**
1. **多模態特徵融合**：語義向量 + 金額特徵 + 法條先驗知識
2. **法律約束**：must-link（同原告同類項目）、cannot-link（不同原告分開）
3. **原告感知（Plaintiff-Aware）**：法律領域獨特需求
4. **自定義法律距離公式**：比傳統歐式距離更適合法律文本

**演算法設計：**

##### 階段1：智能切分（Segmentation）

**方案A：LLM語義切分**（快速原型）
```python
def segment_by_llm(raw_text):
    """
    用LLM將一大段文字切分成獨立的expense描述單元

    優點：
    - 實作簡單（10行代碼）
    - LLM理解語義，切分準確
    - 適合快速測試

    缺點：
    - 每次切分都要呼叫LLM（慢）
    - 格式可能不穩定
    - 難以調試
    """
    prompt = f"請將以下賠償請求文字切分成獨立的項目：\n{raw_text}"
    segments = ollama_call(prompt)
    return segments
```

**方案B：圖分群自動合併**（創新點，適合發paper）
```python
def segment_by_graph(raw_text):
    """
    混合切分 + 圖合併策略

    步驟：
    1. 按標點粗切成句子
    2. 建立句子圖（節點=句子，邊=相似度）
    3. Leiden圖分群（自動合併相關句子）
    4. 每個cluster即為一個expense項目

    優點：
    - 不依賴LLM（更快、更穩定）
    - 可調參數（threshold、resolution）
    - 可視化友善
    - 適合大批量處理

    缺點：
    - 需要igraph套件
    - 需要調參數
    """
    # 1. 粗切
    sentences = rough_split(raw_text)

    # 2. 建立句子圖
    graph = build_sentence_graph_with_adjacency(sentences)

    # 3. 圖分群
    clusters = leiden_clustering(graph)

    # 4. 合併
    segments = merge_clusters(clusters, sentences)

    return segments
```

##### 階段2：多模態特徵提取

```python
def extract_multimodal_features(sentence):
    """
    為每個句子提取多模態特徵
    """
    features = {
        # 1. 語義向量（768維）
        "embedding": text2vec_model.encode(sentence),

        # 2. 金額特徵
        "amount": extract_amount(sentence),  # 整數
        "amount_log": np.log10(amount) if amount > 0 else 0,  # log scale
        "has_amount": bool(amount > 0),

        # 3. 法律關鍵詞特徵（domain knowledge）
        "law_keywords": extract_law_keywords(sentence),
        # 返回：{"medical", "nursing"} 等類別

        # 4. 案件類型先驗
        "case_type": case_type,  # 從案件資訊獲取

        # 5. 原告ID
        "plaintiff_id": plaintiff_id,

        # 6. 句子位置特徵
        "position_in_text": sentence_index / total_sentences,
        "is_adjacent": True/False  # 是否與前句相鄰
    }
    return features

def extract_law_keywords(sentence):
    """
    基於法律領域知識的關鍵詞提取
    """
    keyword_categories = {
        "medical": ["醫療", "醫藥", "治療", "診療", "手術"],
        "nursing": ["看護", "照護", "護理", "照顧"],
        "transportation": ["交通", "往返", "計程車", "車資"],
        "income_loss": ["薪資", "工資", "收入", "工作"],
        "mental": ["精神", "慰撫", "痛苦"],
        "vehicle": ["車輛", "機車", "汽車", "維修"],
        "equipment": ["護具", "輔具", "器材", "義肢"]
    }

    found = set()
    for category, keywords in keyword_categories.items():
        if any(kw in sentence for kw in keywords):
            found.add(category)
    return found
```

##### 階段3：自定義法律相似度公式（核心創新）

```python
def compute_law_similarity(sent_i, sent_j, feat_i, feat_j):
    """
    創新的法律距離公式

    d_law(i,j) = α·d_semantic + β·d_amount + γ·d_legal - δ·penalty
    """

    # 1. 語義距離（基礎）
    d_semantic = 1 - cosine_similarity(feat_i["embedding"], feat_j["embedding"])

    # 2. 金額距離（創新：log scale + 相對差異）
    if feat_i["amount"] > 0 and feat_j["amount"] > 0:
        d_amount = abs(feat_i["amount_log"] - feat_j["amount_log"]) / 6
    else:
        d_amount = 1.0  # 無金額句子距離遠

    # 3. 法律特徵距離（domain knowledge）
    kw_i = feat_i["law_keywords"]
    kw_j = feat_j["law_keywords"]
    intersection = len(kw_i & kw_j)
    union = len(kw_i | kw_j)
    d_legal = 1 - (intersection / union if union > 0 else 0)

    # 4. 懲罰項（法律約束）
    penalty = 0

    # 懲罰4.1：cannot-link（不同原告）
    if feat_i["plaintiff_id"] != feat_j["plaintiff_id"]:
        penalty += 2.0  # 大懲罰，強制分開

    # 懲罰4.2：矛盾類型（如"醫療"vs"精神慰撫金"）
    if are_contradictory_types(kw_i, kw_j):
        penalty += 1.0

    # 懲罰4.3：金額差異過大（可能不同類別）
    if feat_i["amount"] > 0 and feat_j["amount"] > 0:
        ratio = max(feat_i["amount"], feat_j["amount"]) / \
                min(feat_i["amount"], feat_j["amount"])
        if ratio > 100:
            penalty += 0.5

    # 5. Bonus：相鄰句子（鼓勵合併）
    bonus = 0
    if feat_i["is_adjacent"]:
        bonus = 0.3

    # 6. 組合（可調整權重）
    α, β, γ, δ = 0.5, 0.2, 0.2, 0.1

    total_distance = α * d_semantic + β * d_amount + γ * d_legal + δ * penalty - bonus

    return max(0, total_distance)  # 確保非負
```

##### 階段4：圖建構與分群

```python
def build_law_graph(sentences, features):
    """
    建立法律感知的句子圖
    """
    import igraph as ig

    n = len(sentences)
    g = ig.Graph(n=n)

    edges = []
    weights = []

    # 計算所有句子對的相似度
    for i in range(n):
        for j in range(i+1, n):
            distance = compute_law_similarity(
                sentences[i], sentences[j],
                features[i], features[j]
            )

            similarity = 1 - distance

            # 只保留相似度高的邊（稀疏圖）
            if similarity > 0.3:
                edges.append((i, j))
                weights.append(similarity)

    g.add_edges(edges)
    g.es["weight"] = weights

    # 添加節點屬性（用於後處理）
    for i in range(n):
        g.vs[i]["sentence"] = sentences[i]
        g.vs[i]["plaintiff_id"] = features[i]["plaintiff_id"]
        g.vs[i]["amount"] = features[i]["amount"]

    return g

def constrained_clustering(graph):
    """
    約束引導的圖分群（創新核心）
    """
    # 1. 基礎Leiden分群（不需預設K值）
    base_clusters = graph.community_leiden(
        weights="weight",
        resolution=0.8,  # 調整分群粒度
        objective_function="modularity"
    )

    # 2. 應用法律約束（後處理）
    constrained_clusters = []

    for cluster in base_clusters:
        # 檢查：同一cluster不能有不同原告
        plaintiff_groups = {}
        for node_id in cluster:
            pid = graph.vs[node_id]["plaintiff_id"]
            plaintiff_groups.setdefault(pid, []).append(node_id)

        # 拆分混合了多個原告的clusters
        if len(plaintiff_groups) > 1:
            for pid, nodes in plaintiff_groups.items():
                constrained_clusters.append(nodes)
        else:
            constrained_clusters.append(cluster)

    # 3. 合併孤立節點
    refined = refine_singletons(constrained_clusters, graph)

    return refined
```

##### 階段5：結構化信息提取

```python
def extract_expense_from_cluster(cluster_sentences):
    """
    從cluster的句子中提取結構化expense信息
    """
    combined_text = "，".join(cluster_sentences)

    # 用LLM提取
    prompt = f"""
    請從以下文字中提取賠償項目的結構化信息：

    文字：{combined_text}

    請以JSON格式回答：
    {{
      "item": "項目名稱（保留原文，不要改寫）",
      "amount": 金額數字（整數）,
      "supporting_text": "完整描述句子"
    }}
    """

    response = ollama_call(prompt)
    expense = json.loads(response)

    return expense
```

**實作順序：**
1. **[現階段]** 實作方案A（LLM切分），快速測試效果
2. **[跟老師討論後]** 如果需要創新性，實作方案B（圖分群）
3. **[進階]** 實作對比實驗：KMeans vs GMM vs LawCluster
4. **[發Paper用]** 可視化、消融實驗、參數敏感度分析

**相關檔案：**
- `04_向量化與索引/law_cluster_core.py` - 核心LawCluster類別（待實作）
- `04_向量化與索引/test_law_cluster.py` - 測試腳本（待實作）
- `04_向量化與索引/visualize_clusters.py` - 可視化（待實作）
- `04_向量化與索引/benchmark_clustering.py` - 對比實驗（待實作）

**預期效果：**
- ✅ 自動從無結構文字中發現賠償項目
- ✅ 比傳統分群方法更準確（利用domain knowledge）
- ✅ 支援多原告案件（plaintiff-aware）
- ✅ 可調整、可解釋、可視化
- ✅ 論文創新點充足

---

### 🟢 低優先級 / 優化項目

#### 3. 案件分類優化

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

---

## ✅ 已完成項目

### 系統維護
- [x] 修復 Claude Code 自動更新問題（2025-10-02）
  - 升級從 1.0.123 → 2.0.1
  - 解決權限問題
  - 清理舊版本

---

## 📌 備註

- 本文件持續更新
- 新想法請直接加入對應優先級區塊
- 完成的項目移至「已完成項目」區

