# XRAG 論文圖面規劃

本文件整理目前論文建議繪製之圖面，供後續以 Adobe Illustrator 製作正式圖稿。

## 優先順序

建議先完成下列 5 張主圖：

1. `Our Proposed XRAG Scheme`
2. `RAG / CAG / XRAG 問題定義對比圖`
3. `Boolean Matrix 與 Severity Reconstruction 圖`
4. `Dual-Tree Retrieval 圖`
5. `Generation Evaluation 12-panel 主圖框架`

## 圖面總表

### 圖 1 Our Proposed XRAG Scheme

- 建議章節：第 1 章 緒論
- 圖面目的：作為全文第一張主圖，直接建立本研究方法主體
- 構圖重點：
  - 左側：`Lawyer-style Query Input`
  - 中間上層：`Boolean Matrix + Severity Reconstruction`
  - 中間中層：`Experiment-specific Relations`
  - 中間下層：`Anchor + Dual-Tree Retrieval`
  - 右側：`Section-wise Complaint Generation`
  - 最右下：`Generated Civil Complaint`
- 建議風格：總覽式方法架構圖，標題可直接寫 `Our Proposed XRAG Scheme`

### 圖 2 研究問題定義圖

- 建議章節：第 1 章 緒論
- 圖面目的：補充說明本研究欲解決之任務難點
- 構圖重點：
  - 左側：模擬律師輸入
  - 中間：事故事實複雜、傷勢與賠償多樣、生成易偏離 query
  - 右側：四段式民事起訴書輸出
- 建議風格：流程箭頭 + 法律文件卡片

### 圖 3 RAG / CAG / XRAG 問題定義對比圖

- 建議章節：第 2 章 Related Work 或第 3 章方法前言
- 圖面目的：凸顯 XRAG 與 baseline / 對手之差異
- 構圖重點：
  - `RAG`：query -> semantic retrieval -> LLM
  - `CAG`：query -> cached context / preloaded context -> LLM
  - `XRAG`：query -> structured representation -> anchor + dual-tree retrieval -> section-wise generation
- 建議風格：三欄平行比較圖

### 圖 4 XRAG 全系統架構圖

- 建議章節：第 3 章研究方法
- 圖面目的：作為全文主圖
- 構圖重點：
  - Phase 1：boolean matrix -> severity reconstruction
  - Phase 2：18 組 experiment-specific relations
  - Query stage：anchor finding -> dual-tree retrieval
  - Generation stage：facts / laws / damages / conclusion
  - Evaluation stage：metrics
- 建議風格：分層架構圖，主線以粗箭頭強調

### 圖 5 資料流圖

- 建議章節：第 3 章或第 4 章
- 圖面目的：交代資料來源與去向
- 構圖重點：
  - 6057 cases
  - 50 query test set
  - silver reference
  - XRAG generation outputs
  - evaluation outputs
- 建議風格：資料來源與輸出管線圖

### 圖 6 Boolean Matrix 設計圖

- 建議章節：第 3 章 Phase 1
- 圖面目的：說明固定 16 格案件表示
- 構圖重點：
  - Litigants 4 格
  - Fact 4 格
  - Injury 4 格
  - Compensation 4 格
- 建議風格：4 個區塊組成的 4x4 matrix

### 圖 7 Severity Reconstruction 圖

- 建議章節：第 3 章 Phase 1
- 圖面目的：說明 severity 不是直接等於 boolean
- 構圖重點：
  - `h_F -> S_F -> F`
  - `h_I -> S_I -> I`
  - `h_C -> S_C -> C`
  - Compensation 另含保險已賠扣分
- 建議風格：三條平行轉換箭頭 + 補充註解

### 圖 8 Experiment Score / Distance 圖

- 建議章節：第 3 章 Phase 2
- 圖面目的：說明 18 組參數如何改變 relation
- 構圖重點：
  - `Score_i`
  - `d(i,j)`
  - `lambda * L(i,j)`
  - 6 種權重排列 × 3 種 tau
