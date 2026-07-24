# Chapter 5 Proposed SDKG Scheme

In this chapter, the proposed Severity-Aware Dual-Knowledge-Graph (SDKG) scheme is presented for traffic-accident civil complaint generation. The overall procedure of the proposed scheme is shown in Fig. 5.1, and the contents of phase 1, phase 2, and phase 3 are described as follows.

本章提出一種用於交通事故民事起訴書生成之嚴重度感知雙知識圖譜方案（Severity-Aware Dual-Knowledge-Graph, SDKG）。所提出方法之整體流程如 Fig. 5.1 所示，phase 1、phase 2 與 phase 3 之內容說明如下。

Chapter 4 uses paragraph and sentence summaries \(\bar{\theta}_{i,o}\) and \(\bar{\theta}_{i,o,v}\) for sentence-level-aware retrieval. Chapter 5 inherits the summary-based and dual-level organization, but changes the final retrieval unit from paragraphs and sentences to complete case nodes \(n_i\). Therefore, the summaries are no longer used as final retrieval units; instead, they support the construction of the legal feature vector \(\mathbf{f}_i\) and severity vector \(\mathbf{s}_i\).

第四章使用段落摘要 \(\bar{\theta}_{i,o}\) 與句子摘要 \(\bar{\theta}_{i,o,v}\) 進行 sentence-level-aware retrieval。第五章延續摘要化與雙層組織的精神，但將最終檢索單位由段落與句子提升為完整案件節點 \(n_i\)。因此，摘要不再作為最終檢索單位，而是用以支援法律特徵向量 \(\mathbf{f}_i\) 與嚴重度向量 \(\mathbf{s}_i\) 的建構。

![Figure 5.1 Overall procedure of the proposed SDKG scheme.](/home/aru/AI_LAW/0618-02.png)

**Figure 5.1. Overall procedure of the proposed SDKG scheme.** The proposed scheme consists of phase 1 case preprocessing, phase 2 dual-tree retrieval, and phase 3 complaint generation.

**_Phase 1: SDKG-based case preprocessing._** Phase 1 performs case preprocessing to prepare the structured case information required by phase 2. Traffic-accident complaint documents and simulated lawyer inputs are processed to construct observed cases \(\mathbf{c}_i\), legal feature vectors \(\mathbf{f}_i\), severity vectors \(\mathbf{s}_i\), and nodes \(n_i\).

**_Phase 1：案件前處理。_** Phase 1 執行案件前處理，準備 phase 2 所需之結構化案件資訊。交通事故起訴書文件與模擬律師輸入會被處理為可觀測案件 \(\mathbf{c}_i\)、法律特徵向量 \(\mathbf{f}_i\)、嚴重度向量 \(\mathbf{s}_i\) 與節點 \(n_i\)。

**_Phase 2: SDKG-based dual-tree retrieval._** Phase 2 constructs severity-aware DKG configurations \(g^{p,u,\ell}\) from the node set \(\mathcal{V}\) according to legal weight setting \(p\), threshold setting \(u\), and distance-weight setting \(\ell\). At query time, the lawyer input \(\mathbf{q}\) is mapped to the closest case \(c_i\) by the query-mapping distance \(d_{q,i}^{p,\ell}\), and the corresponding node \(n_i\) becomes the anchor node for light-heavy and heavy-light retrieval.

**_Phase 2：雙樹檢索。_** Phase 2 依法律權重設定 \(p\)、門檻設定 \(u\) 與距離權重設定 \(\ell\)，由節點集合 \(\mathcal{V}\) 建立嚴重度感知 DKG 配置 \(g^{p,u,\ell}\)。於查詢階段，律師輸入 \(\mathbf{q}\) 會透過查詢映射距離 \(d_{q,i}^{p,\ell}\) 映射至最近案件 \(c_i\)，且對應節點 \(n_i\) 成為 light-heavy 與 heavy-light 檢索之錨點節點。

**_Phase 3: SDKG-enhanced complaint generation._** Phase 3 assembles the lawyer input, the anchor case, retrieved reference sets, and drafting instructions into a structured prompt through \(\Phi(\cdot)\). The generation model \(M(\cdot)\) then generates the traffic-accident civil complaint.

**_Phase 3：起訴書生成。_** Phase 3 透過 \(\Phi(\cdot)\) 將律師輸入、錨點案件、檢索參考集合與撰寫指令組裝為結構化提示，再由生成模型 \(M(\cdot)\) 生成交通事故民事起訴書。

Fig. 5.2 provides a more detailed view of the proposed SDKG scheme. The legal datasets are first transformed by case feature extraction into legal feature vectors \(\mathbf{f}_i\) and severity vectors \(\mathbf{s}_i\). The case-to-node conversion \(\mathbf{c}_i\mapsto n_i\) produces the node set \(\mathcal{V}\). At query time, the lawyer query \(\mathbf{q}\) is mapped to the closest case \(c_i\), the corresponding node \(n_i\) becomes the anchor node, and the dual-tree retrieval module retrieves available heavier-side and lighter-side references \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\). The retrieved references are then placed into a structured prompt together with \(\mathbf{q}\) and drafting instructions.

Fig. 5.2 進一步呈現所提出方案之詳細架構。法律資料集先經由案件特徵抽取，轉換為法律特徵向量 \(\mathbf{f}_i\) 與嚴重度向量 \(\mathbf{s}_i\)。案件至節點轉換 \(\mathbf{c}_i\mapsto n_i\) 形成節點集合 \(\mathcal{V}\)。於查詢階段，律師輸入 \(\mathbf{q}\) 會被映射至最近案件 \(c_i\)，對應節點 \(n_i\) 成為錨點節點，雙樹檢索模組再取得可用之較重側與較輕側參考 \(\mathcal{R}_{LH}(\mathbf{q})\) 與 \(\mathcal{R}_{HL}(\mathbf{q})\)。最後，檢索參考會與 \(\mathbf{q}\) 及撰寫指令一同放入結構化提示。

The key point of Fig. 5.2 is the separation between preprocessing and query-time retrieval. Phase 1 and the preprocessing part of phase 2 prepare reusable node relations from all \(N=6{,}057\) cases. Query-time retrieval does not insert \(\mathbf{q}\) into the graph. The query \(\mathbf{q}\) only selects the closest case \(c_i\) and uses the corresponding node \(n_i\) as the anchor node. The fixed node structure remains stable, while each query obtains a query-specific retrieval view.

Fig. 5.2 的核心在於區分預處理與查詢階段檢索。Phase 1 與 phase 2 的預處理部分會由全部 \(N=6{,}057\) 筆案件準備可重複使用的節點關係。查詢階段不將 \(\mathbf{q}\) 新增為圖中節點；查詢 \(\mathbf{q}\) 僅用來選出最近案件 \(c_i\)，並使用對應節點 \(n_i\) 作為錨點節點。固定節點結構維持穩定，每一筆查詢則取得查詢專屬之檢索視角。

![Figure 5.2 Detailed architecture of the proposed SDKG scheme.](/home/aru/AI_LAW/ch4_slide-07.png)

**Figure 5.2. Detailed architecture of the proposed SDKG scheme.** The proposed SDKG scheme connects case feature extraction, severity-aware DKG construction, anchor mapping, dual-tree retrieval, structured prompt construction, and LLM generation. If the dual-tree module marks a signed delta, the delta denotes the illustrative weighted-severity difference used to indicate whether a comparable candidate is heavier or lighter than the current node; it is not an additional distance metric.

圖 5.2 若於雙樹檢索模組中標示 signed delta，該標示僅表示兩節點之加權嚴重度差，用來說明候選節點相對於目前節點為較重或較輕；它不是額外的距離指標。

Table 5.1 summarizes how phase 1, phase 2, and phase 3 in Fig. 5.1 and Fig. 5.2 correspond to the symbols defined in Chapter 3. Chapter 5 is an implementation-oriented explanation of the same system model. Phase 1 constructs \(\mathbf{c}_i\), \(\mathbf{f}_i\), and \(\mathbf{s}_i\). Phase 2 converts \(\mathbf{c}_i\) into \(n_i\), builds \(g^{p,u,\ell}\), and retrieves references through \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\). Phase 3 converts the retrieved references into a prompt and generates the final complaint.

