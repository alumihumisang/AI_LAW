# Detail節點重新設計方案

> 設計日期：2025-11-26
> 目標：將Detail節點從純文本轉換為結構化語義節點

---

## 🎯 設計原則

1. **結構化優先**：提取關鍵欄位，不只是存原文
2. **可檢索**：每個欄位都可以單獨查詢
3. **可計算**：數值、日期等可以用於統計和權重計算
4. **可推理**：欄位之間有語義關聯
5. **統一格式**：所有Detail節點遵循相同的設計模式
6. **🆕 句子級定位**：每個Detail節點記錄chunk_id，支援雙層檢索（段落→句子）

---

## 📊 統一的節點結構

### 通用欄位（所有Detail節點都有）

```json
{
  "case_id": "1",                    // 案件ID
  "node_type": "FactDetail",         // 節點類型
  "detail_type": "InjuryInfo",       // 細節類型

  // 🆕 句子級Chunk定位（支援雙層檢索）
  "chunk_id": "case_1_facts_chunk_5",        // 唯一chunk ID
  "chunk_text": "造成原告受有左膝挫傷併十字韌帶撕裂性骨折。",  // chunk原文（按句號切分）
  "chunk_index": 5,                  // 在父段落中的第幾個chunk (0-based)
  "parent_section": "事實概述",       // 來源段落類型 (事實概述|法條引用|損害賠償項目|結論)

  "raw_text": "造成原告受有左膝挫傷併十字韌帶撕裂性骨折。",  // 原始文本（等同chunk_text）
  "semantic_summary": "原告左膝嚴重骨折",    // Gemma生成的語義摘要
  "extracted_at": "2025-11-27",     // 提取時間
  "confidence": 0.95                 // 提取信心度 (0-1)
}
```

**Chunk ID命名規則**：
- 格式：`case_{case_id}_{section}_{chunk_index}`
- 範例：
  - `case_1_facts_chunk_0` - 案件1的事實概述第0個chunk
  - `case_1_laws_chunk_3` - 案件1的法條引用第3個chunk
  - `case_15_compensation_chunk_2` - 案件15的賠償項目第2個chunk

### 📦 Chunking策略（句子級切分）

**目標**：將段落文本切分成句子級chunk，每個Detail節點對應一個chunk

**切分規則**：只按**句號(。)**切分

**為何不用逗號或分號？**
- ✅ **句號**：保留完整語義單元，上下文完整（採用）
- ❌ **逗號**：過度碎片化（逗號數量是句號的2-5倍），LLM難以理解
- ❌ **分號**：起訴書中幾乎不使用（<2%）

```python
def chunk_by_sentence(text, case_id, section_name):
    """
    按句號切分段落成句子級chunk

    Args:
        text: 段落原文（如「事實概述」全文）
        case_id: 案件ID
        section_name: 段落名稱 (facts/laws/compensation/conclusion)

    Returns:
        list of dict: [{chunk_id, chunk_text, chunk_index}, ...]
    """
    import re

    # 按句號切分（保留標點）
    sentences = re.split(r'([。])', text)

    chunks = []
    chunk_index = 0

    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
        sentence = sentence.strip()

        if sentence and len(sentence) > 5:  # 過濾太短的句子
            chunks.append({
                'chunk_id': f'case_{case_id}_{section_name}_chunk_{chunk_index}',
                'chunk_text': sentence,
                'chunk_index': chunk_index,
                'parent_section': section_name
            })
            chunk_index += 1

    return chunks
```

**範例**：

```python
text = "被告騎乘車號000-0000號重型機車。該執照業因酒後駕車案件遭註銷。竟仍駕車行駛，於民國110年8月18日晚間9時26分許左轉。"

chunks = chunk_by_sentence(text, case_id="1", section_name="facts")

# 結果：
[
  {
    'chunk_id': 'case_1_facts_chunk_0',
    'chunk_text': '被告騎乘車號000-0000號重型機車。',
    'chunk_index': 0,
    'parent_section': 'facts'
  },
  {
    'chunk_id': 'case_1_facts_chunk_1',
    'chunk_text': '該執照業因酒後駕車案件遭註銷。',
    'chunk_index': 1,
    'parent_section': 'facts'
  },
  {
    'chunk_id': 'case_1_facts_chunk_2',
    'chunk_text': '竟仍駕車行駛，於民國110年8月18日晚間9時26分許左轉。',
    'chunk_index': 2,
    'parent_section': 'facts'
  }
]
```

