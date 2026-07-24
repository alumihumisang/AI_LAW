# Chapter 3 Preliminaries

Section 3.1 describes the system model, Section 3.2 formulates the problem statement, Section 3.3 introduces the basic idea, and Section 3.4 compares the proposed Severity-Aware Dual-Knowledge-Graph (SDKG) scheme with competing methods.

本章的 3.1 小節描述系統模型，3.2 小節表達問題表述，3.3 小節介紹基本思想，並且 3.4 小節比較所提出 Severity-Aware Dual-Knowledge-Graph (SDKG) scheme 與對手方法之差異。

## 3.1 System Model

Consider a traffic-accident civil complaint generation system assisted by the proposed SDKG scheme. Let \(N=6{,}057\) denote the number of observed complaint-style cases, \(\mathcal{D}\) denote the observed case database, \(\mathbf{q}\) denote the lawyer query, and \(k\) denote the number of retrieved reference nodes. Similar to RAG-based systems [1], [3]-[5], the generation model uses external references during generation. Different from conventional semantic retrieval, the proposed SDKG scheme converts observed cases into nodes and defines node-level relations based on legal features and severity scores, following the general motivation of graph-enhanced retrieval and legal knowledge-augmented generation [10]-[16], [19]-[22].

考慮一個由所提出 SDKG scheme 輔助之交通事故民事起訴書生成系統。設 \(N=6{,}057\) 為可觀測起訴書樣式案件之數量，\(\mathcal{D}\) 為可觀測案件資料庫，\(\mathbf{q}\) 為律師輸入之查詢，\(k\) 為檢索參考節點數量。與 RAG 系統 [1], [3]-[5] 類似，生成模型於生成階段使用外部參考資料。不同於傳統語意檢索，所提出 SDKG scheme 延續圖結構強化檢索與法律知識輔助生成 [10]-[16], [19]-[22] 之概念，並將可觀測案件轉換為節點，再依法律特徵與嚴重度分數建立節點層級關係。

Before defining the system variables, Fig. 3.1 clarifies the conceptual role of the retrieval tree used in the proposed SDKG scheme. A generic knowledge graph may connect cases through multiple relations and does not by itself define a unique retrieval path. In contrast, the proposed retrieval-tree view is query-centered: after a query is mapped to an existing anchor case, the system expands only comparable neighboring nodes that satisfy the distance threshold, the dominant-feature condition, and a clear severity direction. Nodes that do not have sufficiently similar lighter or heavier neighbors are not forced into the tree. The proposed scheme further separates the retrieval structure into two severity directions: the light-heavy tree retrieves references from lighter to heavier nodes, while the heavy-light tree retrieves references from heavier to lighter nodes. The paragraph introduces the design intuition, and the formal symbols of the two trees are defined after the case, feature, severity, and distance models are established in Model D.

在定義系統變數之前，圖 3.1 先說明所提出 SDKG scheme 中檢索樹之概念角色。一般知識圖譜可透過多種關係連接案件，但其本身不會直接定義唯一檢索路徑。相對地，本文所稱之檢索樹採查詢中心觀點：查詢先映射至既有錨點案件，再由該錨點節點展開同時滿足距離門檻、主導特徵條件與嚴重度方向之可比較鄰近節點。若某節點找不到足夠相近且方向明確的較輕或較重鄰近節點，系統不強迫將其納入樹中。所提出 SDKG scheme 進一步將此檢索結構分為兩個嚴重度方向：light-heavy tree 由較輕節點往較重節點檢索參考，heavy-light tree 則由較重節點往較輕節點檢索參考。本段先說明設計直覺；兩棵樹之正式符號定義，則於案件、法律特徵、嚴重度與距離模型建立後，在 D 模組中完整給出。

![Figure 3.1 Concept of severity-aware dual retrieval trees.](/home/aru/AI_LAW/fig3_1_tree_definition-04.png)

**Figure 3.1. Concept of severity-aware dual retrieval trees.** The proposed SDKG scheme organizes comparable node relations into query-centered severity-directed retrieval trees. Tree expansion starts from the anchor node, keeps only relations that satisfy the distance threshold and dominant-feature condition, and separates heavier-side and lighter-side references through the light-heavy and heavy-light directions. The signed delta shown in the figure is used only as a visual cue for the weighted-severity difference between two nodes: a positive value indicates that the candidate node is heavier under the current severity-weight setting, while a negative value indicates that it is lighter. The formal LH/HL direction is still determined by directly comparing the expanded weighted severity scores.

圖 3.1 中標示之 signed delta 僅用來輔助說明兩節點之加權嚴重度差異；delta 為正表示候選節點在目前權重設定下相對較重，delta 為負則表示相對較輕。正式定義仍以兩節點加權嚴重度分數之大小比較判斷 light-heavy 與 heavy-light 方向。

Following the modular style of the referenced theses, Section 3.1 describes the system through five models: case database model, legal feature model, severity and weight model, light-heavy and heavy-light tree construction model, and query-time retrieval and generation model. The models are ordered so that the formal definitions of the two retrieval trees use the symbols already introduced in the preceding models.

3.1 節後續之 A 至 E 五個模型，分別定義案件資料庫、法律特徵、嚴重度分數、light-heavy tree 與 heavy-light tree 建構，以及查詢階段檢索與生成。這些模型依序鋪陳，使兩棵檢索樹之正式定義能直接使用前面已建立之符號。

**A. Case Database Model**

The proposed SDKG scheme uses complete cases as the basic retrieval units. While conventional dense retrieval and RAG systems often retrieve passages, chunks, or documents [1], [3]-[5], the proposed scheme treats each complete complaint-style case as one retrieval unit. The observed case database contains \(N=6{,}057\) complaint-style cases and is defined as:

所提出 SDKG scheme 使用完整案件作為基本檢索單位。傳統密集檢索與 RAG 系統常以段落、片段或文件作為檢索單位 [1], [3]-[5]；所提出 SDKG scheme 則將每一筆完整起訴書樣式案件視為一個檢索單位。可觀測案件資料庫包含 \(N=6{,}057\) 筆起訴書樣式案件，定義如下：

\[
\mathcal{D}=\{\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\mid 1\leq i\leq N\},\quad N=6{,}057 .
\tag{3.1}
\]

In (3.1), \(\mathbf{c}_i\) denotes the \(i\)-th observed case. The component \(\mathbf{m}_i\) denotes the complaint-style case material of case \(i\), \(\mathbf{f}_i\) denotes the legal feature vector of case \(i\), and \(\mathbf{s}_i\) denotes the severity vector of case \(i\). The symbol \(\mathbf{m}_i\) is used for case material to avoid using \(t\), which is commonly associated with time. The case materials used in the proposed SDKG scheme are based on a database constructed in prior research from publicly available Taiwanese traffic-accident civil judgments, where the original judgments were processed into complaint-style case materials before being used for retrieval and generation. The case-level retrieval unit is defined for traffic-accident civil complaint generation.

式 (3.1) 中，\(\mathbf{c}_i\) 表示第 \(i\) 筆可觀測案件，\(\mathbf{m}_i\) 表示該案件之起訴書樣式案件材料，\(\mathbf{f}_i\) 表示其法律特徵向量，\(\mathbf{s}_i\) 表示其嚴重度向量。本文使用 \(\mathbf{m}_i\) 表示案件材料，以避免使用容易被理解為時間之 \(t\)。所提出 SDKG scheme 使用之案件資料以前期研究建立之資料庫為基礎，原始資料來源為公開之臺灣交通事故民事判決書，並於前期研究中處理為起訴書樣式案件資料，供後續進行檢索與生成。