Table 5.1 整理 Fig. 5.1 與 Fig. 5.2 中 phase 1、phase 2 與 phase 3 如何對應第三章定義之符號。第五章並非另起一套流程，而是針對同一系統模型進行實作層面的展開。Phase 1 建立 \(\mathbf{c}_i\)、\(\mathbf{f}_i\) 與 \(\mathbf{s}_i\)。Phase 2 將 \(\mathbf{c}_i\) 轉換為 \(n_i\)，建立 \(g^{p,u,\ell}\)，並透過 \(\mathcal{R}_{LH}(\mathbf{q})\) 與 \(\mathcal{R}_{HL}(\mathbf{q})\) 檢索參考。Phase 3 將檢索參考轉換為提示並生成最終起訴書。

**Table 5.1. Relationship between SDKG phases and Chapter 3 symbols.**

| Phase | Main symbols | Implementation meaning |
| --- | --- | --- |
| Phase 1 | observed case \(\mathbf{c}_i\), case material \(\mathbf{m}_i\), legal feature vector \(\mathbf{f}_i\), severity vector \(\mathbf{s}_i\) | Construct each observed case and prepare feature and severity attributes. |
| Phase 2 | node \(n_i\), node set \(\mathcal{V}\), node distance \(d_{i,j}^{p,\ell}\), threshold \(\tau^u\), DKG configuration \(g^{p,u,\ell}\), query-mapping distance \(d_{q,i}^{p,\ell}\), retrieved sets \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\) | Convert cases into nodes, build severity-aware configurations, map the query to the closest case \(c_i\), and retrieve references through two directions. |
| Phase 3 | lawyer query \(\mathbf{q}\), anchor case \(c_i\), retrieved sets \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\), prompt construction function \(\Phi(\cdot)\), generation model \(M(\cdot)\) | Assemble structured references and generate the final civil complaint. |

## 5.1 Phase 1: SDKG-based Case Preprocessing

The purpose of phase 1 is to transform raw complaint-style case materials and corresponding lawyer-input descriptions into structured observed cases that can support severity-aware retrieval. The lawyer input is the query-side starting point of SDKG, because the final complaint must be generated for the current lawyer query \(\mathbf{q}\). During preprocessing, the \(N=6{,}057\) observed cases are represented by the same type of input-side structure so that each case can later be compared with \(\mathbf{q}\). The output of phase 1 is \(\mathcal{D}=\{\mathbf{c}_i\mid 1\leq i\leq N\}\), where each \(\mathbf{c}_i\) contains \(\mathbf{m}_i\), \(\mathbf{f}_i\), and \(\mathbf{s}_i\).

Phase 1 的目的，是將原始起訴書樣式案件資料與對應律師輸入描述轉換為可支援嚴重度感知檢索的結構化可觀測案件。律師輸入是 SDKG 的 query-side 起點，因為最終起訴書必須針對當前律師查詢 \(\mathbf{q}\) 生成。於前處理階段，\(N=6{,}057\) 筆可觀測案件會被整理為相同類型的 input-side 結構，使每一筆案件後續皆可與 \(\mathbf{q}\) 進行比較。Phase 1 之輸出為 \(\mathcal{D}=\{\mathbf{c}_i\mid 1\leq i\leq N\}\)，其中每一個 \(\mathbf{c}_i\) 包含 \(\mathbf{m}_i\)、\(\mathbf{f}_i\) 與 \(\mathbf{s}_i\)。

![Figure 5.3 Phase 1 crop of the SDKG architecture.](/home/aru/AI_LAW/ch5_slide-07_phase1.png)

**Figure 5.3. Phase 1 crop of the SDKG architecture.** The lawyer input and legal datasets are transformed through case feature extraction into legal structure and case severity information, which support \(\mathbf{f}_i\), \(\mathbf{s}_i\), and the later case relation construction.

Fig. 5.3 highlights the phase 1 part of Fig. 5.2. The lawyer input side defines the form of the query \(\mathbf{q}\), while the legal dataset side provides the observed cases \(\mathbf{c}_i\). Case feature extraction prepares the legal structure and case severity attributes used to construct \(\mathbf{f}_i\) and \(\mathbf{s}_i\).

圖 5.3 對應圖 5.2 中的 phase 1 區塊。律師輸入端定義查詢 \(\mathbf{q}\) 的形式，法律資料集端則提供可觀測案件 \(\mathbf{c}_i\)。案件特徵抽取會準備法律結構與案件嚴重度屬性，用以建立 \(\mathbf{f}_i\) 與 \(\mathbf{s}_i\)。

### 5.1.1 Case Node Construction

The finalized phase 1 design is shown in Fig. 5.13. For each observed case \(\mathbf{c}_i\) in the observed case database \(\mathcal{D}\), the system uses the complaint-style case material \(\mathbf{m}_i\) and the corresponding simulated lawyer input as the input materials. The raw case materials are processed by two parallel modules. The first module constructs the legal feature vector \(\mathbf{f}_i\). The second module extracts the severity vector \(\mathbf{s}_i\). Following the notation in Chapter 3, the observed case \(\mathbf{c}_i\) is written as:

最終定稿之 phase 1 如 Fig. 5.13 所示。對於可觀測案件資料庫 \(\mathcal{D}\) 中的每一筆可觀測案件 \(\mathbf{c}_i\)，系統使用起訴書樣式案件材料 \(\mathbf{m}_i\) 及對應之模擬律師輸入作為材料。原始案件資料會經過兩個平行模組。第一個模組建立法律特徵向量 \(\mathbf{f}_i\)，用來描述案件的當事人、事實、傷勢與賠償結構；第二個模組抽取嚴重度向量 \(\mathbf{s}_i\)，用來描述案件在事實、傷勢與賠償三個面向上的程度。依第三章之符號，可觀測案件 \(\mathbf{c}_i\) 可寫為：

\[
\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i),
\quad 1\leq i\leq N,\quad N=6{,}057.
\tag{5.1}
\]

![Figure 5.13 SDKG-based case node construction.](/home/aru/AI_LAW/ch4_slide-18.png)

**Figure 5.13. SDKG-based case construction.** Raw complaint documents and simulated lawyer inputs are converted into observed cases, legal feature vectors, and severity vectors.

The observed case \(\mathbf{c}_i\) is the complete case-level unit prepared in phase 1. The case-level unit differs from the paragraph-level and sentence-level units in Chapter 4 because the proposed SDKG scheme retrieves complete cases rather than isolated chunks. The later tree construction converts each observed case into a node \(n_i\) through \(\mathbf{c}_i\mapsto n_i\), so legal facts, injury descriptions, compensation claims, and conclusions remain connected before node-level retrieval begins.

可觀測案件 \(\mathbf{c}_i\) 是 phase 1 準備的完整案件層級單位。此案件層級單位不同於第四章的段落層或句子層檢索單位，因為所提出方案檢索的是完整案件，而非孤立 chunks。後續樹狀建構會透過 \(\mathbf{c}_i\mapsto n_i\) 將每一筆可觀測案件轉換為節點 \(n_i\)，因此事故事實、傷勢描述、賠償請求與結論會先在案件層級保持連貫，再進入節點層級檢索。

The notation in (5.1) follows the system model in Chapter 3. The bold symbol \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\) denotes the observed case in \(\mathcal{D}\). The legal feature vector \(\mathbf{f}_i\) corresponds to the legal structure of case \(i\), and the severity vector \(\mathbf{s}_i=[s_{i,F},s_{i,U},s_{i,P}]^\top\) corresponds to fact, injury, and compensation severity. Phase 1 does not construct case relations. Phase 1 only prepares the case attributes required by phase 2.