**Section命名對照**：
| parent_section值 | Excel欄位 | 說明 |
|-----------------|----------|------|
| facts | 事實概述 | 事故經過、當事人行為 |
| laws | 法條引用 | 法律適用理由 |
| compensation | 損害賠償項目 | 賠償細項 |
| conclusion | 結論 | 請求總額、利息 |

---

### 🚫 None值過濾機制

**原則**：欄位沒有內容時，**不存入資料庫**（避免出現None/null）

**實作**：所有腳本在存入Neo4j前，使用`filter_smart()`函數過濾：

```python
def filter_smart(data):
    """過濾掉None、空字串、空列表、空字典"""
    def is_meaningful(value):
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True

    return {k: v for k, v in data.items() if is_meaningful(v)}
```

**效果**：
- ❌ 不會出現：`"disability_level": null`
- ✅ 改為：完全不存這個欄位
- 查詢時使用：`COALESCE(n.disability_level, "無")` 處理缺失值

---

## 1️⃣ FactDetail（事實細節）

### 節點類型：

#### 1.1 TimeInfo（時間資訊）

```json
{
  "node_type": "FactDetail",
  "detail_type": "TimeInfo",
  "date": "2024-08-18",
  "time": "21:26",
  "precision": "approximate",        // exact | approximate | unknown
  "datetime_struct": "2024-08-18T21:26:00",
  "raw_text": "民國110年8月18日晚間9時26分許",
  "semantic_summary": "事故發生於2024年8月18日晚間9點半左右"
}
```

#### 1.2 LocationInfo（地點資訊）

```json
{
  "node_type": "FactDetail",
  "detail_type": "LocationInfo",
  "city": "新北市",
  "district": "板橋區",
  "street": "長江路1段",
  "scene_type": "路口",              // 路口 | 直路 | 停車場 | 其他
  "weather": "晴朗",
  "road_condition": "乾燥",
  "lighting": "有路燈",
  "coordinates": null,               // 未來可以加經緯度
  "raw_text": "新北市板橋區長江路1段往北向民生路方向",
  "semantic_summary": "事故發生在板橋區長江路路口，天氣晴朗路面乾燥"
}
```

#### 1.3 VehicleInfo（車輛資訊）

```json
{
  "node_type": "FactDetail",
  "detail_type": "VehicleInfo",
  "vehicle_type": "重型機車",
  "plate_number": "ABC-1234",
  "owner_role": "被告",              // 原告 | 被告 | 第三人
  "license_status": "已註銷",        // 有效 | 已註銷 | 無照
  "vehicle_action": "左轉",          // 直行 | 左轉 | 右轉 | 迴轉 | 靜止
  "fault_indication": true,          // 是否有過失跡象
  "raw_text": "被告騎乘車號000-0000號重型機車，該執照業因酒後駕車案件遭註銷",
  "semantic_summary": "被告無照駕駛機車左轉"
}
```

#### 1.4 InjuryInfo（傷害資訊）

```json
{
  "node_type": "FactDetail",
  "detail_type": "InjuryInfo",
  "injured_person": "原告",
  "injuries": [
    {
      "body_part": "左膝",
      "injury_type": "骨折",
      "severity": "嚴重",            // 輕微 | 中度 | 嚴重 | 致命
      "severity_score": 8.5,         // 🆕 量化分數 (0-10)，用於計算權重
      "medical_term": "十字韌帶撕裂性骨折",
      "severity_indicators": {       // 🆕 嚴重度指標
        "surgery_required": true,
        "hospitalization_days": 14,
        "recovery_months": 7.5,
        "permanent_disability": false
      }
    },
    {
      "body_part": "左肩",
      "injury_type": "擦傷",
      "severity": "輕微",
      "severity_score": 2.0,
      "medical_term": "挫擦傷"
    }
  ],
  "treatment": ["手術", "看護"],
  "surgery_count": 2,
  "recovery_period": "7-8個月",
  "recovery_days": 225,              // 可計算
  "disability_level": null,
  "related_compensations": [         // 🆕 關聯賠償項目（雙向連結）
    "medical_費用",
    "nursing_費用",
    "mental_慰撫金"
  ],
  "raw_text": "造成原告受有左膝挫傷併十字韌帶撕裂性骨折及左肩挫擦傷，嗣後並需接受兩次手術治療",
  "semantic_summary": "原告左膝嚴重骨折需手術，休養7-8個月"
}
```