**B. Legal Feature Model**

Each case is represented by four groups of boolean legal features. The boolean representation is a task-specific design for modeling the legal structure of traffic-accident civil complaint cases:

每一筆案件由四組布林法律特徵表示。此表示方式用於建模交通事故民事起訴書案件之法律結構，並作為所提出 SDKG scheme 的案件層級法律表示：

\[
\mathbf{f}_i=[\mathbf{b}_{i,L};\mathbf{b}_{i,F};\mathbf{b}_{i,U};\mathbf{b}_{i,P}] .
\tag{3.2}
\]

In (3.2), \(\mathbf{b}\) denotes a boolean feature vector. The subscript \(i\) denotes the case index, and the second subscript denotes the feature group. Specifically, \(L\) denotes litigant-related features, \(F\) denotes accident-fact-related features, \(U\) denotes injury-related features, and \(P\) denotes compensation-related features. The symbol \(U\) is used for injury to avoid confusion with the case index \(i\). Each element in the four vectors is a boolean indicator showing whether the corresponding legal feature appears in case \(c_i\). The vector \(\mathbf{f}_i\) therefore records the legal structure of case \(c_i\) through the four feature groups.

式 (3.2) 中，\(\mathbf{b}\) 表示布林特徵向量。下標 \(i\) 表示案件編號，第二個下標表示特徵群組。其中，\(L\) 表示當事人相關特徵，\(F\) 表示事故事實相關特徵，\(U\) 表示傷勢相關特徵，\(P\) 表示賠償相關特徵。本文使用 \(U\) 表示傷勢特徵，以避免與案件索引 \(i\) 混淆。這些向量中的每一個元素皆為布林指標，用以表示案件 \(c_i\) 是否出現對應之法律特徵。因此，\(\mathbf{f}_i\) 透過上述四組特徵記錄案件 \(c_i\) 之法律結構。

For example, \(\mathbf{b}_{i,L}\) records litigant-related indicators; if case \(c_i\) involves one plaintiff and one defendant, the corresponding single-plaintiff and single-defendant indicators are set to 1. \(\mathbf{b}_{i,F}\) records accident-fact-related indicators; if case \(c_i\) involves a negligent rear-end collision, the corresponding negligence and rear-end-collision indicators are set to 1. \(\mathbf{b}_{i,U}\) records injury-related indicators; if case \(c_i\) involves a fracture injury, the corresponding fracture indicator is set to 1. \(\mathbf{b}_{i,P}\) records compensation-related indicators; if case \(c_i\) claims medical expenses and non-pecuniary damages, the corresponding medical-expense and non-pecuniary-damage indicators are set to 1. Indicators for features not appearing in case \(c_i\) are set to 0.

例如，\(\mathbf{b}_{i,L}\) 記錄當事人相關指標；若案件 \(c_i\) 涉及單一原告與單一被告，則單一原告與單一被告對應之指標設為 1。\(\mathbf{b}_{i,F}\) 記錄事故事實相關指標；若案件 \(c_i\) 涉及過失追撞事故，則過失與追撞對應之指標設為 1。\(\mathbf{b}_{i,U}\) 記錄傷勢相關指標；若案件 \(c_i\) 涉及骨折傷害，則骨折對應之指標設為 1。\(\mathbf{b}_{i,P}\) 記錄賠償相關指標；若案件 \(c_i\) 請求醫療費用與精神慰撫金，則醫療費用與精神慰撫金對應之指標設為 1。案件 \(c_i\) 中未出現之特徵，其對應指標則設為 0。

**C. Severity and Weight Model**

The severity of each case is represented by fact severity, injury severity, and compensation severity. For case \(c_i\), the three severity values are denoted by \(s_{i,F}\), \(s_{i,U}\), and \(s_{i,P}\), respectively, and the severity vector is written as \(\mathbf{s}_i=[s_{i,F},s_{i,U},s_{i,P}]\). To compare cases under different legal emphases, the proposed SDKG scheme uses six legal weight settings, indexed by \(p\in\{1,\ldots,6\}\). Under weight setting \(p\), \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\) denote the weights assigned to \(s_{i,F}\), \(s_{i,U}\), and \(s_{i,P}\), respectively. The weighted severity of case \(c_i\) is compared through the expression \(\alpha^p s_{i,F}+\beta^p s_{i,U}+(1-\alpha^p-\beta^p) s_{i,P}\).

每一筆案件之嚴重度由事實嚴重度、傷勢嚴重度與賠償嚴重度表示。對案件 \(c_i\) 而言，三個嚴重度值分別記為 \(s_{i,F}\)、\(s_{i,U}\) 與 \(s_{i,P}\)，嚴重度向量記為 \(\mathbf{s}_i=[s_{i,F},s_{i,U},s_{i,P}]\)。為比較不同法律重心下的案件，所提出 SDKG scheme 使用六組法律權重設定，並以 \(p\in\{1,\ldots,6\}\) 表示權重設定索引。在權重設定 \(p\) 下，\(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 分別表示 \(s_{i,F}\)、\(s_{i,U}\) 與 \(s_{i,P}\) 的權重。案件 \(c_i\) 在權重設定 \(p\) 下之加權嚴重度，透過 \(\alpha^p s_{i,F}+\beta^p s_{i,U}+(1-\alpha^p-\beta^p) s_{i,P}\) 進行比較。

For example, \(s_{i,F}\) records fact severity; if case \(c_i\) involves clear negligence and a high-impact collision, the fact severity value becomes higher. \(s_{i,U}\) records injury severity; if case \(c_i\) involves a fracture rather than a minor abrasion, the injury severity value becomes higher. \(s_{i,P}\) records compensation severity; if case \(c_i\) involves higher claimed medical expenses and non-pecuniary damages, the compensation severity value becomes higher. \(\alpha^p\) increases the influence of fact severity when the legal weight setting emphasizes accident facts. \(\beta^p\) increases the influence of injury severity when the legal weight setting emphasizes bodily injury. \((1-\alpha^p-\beta^p)\) increases the influence of compensation severity when the legal weight setting emphasizes claimed damages.

例如，\(s_{i,F}\) 記錄事實嚴重度；若案件 \(c_i\) 涉及明確過失與高衝擊碰撞，則事實嚴重度較高。\(s_{i,U}\) 記錄傷勢嚴重度；若案件 \(c_i\) 涉及骨折而非輕微擦挫傷，則傷勢嚴重度較高。\(s_{i,P}\) 記錄賠償嚴重度；若案件 \(c_i\) 涉及較高醫療費用與精神慰撫金請求，則賠償嚴重度較高。\(\alpha^p\) 在法律權重設定偏重事故事實時，提高事實嚴重度的影響。\(\beta^p\) 在法律權重設定偏重身體傷害時，提高傷勢嚴重度的影響。\((1-\alpha^p-\beta^p)\) 在法律權重設定偏重損害賠償請求時，提高賠償嚴重度的影響。

**D. light-heavy and heavy-light tree construction model**

Recent KG-guided RAG and GraphRAG studies show that graph relations can organize retrieved evidence beyond isolated semantic chunks [10], [13], [15], and legal case retrieval studies also use graph-based representations to model case relations [20]-[22]. Following the graph-based retrieval direction, the proposed SDKG scheme converts each observed case \(\mathbf{c}_i\) into a node \(n_i\), uses severity-aware node relations as the preprocessing search space, and constructs two severity-directed retrieval trees. The conversion from case to node is written as
\[
\mathbf{c}_i\mapsto n_i,\quad 1\leq i\leq N .
\]

近年知識圖譜引導之 RAG 與 GraphRAG 研究指出，圖結構關係可用於組織檢索證據 [10], [13], [15]，法律案例檢索研究亦使用圖結構表示以建模案件關係 [20]-[22]。所提出 SDKG scheme 延續此一概念，將每一筆可觀測案件 \(\mathbf{c}_i\) 轉換為節點 \(n_i\)，使用嚴重度感知節點關係作為預處理搜尋空間，並建立兩棵嚴重度方向檢索樹。案件轉換為節點之關係寫為
\[
\mathbf{c}_i\mapsto n_i,\quad 1\leq i\leq N .
\]

Let \(\mathcal{V}=\{n_i\mid 1\leq i\leq N\}\) denote the complete node set. Under legal weight setting \(p\) and distance-weight setting \(\ell\), the node distance between two nodes \(n_i\) and \(n_j\) is denoted by \(d_{i,j}^{p,\ell}\). The node distance combines the legal feature distance and the severity-distance function:

令 \(\mathcal{V}=\{n_i\mid 1\leq i\leq N\}\) 表示完整節點集合。在法律權重設定 \(p\) 與距離權重設定 \(\ell\) 下，兩個節點 \(n_i\) 與 \(n_j\) 之節點距離記為 \(d_{i,j}^{p,\ell}\)。此距離結合法律特徵距離與嚴重度距離函數：

\[
d_{i,j}^{p,\ell}
=
\lambda^{\ell} d_f(\mathbf{f}_i,\mathbf{f}_j)
+(1-\lambda^{\ell}) d_s^{p}(\mathbf{s}_i,\mathbf{s}_j).
\tag{3.3}
\]

In (3.3), \(d_f(\mathbf{f}_i,\mathbf{f}_j)\) measures the legal feature distance, and \(d_s^{p}(\mathbf{s}_i,\mathbf{s}_j)\) denotes the severity-distance function under legal weight setting \(p\). The weights \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\) control the fact, injury, and compensation dimensions, respectively. The parameters \(\lambda^{\ell}\) and \((1-\lambda^{\ell})\) control the relative importance of legal feature distance and severity distance. Under threshold setting \(u\), \(\tau^u\) is used to decide whether two nodes are close enough to form a parent-child relation. Chapter 5 explains the implementation of \(d_s^{p}(\cdot)\).