- 建議風格：數學式搭配示意小圖

### 圖 9 Dual-Tree Retrieval 圖

- 建議章節：第 3 章 Query Stage
- 圖面目的：對應老師目前最在意的 query 時期流程
- 構圖重點：
  - query 先映射到 severity space
  - 找最近 anchor node
  - heavy-to-light tree 擴展
  - light-to-heavy tree 擴展
  - 各取 `k/2` 合成 top-k
- 建議風格：中央 anchor + 左右兩棵方向相反的樹

### 圖 10 Anchor-Centered Local Expansion 圖

- 建議章節：第 3 章 Query Stage
- 圖面目的：補充圖 8，說明不是全域亂抓，而是以 anchor 為中心的局部擴展
- 構圖重點：
  - 中心點：anchor
  - 一側：lighter-side cases
  - 另一側：heavier-side cases
  - 可標示 child / grandchild / local neighborhood
- 建議風格：局部放大圖

### 圖 11 Section-wise Generation 圖

- 建議章節：第 3 章 Generation Stage
- 圖面目的：回答「top-k 找到後怎麼用」
- 構圖重點：
  - query 為主體
  - retrieved case summaries 為輔
  - facts / laws / damages / conclusion 四段依序生成
- 建議風格：四段式卡片流程圖

### 圖 12 18 組 XRAG 命名 / 權重表

- 建議章節：第 4 章實作或實驗設計
- 圖面目的：讓讀者理解 `FI-L ~ CI-H`
- 構圖重點：
  - 6 組權重代碼
  - 3 組 tau 等級
  - 對應 `E01-E18`
- 建議風格：整潔表格，可直接做成論文表或圖

### 圖 13 Generation Evaluation 主圖

- 建議章節：第 5 章實驗結果
- 圖面目的：呈現老師要求的結果主圖
- 構圖重點：
  - 12 個 panel
  - 4 個 y-axis metrics
  - 3 個 x-axis 設計
  - 每張含 18 條 XRAG 線 + baseline + CAG
- 建議風格：先畫版型骨架，數據之後再補

## 可選補充圖

### 圖 14 Representative Query Case Study 圖

- 建議章節：第 5 章或附錄
- 圖面目的：展示單一 query 的 anchor、雙樹取例與最終生成結果

### 圖 15 Neo4j 展示圖

- 建議章節：第 4 章實作
- 圖面目的：交代 Neo4j 為展示層，不是主檢索層

### 圖 16 Ablation / Comparison 流程圖

- 建議章節：第 5 章
- 圖面目的：比較 single-tree、dual-tree、baseline、CAG

## Adobe Illustrator 繪圖建議

- 主色系：
  - 深藍灰：系統主架構
  - 橘色：query flow / retrieval
  - 藍綠：lighter-side tree
  - 紅橘：heavier-side tree
- 建議不要一開始就追求最終精修，先完成線框版與章節對應
- 先畫方法圖，再畫結果圖，因為方法圖最能幫你填論文文字

## 目前最建議立即開畫的 5 張

1. 圖 2 `RAG / CAG / XRAG 問題定義對比圖`
2. 圖 4 `XRAG 全系統架構圖`
3. 圖 6 `Boolean Matrix 設計圖`
4. 圖 9 `Dual-Tree Retrieval 圖`
5. 圖 13 `Generation Evaluation 主圖`

## 構圖草稿

以下內容改成可直接照著在 Adobe Illustrator 起稿的版本，先求版面、訊息層次與標註一致，不必一開始就精修。

### 圖 1 `Our Proposed XRAG Scheme`

- 版型：橫式總覽架構圖，左進右出，中間分三層。
- 最左側：
  - `Lawyer-style Query Input`
  - 可放一個文件框，內含：
    - accident facts
    - injury description
    - compensation claims
- 中間第一層：
  - `Phase 1`
  - `Boolean Matrix`
  - `Severity Reconstruction`