式 (5.1) 延續第三章之系統模型符號。其中，粗體符號 \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\) 表示 \(\mathcal{D}\) 中的可觀測案件。\(\mathbf{f}_i\) 對應第 \(i\) 筆案件的法律結構，\(\mathbf{s}_i=[s_{i,F},s_{i,U},s_{i,P}]^\top\) 對應事實、傷勢與賠償三個面向的嚴重度。Phase 1 尚未建立案件關係，而是先準備 phase 2 所需之案件屬性。

### 5.1.2 Legal Feature Construction

The legal feature vector represents the legal structure of a case. As shown in Fig. 5.14, the proposed scheme uses boolean encoding to represent whether each legal feature appears in the case. The feature vector contains four groups: litigant-related features, fact-related features, injury-related features, and compensation-related features:

法律特徵向量表示案件之法律結構。如 Fig. 5.14 所示，所提出方案使用布林編碼表示各項法律特徵是否出現於案件中。特徵向量包含四組特徵：當事人相關特徵、事故事實相關特徵、傷勢相關特徵與賠償相關特徵：

\[
\mathbf{f}_i=[\mathbf{b}_{i,L};\mathbf{b}_{i,F};\mathbf{b}_{i,U};\mathbf{b}_{i,P}].
\tag{5.2}
\]

In (5.2), \(\mathbf{b}\) denotes a boolean feature vector, the subscript \(i\) denotes the case index, and the second subscript denotes the feature group. Specifically, \(L\), \(F\), \(U\), and \(P\) denote litigant-related, accident-fact-related, injury-related, and compensation-related feature groups, respectively. The symbol \(U\) is used for injury to avoid confusion with the case index \(i\). These boolean features allow the system to compare cases at the legal-structure level before considering severity scores.

式 (5.2) 中，\(\mathbf{b}\) 表示布林特徵向量，下標 \(i\) 表示案件編號，第二個下標表示特徵群組。其中，\(L\)、\(F\)、\(U\) 與 \(P\) 分別表示當事人相關、事故事實相關、傷勢相關與賠償相關特徵群。本文使用 \(U\) 表示傷勢特徵，以避免與案件索引 \(i\) 混淆。這些布林特徵使系統能先在法律結構層級比較案件，再進一步考慮嚴重度分數。

The four feature groups have different roles. Litigant-related features describe whether the case involves a single plaintiff, multiple plaintiffs, a single defendant, multiple defendants, an employer, an insurer, or other party configurations. Fact-related features describe accident behavior and liability clues such as negligence, gross negligence, joint liability, prior criminal judgment, speeding, failure to yield, or hit-and-run. Injury-related features describe affected body parts and injury patterns. Compensation-related features describe requested damages such as medical expenses, lost income, non-pecuniary damages, care expenses, and other claims. This feature design allows the distance function in phase 2 to compare cases using legal structure rather than only surface words.

四組特徵各有不同功能。當事人相關特徵描述案件是否涉及單一原告、多數原告、單一被告、多數被告、僱用人、保險人或其他當事人配置。事實相關特徵描述事故行為與責任線索，例如過失、重大過失、共同責任、是否有刑事判決、超速、未禮讓或肇事逃逸等。傷勢相關特徵描述受傷部位與傷害類型。賠償相關特徵描述請求損害項目，例如醫療費、不能工作損失、精神慰撫金、看護費與其他請求。此特徵設計使第二階段的距離函數能依法律結構比較案件，而不只是依表面文字相似度比較。

![Figure 5.14 Legal feature construction using boolean encoding.](/home/aru/AI_LAW/ch4_slide-19.png)

**Figure 5.14. Legal feature construction using boolean encoding.** The legal case is transformed into a boolean feature matrix covering litigants, facts, injuries, and compensation items.

### 5.1.3 Severity Extraction and Weighted Severity Scoring

Legal feature similarity alone is not sufficient for complaint drafting because two cases may share similar labels but differ significantly in accident seriousness, injury consequences, and compensation level. Therefore, the proposed scheme also extracts a severity vector:

僅有法律特徵相似度並不足以支援起訴書撰寫，因為兩個案件可能具有相似標籤，但在事故嚴重程度、傷害結果與賠償程度上差異甚大。因此，所提出方案進一步抽取嚴重度向量：

\[
\mathbf{s}_i=[s_{i,F},s_{i,U},s_{i,P}]^\top.
\tag{5.3}
\]

The three components denote fact severity, injury severity, and compensation severity. Fig. 5.15 illustrates the severity extraction table. Fact severity may reflect driving behavior and accident circumstances, injury severity may reflect medical consequences such as fracture, hospitalization, surgery, long-term care, or disability, and compensation severity may reflect the claimed or reconstructed compensation level.

其中三個分量分別表示事實嚴重度、傷勢嚴重度與賠償嚴重度。Fig. 5.15 顯示嚴重度抽取表。事實嚴重度可反映駕駛行為與事故情節；傷勢嚴重度可反映骨折、住院、手術、長期照護或失能等醫療後果；賠償嚴重度則反映請求或重建之賠償程度。

![Figure 5.15 Severity extraction and weighted severity scoring.](/home/aru/AI_LAW/ch4_slide-20.png)

**Figure 5.15. Severity extraction and weighted severity comparison.** Fact, injury, and compensation severity scores are extracted and compared under legal weight setting \(p\).

Under legal weight setting \(p\), the three severity dimensions are controlled by \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\). To avoid introducing an additional severity-score symbol, Chapter 5 directly uses the expanded weighted severity expression:

在法律權重設定 \(p\) 下，三個嚴重度面向分別由 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 控制。為避免另外引入加權嚴重度分數符號，第五章直接使用展開後之加權嚴重度表示：

\[
\alpha^p s_{i,F}
+
\beta^p s_{i,U}
+
(1-\alpha^p-\beta^p) s_{i,P},
\quad 1\leq p\leq 6.
\tag{5.4}
\]

The three weights used in (5.4) are:

式 (5.4) 使用之三個權重為：

\[
\alpha^p,\quad
\beta^p,\quad
(1-\alpha^p-\beta^p),
\quad 1\leq p\leq 6.
\tag{5.5}
\]

The severity direction is obtained by directly comparing the expanded weighted severity expression in (5.4) between two cases. If case \(j\) has a larger value than case \(i\), it is treated as the heavier-side case for light-heavy retrieval. If case \(j\) has a smaller value than case \(i\), it is treated as the lighter-side case for heavy-light retrieval.

嚴重度方向係直接比較兩案在式 (5.4) 下之展開加權嚴重度。若案件 \(j\) 的數值大於案件 \(i\)，則將其視為 light-heavy 檢索中的較重側案件；若案件 \(j\) 的數值小於案件 \(i\)，則將其視為 heavy-light 檢索中的較輕側案件。

For the light-heavy direction, the comparison is:

對 light-heavy 方向而言，其比較式為：

\[
\alpha^p s_{i,F}
+\beta^p s_{i,U}
+(1-\alpha^p-\beta^p)s_{i,P}
<
\alpha^p s_{j,F}
+\beta^p s_{j,U}
+(1-\alpha^p-\beta^p)s_{j,P}.
\]

For the heavy-light direction, the comparison is reversed:

對 heavy-light 方向而言，其比較式則相反：

\[
\alpha^p s_{i,F}
+\beta^p s_{i,U}
+(1-\alpha^p-\beta^p)s_{i,P}
>
\alpha^p s_{j,F}
+\beta^p s_{j,U}
+(1-\alpha^p-\beta^p)s_{j,P}.
\]

In (5.4)-(5.5), \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\) are the fact, injury, and compensation severity weights. A fact-oriented setting emphasizes accident behavior, an injury-oriented setting emphasizes bodily harm, and a compensation-oriented setting emphasizes monetary claim level. Phase 2 uses \(d_{i,j}^{p,\ell}\) to decide whether two nodes are close enough and uses the weighted severity comparison to decide the light-heavy or heavy-light direction.