式 (3.3) 中，\(d_f(\mathbf{f}_i,\mathbf{f}_j)\) 表示法律特徵距離，\(d_s^{p}(\mathbf{s}_i,\mathbf{s}_j)\) 表示權重設定 \(p\) 下之嚴重度距離函數。\(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 分別控制事實、傷勢與賠償三個面向。\(\lambda^{\ell}\) 與 \((1-\lambda^{\ell})\) 分別控制法律特徵距離與嚴重度距離的重要性。在門檻設定 \(u\) 下，\(\tau^u\) 用以判斷兩節點距離是否足以形成父子關係。\(d_s^{p}(\cdot)\) 之實作方式於第四章說明。

To prevent cases from being connected only because their aggregate severity scores are close, SDKG also uses the dominant feature group under weight setting \(p\) as a comparability basis. The dominant feature group is selected from the accident-fact, injury, and compensation feature groups according to the largest weight among \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\). Two nodes are admitted into the comparable-node relation set only when their feature subvectors in this dominant group share at least one boolean feature. For example, under an injury-oriented setting, two cases must share at least one injury feature before their distance and severity direction are used to form LH or HL relations. Under a compensation-oriented setting, two cases must share at least one compensation feature before they are compared as compensation-related references.

為避免兩案僅因總體嚴重度分數接近而被連接，SDKG 亦使用權重設定 \(p\) 下的主導特徵群作為可比較基礎。主導特徵群依 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 三者中最大權重，從事故事實、傷勢與賠償特徵群中選出。兩節點除距離須足夠接近外，也必須在該主導特徵群的特徵子向量中至少共享一個 boolean feature，才會被納入可比較節點關係。例如，在偏重傷勢的設定下，兩案需至少具有一個共同傷勢特徵，才會進一步以距離與嚴重度方向形成 LH 或 HL 關係；在偏重賠償的設定下，兩案需至少具有一個共同賠償特徵，才會作為賠償相關參考進行比較。

This design can be illustrated by a pair of cases with similar litigant and accident-fact features but different injury and compensation severity. If one case involves only abrasions while the other case involves a fracture and higher medical expenses, \(d_f(\mathbf{f}_i,\mathbf{f}_j)\) may remain small, but \(d_s^{p}(\mathbf{s}_i,\mathbf{s}_j)\) reflects the difference in injury and compensation severity. Under an injury-oriented weight setting, \(\beta^p\) makes the severity-distance function more sensitive to the fracture difference. Under a compensation-oriented weight setting, \((1-\alpha^p-\beta^p)\) makes the severity-distance function more sensitive to the difference in claimed damages. The distance-weight setting \(\ell\) further controls whether relation construction emphasizes shared legal features or severity-distance differences.

此設計可由一組具有相近當事人與事故事實特徵，但傷勢與賠償嚴重度不同的案件加以說明。若一案僅有擦挫傷，另一案則涉及骨折與較高醫療費用，則 \(d_f(\mathbf{f}_i,\mathbf{f}_j)\) 可能仍然較小，但 \(d_s^{p}(\mathbf{s}_i,\mathbf{s}_j)\) 會反映傷勢與賠償嚴重度差異。在偏重傷勢之權重設定下，\(\beta^p\) 會使嚴重度距離函數更重視骨折差異；在偏重賠償之權重設定下，\((1-\alpha^p-\beta^p)\) 會使嚴重度距離函數更重視請求損害金額差異。距離權重設定 \(\ell\) 則進一步控制建構關係時較偏重共同法律特徵，或較偏重嚴重度距離差異。

The severity direction is determined by directly comparing the weighted severity of the candidate node \(n_j\) with that of the current node \(n_i\) under weight setting \(p\). If the candidate node has higher weighted severity, \(n_j\) is treated as heavier than \(n_i\). If the candidate node has lower weighted severity, \(n_j\) is treated as lighter than \(n_i\). Thus, the node distance \(d_{i,j}^{p,\ell}\) determines whether two nodes are close enough to be comparable, while the weighted severity comparison determines the light-heavy or heavy-light direction.

嚴重度方向係直接比較候選節點 \(n_j\) 與目前節點 \(n_i\) 在權重設定 \(p\) 下之加權嚴重度。若候選節點之加權嚴重度較高，則 \(n_j\) 被視為比 \(n_i\) 嚴重；若候選節點之加權嚴重度較低，則 \(n_j\) 被視為比 \(n_i\) 輕微。因此，節點距離 \(d_{i,j}^{p,\ell}\) 用以判斷兩節點是否足夠接近而可比較，加權嚴重度比較則用以判斷 light-heavy 或 heavy-light 方向。

Under weight setting \(p\), threshold setting \(u\), and distance-weight setting \(\ell\), \(E^{p,u,\ell}\) denotes the comparable-node relation set. A node pair belongs to \(E^{p,u,\ell}\) only when the distance \(d_{i,j}^{p,\ell}\) is no larger than \(\tau^u\) and the two cases share at least one boolean feature in the dominant feature group determined by \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\). The configuration \(g^{p,u,\ell}\) denotes the severity-aware DKG formed by \(\mathcal{V}\) and \(E^{p,u,\ell}\). The notation \(\mathrm{LH}\) denotes the light-heavy direction, and \(\mathrm{HL}\) denotes the heavy-light direction. Query-time tree expansion starts from the anchor node \(n_i\) corresponding to the closest observed case \(c_i\).