- 中間第二層：
  - `Phase 2`
  - `18 Experiment-specific Relations`
  - 可並列兩個小樹：
    - `Heavy-to-Light Tree`
    - `Light-to-Heavy Tree`
- 中間第三層：
  - `Anchor Finding`
  - `Dual-Tree Retrieval`
  - `Top-k Structured References`
- 最右側：
  - 四個縱向卡片：
    - `Facts`
    - `Laws`
    - `Damages`
    - `Conclusion`
  - 最後合流至 `Generated Civil Complaint`
- 圖上方大標題可直接寫：
  - `Our Proposed XRAG Scheme for Traffic-Accident Civil Complaint Generation`
- 視覺建議：
  - 這張要比其他圖更完整、更像論文招牌圖
  - 主色用深藍灰，query/retrieval 路徑用橘色強調

### 圖 3 `RAG / CAG / XRAG 問題定義對比圖`

- 版型：橫式三欄比較圖，三欄寬度一致，上方同一條主標題。
- 左欄 `RAG`：
  - 上方放 `Query`
  - 中間放 `Semantic Retrieval`
  - 下方放 `Retrieved Cases`
  - 最下方接 `LLM Generation`
  - 旁邊用灰色小字標註：
    - `similar cases returned by semantic similarity`
    - `risk of detail borrowing`
- 中欄 `CAG`：
  - 上方放 `Query`
  - 中間放 `Cached / Preloaded Context`
  - 下方放 `LLM Generation`
  - 旁邊標註：
    - `preloaded context`
    - `limited case-structure control`
- 右欄 `XRAG`：
  - 上方放 `Query`
  - 第二層放 `Boolean + Severity Representation`
  - 第三層放 `Anchor Finding`
  - 第四層放 `Dual-Tree Retrieval`
  - 第五層放 `Section-wise Generation`
  - 旁邊標註：
    - `structure-aware retrieval`
    - `query-centered drafting`
    - `reduced factual drift`
- 視覺建議：
  - `RAG` 用灰藍色
  - `CAG` 用中性色
  - `XRAG` 用深藍主色加橘色流程箭頭
- 要畫出的核心差異：
  - `RAG` 強調語意最近
  - `CAG` 強調預載 context
  - `XRAG` 強調結構化表示、anchor、雙樹、分段生成

### 圖 4 `XRAG 全系統架構圖`

- 版型：由左到右的五段式主流程，外加上下兩層輔助標籤。
- 第一段 `Case Corpus Preparation`：
  - `6057 Civil Cases`
  - 向下分成：
    - `Boolean Matrix`
    - `Severity Reconstruction`
- 第二段 `Experiment-specific Relation Construction`：
  - 中央方塊寫：
    - `18 Experiment Settings`
    - `6 Weight Permutations × 3 Tau Values`
  - 下方接：
    - `Heavy-to-Light Tree`
    - `Light-to-Heavy Tree`
- 第三段 `Query Processing`：
  - `50 Test Queries`
  - 接 `Boolean + Severity Mapping`
  - 接 `Nearest Anchor Case`
- 第四段 `Dual-Tree Retrieval`：
  - 左半邊 `Lighter-side Expansion`
  - 右半邊 `Heavier-side Expansion`
  - 中央合流到 `Top-k Structured References`
- 第五段 `Section-wise Generation and Evaluation`：
  - 依序排：
    - `Facts`
    - `Laws`
    - `Damages`
    - `Conclusion`
    - `Full Complaint`
  - 最後接 `BERTScore / ROUGE-L / BLEU / Human Score`
- 視覺建議：
  - 主流程用粗箭頭
  - `Phase 1`、`Phase 2`、`Query Stage`、`Generation Stage` 用上方小標區隔
  - query 流程用橘色強調
  - relation/tree 流程用藍綠與紅橘區分雙向

### 圖 6 `Boolean Matrix 設計圖`

- 版型：中央一個 4x4 matrix，外圍四個大區塊標註。
- 四列或四欄分別標為：
  - `Litigants`
  - `Fact`
  - `Injury`
  - `Compensation`