#### 1.5 PartyInfo（當事人資訊）

```json
{
  "node_type": "FactDetail",
  "detail_type": "PartyInfo",
  "role": "被告",                   // 原告 | 被告 | 第三人
  "party_name": "林○○",
  "party_type": "individual",       // individual | company | government
  "fault_actions": [
    "未打方向燈",
    "未暫停",
    "未注意來往車輛"
  ],
  "legal_capacity": "完全行為能力人",
  "raw_text": "被告本應依規定於欲左轉時先行打方向燈、暫停並注意來往車輛，竟疏未為之",
  "semantic_summary": "被告違反多項交通規則導致事故"
}
```

#### 1.6 EvidenceInfo（證據資訊）

```json
{
  "node_type": "FactDetail",
  "detail_type": "EvidenceInfo",
  "evidence_type": "document",       // document | witness | physical | electronic
  "evidence_name": "診斷證明書",
  "evidence_source": "台大醫院",
  "evidence_purpose": "證明傷害",
  "authenticity": "已認證",
  "raw_text": "有台大醫院診斷證明書可證",
  "semantic_summary": "提供醫院診斷證明作為傷害證據"
}
```

---

## 2️⃣ LawDetail（法條細節）

```json
{
  "node_type": "LawDetail",
  "article": "民法第184條第1項前段",
  "article_full_text": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。",

  // 🆕 法律要件分析
  "legal_elements": {
    "故意或過失": {
      "satisfied": true,
      "fact_refs": ["VehicleInfo_1", "PartyInfo_1"],  // 🆕 關聯到FactDetail節點
      "reasoning": "被告未打方向燈、未注意來車，構成過失"
    },
    "不法侵害": {
      "satisfied": true,
      "fact_refs": ["VehicleInfo_1"],
      "reasoning": "違反道路交通安全規則第102條"
    },
    "權利受損": {
      "satisfied": true,
      "fact_refs": ["InjuryInfo_1"],
      "reasoning": "原告受有身體傷害"
    },
    "因果關係": {
      "satisfied": true,
      "fact_refs": ["VehicleInfo_1", "InjuryInfo_1"],
      "reasoning": "被告左轉行為直接導致碰撞與傷害"
    }
  },

  // 結構化核心
  "applicable_reason": "被告未注意車前狀況",
  "supporting_facts": [
    "疏未注意",
    "貿然左轉",
    "未打方向燈"
  ],
  "legal_element_matched": "過失侵權",
  "fault_type": "negligence",       // negligence | intent | strict_liability
  "causation_established": true,
  "fault_ratio": null,              // 🆕 若有過失比例（民法217條）

  // 法條關係
  "related_articles": [
    {
      "article": "民法第191條之2",
      "relation": "共同適用",
      "reason": "車輛侵權責任"
    }
  ],
  "law_chain_position": 1,          // 在法律推理鏈中的位置

  "raw_text": "按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」民法第184條第1項前段定有明文。查被告因上開事故侵害原告之權益...",
  "semantic_summary": "被告過失侵權，符合民法184條第1項前段要件"
}
```

---

## 3️⃣ CompensationDetail（賠償細節）

```json
{
  "node_type": "CompensationDetail",

  // 分類（使用標準化類別）
  "category": "medical",             // medical | nursing | vehicle | income_loss | mental | equipment | transportation | other
  "item_name": "醫療費用",
  "item_name_standardized": "醫療費用", // 標準化名稱（用於統計）

  // 金額
  "amount": 171170,
  "amount_range": "150k-200k",      // 便於統計
  "currency": "TWD",

  // 🆕 計算公式（針對複合項目）
  "calculation_method": "實際支出", // 實際支出 | 估算 | 固定標準 | 公式計算
  "calculation_formula": {          // 🆕 當為公式計算時
    "type": "multiplication",       // multiplication | daily_rate | percentage
    "base_amount": 30000,
    "multiplier": 3,
    "unit": "個月",
    "formula_text": "30,000元×3個月"
  },
  "supporting_evidence": ["收據", "診斷證明"],
  "evidence_strength": "strong",    // strong | medium | weak

  // 🆕 因果關聯
  "caused_by_injuries": [            // 🆕 雙向連結到InjuryInfo
    "InjuryInfo_1_左膝骨折",
    "InjuryInfo_1_左肩擦傷"
  ],
  "causation_reasoning": "因骨折手術產生之醫療費用",

  // 合理性
  "reasonableness": "合理必要",
  "necessity": "必要",
  "proportion_of_total": 0.138,     // 佔總賠償的比例

  // 原告相關
  "plaintiff_id": "原告1",          // 多原告案件用
  "approved_by_court": null,        // 若已判決

  "raw_text": "(一)醫療費用:171,170元 原告因本件事故所受傷害,總計支出醫療費用171,170元。",
  "semantic_summary": "原告因事故支出醫療費17萬元，有收據證明"
}
```