式 (5.4) 至式 (5.5) 中，\(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 分別為事實、傷勢與賠償嚴重度權重。偏重事實的設定會強調事故行為，偏重傷勢的設定會強調身體損害，偏重賠償的設定則會強調金額請求程度。Phase 2 使用 \(d_{i,j}^{p,\ell}\) 判斷兩節點是否足夠接近，並使用加權嚴重度比較判斷 light-heavy 或 heavy-light 方向。

## 5.2 Phase 2: SDKG-based Dual-tree Retrieval

Phase 2 converts the observed cases produced in phase 1 into severity-aware retrieval structures. Phase 2 has two parts. The first part converts cases into nodes and constructs severity-aware DKG configurations. The second part performs query-time anchor mapping and dual-tree retrieval. The preprocessing part prepares node relations, while the query-time part uses those relations to retrieve top-\(k\) comparable references for a specific lawyer input.

Phase 2 將 phase 1 產生之可觀測案件轉換為嚴重度感知檢索結構。Phase 2 包含兩個部分。第一部分將案件轉換為節點並建立嚴重度感知 DKG 配置；第二部分執行查詢階段之錨點映射與雙樹檢索。預處理部分負責準備節點關係，查詢階段則使用這些關係，針對特定律師輸入檢索前 \(k\) 筆可比較參考。

![Figure 5.4 Phase 2 crop of the SDKG architecture.](/home/aru/AI_LAW/ch5_slide-07_phase2.png)

**Figure 5.4. Phase 2 crop of the SDKG architecture.** The preprocessed case relations form the severity-aware DKG, the lawyer query is mapped to an anchor node, and the dual-tree retrieval module obtains comparable heavier-side and lighter-side references.

Fig. 5.4 highlights the phase 2 part of Fig. 5.2. The preprocessed relations are represented by \(g^{p,u,\ell}\), the query \(\mathbf{q}\) is mapped to an anchor case \(c_i\) and anchor node \(n_i\), and the LH/HL directions define the node sets used to select \(\mathcal{R}(\mathbf{q})\).

圖 5.4 對應圖 5.2 中的 phase 2 區塊。前處理關係以 \(g^{p,u,\ell}\) 表示，查詢 \(\mathbf{q}\) 會映射至錨點案件 \(c_i\) 與錨點節點 \(n_i\)，LH/HL 方向則形成用於選取 \(\mathcal{R}(\mathbf{q})\) 的節點集合。

The conversion from case to node is written as:

案件轉換為節點之關係寫為：

\[
\mathbf{c}_i\mapsto n_i,\quad 1\leq i\leq N,\quad N=6{,}057.
\tag{5.6}
\]

The complete node set is:

完整節點集合為：

\[
\mathcal{V}=\{n_i\mid 1\leq i\leq N\}.
\tag{5.7}
\]

The query-time part does not insert \(\mathbf{q}\) into \(\mathcal{V}\). Query-time retrieval only maps \(\mathbf{q}\) to one existing case \(c_i\), uses the corresponding node \(n_i\) as the anchor node, and expands two retrieval trees for that query.

查詢階段不將 \(\mathbf{q}\) 加入 \(\mathcal{V}\)。查詢階段檢索僅將 \(\mathbf{q}\) 映射至一個既有案件 \(c_i\)，使用對應節點 \(n_i\) 作為錨點節點，並針對該查詢展開兩棵檢索樹。

### 5.2.1 Preprocessing Construction of Severity-Aware DKG Configurations

As shown in Fig. 5.16, the system starts from \(\mathcal{V}\) and applies six legal weight settings, three threshold settings, and three distance-weight settings. The legal weight setting \(p\) determines the weighted severity comparison used for the light-heavy and heavy-light directions. The threshold setting \(u\) determines whether two nodes are close enough to become comparable candidates. The distance-weight setting \(\ell\) determines the relative contribution of legal feature distance and severity distance in (5.8). Together, these settings produce \(6\times3\times3=54\) severity-aware DKG configurations.

如 Fig. 5.16 所示，系統由 \(\mathcal{V}\) 出發，套用六組法律權重設定、三組距離門檻設定與三組距離權重設定。法律權重設定 \(p\) 決定 light-heavy 與 heavy-light 方向所使用之加權嚴重度比較；門檻設定 \(u\) 決定兩節點是否足以成為可比較候選；距離權重設定 \(\ell\) 決定式 (5.8) 中法律特徵距離與嚴重度距離之相對比重。三者組合後形成 \(6\times3\times3=54\) 組嚴重度感知 DKG 配置。

![Figure 5.16 Preprocessing construction of severity-aware DKG configurations.](/home/aru/AI_LAW/ch4_slide-21.png)

**Figure 5.16. Preprocessing construction of severity-aware DKG configurations.** The same 6,057 nodes are evaluated under six legal weight settings, three threshold settings, and three distance-weight settings to construct fifty-four severity-aware DKG configurations. The signed delta in the construction diagram is a visual annotation of the weighted-severity difference between two nodes, used only to explain the heavier/lighter direction after the distance threshold and dominant-feature condition have been checked.

Fig. 5.16 中之 signed delta 為兩節點加權嚴重度差的視覺化標示，用於輔助說明在距離門檻與主導特徵條件成立後，如何判斷較重或較輕方向；本文正式建構條件仍以加權嚴重度分數比較為準。

For any two nodes \(n_i,n_j\in\mathcal{V}\), the node distance under legal weight setting \(p\) and distance-weight setting \(\ell\) is:

對於任意兩個節點 \(n_i,n_j\in\mathcal{V}\)，其在法律權重設定 \(p\) 與距離權重設定 \(\ell\) 下之節點距離為：

\[
d_{i,j}^{p,\ell}
=\lambda^{\ell} d_f(\mathbf{f}_i,\mathbf{f}_j)
+(1-\lambda^{\ell}) d_s^{p}(\mathbf{s}_i,\mathbf{s}_j).
\tag{5.8}
\]

In (5.8), \(d_f(\mathbf{f}_i,\mathbf{f}_j)\) measures the legal feature distance, and \(d_s^{p}(\mathbf{s}_i,\mathbf{s}_j)\) denotes the severity-distance function under weight setting \(p\). The distance weights \(\lambda^{\ell}\) and \((1-\lambda^{\ell})\) control the relative importance of legal structure and severity.

式 (5.8) 中，\(d_f(\mathbf{f}_i,\mathbf{f}_j)\) 衡量法律特徵距離，\(d_s^{p}(\mathbf{s}_i,\mathbf{s}_j)\) 表示權重設定 \(p\) 下之嚴重度距離函數。距離權重 \(\lambda^{\ell}\) 與 \((1-\lambda^{\ell})\) 分別控制法律結構與嚴重度之相對重要性。

Before the threshold rule is applied, the implementation identifies the dominant feature group from the largest weight among \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\). If the fact weight is dominant, the accident-fact feature group is used; if the injury weight is dominant, the injury feature group is used; if the compensation weight is dominant, the compensation feature group is used. A pair of nodes is eligible for relation construction only when the node distance satisfies the distance threshold \(\tau^u\) and the two cases share at least one boolean feature in this dominant feature group:

在套用門檻規則前，實作會先由 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 三者中的最大權重決定主導特徵群。若事實權重最大，則使用事故事實特徵群；若傷勢權重最大，則使用傷勢特徵群；若賠償權重最大，則使用賠償特徵群。兩節點必須同時滿足距離門檻 \(\tau^u\)，且兩案在此主導特徵群中至少共享一個 boolean feature，才具有建立關係之資格：

\[
d_{i,j}^{p,\ell}\leq\tau^u
\quad,\quad
\left[
\begin{aligned}
&\alpha^p=\max\{\alpha^p,\beta^p,1-\alpha^p-\beta^p\}
\land \mathbf{b}_{i,F}\cdot\mathbf{b}_{j,F}>0\\
&\lor\ \beta^p=\max\{\alpha^p,\beta^p,1-\alpha^p-\beta^p\}
\land \mathbf{b}_{i,U}\cdot\mathbf{b}_{j,U}>0\\
&\lor\ (1-\alpha^p-\beta^p)=\max\{\alpha^p,\beta^p,1-\alpha^p-\beta^p\}
\land \mathbf{b}_{i,P}\cdot\mathbf{b}_{j,P}>0
\end{aligned}
\right].
\tag{5.9}
\]