- 每一區塊內畫 4 個小格，共 16 格。
- 每個區塊旁可放極短說明：
  - `Litigants`: party structure / plaintiff-defendant pattern
  - `Fact`: accident pattern / liability-related fact
  - `Injury`: injury presence / severity clues
  - `Compensation`: compensation claim items / insurance-paid indicator
- 下方補一行：
  - `Fixed-length case representation for all 6,057 cases`
- 視覺建議：
  - 各區塊用不同但同系色塊
  - 格內不必塞太多文字，重點是讓讀者一眼看懂 `4 × 4 = 16`

### 圖 9 `Dual-Tree Retrieval 圖`

- 版型：中央一個 `Anchor Case`，左右各一棵方向相反的樹。
- 最左上角放 `Query`
  - 箭頭指向 `Boolean + Severity Mapping`
  - 再指向 `Nearest Anchor Node`
  - 再落到中央 `Anchor Case`
- 左側樹：
  - 標題 `Heavy-to-Light Tree`
  - 樹由上往下變淺色
  - 從 anchor 往下連到 `lighter-side examples`
  - 旁邊標 `k/2`
- 右側樹：
  - 標題 `Light-to-Heavy Tree`
  - 樹由上往下變深色
  - 從 anchor 往下連到 `heavier-side examples`
  - 旁邊標 `k/2`
- 底部合流：
  - `Top-k Structured References`
  - 再接 `Section-wise Complaint Generation`
- 小字標註建議：
  - `anchor-centered local expansion`
  - `bidirectional case reference`
  - `lighter and heavier neighboring cases`
- 視覺建議：
  - 左樹用藍綠色系
  - 右樹用紅橘色系
  - anchor 用深色圓點或六角形突出

### 圖 13 `Generation Evaluation 主圖`

- 版型：3 欄 × 4 列，共 12 個 panel。
- 三欄標題建議：
  - `Top-k Retrieval Depth`
  - `LLM Model Scale`
  - `Query Token Count`
- 四列標題建議：
  - `BERTScore`
  - `ROUGE-L`
  - `BLEU`
  - `Human Score`
- 每個 panel 內放：
  - `18 XRAG lines`
  - `RAG-Baseline`
  - `CAG`
- 圖例不建議塞進每個 panel，應統一放在整張圖右側或下方。
- 線條命名統一用：
  - `FI-L ~ CI-H`
  - `RAG-Baseline`
  - `CAG`
- 視覺建議：
  - 18 條 XRAG 線用同色系深淺區分
  - `RAG-Baseline` 用黑灰虛線
  - `CAG` 用深紫或深綠實線
  - 先做空版型，之後再補真數據

## 圖說草稿

以下圖說先用作論文初稿或 Illustrator 檔案命名依據，後續可再精簡。

- 圖 1：Our Proposed XRAG Scheme for Traffic-Accident Civil Complaint Generation.
- 圖 2：Traffic-Accident Civil Complaint Generation Problem Formulation.
- 圖 3：Comparison of Problem Formulation and Processing Flow among RAG, CAG, and XRAG.
- 圖 4：Overall Architecture of the Proposed XRAG Framework.
- 圖 5：Data Flow of Case Corpus, Query Set, Reference Set, and Evaluation Outputs.
- 圖 6：Fixed 16-Slot Boolean Matrix Design for Traffic-Accident Civil Cases.
- 圖 7：Severity Reconstruction from Boolean Case Representation.
- 圖 8：Experiment-specific Score and Distance Design under Weight and Tau Settings.
- 圖 9：Anchor-centered Dual-Tree Retrieval Mechanism for Query-time Case Expansion.
- 圖 10：Local Bidirectional Expansion around the Anchor Case.
- 圖 11：Section-wise Complaint Generation with Structured Retrieved References.
- 圖 12：Naming Scheme of the 18 XRAG Experiment Configurations.
- 圖 13：Twelve-panel Evaluation Layout for XRAG, RAG Baseline, and CAG.