**標準化類別對照表：**

| category | 中文名稱 | 常見變體 |
|----------|---------|---------|
| medical | 醫療費用 | 醫藥費、診療費、手術費 |
| nursing | 看護費用 | 照護費、護理費 |
| vehicle | 車輛損失 | 維修費、車損 |
| income_loss | 工作損失 | 薪資損失、收入減少 |
| mental | 精神慰撫金 | 精神賠償、慰撫金 |
| equipment | 器材費用 | 護具、輔具、義肢 |
| transportation | 交通費用 | 車資、計程車費 |
| other | 其他費用 | 其他 |

---

## 4️⃣ ConclusionDetail（結論細節）

```json
{
  "node_type": "ConclusionDetail",
  "detail_type": "total_amount",    // total_amount | interest | costs | plaintiff_specific

  // 金額資訊
  "amount": 1237470,
  "amount_type": "single_plaintiff_total", // single_plaintiff_total | multiple_plaintiff_total | deducted_total
  "deductions": [
    {
      "reason": "強制險理賠",
      "amount": 50000,
      "date": "2024-09-15"
    }
  ],
  "net_amount": 1187470,

  // 🆕 利息詳細資訊
  "interest": {
    "rate": 0.05,
    "rate_type": "年息",              // 年息 | 法定利率
    "start_date": "起訴狀繕本送達翌日",
    "start_date_standardized": "2024-10-15",  // 🆕 標準化日期
    "end_date": "清償日止",
    "calculation_basis": "本金",
    "calculation_formula": "自起訴狀繕本送達翌日起至清償日止，按年息5%計算"
  },

  // 🆕 訴訟費用詳細
  "litigation_costs": {
    "court_fees": 12374,              // 🆕 裁判費（總額的1%）
    "service_fees": null,
    "total_costs": 12374,
  "responsibility": "被告負擔",
    "proportion": "全部"              // 全部 | 按比例
  },

  // 🆕 給付方式
  "payment_terms": {
    "method": "一次給付",              // 一次給付 | 分期給付 | 定期給付
    "deadline": null,
    "installment_plan": null          // 若為分期
  },

  // 🆕 法律依據摘要
  "legal_basis_summary": [
    "民法第184條第1項前段",
    "民法第191條之2",
    "民法第193條第1項",
    "民法第195條第1項"
  ],

  // 原告統計
  "plaintiff_count": 1,
  "defendant_count": 1,
  "fault_ratio": null,              // 過失比例（如217條適用）

  // 🆕 賠償項目分解
  "breakdown": {                     // 🆕 各類別總額
    "medical": 171170,
    "nursing": 90000,
    "vehicle": 45000,
    "mental": 800000,
    "other": 131300
  },

  "raw_text": "綜上所陳,原告因本件事故所受損害合計1,237,470元,爰依民法第184條、第191條之2、第193條及第195條規定,請求被告給付損害賠償1,237,470元",
  "semantic_summary": "請求被告賠償總計123萬元並負擔訴訟費用"
}
```

---

## 🔍 設計改進總結（基於真實案例分析）

> 分析案例：case_id=1（左膝骨折案）

### ✅ 已解決的6大設計缺口

#### **改進1：Facts ↔ Laws 的連結**
- **問題**：法條要件與支持事實沒有明確連結
- **解決方案**：在LawDetail新增`legal_elements`結構
  ```json
  "legal_elements": {
    "故意或過失": {
      "satisfied": true,
      "fact_refs": ["VehicleInfo_1", "PartyInfo_1"],
      "reasoning": "被告未打方向燈、未注意來車，構成過失"
    }
  }
  ```
- **效果**：可追溯每個法律要件的事實依據

#### **改進2：Injury ↔ Compensation 的因果連結**
- **問題**：賠償項目與導致它的傷害沒有關聯
- **解決方案**：
  - InjuryInfo新增`related_compensations`陣列
  - CompensationDetail新增`caused_by_injuries`陣列和`causation_reasoning`
  ```json
  "caused_by_injuries": ["InjuryInfo_1_左膝骨折"],
  "causation_reasoning": "因骨折手術產生之醫療費用"
  ```