在權重設定 \(p\)、門檻設定 \(u\) 與距離權重設定 \(\ell\) 下，\(E^{p,u,\ell}\) 表示可比較節點關係集合。節點對必須同時滿足距離 \(d_{i,j}^{p,\ell}\) 不大於 \(\tau^u\)，且兩案在由 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 決定之主導特徵群中至少共享一個 boolean feature，才會被納入 \(E^{p,u,\ell}\)。\(g^{p,u,\ell}\) 表示由 \(\mathcal{V}\) 與 \(E^{p,u,\ell}\) 形成之嚴重度感知 DKG 配置。符號 \(\mathrm{LH}\) 表示 light-heavy direction，符號 \(\mathrm{HL}\) 表示 heavy-light direction。查詢階段之樹狀展開由最接近既有案件 \(c_i\) 所對應之錨點節點 \(n_i\) 開始。

**Definition 1. light-heavy retrieval tree.**
Given the light-heavy direction \(\mathrm{LH}\), each observed case is first converted into a node, written as \(\mathbf{c}_i\mapsto n_i\), \(1\leq i\leq N\). The root node \(n_r\) of the light-heavy tree is the node with the lowest weighted severity in \(\mathcal{V}\) under weight setting \(p\). The severity ordering is determined by the weighted severity of the fact, injury, and compensation severity components, whose weights are \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\), respectively. For any parent node \(n_i\in\mathcal{V}\) and any candidate child node \(n_j\in\mathcal{V}\), \(n_j\) becomes a child node of \(n_i\), written as \(n_i\xrightarrow{\mathrm{LH}}n_j\), if \((n_i,n_j)\in E^{p,u,\ell}\) and \(n_j\) has higher weighted severity than \(n_i\) under weight setting \(p\). The relation \((n_i,n_j)\in E^{p,u,\ell}\) means that the two nodes are close enough under threshold setting \(u\) and share at least one boolean feature in the dominant feature group determined by the largest severity weight. Once included, \(n_j\) can be treated as the next parent node, so the same rule recursively forms child and descendant nodes. If no candidate satisfies these conditions, no child is forced for the current node. At query time, the closest case \(c_i\) retrieved by the query-mapping distance \(d_{q,i}^{p,\ell}\) becomes the anchor case, and the corresponding node is used as the starting node for local retrieval rather than replacing the global root node \(n_r\).

**定義一：light-heavy retrieval tree。**
給定 light-heavy direction \(\mathrm{LH}\)，每一筆可觀測案件先轉換為節點，寫為 \(\mathbf{c}_i\mapsto n_i\)，\(1\leq i\leq N\)。light-heavy tree 之根節點 \(n_r\) 定義為節點集合 \(\mathcal{V}\) 中，在權重設定 \(p\) 下加權嚴重度最低的節點。嚴重度排序係由事實、傷勢與賠償三個嚴重度面向的加權嚴重度決定，其權重分別為 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\)。對任一父節點 \(n_i\in\mathcal{V}\)，以及任一候選子節點 \(n_j\in\mathcal{V}\)，若 \((n_i,n_j)\in E^{p,u,\ell}\)，且 \(n_j\) 在權重設定 \(p\) 下之加權嚴重度高於 \(n_i\)，則 \(n_j\) 成為 \(n_i\) 的子節點，記為 \(n_i\xrightarrow{\mathrm{LH}}n_j\)。關係 \((n_i,n_j)\in E^{p,u,\ell}\) 表示兩節點在門檻設定 \(u\) 下足夠接近，且在由最大嚴重度權重決定之主導特徵群中至少共享一個 boolean feature。當 \(n_j\) 被納入後，\(n_j\) 可作為下一個父節點，因此同一規則可遞迴形成子節點與後代節點。若沒有候選節點滿足上述條件，系統不會強迫目前節點產生子節點。於查詢階段，經由查詢映射距離 \(d_{q,i}^{p,\ell}\) 取得之最近案件 \(c_i\) 成為錨點案件，並使用其對應節點作為局部檢索起始節點，而不是取代全域根節點 \(n_r\)。

**Definition 2. heavy-light retrieval tree.**
Given the heavy-light direction \(\mathrm{HL}\), each observed case is first converted into a node, written as \(\mathbf{c}_i\mapsto n_i\), \(1\leq i\leq N\). The root node \(n_r\) of the heavy-light tree is the node with the highest weighted severity in \(\mathcal{V}\) under weight setting \(p\). The severity ordering is determined by the same weighted severity rule, where the fact, injury, and compensation severity components are weighted by \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\), respectively. For any parent node \(n_i\in\mathcal{V}\) and any candidate child node \(n_j\in\mathcal{V}\), \(n_j\) becomes a child node of \(n_i\), written as \(n_i\xrightarrow{\mathrm{HL}}n_j\), if \((n_i,n_j)\in E^{p,u,\ell}\) and \(n_j\) has lower weighted severity than \(n_i\) under weight setting \(p\). The relation \((n_i,n_j)\in E^{p,u,\ell}\) means that the two nodes are close enough under threshold setting \(u\) and share at least one boolean feature in the dominant feature group determined by the largest severity weight. Once included, \(n_j\) can be treated as the next parent node, so the same rule recursively forms child and descendant nodes. If no candidate satisfies these conditions, no child is forced for the current node. At query time, the closest case \(c_i\) retrieved by the query-mapping distance \(d_{q,i}^{p,\ell}\) becomes the anchor case, and the corresponding node is used as the starting node for local retrieval rather than replacing the global root node \(n_r\).

**定義二：heavy-light retrieval tree。**
給定 heavy-light direction \(\mathrm{HL}\)，每一筆可觀測案件先轉換為節點，寫為 \(\mathbf{c}_i\mapsto n_i\)，\(1\leq i\leq N\)。heavy-light tree 之根節點 \(n_r\) 定義為節點集合 \(\mathcal{V}\) 中，在權重設定 \(p\) 下加權嚴重度最高的節點。嚴重度排序採用相同的加權嚴重度規則，其中事實、傷勢與賠償三個嚴重度面向分別由 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 加權。對任一父節點 \(n_i\in\mathcal{V}\)，以及任一候選子節點 \(n_j\in\mathcal{V}\)，若 \((n_i,n_j)\in E^{p,u,\ell}\)，且 \(n_j\) 在權重設定 \(p\) 下之加權嚴重度低於 \(n_i\)，則 \(n_j\) 成為 \(n_i\) 的子節點，記為 \(n_i\xrightarrow{\mathrm{HL}}n_j\)。關係 \((n_i,n_j)\in E^{p,u,\ell}\) 表示兩節點在門檻設定 \(u\) 下足夠接近，且在由最大嚴重度權重決定之主導特徵群中至少共享一個 boolean feature。當 \(n_j\) 被納入後，\(n_j\) 可作為下一個父節點，因此同一規則可遞迴形成子節點與後代節點。若沒有候選節點滿足上述條件，系統不會強迫目前節點產生子節點。於查詢階段，經由查詢映射距離 \(d_{q,i}^{p,\ell}\) 取得之最近案件 \(c_i\) 成為錨點案件，並使用其對應節點作為局部檢索起始節點，而不是取代全域根節點 \(n_r\)。

