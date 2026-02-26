# TAARN 技術細節解說（給老師的問答準備）

## 預期問題 1：這篇論文是怎樣從知識圖譜提取路徑的？

### 一、基本概念：什麼是「路徑提取」？

**白話解釋**：
就像 Google Maps 給你找路一樣，從起點（查詢的實體）到終點（答案），中間可能經過好幾個路口。

**在知識圖譜裡**：
- 起點實體：例如「Ilya Sutskever」（某個人）
- 終點實體：例如「University of Toronto」（某個學校）
- 中間路徑：Ilya → advisor → Geoffrey Hinton → works_at → University of Toronto

### 二、TAARN 的路徑提取方法：語義-深度引導的隨機遊走

#### 步驟 1：基礎隨機遊走（Random Walk）

**類比：在城市裡閒逛**
- 你站在一個路口，有 3 條路可以走
- 傳統隨機遊走：每條路都有 1/3 的機會被選
- 但這樣會走到很多無關的地方

**在知識圖譜裡**：
```
Ilya Sutskever（起點）
  ↓ 有 5 條邊可以走：
  1. advisor → Geoffrey Hinton
  2. works_at → OpenAI
  3. nationality → Canadian
  4. born_in → Moscow
  5. knows → Elon Musk

傳統隨機遊走：每條邊都有 20% 機會
問題：如果我要找他的教育背景，走到 Elon Musk 就沒用了
```

#### 步驟 2：加入「語義偏差」（Semantic Bias）

**核心想法**：用 AI 語言模型判斷哪條路「更有意義」

**具體做法**：
1. 把每個三元組 (頭實體, 關係, 尾實體) 轉成一句話
   - 例如：(Ilya, advisor, Hinton) → "Ilya's advisor is Hinton"

2. 用預訓練語言模型（PLM）算這句話的「合理性分數」
   - 方法：把關係換成 `[MASK]`，看模型能不能猜對
   - 例如："Ilya's [MASK] is Hinton" → 模型預測 "advisor" 的機率高 → 分數高

3. 分數高的路徑，被選中的機會就大

**公式形式**（不用記，給老師看起來專業用的）：
```
semantic_score = PLM("Ilya's [MASK] is Hinton")
```

**實際效果**：
```
Ilya Sutskever（起點）
  ↓ 計算每條邊的語義分數：
  1. advisor → Hinton         (分數 0.85) ← 跟教育有關，高分！
  2. works_at → OpenAI        (分數 0.75)
  3. nationality → Canadian   (分數 0.30)
  4. born_in → Moscow         (分數 0.25)
  5. knows → Elon Musk        (分數 0.20) ← 太八卦，低分

現在不是每條 20%，而是根據分數加權：
  advisor 被選的機率變成 35%，knows 只剩 8%
```

#### 步驟 3：加入「深度偏差」（Depth Bias）

**發現的問題**：走太遠會偏題

**論文實驗結果**（Table 1）：
- 深度 1：太淺，資訊不夠
- 深度 2：剛剛好！（最佳）
- 深度 3+：太遠，雜訊太多

**類比：你問我「誰是 Steve Jobs 的偶像？」**
- 深度 1：只看 Steve Jobs 直接連的人 → Bob Dylan（答案！）
- 深度 2：Steve Jobs → Apple → Tim Cook → ... → 還算相關
- 深度 5：Steve Jobs → Apple → iPhone → 使用者 → 某個路人 → 他媽媽 → 完全無關了！

**具體實作**：
```python
depth_penalty = 0.8 ** current_depth

最終選擇機率 = semantic_score × depth_penalty
```

走越深，懲罰越重，避免走太遠。

#### 步驟 4：完整的 Biased Random Walk 流程

**實際執行（以 Ilya 找學校為例）**：

```
起點：Ilya Sutskever
目標：找到他的畢業學校

第 1 步（depth=1）：
  - 看 Ilya 的所有鄰居
  - 計算每條邊的 semantic_score × depth_penalty
  - 選到：advisor → Geoffrey Hinton（機率最高）

第 2 步（depth=2）：
  - 現在從 Hinton 出發
  - 看 Hinton 的所有鄰居
  - 計算分數，但乘以 0.8 懲罰（因為 depth=2）
  - 選到：works_at → University of Toronto（答案！）

停止條件：
  - 達到深度限制（depth=2）
  - 或已經找到答案
```

**最終輸出**：
一條路徑：Ilya → advisor → Hinton → works_at → U of T

---

## 預期問題 2：這篇論文是怎樣融合結構與文本資訊的？

### 一、為什麼要融合兩種資訊？

**問題情境**：
- **只看結構**：知道 Ilya 和 Hinton 有連結，但不知道是什麼關係（師生？同事？朋友？）
- **只看文本**：知道「Ilya Sutskever is a researcher」，但不知道他在圖譜裡跟誰連結