- **效果**：可查詢「骨折通常導致哪些賠償項目」

#### **改進3：複合項目的計算公式**
- **問題**：「30,000元×3個月」這類計算沒有結構化
- **解決方案**：CompensationDetail新增`calculation_formula`物件
  ```json
  "calculation_formula": {
    "type": "multiplication",
    "base_amount": 30000,
    "multiplier": 3,
    "unit": "個月",
    "formula_text": "30,000元×3個月"
  }
  ```
- **效果**：可分析日薪/月薪標準，計算合理性

#### **改進4：傷害嚴重度量化**
- **問題**：「嚴重」太主觀，無法用於權重計算
- **解決方案**：InjuryInfo新增`severity_score`和`severity_indicators`
  ```json
  "severity_score": 8.5,
  "severity_indicators": {
    "surgery_required": true,
    "hospitalization_days": 14,
    "recovery_months": 7.5,
    "permanent_disability": false
  }
  ```
- **效果**：可用數值計算傷害-賠償相關性

#### **改進5：結論的詳細分解**
- **問題**：利息、訴訟費、給付方式資訊缺失
- **解決方案**：ConclusionDetail新增結構化欄位
  ```json
  "interest": {
    "rate": 0.05,
    "start_date_standardized": "2024-10-15",
    "calculation_formula": "自起訴狀繕本送達翌日起至清償日止，按年息5%計算"
  },
  "litigation_costs": {
    "court_fees": 12374,
    "responsibility": "被告負擔"
  },
  "breakdown": {
    "medical": 171170,
    "nursing": 90000,
    "mental": 800000
  }
  ```
- **效果**：完整重建判決書結論結構

#### **改進6：賠償項目8類別驗證**
- **驗證結果**：8個類別（medical/nursing/vehicle/income_loss/mental/equipment/transportation/other）**足夠涵蓋**真實案例
- **證據**：case_id=1的賠償項目都能對應到這8類

---

## 🔧 實施策略

### 階段1：刪除舊節點（5分鐘）

```cypher
MATCH (n:LawDetail) DETACH DELETE n;
MATCH (n:CompensationDetail) DETACH DELETE n;
MATCH (n:ConclusionDetail) DETACH DELETE n;
```

### 階段2：Chunking + 提取結構化信息（使用Gemma）

**流程**：

```python
# 偽代碼示意
for each case in 6057_cases:
    # Step 2.1: 切分段落成chunks
    facts_chunks = chunk_by_sentence(case.事實概述, case.id, "facts")
    laws_chunks = chunk_by_sentence(case.法條引用, case.id, "laws")
    comp_chunks = chunk_by_sentence(case.損害賠償項目, case.id, "compensation")
    conc_chunks = chunk_by_sentence(case.結論, case.id, "conclusion")

    # Step 2.2: 對每個chunk用Gemma提取結構化信息
    for chunk in facts_chunks:
        structured_info = gemma_extract(
            chunk_text=chunk['chunk_text'],
            chunk_id=chunk['chunk_id'],
            extraction_type='FactDetail'  # 提取 InjuryInfo/VehicleInfo/...
        )
        save_to_jsonl(structured_info)
```

**輸出檔案**：`structured_summaries_with_chunks.jsonl`

**範例輸出**：
```json
{
  "case_id": "1",
  "chunk_id": "case_1_facts_chunk_5",
  "chunk_text": "造成原告受有左膝挫傷併十字韌帶撕裂性骨折。",
  "chunk_index": 5,
  "parent_section": "facts",
  "extracted_details": [
    {
      "node_type": "FactDetail",
      "detail_type": "InjuryInfo",
      "injuries": [...],
      "severity_score": 8.5,
      ...
    }
  ]
}
```

### 階段3：建立新的Detail節點（含chunk_id）

**新腳本**：
- `KG_200v2_setting_law_structured.py` - 建立LawDetail（含chunk_id）
- `KG_300v2_setting_compensation_structured.py` - 建立CompensationDetail（含chunk_id）
- `KG_350_setting_fact_structured.py`（新增）- 建立FactDetail（含chunk_id）
- `KG_400v2_setting_conclusion_structured.py` - 建立ConclusionDetail（含chunk_id）