In both retrieval trees, each included child node keeps only one parent node. If multiple reached parent nodes can connect to the same \(n_j\), the retained parent is the node with the smallest \(d_{i,j}^{p,\ell}\). The single-parent rule does not limit how many child nodes a parent node may have; the single-parent rule only preserves a unique comparison path from the corresponding anchor node to each included node.

在兩棵檢索樹中，每一個被納入之子節點僅保留一個父節點。若多個已到達父節點皆可連接至同一 \(n_j\)，則保留 \(d_{i,j}^{p,\ell}\) 最小者作為父節點。此單一父節點規則不限制同一父節點可具有多少子節點，而是用以維持每一個被納入節點相對於對應錨點節點的唯一比較路徑。

**E. Query-Time Retrieval and Generation Model**

At query time, the lawyer input is denoted by \(\mathbf{q}\). Following the retrieval-before-generation principle of RAG [1], [3] and graph-guided retrieval systems [10]-[16], the system extracts the query legal feature vector \(\mathbf{f}_q\) and query severity vector \(\mathbf{s}_q\), selects case-level references, and then uses the selected references for complaint generation. The retrieved heavier-direction nodes are denoted by \(\mathcal{R}_{LH}(\mathbf{q})\), and the retrieved lighter-direction nodes are denoted by \(\mathcal{R}_{HL}(\mathbf{q})\). The function \(\Phi(\cdot)\) denotes structured prompt construction, and \(M(\cdot)\) denotes the complaint generation model. Section 3.2 first formulates the generation-gap problem and the retrieval-conditioned reference selection problem. The detailed SDKG solution, including anchor-case mapping and dual-tree retrieval, is presented in Chapter 5.

於查詢階段，律師輸入以 \(\mathbf{q}\) 表示。系統會萃取其法律特徵向量 \(\mathbf{f}_q\) 與嚴重度向量 \(\mathbf{s}_q\)，選取案件層級參考，並使用所選參考支援起訴書生成。\(\mathcal{R}_{LH}(\mathbf{q})\) 表示由 light-heavy tree 取得之相對較重方向節點，\(\mathcal{R}_{HL}(\mathbf{q})\) 表示由 heavy-light tree 取得之相對較輕方向節點。\(\Phi(\cdot)\) 表示結構化提示建構，\(M(\cdot)\) 表示起訴書生成模型。3.2 節先定義生成差距問題與檢索條件下之參考集合選擇問題；至於錨點案件映射與雙樹檢索之 SDKG 解法，則於第五章完整說明。

## 3.2 Problem Formulation

The observed case database is denoted by \(\mathcal{D}=\{\mathbf{c}_1,\mathbf{c}_2,\mathbf{c}_3,\ldots,\mathbf{c}_N\}\), where \(N\) is the number of observed cases and \(\mathbf{c}_i\) is the \(i\)-th case, \(1\leq i\leq N\). Each case keeps the same representation \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\), where \(\mathbf{m}_i\) denotes case metadata and text, \(\mathbf{f}_i\) denotes the legal-feature profile, and \(\mathbf{s}_i\) denotes the severity vector. For a lawyer query \(\mathbf{q}_m\), the corresponding human-written complaint is denoted by \(\mathbf{y}^{*}_m\), where the subscript \(m\) is used only as the query index. The retrieval module selects a reference set \(\mathcal{R}(\mathbf{q}_m)\) from \(\mathcal{D}\), the prompt function \(\Phi(\cdot)\) forms \(\mathbf{z}_m=\Phi(\mathbf{q}_m,\mathcal{R}(\mathbf{q}_m))\), and the generation model \(M(\cdot)\) outputs \(\hat{\mathbf{y}}_m=M(\mathbf{z}_m)\). The difference between \(\hat{\mathbf{y}}_m\) and \(\mathbf{y}^{*}_m\) is measured by \(\mathcal{L}(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m)\).

可觀測案件資料庫記為 \(\mathcal{D}=\{\mathbf{c}_1,\mathbf{c}_2,\mathbf{c}_3,\ldots,\mathbf{c}_N\}\)，其中 \(N\) 為可觀測案件總數，\(\mathbf{c}_i\) 表示第 \(i\) 筆案件，\(1\leq i\leq N\)。每一筆案件維持相同表示方式 \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\)，其中 \(\mathbf{m}_i\) 表示案件 metadata 與文本，\(\mathbf{f}_i\) 表示法律特徵輪廓，\(\mathbf{s}_i\) 表示嚴重度向量。對任一律師查詢 \(\mathbf{q}_m\)，其對應人工起訴書記為 \(\mathbf{y}^{*}_m\)，其中下標 \(m\) 僅表示查詢索引。檢索模組自 \(\mathcal{D}\) 中選出參考集合 \(\mathcal{R}(\mathbf{q}_m)\)，提示函數 \(\Phi(\cdot)\) 形成 \(\mathbf{z}_m=\Phi(\mathbf{q}_m,\mathcal{R}(\mathbf{q}_m))\)，生成模型 \(M(\cdot)\) 再輸出 \(\hat{\mathbf{y}}_m=M(\mathbf{z}_m)\)。\(\hat{\mathbf{y}}_m\) 與 \(\mathbf{y}^{*}_m\) 之差距以 \(\mathcal{L}(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m)\) 衡量。

The problem is divided into two simple objectives. \(\mathbf{P}_1\) asks the system to generate a complaint \(\hat{\mathbf{y}}_m\) close to the human complaint \(\mathbf{y}^{*}_m\). \(\mathbf{P}_2\) asks the retrieval module to choose a better reference set \(\mathcal{R}^{*}(\mathbf{q}_m)\) for each \(\mathbf{q}_m\), so that the selected cases can support the same generation objective. They are written together as:

此問題分為兩個簡單目標。\(\mathbf{P}_1\) 要求系統生成接近人工起訴書 \(\mathbf{y}^{*}_m\) 的起訴書 \(\hat{\mathbf{y}}_m\)。\(\mathbf{P}_2\) 則要求檢索模組針對每一筆 \(\mathbf{q}_m\) 選出較合適的參考集合 \(\mathcal{R}^{*}(\mathbf{q}_m)\)，使被選出的案例能支援同一生成目標。兩者共同表示如下：

\[
\begin{alignedat}{2}
\text{opt.}\quad \mathbf{P}_{1}:&\quad
\min_{\hat{\mathbf{y}}_m}
&&
\mathcal{L}\!\left(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m\right),\\
\mathbf{P}_{2}:&\quad
\mathcal{R}^{*}(\mathbf{q}_m)
&&=
\operatorname*{arg\,min}_{\mathcal{R}(\mathbf{q}_m)}
\mathcal{L}\!\left(
M\!\left(\Phi\!\left(\mathbf{q}_m,\mathcal{R}(\mathbf{q}_m)\right)\right),
\mathbf{y}^{*}_m
\right),\\
\mathrm{C}_{1}:&\quad
\mathbf{z}_m
&&=
\Phi\!\left(\mathbf{q}_m,\mathcal{R}(\mathbf{q}_m)\right),\\
\mathrm{C}_{2}:&\quad
\mathbf{c}_j
&&\in
\mathcal{D},
\quad
\forall \mathbf{c}_j\in\mathcal{R}(\mathbf{q}_m),\\
\mathrm{C}_{3}:&\quad
|\mathcal{R}(\mathbf{q}_m)|
&&\leq
k.
\end{alignedat}
\tag{3.4}
\]