Accordingly, the comparable-node relation set \(E^{p,u,\ell}\) under weight setting \(p\), threshold setting \(u\), and distance-weight setting \(\ell\) is:

因此，在權重設定 \(p\)、門檻設定 \(u\) 與距離權重設定 \(\ell\) 下，可比較節點關係集合 \(E^{p,u,\ell}\) 定義為：

\[
E^{p,u,\ell}
=
\{(n_i,n_j)\mid n_i,n_j\in\mathcal{V},\ i\neq j,
(5.9)\}.
\tag{5.10}
\]

The threshold and shared-feature conditions define comparable neighboring candidates, but these conditions do not by themselves define a retrieval tree. The light-heavy direction additionally requires the child node to be heavier than the parent node:

門檻條件與共同特徵條件僅定義可比較的鄰近候選節點，但這些條件本身尚未定義檢索樹。light-heavy 方向進一步要求子節點比父節點更重：

\[
n_i\xrightarrow{\mathrm{LH}}n_j
\Longleftrightarrow
(n_i,n_j)\in E^{p,u,\ell}
\ \land\
\alpha^p s_{i,F}
+\beta^p s_{i,U}
+(1-\alpha^p-\beta^p)s_{i,P}
<
\alpha^p s_{j,F}
+\beta^p s_{j,U}
+(1-\alpha^p-\beta^p)s_{j,P}.
\tag{5.11}
\]

The heavy-light direction instead requires the child node to be lighter than the parent node:

heavy-light 方向則要求子節點比父節點更輕：

\[
n_i\xrightarrow{\mathrm{HL}}n_j
\Longleftrightarrow
(n_i,n_j)\in E^{p,u,\ell}
\ \land\
\alpha^p s_{i,F}
+\beta^p s_{i,U}
+(1-\alpha^p-\beta^p)s_{i,P}
>
\alpha^p s_{j,F}
+\beta^p s_{j,U}
+(1-\alpha^p-\beta^p)s_{j,P}.
\tag{5.12}
\]

Equation (5.11) keeps node relations from lighter nodes to heavier nodes. Equation (5.12) keeps node relations from heavier nodes to lighter nodes. Equal-severity relations are excluded because no clear severity direction exists. The threshold and shared-feature conditions in (5.9)-(5.10) prevent cases from being connected only because their aggregate severity scores are close. For example, under an injury-oriented setting, a case with only head-neck injury features is not connected to a case with only extremity injury features unless another dominant injury feature is shared.

式 (5.11) 保留由較輕節點指向較重節點之關係。式 (5.12) 保留由較重節點指向較輕節點之關係。相同嚴重度關係不被納入，因為相同嚴重度無法提供明確方向。式 (5.9) 至式 (5.10) 的門檻與共同特徵條件，可避免兩案僅因總體嚴重度分數接近而被連接。例如在偏重傷勢的設定下，僅有頭頸部傷勢特徵的案件，不會與僅有四肢傷勢特徵的案件連接，除非兩案另有共同的主導傷勢特徵。

Each severity-aware DKG configuration \(g^{p,u,\ell}\) is represented as:

每一組嚴重度感知 DKG 配置 \(g^{p,u,\ell}\) 表示為：

\[
g^{p,u,\ell}=(\mathcal{V},E^{p,u,\ell}),
\quad 1\leq p\leq 6,\quad 1\leq u\leq 3,\quad 1\leq \ell\leq 3.
\tag{5.13}
\]

where \(\mathcal{V}\) is the same node set for all configurations, and \(E^{p,u,\ell}\) is the relation set determined by the selected legal weight, threshold, and distance-weight settings. The full collection of configurations is:

其中，\(\mathcal{V}\) 為所有配置共用之節點集合，\(E^{p,u,\ell}\) 則為依所選法律權重、門檻與距離權重形成之關係集合。完整配置集合表示為：

\[
\{g^{p,u,\ell}\mid 1\leq p\leq 6,\ 1\leq u\leq 3,\ 1\leq \ell\leq 3\},
\quad
\left|\{g^{p,u,\ell}\mid 1\leq p\leq 6,\ 1\leq u\leq 3,\ 1\leq \ell\leq 3\}\right|=54.
\tag{5.14}
\]

In the experimental implementation, the threshold settings are \(\tau^u\in\{0.1,0.25,0.5\}\), corresponding to low, medium, and high relation thresholds. The distance-weight settings are \(\lambda^{\ell}\in\{0.2,0.5,0.7\}\), where a larger \(\lambda^{\ell}\) gives more weight to legal feature distance and a smaller \(\lambda^{\ell}\) gives more weight to severity distance.

於實驗實作中，門檻設定為 \(\tau^u\in\{0.1,0.25,0.5\}\)，分別對應低、中、高關係門檻。距離權重設定為 \(\lambda^{\ell}\in\{0.2,0.5,0.7\}\)，其中較大的 \(\lambda^{\ell}\) 代表更重視法律特徵距離，較小的 \(\lambda^{\ell}\) 則代表更重視嚴重度距離。

### 5.2.2 Query-time Anchor Mapping and top-\(k\) Dual-tree Retrieval

At query time, the lawyer query \(\mathbf{q}\) is first processed by the same type of extraction used for database cases. The system obtains the query legal feature vector \(\mathbf{f}_q\) and the query severity vector \(\mathbf{s}_q\):

於查詢階段，律師查詢 \(\mathbf{q}\) 會先經過與資料庫案件相同類型之抽取。系統取得查詢法律特徵向量 \(\mathbf{f}_q\) 與查詢嚴重度向量 \(\mathbf{s}_q\)：

\[
\mathbf{q}\mapsto(\mathbf{f}_q,\mathbf{s}_q).
\tag{5.15}
\]

The query-mapping distance \(d_{q,i}^{p,\ell}\) between query \(\mathbf{q}\) and case \(c_i\in\mathcal{D}\) is computed as:

查詢 \(\mathbf{q}\) 與案件 \(c_i\in\mathcal{D}\) 之查詢映射距離 \(d_{q,i}^{p,\ell}\) 定義為：

\[
d_{q,i}^{p,\ell}
=\lambda^{\ell} d_f(\mathbf{f}_q,\mathbf{f}_i)
+(1-\lambda^{\ell}) d_s^{p}(\mathbf{s}_q,\mathbf{s}_i).
\tag{5.16}
\]

The query is not inserted into \(\mathcal{V}\) as a new node. The closest case \(c_i\) retrieved by \(d_{q,i}^{p,\ell}\) satisfies the anchor condition \(a(c_i,\mathbf{q})\):

查詢不會被加入 \(\mathcal{V}\) 成為新節點。經由 \(d_{q,i}^{p,\ell}\) 取得之最近案件 \(c_i\) 滿足錨點條件 \(a(c_i,\mathbf{q})\)：

\[
a(c_i,\mathbf{q})
\Longleftrightarrow
c_i
=
\operatorname*{arg\,min}_{c_j\in\mathcal{D}}
\left\{
d_{q,j}^{p,\ell}
\right\}.
\tag{5.17}
\]

After the anchor case \(c_i\) is selected by (5.17), the conversion \(\mathbf{c}_i\mapsto n_i\) gives the corresponding anchor node \(n_i\). The selected severity-aware DKG configuration \(g^{p,u,\ell}\) provides the comparable-node relation set \(E^{p,u,\ell}\). Starting from \(n_i\), the system defines two query-specific retrieval trees by (5.18)-(5.20). The final top-\(k\) references are then selected from the node sets in (5.22)-(5.24) according to the query-to-node distance in (5.25).

