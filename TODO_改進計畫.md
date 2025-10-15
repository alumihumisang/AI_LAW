# AI_LAW 系統改進計畫

> 本文件記錄所有待實現的改進項目和想法
>
> 最後更新：2025-10-02

---

## 📋 待辦事項列表

### 🔴 高優先級

#### 1. 段落對稱性匹配問題
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