In (3.4), \(\mathbf{P}_1\) focuses on the generated text \(\hat{\mathbf{y}}_m\), and \(\mathbf{P}_2\) focuses on the retrieved cases \(\mathcal{R}(\mathbf{q}_m)\). \(\mathrm{C}_1\) states that the prompt \(\mathbf{z}_m\) is constructed from the query \(\mathbf{q}_m\) and the selected reference set \(\mathcal{R}(\mathbf{q}_m)\). \(\mathrm{C}_2\) states that every selected case \(\mathbf{c}_j\) must come from the observed case database \(\mathcal{D}\). \(\mathrm{C}_3\) states that the number of selected cases is limited by the top-\(k\) budget. Therefore, \(\mathcal{R}(\mathbf{q}_m)\) is not arbitrary external text, but a limited case set selected from \(\mathcal{D}\). Once \(\mathcal{R}(\mathbf{q}_m)\) is selected, the sequence \(\mathcal{R}(\mathbf{q}_m)\rightarrow\mathbf{z}_m\rightarrow\hat{\mathbf{y}}_m\rightarrow\mathcal{L}(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m)\) describes how retrieval affects generation quality.

式 (3.4) 中，\(\mathbf{P}_1\) 關注生成結果 \(\hat{\mathbf{y}}_m\)，\(\mathbf{P}_2\) 關注檢索所得案例 \(\mathcal{R}(\mathbf{q}_m)\)。\(\mathrm{C}_1\) 表示提示 \(\mathbf{z}_m\) 由查詢 \(\mathbf{q}_m\) 與參考集合 \(\mathcal{R}(\mathbf{q}_m)\) 組成；\(\mathrm{C}_2\) 表示每一個被選入之案件 \(\mathbf{c}_j\) 皆必須來自可觀測案件資料庫 \(\mathcal{D}\)；\(\mathrm{C}_3\) 表示被選案件數量受 top-\(k\) 預算限制。因此，\(\mathcal{R}(\mathbf{q}_m)\) 並非任意外部文本，而是從 \(\mathcal{D}\) 中選出的有限案件集合。當 \(\mathcal{R}(\mathbf{q}_m)\) 被決定後，\(\mathcal{R}(\mathbf{q}_m)\rightarrow\mathbf{z}_m\rightarrow\hat{\mathbf{y}}_m\rightarrow\mathcal{L}(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m)\) 描述了檢索如何影響生成品質。

This setting explains why the retrieval unit matters. If a retrieved case \(\mathbf{c}_j\) only has similar wording to \(\mathbf{q}_m\), but its legal features \(\mathbf{f}_j\) or severity vector \(\mathbf{s}_j\) are different from the needs of \(\mathbf{q}_m\), then \(\mathbf{c}_j\) may not help reduce \(\mathcal{L}(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m)\). In contrast, a useful reference case should provide comparable facts, legal basis, injury severity, and compensation information. For this reason, Chapter 4 first presents the earlier paragraph-level and sentence-level retrieval design for \(\mathbf{P}_2\), and Chapter 5 further changes \(\mathcal{R}(\mathbf{q}_m)\) into a case-level SDKG retrieval result. In SDKG, each case \(\mathbf{c}_i\) is converted into a node \(n_i\), and the final references are selected by \(\mathbf{f}_i\), \(\mathbf{s}_i\), \(d_{q,i}^{p,\ell}\), \(d_{i,j}^{p,\ell}\), \(\tau^u\), and the light-heavy/heavy-light directions.

此設定說明了檢索單位的重要性。若被檢索出的案件 \(\mathbf{c}_j\) 只是與 \(\mathbf{q}_m\) 在文字上相似，但其法律特徵 \(\mathbf{f}_j\) 或嚴重度向量 \(\mathbf{s}_j\) 並不符合 \(\mathbf{q}_m\) 的需求，則 \(\mathbf{c}_j\) 不一定能降低 \(\mathcal{L}(\hat{\mathbf{y}}_m,\mathbf{y}^{*}_m)\)。相對地，有用的參考案件應能提供可比較的事實、法律依據、傷勢嚴重度與賠償資訊。因此，第四章先呈現早期針對 \(\mathbf{P}_2\) 所設計之段落層與句子層檢索方法；第五章則進一步將 \(\mathcal{R}(\mathbf{q}_m)\) 改為案件層級的 SDKG 檢索結果。在 SDKG 中，每一筆案件 \(\mathbf{c}_i\) 會轉換為節點 \(n_i\)，最後參考案例則由 \(\mathbf{f}_i\)、\(\mathbf{s}_i\)、\(d_{q,i}^{p,\ell}\)、\(d_{i,j}^{p,\ell}\)、\(\tau^u\)，以及 light-heavy/heavy-light 方向共同決定。

## 3.3 Basic Idea

The basic idea of the proposed SDKG scheme is illustrated through the comparison between the TAARN-style competing method and the proposed severity-aware dual-tree retrieval design. TAARN combines a knowledge graph, case text descriptions, path extraction, and graph/text attention [2]. Compared with conventional semantic retrieval, the graph-text method can use graph paths and textual representations to capture case relations beyond flat semantic similarity. Therefore, TAARN is a meaningful competing method because both approaches attempt to use graph structure to improve legal case retrieval.

However, the graph structure in TAARN is mainly designed for general graph/text representation. The goal of TAARN is to learn whether cases are relevant through graph paths, text-augmented embeddings, and attention-based representation learning. Such a design can strengthen general relevance modeling, but the TAARN graph structure does not directly organize traffic-accident cases according to the severity direction required by civil complaint generation. In other words, TAARN can help answer whether two cases are related, but TAARN does not explicitly answer whether a neighboring node is relatively lighter or heavier than the node corresponding to the anchor case.

所提出 SDKG scheme 之基本思想，可透過 TAARN 式對手方法與嚴重度感知雙樹檢索設計之比較加以說明。TAARN 結合知識圖譜、案件文字描述、路徑抽取，以及圖文注意力機制 [2]。相較於傳統語意檢索，此類圖文方法能使用圖譜路徑與文字表示，以捕捉超越平面語意相似度之案件關係。因此，TAARN 是一個有意義的對手方法，因為兩者皆嘗試透過圖結構改善法律案件檢索。

然而，TAARN 之圖結構主要是為一般圖文表示而設計。其目標是透過圖譜路徑、文字增強向量與注意力式表示學習，判斷案件是否相關。此設計雖可強化一般關聯性建模，但並未直接依交通事故民事起訴書生成所需之嚴重度方向組織案例。換言之，TAARN 可以協助回答兩個案件是否相關，但並未明確回答鄰近節點相對於錨點案件之對應節點是較輕或較重。

因此，所提出 SDKG scheme 之基本思想，在於重新定義圖譜於交通事故民事起訴書生成任務中的角色。一般圖文檢索方法重視案件間之關聯性，但對起訴書生成而言，僅知道「案件相關」仍然不足。合適之參考案例必須同時具備法律結構可比性與嚴重度方向意義，否則生成模型可能錯誤借用他案之事故事實、傷勢程度或賠償金額。

Based on the observation, the proposed SDKG scheme uses four main steps. First, the system performs case preprocessing and converts each case into a case-level legal representation. Second, the system reconstructs severity scores from fact, injury, and compensation dimensions. Third, the system converts observed cases into nodes and constructs severity-aware node relations. Fourth, at query time, the system selects the closest case \(c_i\) retrieved by the query-mapping distance \(d_{q,i}^{p,\ell}\) as the anchor case and retrieves neighboring nodes from the light-heavy tree and the heavy-light tree according to the lighter-to-heavier and heavier-to-lighter directions. The retrieved nodes are then converted into structured prompts for complaint generation.