錨點案件 \(c_i\) 經式 (5.17) 選出後，案件至節點之轉換 \(\mathbf{c}_i\mapsto n_i\) 給出對應錨點節點 \(n_i\)。所選嚴重度感知 DKG 配置 \(g^{p,u,\ell}\) 提供可比較節點關係集合 \(E^{p,u,\ell}\)。系統以 \(n_i\) 作為起始節點，並依式 (5.18) 至式 (5.20) 定義兩棵查詢專屬檢索樹。最終 top-\(k\) 參考則由式 (5.22) 至式 (5.24) 的節點集合取得，並依式 (5.25) 中的查詢至節點距離選取。

Let \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\) and \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\) denote the two query-specific retrieval trees expanded from anchor node \(n_i\). The two trees are initialized as:

令 \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\) 與 \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\) 表示由錨點節點 \(n_i\) 展開之兩棵查詢專屬檢索樹。兩棵樹之初始化為：

\[
\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\leftarrow\{n_i\},
\quad
\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\leftarrow\{n_i\}.
\tag{5.18}
\]

For any current node \(n_i\) in \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\) and any candidate node \(n_j\in\mathcal{V}\), the light-heavy expansion rule is:

對 \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\) 中任一目前節點 \(n_i\) 與任一候選節點 \(n_j\in\mathcal{V}\)，light-heavy 展開規則為：

\[
n_i\xrightarrow{\mathrm{LH}}n_j
\Longleftrightarrow
(n_i,n_j)\in E^{p,u,\ell}
\ \land\
\alpha^p s_{i,F}
+\beta^p s_{i,U}
+(1-\alpha^p-\beta^p)s_{i,P}
<
\alpha^p s_{j,F}
+\beta^p s_{j,U}
+(1-\alpha^p-\beta^p)s_{j,P}.
\tag{5.19}
\]

For any current node \(n_i\) in \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\) and any candidate node \(n_j\in\mathcal{V}\), the heavy-light expansion rule is:

對 \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\) 中任一目前節點 \(n_i\) 與任一候選節點 \(n_j\in\mathcal{V}\)，heavy-light 展開規則為：

\[
n_i\xrightarrow{\mathrm{HL}}n_j
\Longleftrightarrow
(n_i,n_j)\in E^{p,u,\ell}
\ \land\
\alpha^p s_{i,F}
+\beta^p s_{i,U}
+(1-\alpha^p-\beta^p)s_{i,P}
>
\alpha^p s_{j,F}
+\beta^p s_{j,U}
+(1-\alpha^p-\beta^p)s_{j,P}.
\tag{5.20}
\]

For each included child node \(n_j\), the corresponding directional tree keeps one parent node. Let \(h_j\) denote the retained parent node of \(n_j\), and let \(n_h\) denote a possible parent node that has already been reached. If multiple reached nodes can connect to \(n_j\), \(h_j\) is selected by:

對每一個被納入之子節點 \(n_j\) 而言，對應方向樹只會保留一個父節點。令 \(h_j\) 表示 \(n_j\) 被保留之父節點，並令 \(n_h\) 表示已到達且可能成為父節點的節點。若多個已到達節點皆可連接至 \(n_j\)，則 \(h_j\) 之選擇方式為：

\[
\begin{aligned}
h_j
&=
\operatorname*{arg\,min}_{n_h}
d_{h,j}^{p,\ell},\\
\mathrm{s.t.}\quad
&n_h\xrightarrow{\mathrm{LH}}n_j
\lor
n_h\xrightarrow{\mathrm{HL}}n_j,\\
&n_h\in
\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})
\lor
n_h\in
\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q}).
\end{aligned}
\tag{5.21}
\]

This rule keeps a unique parent for each included child node, while one parent node may still have multiple child nodes. The anchor condition remains \(a(c_i,\mathbf{q})\) in (5.17); \(h_j\) in (5.21) only describes parent selection inside the retrieval trees.

此規則使每一個被納入之子節點只保留一個父節點，但同一父節點仍可具有多個子節點。錨點條件仍為式 (5.17) 的 \(a(c_i,\mathbf{q})\)；式 (5.21) 的 \(h_j\) 僅描述檢索樹內部的父節點選擇。

The two severity directions first produce reachable non-anchor node sets. Let \(\mathcal{V}_{LH}(\mathbf{q})\) and \(\mathcal{V}_{HL}(\mathbf{q})\) denote the non-anchor nodes reached by the two retrieval trees:

兩個嚴重度方向會先形成可到達之非錨點節點集合。令 \(\mathcal{V}_{LH}(\mathbf{q})\) 與 \(\mathcal{V}_{HL}(\mathbf{q})\) 表示兩棵檢索樹中被到達且非錨點之節點：

\[
\mathcal{V}_{LH}(\mathbf{q})
=
\{n_j\mid n_i\leadsto n_j\in\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q}),\ n_j\neq n_i\},
\tag{5.22}
\]

\[
\mathcal{V}_{HL}(\mathbf{q})
=
\{n_j\mid n_i\leadsto n_j\in\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q}),\ n_j\neq n_i\}.
\tag{5.23}
\]

The two directional node sets define the available SDKG node set for query \(\mathbf{q}\):

兩個方向節點集合共同形成查詢 \(\mathbf{q}\) 下可用之 SDKG 節點集合：

\[
\mathcal{V}_{\mathrm{SDKG}}(\mathbf{q})
=
\mathcal{V}_{LH}(\mathbf{q})
\cup
\mathcal{V}_{HL}(\mathbf{q}).
\tag{5.24}
\]

The final retrieved set \(\mathcal{R}(\mathbf{q})\) is selected from \(\mathcal{V}_{\mathrm{SDKG}}(\mathbf{q})\) by minimizing the total query-to-node distance under the top-\(k\) budget. If fewer than \(k\) nodes are available, all available nodes can be selected:

最終檢索集合 \(\mathcal{R}(\mathbf{q})\) 由 \(\mathcal{V}_{\mathrm{SDKG}}(\mathbf{q})\) 中選取，並在 top-\(k\) 預算內使查詢至節點距離總和最小。若可用節點少於 \(k\) 個，則選取所有可用節點：

\[
\begin{aligned}
\mathcal{R}(\mathbf{q})
&=
\operatorname*{arg\,min}_{R}
\sum_{n_j\in R} d_{q,j}^{p,\ell},\\
\mathrm{s.t.}\quad
&n_j\in\mathcal{V}_{\mathrm{SDKG}}(\mathbf{q}),
\quad
\forall n_j\in R,\\
&|R|
=
\min\{k,|\mathcal{V}_{\mathrm{SDKG}}(\mathbf{q})|\}.
\end{aligned}
\tag{5.25}
\]

For analysis and prompt assembly, the selected references can still be separated by their source direction:

為了分析與提示組裝，所選參考仍可依其來源方向分為：

\[
\mathcal{R}_{LH}(\mathbf{q})
=
\mathcal{R}(\mathbf{q})
\cap
\mathcal{V}_{LH}(\mathbf{q}),
\quad
\mathcal{R}_{HL}(\mathbf{q})
=
\mathcal{R}(\mathbf{q})
\cap
\mathcal{V}_{HL}(\mathbf{q}).
\tag{5.26}
\]

Equations (5.24)-(5.26) use the two trees to form the available SDKG node set and then select nodes by \(d_{q,j}^{p,\ell}\) within the top-\(k\) budget. The method does not force each direction to return a fixed number of cases. If one direction has no comparable nodes, the final reference set is selected from the available direction only.

式 (5.24) 至式 (5.26) 先由兩棵樹形成可用 SDKG 節點集合，再於 top-\(k\) 預算內依 \(d_{q,j}^{p,\ell}\) 選取節點。此方法不強迫每一方向回傳固定數量之案例；若某一方向沒有可比較節點，最終參考集合即由可用方向中選取。

This retrieval rule preserves the benefit of two severity directions without imposing a rigid balance constraint. When both directions contain comparable candidates, the final reference set may include both heavier-side and lighter-side examples. When only one side contains useful candidates, the system avoids injecting unrelated cases merely to satisfy a directional quota.

此檢索規則保留兩個嚴重度方向的優點，但不施加僵硬的平衡限制。當兩側皆有可比較候選時，最終參考集合可同時包含較重側與較輕側案例；當僅有一側具有可用候選時，系統不會為了滿足方向配額而加入不相關案例。