**解決方案**：兩種資訊都要！

### 二、模組架構：Text-Augmented Embedding

這個模組做兩件事，然後把結果合併。

#### 部分 A：提取「結構資訊」→ 用 GAT（圖注意力網絡）

**核心想法**：看一個實體的鄰居，判斷哪些鄰居重要

**類比：你在 LinkedIn 上看一個人的人脈**
- 這個人認識 100 個人
- 但其中 5 個是業界大佬，95 個是普通同事
- GAT 會自動判斷「大佬權重高，普通人權重低」

**具體步驟**：

1. **每個實體先有一個初始向量**（從 TransE 或 ComplEx 預訓練來的）
   ```
   Ilya 的初始向量：[0.2, 0.5, 0.1, ..., 0.8]（300 維）
   ```

2. **看 Ilya 的所有鄰居**（Hinton, OpenAI, Canada, ...）
   ```
   鄰居們的向量：
   Hinton:  [0.3, 0.6, 0.2, ..., 0.7]
   OpenAI:  [0.1, 0.4, 0.3, ..., 0.6]
   Canada:  [0.5, 0.2, 0.1, ..., 0.4]
   ```

3. **計算注意力權重**（哪個鄰居重要？）
   ```python
   attention_score(Ilya, Hinton) =
       similarity(Ilya_vector, Hinton_vector) × relation_importance("advisor")

   結果：
   Hinton:  0.85  ← 最重要！（學術導師）
   OpenAI:  0.60  ← 次重要（工作單位）
   Canada:  0.15  ← 不重要（只是國籍）
   ```

4. **加權聚合**（把重要鄰居的資訊融合到 Ilya）
   ```
   Ilya 的新向量 =
       0.85 × Hinton_vector +
       0.60 × OpenAI_vector +
       0.15 × Canada_vector
   ```

**這就是 GAT 的結構資訊！**

#### 部分 B：提取「文本資訊」→ 用 PLM + Prompt Learning

**核心想法**：把實體和關係當作「填空題」，讓語言模型填

**具體步驟**：

1. **設計 Prompt 模板**
   ```
   對於實體：
   "[MASK] is an entity."

   對於關係：
   "The relation between X and Y is [MASK]."
   ```

2. **讓語言模型填空**
   ```
   輸入："[MASK] is an entity."
   把 Ilya Sutskever 的名字藏起來，讓模型猜

   模型輸出：
   - researcher (機率 0.4)
   - scientist  (機率 0.3)
   - engineer   (機率 0.2)
   - person     (機率 0.1)
   ```

3. **用填空的機率分布當作文本向量**
   ```
   Ilya 的文本向量 = [0.4, 0.3, 0.2, 0.1, ...]（詞彙表大小的向量）

   再用一個神經網絡壓縮成固定大小：
   Ilya_text_embedding = [0.7, 0.3, 0.5, ..., 0.9]（300 維）
   ```

**這就是 PLM 的文本資訊！**

#### 部分 C：融合兩種資訊

**最簡單的方法：線性融合**

```python
Ilya_final_embedding = α × Ilya_structure_embedding  (來自 GAT)
                     + β × Ilya_text_embedding       (來自 PLM)

其中 α + β = 1（例如 α=0.6, β=0.4）
```

**實際效果**：
- 結構資訊告訴你：Ilya 在圖譜裡很重要，因為他連到很多核心人物
- 文本資訊告訴你：Ilya 的職業是 researcher，專長是 AI
- 融合後：既知道他在圖譜裡的位置，也知道他的語義含義

---

## 三、完整流程串起來（給老師看全貌）

**情境：問題是「Who is Ilya Sutskever's advisor?」**

### Step 1：路徑提取模組
```
1. 從「Ilya Sutskever」出發
2. 用語義偏差 + 深度偏差做 biased random walk
3. 提取出多條路徑：
   - Path 1: Ilya → advisor → Hinton
   - Path 2: Ilya → works_at → OpenAI → founded_by → Sam Altman
   - Path 3: ...
```

### Step 2：文本增強嵌入模組
```
1. 對每條路徑上的實體和關係，用 GAT 提取結構資訊
2. 對每條路徑上的實體和關係，用 PLM 提取文本資訊
3. 融合得到每個實體的最終向量
```

### Step 3：跨注意力推理模組（這個比較複雜，老師可能不會深入問）
```
用 RNN 沿著路徑走，每一步都用注意力機制判斷：
「這一步對回答問題有多重要？」

最終輸出：Hinton（答案！）
```

---

## 四、預期追問與回答

### Q1：「這個方法是不是很慢？每次都要走圖？」

**A**：
對！所以 TAARN 是給「訓練階段」用的，不是即時查詢。