**Cypher範例**（建立Detail節點）：
```cypher
MERGE (fd:FactDetail {chunk_id: $chunk_id})
SET fd.case_id = $case_id,
    fd.node_type = 'FactDetail',
    fd.detail_type = $detail_type,
    fd.chunk_text = $chunk_text,
    fd.chunk_index = $chunk_index,
    fd.parent_section = $parent_section,
    fd.injuries = $injuries,
    fd.severity_score = $severity_score,
    fd.semantic_summary = $semantic_summary,
    ...

// 建立與父節點的關係
MATCH (f:Facts {case_id: $case_id})
MATCH (fd:FactDetail {chunk_id: $chunk_id})
MERGE (f)-[:HAS_DETAIL {chunk_index: $chunk_index}]->(fd)
```

### 階段4：驗證和統計

```cypher
// 統計各類節點數量
MATCH (n:FactDetail) RETURN n.detail_type, count(*) as count;
MATCH (n:LawDetail) RETURN n.article, count(*) as count ORDER BY count DESC;
MATCH (n:CompensationDetail) RETURN n.category, count(*) as count;
```

---

## 📈 預期效果

### 可精確檢索

```cypher
// 找所有骨折案件的醫療費用分布
MATCH (i:FactDetail {detail_type: "InjuryInfo"})-[]-(c:Case)-[]-(cd:CompensationDetail {category: "medical"})
WHERE any(injury IN i.injuries WHERE injury.injury_type = "骨折")
RETURN avg(cd.amount), min(cd.amount), max(cd.amount)

// 找所有因「未注意車前狀況」適用184條的案件
MATCH (l:LawDetail {article: "民法第184條第1項前段"})
WHERE l.applicable_reason CONTAINS "未注意車前狀況"
RETURN count(*), avg(l.confidence)
```

### 可計算權重

```python
# 統計權重
injury_severity_weight = {
    "嚴重": 1.0,
    "中度": 0.6,
    "輕微": 0.3
}

medical_frequency = count(category="medical") / 6057
medical_avg_amount = avg(amount WHERE category="medical")
```

### 支持推理

```
查詢：「騎機車左轉未打方向燈，造成對方骨折，要賠多少？」

推理鏈：
1. FactDetail (VehicleInfo) → 找「左轉」+「未打方向燈」案件
2. FactDetail (InjuryInfo) → 過濾「骨折」
3. LawDetail → 確認適用法條（184+191-2）
4. CompensationDetail → 統計賠償金額範圍
5. 返回：平均120萬，範圍80-180萬
```

---

## ✅ 下一步行動

### 當前進度：Step 1 執行中

- ✅ **Step 0**：用Gemma3修正結論金額（已完成）
- 🔄 **Step 1**：擴增起訴書主幹到6057筆（進行中）
  - ✅ KG_100完成：6057個Case主幹節點
  - ✅ KG_200完成：23,371個LawDetail（舊版，待重建）
  - ⏸️ KG_300停止：CompensationDetail（舊版，需重新設計）

### 設計已完成（本文件）

✅ **Detail節點重新設計**：
- 結構化欄位設計（6大改進）
- Chunk機制設計（句子級切分）
- None值過濾機制
- 雙層檢索支援（段落→chunk）

### 待執行任務

**立即待辦**：
1. **刪除舊Detail節點**（5分鐘）
   ```cypher
   MATCH (n:LawDetail) DETACH DELETE n;
   MATCH (n:CompensationDetail) DETACH DELETE n;
   MATCH (n:ConclusionDetail) DETACH DELETE n;
   ```

2. **調整KG_560腳本**（加入chunking）
   - 修改為：先切chunk，再對每個chunk做Gemma提取
   - 輸出：`structured_summaries_with_chunks.jsonl`

3. **執行Step 2-4**：建立新的Detail節點
   - KG_350：FactDetail（新增，含chunk_id）
   - KG_200v2：LawDetail（重建，含chunk_id）
   - KG_300v2：CompensationDetail（重建，含chunk_id）
   - KG_400v2：ConclusionDetail（重建，含chunk_id）

4. **執行Step 5-6**：計算權重
   - Step 5：統計權重（frequency-based）
   - Step 6：語義權重（Gemma計算相似度）

5. **之後**：設計「權重 + 雙層檢索」整合方案

---

**當前選擇**：按選項A執行，先完成基礎設計和Detail節點建立，權重計算和檢索整合留待之後。