**Algorithm 5.1. Anchor mapping and dual-tree retrieval with top-\(k\) budget.**

```text
Input: lawyer query \mathbf{q}, observed case database \mathcal{D},
configuration g^{p,u,\ell}=(\mathcal{V},E^{p,u,\ell}), top-\(k\) budget k
Output: retrieved reference set \mathcal{R}(\mathbf{q}) and direction groups
\mathcal{R}_{LH}(\mathbf{q}), \mathcal{R}_{HL}(\mathbf{q})

1. Extract the query legal feature vector \mathbf{f}_q.
2. Extract the query severity vector \mathbf{s}_q.
3. Compute d_{q,i}^{p,\ell} from \mathbf{q} to each case \mathbf{c}_i\in\mathcal{D}.
4. Select the nearest case \mathbf{c}_i satisfying a(c_i,\mathbf{q}).
5. Convert the anchor case into the anchor node n_i by \mathbf{c}_i\mapsto n_i.
6. Initialize \mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q}) and
   \mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q}) with the anchor node n_i.
7. Expand the light-heavy tree from reached nodes using n_h\xrightarrow{\mathrm{LH}}n_j.
8. Expand the heavy-light tree from reached nodes using n_h\xrightarrow{\mathrm{HL}}n_j.
9. Form \mathcal{V}_{LH}(\mathbf{q}), \mathcal{V}_{HL}(\mathbf{q}), and
   \mathcal{V}_{\mathrm{SDKG}}(\mathbf{q}) from the two directional trees.
10. Select \mathcal{R}(\mathbf{q}) from \mathcal{V}_{\mathrm{SDKG}}(\mathbf{q})
    under the top-\(k\) budget using d_{q,j}^{p,\ell}.
11. Separate \mathcal{R}(\mathbf{q}) into
    \mathcal{R}_{LH}(\mathbf{q}) and \mathcal{R}_{HL}(\mathbf{q}).
```

## 5.3 Phase 3: SDKG-enhanced Complaint Generation

Phase 3 converts the retrieval results from phase 2 into a structured prompt and generates the final traffic-accident civil complaint. The retrieved nodes are first mapped back to their corresponding cases. The anchor case is indicated by \(a(c_i,\mathbf{q})\) in (5.17), while the reference cases are represented by the source-direction groups \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\) in (5.26). These two groups are derived from the final retrieved set \(\mathcal{R}(\mathbf{q})\) in (5.25). The generator uses comparable cases without replacing the facts of the current query case.

Phase 3 將 phase 2 取得的檢索結果轉換為結構化提示，並生成最終交通事故民事起訴書。被檢索之節點會先映射回對應案件。錨點案件由式 (5.17) 的 \(a(c_i,\mathbf{q})\) 表示，參考案件則由式 (5.26) 的來源方向群組 \(\mathcal{R}_{LH}(\mathbf{q})\) 與 \(\mathcal{R}_{HL}(\mathbf{q})\) 表示。這兩組參考由式 (5.25) 的最終檢索集合 \(\mathcal{R}(\mathbf{q})\) 拆分而來。生成模型使用可比較案件，但不取代當前查詢案件本身的事實。

![Figure 5.5 Phase 3 crop of the SDKG architecture.](/home/aru/AI_LAW/ch5_slide-07_phase3.png)

**Figure 5.5. Phase 3 crop of the SDKG architecture.** The lawyer query, retrieved references, and drafting instructions are assembled into a structured prompt, and the generation model produces the civil complaint response.

Fig. 5.5 highlights the phase 3 part of Fig. 5.2. The structured prompt \(\mathbf{z}_{p,u,\ell}\) combines \(\mathbf{q}\), the anchor case, retrieved references, and drafting instructions. The generation model \(M(\cdot)\) then produces \(\hat{\mathbf{y}}_{p,u,\ell}\).

圖 5.5 對應圖 5.2 中的 phase 3 區塊。結構化提示 \(\mathbf{z}_{p,u,\ell}\) 結合 \(\mathbf{q}\)、錨點案件、檢索參考與撰寫指令，再由生成模型 \(M(\cdot)\) 產生 \(\hat{\mathbf{y}}_{p,u,\ell}\)。

As shown in Fig. 5.18, the prompt assembler \(\Phi(\cdot)\) receives four inputs: the lawyer query \(\mathbf{q}\), the anchor case indicated by \(a(c_i,\mathbf{q})\), the two source-direction reference groups \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\), and the drafting instruction set \(\mathbf{I}\).

如 Fig. 5.18 所示，提示組裝器 \(\Phi(\cdot)\) 接收四項輸入：律師查詢 \(\mathbf{q}\)、由 \(a(c_i,\mathbf{q})\) 表示之錨點案件、兩組來源方向參考 \(\mathcal{R}_{LH}(\mathbf{q})\) 與 \(\mathcal{R}_{HL}(\mathbf{q})\)，以及撰寫指令集合 \(\mathbf{I}\)。

![Figure 5.18 SDKG-enhanced complaint generation.](/home/aru/AI_LAW/ch4_slide-23.png)

**Figure 5.18. SDKG-enhanced complaint generation.** The lawyer input, anchor case, two severity-side reference sets, and drafting instructions are assembled into a structured prompt for complaint generation.

The structured prompt is assembled by \(\Phi(\cdot)\) from \(\mathbf{q}\), the anchor case indicated by \(a(c_i,\mathbf{q})\), the two source-direction reference groups \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\), and the drafting instruction set \(\mathbf{I}\):

結構化提示由提示組裝器 \(\Phi(\cdot)\) 根據 \(\mathbf{q}\)、由 \(a(c_i,\mathbf{q})\) 表示之錨點案件、兩組來源方向參考 \(\mathcal{R}_{LH}(\mathbf{q})\) 與 \(\mathcal{R}_{HL}(\mathbf{q})\)，以及撰寫指令集合 \(\mathbf{I}\) 建立：

\[
\mathbf{z}_{p,u,\ell}
=
\Phi\!\left(
\mathbf{q},
a(c_i,\mathbf{q}),
\mathcal{R}_{LH}(\mathbf{q}),
\mathcal{R}_{HL}(\mathbf{q}),
\mathbf{I}
\right).
\tag{5.27}
\]

The generated complaint is then produced by:

接著，生成之起訴書由下式產生：

\[
\hat{\mathbf{y}}_{p,u,\ell}=M(\mathbf{z}_{p,u,\ell}).
\tag{5.28}
\]

The prompt content depends on weight setting \(p\), threshold setting \(u\), and distance-weight setting \(\ell\) because the anchor case and retrieved references are produced from \(g^{p,u,\ell}\).

提示內容會受到權重設定 \(p\)、門檻設定 \(u\) 與距離權重設定 \(\ell\) 影響，因為錨點案件與檢索參考皆來自 \(g^{p,u,\ell}\)。

The structured prompt separates four types of information. First, the lawyer input provides the current case facts and drafting target. This part has the highest priority because the generated complaint must be written for the current query case. Second, the anchor case provides the closest case-level reference. The anchor case is not used as a template to be copied, but as a reference case that indicates the most comparable legal structure under the selected weight setting. Third, the light-heavy and heavy-light references provide heavier-side and lighter-side comparable cases. These two sets give the generator a severity range around the query case. Fourth, the drafting instructions constrain the generator to preserve the query facts, avoid unsupported fact borrowing, maintain legal pleading structure, and generate the complaint in the expected section order.

結構化提示區分四類資訊。第一，律師輸入提供當前案件事實與撰寫目標，且具有最高優先性，因為生成之起訴書必須服務於當前查詢案件。第二，錨點案件提供最接近之案件層級參考。錨點案件不是用來直接複製的模板，而是表示在所選權重設定下，與當前案件法律結構最接近的參考案件。第三，light-heavy 與 heavy-light 參考集合提供較重側與較輕側之可比較案例，使生成模型能掌握當前案件周圍的嚴重度範圍。第四，撰寫指令限制生成模型必須保留查詢事實、避免未受支持之事實借用、維持法律書狀結構，並依預期段落順序生成起訴書。