- **訓練時**：可以慢慢算，生成大量路徑，訓練模型
- **推理時**：用訓練好的模型直接預測，不用再走圖

**我們的系統不一樣**：
- 我們是「檢索系統」，不是「訓練模型」
- 我們用規則直接算相似度，不需要訓練
- 所以我們的方法更快，但借鑒了 TAARN 的「多維度融合」思想

### Q2：「為什麼你們不用這個方法？」

**A**（5 個理由）：
1. **沒有訓練資料**：TAARN 需要幾萬對問答標註，我們沒有
2. **任務不同**：TAARN 是問答（QA），我們是案例檢索（Retrieval）
3. **需要可解釋性**：法律領域要能說明「為什麼推薦這個案例」
4. **資源限制**：訓練這種模型需要 GPU，我們只有 CPU
5. **規則就夠用**：案例類型、法條重疊都可以直接算

**但我們借鑒了這 3 個原則**：
1. 多維度融合（案例類型 + 法條 + 賠償項目 + 事實關鍵字）
2. 重要性分級（案例類型權重 60% > 法條 20%）
3. 稀疏化策略（每個案例只連前 5 名，對應 TAARN 的深度限制）

### Q3：「PLM 是什麼？怎麼用？」

**A**：
PLM = Pre-trained Language Model（預訓練語言模型）

**例子**：BERT、RoBERTa、GPT

**怎麼用**：
1. 先用大量文本訓練好一個通用模型（例如維基百科）
2. 再用特定任務微調（例如知識圖譜問答）
3. TAARN 論文裡用的是 RoBERTa

**我們有用嗎**？
- 我們用 Gemma 來做結論金額修正（Step 0）
- 但在相似度計算上，我們用規則，不用語言模型

### Q4：「GAT 是什麼？」

**A**：
GAT = Graph Attention Network（圖注意力網絡）

**核心想法**：
- 傳統 GCN（圖卷積）：鄰居的權重都一樣
- GAT：用注意力機制，讓重要的鄰居權重高

**類比**：
- GCN：你 100 個朋友的意見「平均」一下
- GAT：你 5 個摯友的意見權重 80%，95 個普通朋友權重 20%

**公式**（給老師看專業度用）：
```
α_ij = attention(node_i, node_j)
h_i' = Σ α_ij × h_j  (對所有鄰居 j 加權求和)
```

---

## 五、總結：一句話說清楚

**TAARN 怎麼做**：
用深度學習（GAT + PLM + RNN）從知識圖譜裡提取多條路徑，融合結構和文本資訊，訓練一個能回答問題的模型。

**我們怎麼做**：
用規則（Jaccard 相似度 + 權重分配）從知識圖譜裡找相似案例，不需要訓練，但借鑒了 TAARN 的多維度融合和重要性分級思想。

**類比**：
- TAARN：訓練一個 AI 廚師，讓他學會做菜
- 我們：拿著食譜（規則）直接做菜，但學習了 AI 廚師的配料比例和烹飪順序

---

## 附錄：論文關鍵數據（老師可能會問）

### Table 1：路徑深度統計（FB15k-237 數據集）

| Depth | 1-hop | 2-hop | 3-hop | 4-hop | 5-hop |
|-------|-------|-------|-------|-------|-------|
| 比例  | 32.1% | 41.3% | 18.7% | 6.2%  | 1.7%  |

**結論**：41.3% 的答案在 2-hop 就能找到，所以設 depth=2 最佳。

### 我們的數據（6,057 個案例）

| 維度         | 相似案例佔比 | 平均相似度 |
|--------------|--------------|------------|
| 案例類型相同 | ~85%         | 60% 權重   |
| 法條重疊 >3  | ~60%         | 20% 權重   |
| 賠償項目 >2  | ~70%         | 15% 權重   |
| 關鍵字重疊   | ~40%         | 5% 權重    |

**稀疏化**：每個案例只連前 5 名 → 6,057 × 5 = 30,285 條邊（理論上限）
**實際預估**：約 15,000 條邊（因為有些案例找不到 5 個相似案例）

---

## 使用建議

### 準備策略：

1. **先講完整流程**（用類比）
   - 路徑提取 = Google Maps 找路 + 偏好某些路線
   - 結構文本融合 = LinkedIn 人脈 + 職業描述

2. **老師問細節時**（看他問哪個）
   - 問路徑提取 → 講 semantic bias + depth bias
   - 問融合方法 → 講 GAT + PLM + 線性融合

3. **隨時準備回答「為什麼你們不用」**
   - 5 個理由背起來
   - 強調我們借鑒了 3 個原則

4. **準備論文截圖**
   - Fig.2：整體架構圖
   - Table 1：深度統計（證明 depth=2 最好）
   - Fig.1：Ilya Sutskever 的知識圖譜（具體例子）

祝討論順利！