基於上述觀察，所提出 SDKG scheme 包含四個主要步驟。首先，系統執行案件預處理，並將每一筆案件轉換為案件層級法律表示。其次，系統自事實、傷勢與賠償三個面向重建嚴重度分數。第三，系統將可觀測案件轉換為節點，並建立嚴重度感知節點關係。第四，於查詢階段，系統選出經由查詢映射距離 \(d_{q,i}^{p,\ell}\) 取得之最近案件 \(c_i\) 作為錨點案件，並依較輕至較重與較重至較輕兩個方向，自 light-heavy tree 與 heavy-light tree 中檢索鄰近節點。最終，檢索所得節點被轉換為結構化提示，以支援民事起訴書生成。

![Figure 3.2 Comparison between TAARN-style competing method and proposed SDKG scheme.](/home/aru/AI_LAW/image copy 37.png)

**Figure 3.2. Comparison between TAARN-style competing method and proposed SDKG scheme.** TAARN uses graph paths, text descriptions, and attention-based representation learning to retrieve relevant cases. The proposed SDKG scheme uses case preprocessing, severity-aware node-relation construction, anchor-case mapping, and light-heavy/heavy-light tree retrieval to obtain structured references for complaint generation.

As shown in Figure 3.2, the TAARN-style competing method starts from a case database and constructs a general case graph. The TAARN-style competing method then uses graph paths and text information to obtain case representations and retrieve relevant cases. By contrast, the proposed SDKG scheme does not treat the structure as a generic relevance graph. Instead, the proposed SDKG scheme first extracts legal structure and reconstructs case severity, then constructs severity-aware node relations and retrieves references through the light-heavy tree and the heavy-light tree according to legal distance and severity direction. At query time, the system identifies the anchor case by selecting the closest case \(c_i\) retrieved by the query-mapping distance \(d_{q,i}^{p,\ell}\) and retrieves references from the two trees.

如圖 3.2 所示，TAARN 式對手方法自案件資料庫出發，建立一般案件圖譜，接著使用圖譜路徑與文字資訊取得案件表示，並檢索相關案例。相較之下，所提出 SDKG scheme 不將此結構視為一般關聯圖譜，而是先萃取法律結構並重建案件嚴重度，再建立嚴重度感知節點關係，並依法律距離與嚴重度方向，透過 light-heavy tree 與 heavy-light tree 檢索參考節點。於查詢階段，系統先識別經由查詢映射距離 \(d_{q,i}^{p,\ell}\) 取得之最近案件 \(c_i\) 作為錨點案件，再由兩棵樹取得參考節點。

因此，TAARN 式對手方法與所提出 SDKG scheme 之差異不在於是否使用圖譜，而在於圖譜所表達之關係類型不同。TAARN 式對手方法主要建模一般案件關聯性；所提出 SDKG scheme 則進一步建模案件在法律結構與嚴重度方向上的相對位置。此差異使所提出 SDKG scheme 更適合交通事故民事起訴書生成，因為起訴書撰寫需要的不只是相似案例，而是能支援賠償請求、法律理由與事實結構之參考案例。

## 3.4 Comparison with Competing Methods

Table 3.1 compares conventional RAG, the TAARN-style competing method, legal KG/RAG methods, and the proposed SDKG scheme. Among the compared methods, TAARN is the main competing method because TAARN also uses graph and text information for retrieval. Conventional RAG and legal KG/RAG methods are included as background categories to clarify the design motivation of the proposed scheme.

表 3.1 比較一般 RAG、TAARN 式對手方法、法律知識圖譜與 RAG 方法，以及所提出 SDKG scheme。上述方法中，TAARN 是主要對手方法，因為其同樣使用圖譜與文字資訊進行檢索。一般 RAG 與法律知識圖譜／RAG 方法則作為背景類別，用以說明所提出 SDKG scheme 之設計動機。

**Table 3.1. Comparison of the proposed SDKG scheme with competing methods.**

| Models | Advantages | Limitations |
| --- | --- | --- |
| Conventional RAG [1], [3]-[5] | Simple, efficient, and easy to integrate with LLM-based generation. Conventional RAG can provide external examples and reduce purely parametric generation. | Retrieval is mainly based on semantic similarity. Conventional RAG does not explicitly model legal structure, severity direction, or whether a retrieved case is suitable for complaint drafting. |
| TAARN-style competing method [2] | Jointly uses graph relations and textual descriptions, making TAARN stronger than pure semantic retrieval for general case relevance modeling. TAARN can capture graph-path dependencies beyond flat text similarity. | Graph relations mainly capture general relevance. TAARN does not explicitly distinguish whether neighboring nodes are lighter or heavier than the node corresponding to the anchor case for traffic-accident complaint generation. |
| Legal KG/RAG methods [10]-[16], [19]-[22] | Improve legal grounding and provide more structured external references than flat document retrieval. Legal KG/RAG methods are useful for organizing statutes, legal entities, or legal knowledge. | Mostly designed for legal QA, statute retrieval, or general legal knowledge support rather than traffic-accident civil complaint generation. |
| Proposed SDKG scheme | Uses complete cases as nodes, constructs severity-aware relations, and retrieves references from both the light-heavy tree and the heavy-light tree. The proposed SDKG scheme is better aligned with complaint drafting needs. | Requires legal feature extraction, severity reconstruction, and multiple tree configurations, increasing preprocessing and implementation complexity. |

Compared with conventional RAG, the proposed SDKG scheme does not treat retrieved references as a flat collection of semantically similar texts. Instead, the proposed SDKG scheme converts observed cases into nodes and uses legal feature vectors and severity vectors to construct structured node relations. The severity-aware design is important because two cases may be semantically similar in language but different in liability structure, injury severity, or compensation claims. If structurally mismatched references are retrieved without control, the generated complaint may contain unsuitable facts or unsupported compensation arguments.

相較於一般 RAG，所提出 SDKG scheme 不將檢索參考視為語意相似文本的平面集合，而是將可觀測案件轉換為節點，並使用法律特徵向量與嚴重度向量建立結構化節點關係。此設計具有必要性，因為兩個案件可能在語言上相似，卻在責任結構、傷勢嚴重度或賠償請求上有所差異。若缺乏結構控制而直接檢索結構不匹配之參考資料，生成起訴書可能包含不適當事實或缺乏支撐之賠償主張。

Compared with the TAARN-style competing method, the proposed SDKG scheme focuses less on learning a general graph-text representation and more on constructing a task-specific retrieval structure. TAARN-style graph/text retrieval is useful for modeling general relevance and multi-hop relations, but the graph relation in TAARN does not explicitly distinguish whether the retrieved neighboring nodes are relatively lighter or heavier than the node corresponding to the anchor case. For traffic-accident civil complaint generation, the lighter-or-heavier distinction is important because the model must decide how retrieved facts, injuries, and compensation amounts should be used as references rather than copied directly.

相較於 TAARN 式對手方法，所提出 SDKG scheme 較不強調學習一般圖文表示，而是著重於建立任務特定之檢索結構。TAARN 式圖文檢索適合建模一般關聯性與多跳關係，但其圖譜關係未明確區分檢索到的鄰近節點相對於錨點案件之對應節點較輕或較重。對交通事故民事起訴書生成而言，此區分相當重要，因為模型必須判斷檢索到的事實、傷勢與賠償金額應如何作為參考，而非直接複製。