The role of the anchor case differs from the role of the two retrieval trees. The anchor case \(c_i\) in (5.17) represents the nearest existing case selected by \(d_{q,i}^{p,\ell}\). The corresponding anchor node \(n_i\) starts \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\) and \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\). A single anchor case may be insufficient for drafting because a single case provides only one reference point. Therefore, the proposed scheme further retrieves two groups of neighboring nodes from different severity directions. The light-heavy tree supplies heavier references, while the heavy-light tree supplies lighter references.

錨點案件與兩棵檢索樹的角色不同。式 (5.17) 中之錨點案件 \(c_i\) 表示經由 \(d_{q,i}^{p,\ell}\) 選出之最近既有案件。對應錨點節點 \(n_i\) 用以啟動 \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\) 與 \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\)。單一錨點案件對撰寫而言仍可能不足，因為單一案件只提供一個參考點。因此，所提出方案進一步由兩個嚴重度方向檢索鄰近節點。light-heavy tree 提供較重參考，heavy-light tree 提供較輕參考。

The directional reference allocation also affects generation. If all references are selected only by distance, the reference set may contain mostly cases from one severity side. For example, if the nearest neighbors are mostly lighter cases, the generator may underestimate the compensation context of a more serious query. Conversely, if the nearest neighbors are mostly heavier cases, the generator may overstate the injury consequence or compensation level. The proposed allocation gives priority to both severity directions when comparable candidates are available, while still avoiding forced retrieval from a side with no sufficiently similar cases. This does not mean that the final complaint mechanically averages the two sides. Instead, the two sides provide controlled comparative context, while the lawyer query remains the primary factual source.

方向參考分配也會影響生成結果。若所有參考案例都只依距離選取，參考集合可能集中於單一嚴重度方向。例如，若最近鄰多為較輕案件，模型可能低估較嚴重查詢案件之賠償脈絡；反之，若最近鄰多為較重案件，模型可能高估傷勢後果或賠償程度。所提出分配方式會在兩側皆有可比較候選時優先納入兩個嚴重度方向，同時避免從沒有足夠相似案例的一側強迫檢索。這並不表示最終起訴書會機械式取兩側平均，而是讓兩側參考提供受控制的比較脈絡，並仍以律師查詢作為主要事實來源。

The generated complaint is organized into four major sections: facts, legal grounds, compensation, and conclusion. The facts section mainly follows the lawyer input and should not introduce facts that appear only in retrieved cases. The legal grounds section uses retrieved references to support legal provisions and liability reasoning. The compensation section uses severity-side references as comparative support for damages and compensation items. The conclusion section summarizes the final claims and requested relief. This section-level organization follows the complaint-structure observation in Chapter 4, but the source of references is different: the final SDKG scheme obtains references through severity-aware dual-tree retrieval rather than only sentence-level or paragraph-level similarity retrieval.

生成之起訴書被組織為四個主要段落：事實、法律依據、損害賠償與結論。事實段落主要依據律師輸入，不應加入僅存在於檢索案例中的事實。法律依據段落使用檢索參考支援法條與責任論述。損害賠償段落使用兩個嚴重度方向之參考案例，作為損害項目與賠償程度之比較依據。結論段落則整理最終請求與聲明。此段落組織延續第四章對起訴書結構的觀察，但參考來源已不同：最終方案透過嚴重度感知雙樹檢索取得參考，而不只是依句子或段落相似度取得文字。

**Table 5.2. Components of the structured prompt.**

| Component | Role in generation |
| --- | --- |
| Lawyer input \(\mathbf{q}\) | Provides the current case facts and drafting target. |
| Anchor case \(c_i\) | Provides the nearest case-level reference selected by \(d_{q,i}^{p,\ell}\). |
| \(\mathcal{R}_{LH}(\mathbf{q})\) | Provides available heavier-side comparable nodes from \(\mathcal{T}_{LH}^{p,u,\ell}(\mathbf{q})\). |
| \(\mathcal{R}_{HL}(\mathbf{q})\) | Provides available lighter-side comparable nodes from \(\mathcal{T}_{HL}^{p,u,\ell}(\mathbf{q})\). |
| Drafting instructions \(\mathbf{I}\) | Constrain structure, fact usage, legal reasoning, and compensation drafting. |
| LLM generator \(M(\cdot)\) | Produces the final traffic-accident civil complaint. |

Table 5.2 shows that the prompt is not a simple concatenation of retrieved cases. Each component has a separate function. The lawyer input controls the case to be drafted. The anchor case provides the nearest structural reference. The light-heavy references provide more serious comparable examples. The heavy-light references provide less serious comparable examples. The drafting instructions control how these sources may be used. This separation is designed to reduce three common generation problems: copying irrelevant facts, mixing compensation items from incompatible cases, and producing a pleading that lacks a stable legal structure.

Table 5.2 顯示，提示並不是單純把檢索案例串接在一起。每一個組件都有不同功能。律師輸入控制當前要撰寫的案件；錨點案件提供最接近的結構參考；light-heavy 參考提供較嚴重的可比較例子；heavy-light 參考提供較不嚴重的可比較例子；撰寫指令則控制這些來源可以如何被使用。此分離設計用以降低三種常見生成問題：複製不相關事實、混用不相容案件的賠償項目，以及生成缺乏穩定法律結構的書狀。

The structured prompt also reflects the design evolution from the Chapter 4 method. In the sentence-level-aware method, sentence-level and paragraph-level summaries were already used to prevent the generator from reading long and noisy complaint texts. However, those summaries were mainly retrieved by textual similarity. In the proposed SDKG scheme, the summaries used in phase 3 are selected through the anchor-centered severity-aware retrieval mechanism in phase 2. Therefore, the generation phase still benefits from concise structured summaries, but the selected references are better aligned with the legal structure and severity direction of the current query.

結構化提示也反映第四章方法至最終方案的設計演化。於 sentence-level-aware method 中，句子層與段落層摘要已被用來避免生成模型讀取過長且雜訊較高的起訴書文本。然而，這些摘要主要仍依文字相似度被檢索。於所提出方案中，第三階段使用的摘要係由第二階段之錨點中心、嚴重度感知檢索機制選出。因此，生成階段仍保留簡潔結構化摘要的優點，但被選入提示的參考案例更能對齊當前查詢之法律結構與嚴重度方向。

Overall, Chapter 5 defines how the proposed SDKG scheme is implemented from raw case materials to final complaint generation. The Chapter 4 method explains the design evolution from graph storage, vector retrieval, and summary-based prompting toward the current severity-aware retrieval design. The finalized method first constructs \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\), converts \(\mathbf{c}_i\) into \(n_i\), builds \(g^{p,u,\ell}\), maps \(\mathbf{q}\) to the closest case \(c_i\) by \(d_{q,i}^{p,\ell}\), retrieves \(\mathcal{R}_{LH}(\mathbf{q})\) and \(\mathcal{R}_{HL}(\mathbf{q})\), and finally generates \(\hat{\mathbf{y}}_{p,u,\ell}=M(\mathbf{z}_{p,u,\ell})\).

整體而言，第五章定義所提出之嚴重度感知雙知識圖譜方案如何由原始案件資料實作至最終起訴書生成。第四章方法說明本研究如何由圖形資料庫儲存、向量檢索與摘要式提示，演化至目前的嚴重度感知檢索設計。最終方法先建立 \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\)，再將 \(\mathbf{c}_i\) 轉換為 \(n_i\)，建立 \(g^{p,u,\ell}\)，透過 \(d_{q,i}^{p,\ell}\) 將 \(\mathbf{q}\) 映射至最近案件 \(c_i\)，檢索 \(\mathcal{R}_{LH}(\mathbf{q})\) 與 \(\mathcal{R}_{HL}(\mathbf{q})\)，最後生成 \(\hat{\mathbf{y}}_{p,u,\ell}=M(\mathbf{z}_{p,u,\ell})\)。