Compared with general legal KG/RAG methods, the proposed SDKG scheme is more narrowly designed for traffic-accident civil complaint generation. Many legal KG/RAG methods aim to improve legal question answering, statute retrieval, or general legal knowledge grounding. Legal KG/RAG methods provide useful structural support, but legal KG/RAG methods are not necessarily designed to organize complete traffic-accident cases according to legal comparability and compensation severity. The proposed SDKG scheme therefore uses complete cases as nodes, defines severity-aware relations, and retrieves structured references from the light-heavy tree and the heavy-light tree.

相較於一般法律知識圖譜與 RAG 方法，所提出 SDKG scheme 更聚焦於交通事故民事起訴書生成。許多法律知識圖譜與 RAG 方法旨在改善法律問答、法條檢索或一般法律知識支撐。這些方法能提供有用的結構化輔助，但未必以法律可比較性與賠償嚴重度組織完整交通事故案件。因此，所提出 SDKG scheme 使用完整案件作為節點，定義嚴重度感知關係，並由 light-heavy tree 與 heavy-light tree 檢索結構化參考案例。

整體而言，所提出 SDKG scheme 之核心優勢在於將「案件是否相關」進一步轉換為「節點是否在法律結構上可比，且相對於錨點案件之對應節點是較輕或較重」。此種設計使檢索結果較能符合交通事故民事起訴書生成之需求，並可降低生成模型錯誤借用他案事實、傷勢或賠償金額之風險。然而，所提出 SDKG scheme 亦需進行法律特徵萃取、嚴重度分數重建與多組樹狀參數設定，因此其預處理與系統實作成本高於一般 RAG。上述差異構成後續方法設計與實驗評估之基礎。

**Table 3.2. Symbol table used in Chapter 3.**

| Symbol | Description |
| --- | --- |
| \(N\) | Number of observed complaint-style cases, where \(N=6{,}057\). |
| \(\mathcal{D}\) | Observed complaint-style case database. |
| \(\mathbf{c}_i\) | The \(i\)-th observed complaint-style case. |
| \(\mathbf{m}_i\) | Complaint-style case material of case \(i\). |
| \(\mathbf{f}_i\) | Legal feature vector of case \(i\). |
| \(\mathbf{s}_i\) | Severity vector of case \(i\). |
| \(\mathbf{b}_{i,L}\) | Litigant-related boolean feature vector of case \(i\). |
| \(\mathbf{b}_{i,F}\) | Accident-fact-related boolean feature vector of case \(i\). |
| \(\mathbf{b}_{i,U}\) | Injury-related boolean feature vector of case \(i\). |
| \(\mathbf{b}_{i,P}\) | Compensation-related boolean feature vector of case \(i\). |
| \(s_{i,F}\) | Fact severity score of case \(i\). |
| \(s_{i,U}\) | Injury severity score of case \(i\). |
| \(s_{i,P}\) | Compensation severity score of case \(i\). |
| \(\alpha^p\) | Weight of fact severity under legal weight setting \(p\). |
| \(\beta^p\) | Weight of injury severity under legal weight setting \(p\). |
| \((1-\alpha^p-\beta^p)\) | Weight of compensation severity under legal weight setting \(p\). |
| \(p\) | Legal weight setting index, where \(1\leq p\leq 6\). |
| \(u\) | Threshold setting index. |
| \(\ell\) | Distance-weight setting index for \(\lambda^{\ell}\). |
| \(\tau^{u}\) | Distance threshold under threshold setting \(u\). |
| \(d_{i,j}^{p,\ell}\) | Node distance between nodes \(n_i\) and \(n_j\) under legal weight setting \(p\) and distance-weight setting \(\ell\). |
| \(d_s^{p}(\cdot)\) | Severity-distance function evaluated under legal weight setting \(p\). |
| \(\lambda^{\ell},(1-\lambda^{\ell})\) | Weights of legal feature distance and severity distance in \(d_{i,j}^{p,\ell}\). |
| \(n_i\) | Node converted from the observed case \(\mathbf{c}_i\). |
| \(n_r\) | Root node of a severity-directed retrieval tree. In the light-heavy tree it denotes the lowest-severity node, and in the heavy-light tree it denotes the highest-severity node under weight setting \(p\). |
| \(\mathbf{c}_i\mapsto n_i\) | Conversion from the observed case \(\mathbf{c}_i\) to node \(n_i\). |
| \(\mathcal{V}\) | Complete node set. |
| \(E^{p,u,\ell}\) | Comparable-node relation set under weight setting \(p\), threshold setting \(u\), and distance-weight setting \(\ell\). |
| \(g^{p,u,\ell}\) | Severity-aware DKG configuration under weight setting \(p\), threshold setting \(u\), and distance-weight setting \(\ell\). |
| \(n_i,n_j\) | Generic nodes used to define parent-child relations. |
| \(\mathrm{LH}\) | light-heavy direction. |
| \(\mathrm{HL}\) | heavy-light direction. |
| \(n_i\xrightarrow{\mathrm{LH}}n_j\) | Parent-child relation in the light-heavy tree, where \(n_j\) is a child node of \(n_i\). |
| \(n_i\xrightarrow{\mathrm{HL}}n_j\) | Parent-child relation in the heavy-light tree, where \(n_j\) is a child node of \(n_i\). |
| \(\mathbf{q}\) | Lawyer query. |
| \(m\) | Query index. |
| \(\mathbf{q}_m\) | The \(m\)-th testing query. |
| \(\mathbf{y}^{*}_m\) | Human-written reference complaint corresponding to query \(\mathbf{q}_m\). |
| \(\hat{\mathbf{y}}_m\) | Generated complaint for query \(\mathbf{q}_m\). |
| \(\mathbf{z}_m\) | Structured prompt constructed for query \(\mathbf{q}_m\). |
| \(\mathcal{L}(\cdot)\) | Generation-gap measurement between a generated complaint and a human-written reference complaint. |
| \(\mathcal{R}(\mathbf{q}_m)\) | Reference case set selected for query \(\mathbf{q}_m\). |
| \(\mathcal{R}^{*}(\mathbf{q}_m)\) | Selected reference case set that minimizes the generation gap for query \(\mathbf{q}_m\). |
| \(\mathbf{f}_q\) | Extracted legal feature vector of the query. |
| \(\mathbf{s}_q\) | Extracted severity vector of the query. |
| \(d_{q,i}^{p,\ell}\) | Query-mapping distance between query \(\mathbf{q}\) and case \(c_i\) under weight setting \(p\) and distance-weight setting \(\ell\). |
| \(a(c_i,\mathbf{q})\) | Anchor condition indicating that case \(c_i\) is the closest observed case retrieved for query \(\mathbf{q}\). |
| \(\mathcal{R}_{LH}(\mathbf{q})\) | Retrieved heavier-direction references from the light-heavy tree. |
| \(\mathcal{R}_{HL}(\mathbf{q})\) | Retrieved lighter-direction references from the heavy-light tree. |
| \(k\) | Total number of retrieved reference nodes. |
| \(\Phi(\cdot)\) | Structured prompt construction function. |
| \(M(\cdot)\) | Complaint generation model. |
| \(\mathbf{P}_1\) | Complaint-generation objective that minimizes the generation gap. |
| \(\mathbf{P}_2\) | Reference-selection objective that chooses \(\mathcal{R}^{*}(\mathbf{q}_m)\). |
| \(\mathrm{C}_1\) | Prompt-construction condition for \(\mathbf{z}_m\). |
| \(\mathrm{C}_2\) | Database-membership condition for each selected case \(\mathbf{c}_j\). |
| \(\mathrm{C}_3\) | top-\(k\) budget condition for \(\mathcal{R}(\mathbf{q}_m)\). |
