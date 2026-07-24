# Chapter 6 Experimental Results and Discussion

This chapter presents the experimental design and evaluation results for the proposed Severity-Aware Dual-Knowledge-Graph (SDKG) scheme. The goal is to examine whether the proposed retrieval structure can select legally comparable traffic-accident cases and improve civil complaint generation. The evaluation compares the generated complaint with the human-written reference complaint under automatic metrics and legal-domain human evaluation.

本章說明所提出 Severity-Aware Dual-Knowledge-Graph (SDKG) scheme 之實驗設計與評估結果。實驗目的在於檢驗所提出之檢索結構是否能取得具法律可比性之交通事故案例，並進一步提升民事起訴書生成品質。評估方式包含自動化指標，以及法律背景人員之人工驗證。

## 6.1 Experimental Setup

The experiments are conducted on the traffic-accident civil complaint generation task. The case database contains \(6{,}057\) complaint-style cases. Each case is represented by legal boolean features and severity scores as defined in Chapters 3 and 5. The evaluation compares SDKG with TAARN, gpt-4o-mini, and the Baseline Method derived from the sentence-level-aware dual retrieval method in Chapter 4. For each SDKG test query, the system first maps the query to the closest observed case, uses the corresponding node as the anchor node, retrieves references from the light-heavy and heavy-light retrieval trees, and then generates a complaint through the prompt assembler and generation model.

本研究以交通事故民事起訴書生成任務作為實驗場景。案件資料庫包含 \(6{,}057\) 筆起訴書樣式案件，每筆案件皆依第三章與第五章所述方法轉換為法律布林特徵與嚴重度分數。評估對象包含 SDKG、TAARN、gpt-4o-mini，以及由第四章 sentence-level-aware dual retrieval method 延伸而來的 Baseline Method。對每一筆 SDKG 測試查詢，系統先將查詢映射至最接近之既有案件，再以該案件對應節點作為錨點節點，從 light-heavy 與 heavy-light 檢索樹取得參考案例，最後經由提示組裝器與生成模型產生起訴書。

**Table 6.1. Experimental setup.**

| Item | Setting |
| --- | --- |
| Implementation language | Python |
| Graph database | Neo4j |
| Case database size | 6,057 traffic-accident complaint-style cases |
| Test queries | 50 simulated lawyer queries |
| Retrieval depth | top-\(k\) from 1 to 10 |
| SDKG configurations | \(6\times3\times3=54\) configurations |
| Compared methods | SDKG, Baseline Method, TAARN, gpt-4o-mini |
| Automatic metrics | BERTScore, BLEU, ROUGE-L |
| Human evaluation | Legal-domain scoring and comments |

Let the test set be denoted as:

測試集合表示如下：

\[
\mathcal{Q}_{test}
=
\{(\mathbf{q}_m,\mathbf{y}^{*}_m)\}_{m=1}^{M},
\quad M=50,
\tag{6.1}
\]

where \(\mathbf{q}_m\) denotes the \(m\)-th simulated lawyer query, and \(\mathbf{y}^{*}_m\) denotes the corresponding human-written reference complaint. For SDKG configuration \(g^{p,u,\ell}\) and retrieval depth \(k\), the generated complaint is denoted by \(\hat{\mathbf{y}}_{m}^{p,u,\ell,k}\). Let \(\mu(\cdot,\cdot)\) denote an automatic evaluation function, such as BERTScore, BLEU, or ROUGE-L. The automatic evaluation result \(S^{p,u,\ell,k}\) of a configuration is computed by averaging over all test queries:

其中，\(\mathbf{q}_m\) 表示第 \(m\) 筆模擬律師查詢，\(\mathbf{y}^{*}_m\) 表示對應之人工參考起訴書。對 SDKG 配置 \(g^{p,u,\ell}\) 與檢索深度 \(k\) 而言，生成起訴書記為 \(\hat{\mathbf{y}}_{m}^{p,u,\ell,k}\)。令 \(\mu(\cdot,\cdot)\) 表示自動化評估函數，例如 BERTScore、BLEU 或 ROUGE-L。配置之自動化評估結果 \(S^{p,u,\ell,k}\) 以所有測試查詢之平均值計算：

\[
S^{p,u,\ell,k}
=
\frac{1}{M}
\sum_{m=1}^{M}
\mu
(\hat{\mathbf{y}}_{m}^{p,u,\ell,k},\mathbf{y}^{*}_m).
\tag{6.2}
\]

## 6.2 Performance Settings

The SDKG experiments evaluate three parameter dimensions. The first dimension is the legal severity weight setting \(p\), which controls the relative importance of fact severity, injury severity, and compensation severity through \(\alpha^p\), \(\beta^p\), and \((1-\alpha^p-\beta^p)\). The second dimension is the relation threshold setting \(u\), which controls how strict the pairwise edge construction is. The third dimension is the distance-weight setting \(\ell\), which controls the balance between legal feature distance and severity distance in \(d_{i,j}^{p,\ell}\). In contrast, the Baseline Method keeps the Chapter 4 retrieval form: it uses paragraph summaries \(\bar{\theta}_{i,o}\), sentence summaries \(\bar{\theta}_{i,o,v}\), and the retrieved paragraph and sentence results \(R_o(\mathbf{q}_m)\) and \(R_v(\mathbf{q}_m)\), but does not construct the severity-aware edge set \(E^{p,u,\ell}\) or the light-heavy and heavy-light trees.

SDKG 實驗包含三個參數維度。第一個維度為法律嚴重度權重設定 \(p\)，透過 \(\alpha^p\)、\(\beta^p\) 與 \((1-\alpha^p-\beta^p)\) 控制事故事實、傷勢與賠償嚴重度之相對重要性。第二個維度為關係門檻設定 \(u\)，用以控制兩兩案件建邊時的嚴格程度。第三個維度為距離權重設定 \(\ell\)，用以控制 \(d_{i,j}^{p,\ell}\) 中法律特徵距離與嚴重度距離之比重。相對地，Baseline Method 保留第四章的檢索形式：其使用段落摘要 \(\bar{\theta}_{i,o}\)、句子摘要 \(\bar{\theta}_{i,o,v}\)，以及檢索得到的段落與句子結果 \(R_o(\mathbf{q}_m)\)、\(R_v(\mathbf{q}_m)\)，但不建立嚴重度感知邊集合 \(E^{p,u,\ell}\)，也不建立 light-heavy 與 heavy-light 樹。

The evaluated parameter values are summarized in Table 6.2.

實驗參數設定整理如 Table 6.2 所示。

**Table 6.2. SDKG parameter settings.**

| Parameter | Values | Meaning |
| --- | --- | --- |
| \((\alpha,\beta)\) | \((0.2,0.3),(0.2,0.5),(0.3,0.2),(0.3,0.5),(0.5,0.2),(0.5,0.3)\) | Six legal severity weight settings |
| \(\tau\) | \(0.1,0.25,0.5\) | Low, medium, and high relation thresholds |
| \(\lambda\) | \(0.2,0.5,0.7\) | Distance weights between legal feature distance and severity distance |
| top-\(k\) | \(1,\ldots,10\) | Number of retrieved reference cases |

Thus, the total number of SDKG configurations is:

因此，SDKG 配置總數為：

\[
6\times3\times3=54.
\tag{6.3}
\]

The threshold \(\tau=0.1\) represents a strict setting, where only highly similar case pairs are connected. The threshold \(\tau=0.25\) represents a medium setting, which allows more comparable cases while still filtering out distant cases. The threshold \(\tau=0.5\) represents a high setting, which keeps a broader set of comparable cases and provides more candidate references during retrieval. These values are selected within the normalized distance range \([0,1]\), so the threshold settings can be interpreted as low, medium, and high relation strictness.

\(\tau=0.1\) 表示較嚴格之建邊設定，只有高度相似的案件對會被連接。\(\tau=0.25\) 表示中等設定，可保留較多可比較案例，同時仍排除距離較遠之案件。\(\tau=0.5\) 表示較寬鬆之設定，可保留更廣的可比較案例並提供較多檢索候選。由於距離值已正規化至 \([0,1]\)，上述門檻可合理解釋為低、中、高三種關係嚴格程度。

The value \(\lambda=0.2\) emphasizes severity distance, \(\lambda=0.7\) emphasizes legal feature distance, and \(\lambda=0.5\) provides a balanced setting. Including \(\lambda\) in the experiment is necessary because the construction of \(E^{p,u,\ell}\) depends on \(d_{i,j}^{p,\ell}\). Different \(\lambda\) values may therefore produce different edges, different retrieval candidates, and different generated complaints.

\(\lambda=0.2\) 較重視嚴重度距離，\(\lambda=0.7\) 較重視法律特徵距離，\(\lambda=0.5\) 則作為平衡設定。由於 \(E^{p,u,\ell}\) 之建構依賴 \(d_{i,j}^{p,\ell}\)，因此將 \(\lambda\) 納入實驗是必要的。不同 \(\lambda\) 可能產生不同邊集合、不同檢索候選，進而影響最終生成結果。

### 6.2.1 Automatic Evaluation Metrics

This study uses BERTScore, BLEU, and ROUGE-L as automatic metrics. These metrics evaluate different aspects of complaint generation quality. BERTScore measures semantic similarity, BLEU measures phrase-level overlap, and ROUGE-L measures sequence and structural overlap. Since legal complaints may have multiple valid expressions, no single automatic metric is sufficient by itself. The three metrics are interpreted together and supplemented by human evaluation.

本研究採用 BERTScore、BLEU 與 ROUGE-L 作為自動化評估指標。三項指標分別觀察起訴書生成品質之不同面向：BERTScore 衡量語意相似度，BLEU 衡量片語層級重疊，ROUGE-L 衡量文字順序與結構重疊。由於法律起訴書可能存在多種合理寫法，單一自動化指標不足以完整評估生成品質，因此本文將三項指標共同解讀，並以人工驗證作為補充。

### 6.2.2 BERTScore

BERTScore compares contextual embeddings between the generated complaint and the reference complaint [23]. Given generated complaint \(\hat{\mathbf{y}}\) and reference complaint \(\mathbf{y}^{*}\), let \(\mathbf{h}_i\) denote the contextual embedding of the \(i\)-th token in \(\hat{\mathbf{y}}\), and let \(\mathbf{h}^{*}_j\) denote the contextual embedding of the \(j\)-th token in \(\mathbf{y}^{*}\). BERTScore precision and recall are:

BERTScore 透過上下文詞向量比較生成起訴書與人工參考起訴書之語意相似度 [23]。給定生成起訴書 \(\hat{\mathbf{y}}\) 與參考起訴書 \(\mathbf{y}^{*}\)，令 \(\mathbf{h}_i\) 表示 \(\hat{\mathbf{y}}\) 中第 \(i\) 個詞元之上下文向量，\(\mathbf{h}^{*}_j\) 表示 \(\mathbf{y}^{*}\) 中第 \(j\) 個詞元之上下文向量。BERTScore precision 與 recall 定義如下：

\[
P_{BERT}
=
\frac{1}{|\hat{\mathbf{y}}|}
\sum_{\mathbf{h}_i\in\hat{\mathbf{y}}}
\max_{\mathbf{h}^{*}_j\in\mathbf{y}^{*}}
\cos(\mathbf{h}_i,\mathbf{h}^{*}_j),
\tag{6.4}
\]

\[
R_{BERT}
=
\frac{1}{|\mathbf{y}^{*}|}
\sum_{\mathbf{h}^{*}_j\in\mathbf{y}^{*}}
\max_{\mathbf{h}_i\in\hat{\mathbf{y}}}
\cos(\mathbf{h}^{*}_j,\mathbf{h}_i).
\tag{6.5}
\]

The final BERTScore is computed as:

最終 BERTScore 計算如下：

\[
F_{BERT}
=
\frac{2P_{BERT}R_{BERT}}
{P_{BERT}+R_{BERT}}.
\tag{6.6}
\]

In this task, BERTScore is used to observe whether the generated complaint preserves the semantic content of the reference complaint, such as accident facts, injury descriptions, and compensation claims.

在本任務中，BERTScore 用以觀察生成起訴書是否保留人工參考起訴書之語意內容，例如事故經過、傷勢描述與賠償請求。

### 6.2.3 BLEU

BLEU is a precision-based metric originally proposed for machine translation evaluation [24]. It measures whether n-grams in the generated text also appear in the reference text. The BLEU score is:

BLEU 是一種以 precision 為基礎之文本生成評估指標，最初用於機器翻譯評估 [24]。BLEU 衡量生成文本中的 n-gram 是否也出現在參考文本中。BLEU 定義如下：

\[
\mathrm{BLEU}
=
\mathrm{BP}\cdot
\exp\left(
\sum_{n=1}^{N}w_n\log p_n
\right),
\tag{6.7}
\]

where \(p_n\) is the modified n-gram precision, \(w_n\) is the weight of each n-gram order, and \(\mathrm{BP}\) is the brevity penalty:

其中，\(p_n\) 為修正後之 n-gram precision，\(w_n\) 為各階 n-gram 權重，\(\mathrm{BP}\) 為長度懲罰：

\[
\mathrm{BP}
=
\begin{cases}
1, & c>r,\\
\exp(1-r/c), & c\leq r,
\end{cases}
\tag{6.8}
\]

where \(c\) is the generated text length and \(r\) is the reference text length. In this study, BLEU is used as a surface-form overlap indicator. It is useful for checking whether legal terms, compensation items, and common pleading expressions are preserved, but it should not be interpreted alone because legally correct paraphrases may receive lower BLEU scores.

其中，\(c\) 為生成文本長度，\(r\) 為參考文本長度。本研究將 BLEU 作為表層文字重疊指標，用以觀察法條用語、賠償項目與常見書狀表達是否被保留。然而，由於法律上正確的改寫可能使用不同文字，BLEU 不宜單獨作為判斷依據。

### 6.2.4 ROUGE-L

ROUGE-L evaluates the longest common subsequence between the generated text and the reference text [25]. It is useful for observing whether the generated complaint preserves the order and structure of the reference complaint. Let \(\mathrm{LCS}(\hat{\mathbf{y}},\mathbf{y}^{*})\) denote the length of the longest common subsequence. The precision and recall are:

ROUGE-L 透過生成文本與參考文本之最長共同子序列評估文本生成品質 [25]，適合觀察生成起訴書是否保留參考起訴書之內容順序與段落結構。令 \(\mathrm{LCS}(\hat{\mathbf{y}},\mathbf{y}^{*})\) 表示最長共同子序列長度，precision 與 recall 定義如下：

\[
P_{LCS}
=
\frac{\mathrm{LCS}(\hat{\mathbf{y}},\mathbf{y}^{*})}
{|\hat{\mathbf{y}}|},
\tag{6.9}
\]

\[
R_{LCS}
=
\frac{\mathrm{LCS}(\hat{\mathbf{y}},\mathbf{y}^{*})}
{|\mathbf{y}^{*}|}.
\tag{6.10}
\]

The ROUGE-L F1 score is:

ROUGE-L F1 分數為：

\[
F_{LCS}
=
\frac{(1+\gamma^2)P_{LCS}R_{LCS}}
{R_{LCS}+\gamma^2P_{LCS}}.
\tag{6.11}
\]

where \(\gamma\) controls the relative weight of precision and recall in ROUGE-L. In this study, \(\gamma=1\) is used for the F1 form.

其中，\(\gamma\) 控制 ROUGE-L 中 precision 與 recall 的相對權重。本文採用 \(\gamma=1\) 之 F1 形式。

In the complaint generation task, ROUGE-L is used to observe whether the generated text maintains the main sequence of accident facts, legal grounds, damages, and claims.

在起訴書生成任務中，ROUGE-L 用以觀察生成文本是否維持事故事實、法律依據、損害賠償與請求事項之主要順序。

### 6.2.5 Human Evaluation Design

Automatic metrics provide quantitative comparison, but they cannot fully determine legal correctness. Therefore, this study further uses human evaluation by legal-domain reviewers. Each generated complaint is evaluated as a complete legal document, rather than only as a text similar to the reference answer.

自動化指標可提供量化比較，但無法完整判斷法律正確性。因此，本研究進一步採用法律背景人員進行人工驗證。人工驗證時，每篇生成起訴書會被視為一份完整法律文書評估，而非僅視為與參考答案相似的文本。

To keep the human evaluation workload manageable, the human evaluation compares representative systems rather than all 54 SDKG configurations. The selected systems include gpt-4o-mini, three SDKG representatives grouped by \(\alpha\), Baseline Method, and TAARN. For SDKG, the representative configuration is selected separately from the \(\alpha=0.5\), \(\alpha=0.3\), and \(\alpha=0.2\) groups by choosing the best-performing curve within each group under the automatic metrics. The selected SDKG configurations are SDKG \((\alpha=0.5,\beta=0.2,\lambda=0.5,\tau=0.5)\), SDKG \((\alpha=0.3,\beta=0.2,\lambda=0.5,\tau=0.5)\), and SDKG \((\alpha=0.2,\beta=0.5,\lambda=0.5,\tau=0.5)\). This design allows the human evaluation to compare the legal quality of the best SDKG outputs under different fact-severity emphases, instead of using vague high, middle, and low labels. Baseline Method is included to compare the Chapter 4 sentence-level-aware retrieval design with the Chapter 5 case-level SDKG design.

為控制人工評估工作量，人工驗證不逐一評估全部 54 組 SDKG 配置，而是比較具代表性的方法。選定方法包含 gpt-4o-mini、依 \(\alpha\) 分組之三組 SDKG 代表配置、Baseline Method 與 TAARN。對 SDKG 而言，代表配置分別從 \(\alpha=0.5\)、\(\alpha=0.3\) 與 \(\alpha=0.2\) 三組中選取，並以各組在自動化指標下表現最佳的曲線作為人工評估對象。選定之 SDKG 配置為 SDKG \((\alpha=0.5,\beta=0.2,\lambda=0.5,\tau=0.5)\)、SDKG \((\alpha=0.3,\beta=0.2,\lambda=0.5,\tau=0.5)\) 與 SDKG \((\alpha=0.2,\beta=0.5,\lambda=0.5,\tau=0.5)\)。此設計可比較不同事故事實嚴重度權重下最佳 SDKG 輸出的法律品質，而不使用較模糊的 high、middle 與 low 標籤。Baseline Method 則用以比較第四章 sentence-level-aware retrieval 設計與第五章 case-level SDKG 設計之差異。

**Table 6.3. Candidate systems for human evaluation.**

| Method | Role |
| --- | --- |
| gpt-4o-mini | Strong external model baseline |
| SDKG \((\alpha=0.5,\beta=0.2,\lambda=0.5,\tau=0.5)\) | Best-performing SDKG configuration within the \(\alpha=0.5\) group |
| SDKG \((\alpha=0.3,\beta=0.2,\lambda=0.5,\tau=0.5)\) | Best-performing SDKG configuration within the \(\alpha=0.3\) group |
| SDKG \((\alpha=0.2,\beta=0.5,\lambda=0.5,\tau=0.5)\) | Best-performing SDKG configuration within the \(\alpha=0.2\) group |
| Baseline Method | Chapter 4 sentence-level-aware dual retrieval baseline |
| TAARN | Graph-based competing method |

The human evaluation criteria are shown in Table 6.4.

人工評分規準如 Table 6.4 所示。

**Table 6.4. Human evaluation criteria.**

| Criterion | Description |
| --- | --- |
| Fact consistency | Whether the generated complaint preserves parties, accident facts, injuries, and claimed damages |
| Legal basis | Whether the cited legal grounds are appropriate |
| Compensation correctness | Whether compensation items and amounts are preserved without unsupported changes |
| Complaint structure | Whether the generated text follows the structure of a civil complaint |
| Overall legal usability | Whether the output can serve as a useful drafting reference |

For each evaluated output, the legal-domain reviewer assigns a score and may provide a short comment. This design allows the evaluation to capture both numerical quality and concrete legal errors, such as missing parties, incorrect compensation items, unsupported statutes, or structurally incomplete claims. The human evaluation has not yet been completed at this stage, so this subsection defines the evaluation protocol and candidate systems only.

對每一篇受評生成結果，法律背景評估者給予分數，並可補充簡短備註。此設計可同時取得數值評分與具體法律錯誤說明，例如當事人遺漏、賠償項目錯誤、法條引用不當，或請求結構不完整等問題。本階段尚未完成人工驗證，因此本小節僅先定義評估流程與候選系統。

## 6.3 Evaluation Results

This section reports the automatic evaluation results by metric. For each metric, two experiments are presented together. The first experiment varies top-\(k\) from 1 to 10 to examine how the number of retrieved reference cases affects complaint generation. The second experiment fixes top-\(k\) at 8 and varies the number of cases used to construct the SDKG retrieval trees, including 1,000, 2,000, 3,000, 4,000, 5,000, and the full database of 6,057 cases. Therefore, each metric is analyzed from both the retrieval-depth perspective and the case-coverage perspective. Baseline Method is also included in the figures. It follows the Chapter 4 setting, where \(R_o(\mathbf{q}_m)\) and \(R_v(\mathbf{q}_m)\) are retrieved from paragraph-level and sentence-level summaries and then assembled into \(\mathbf{z}_m\). This baseline allows the experiment to directly observe the effect of moving from paragraph and sentence retrieval to case-level severity-aware SDKG retrieval.

本節依自動化指標呈現實驗結果。對每一項指標，本文同時呈現兩組實驗。第一組實驗將 top-\(k\) 由 1 調整至 10，以觀察檢索參考案例數量對起訴書生成品質之影響。第二組實驗固定 top-\(k\) 為 8，並改變用於建構 SDKG 檢索樹之案件數量，包含 1,000、2,000、3,000、4,000、5,000 與完整資料庫 6,057 筆。因此，每一項指標皆同時從檢索深度與案件覆蓋率兩個角度分析。圖中亦納入 Baseline Method。此方法延續第四章設定，先由段落層級與句子層級摘要取得 \(R_o(\mathbf{q}_m)\) 與 \(R_v(\mathbf{q}_m)\)，再組成 \(\mathbf{z}_m\)。透過此 baseline，可直接觀察從 paragraph and sentence retrieval 轉向 case-level severity-aware SDKG retrieval 後所帶來的差異。

In the top-\(k\) experiment, the scores at top-1 and top-2 are usually not the highest because the prompt contains only a very small number of reference cases. Although these cases are selected by SDKG retrieval, one or two references may cover only part of the required drafting information, such as the accident facts, the injury description, or the compensation claim, but not all of them at the same time. As \(k\) increases, the prompt can include more comparable cases from the light-heavy and heavy-light directions, so the generation model receives a more complete range of legal and severity-side references. Therefore, the scores generally improve after more references are added, until the useful information becomes saturated.

在 top-\(k\) 實驗中，top-1 與 top-2 的分數通常不是最高，原因是提示中只有極少量參考案例。即使這些案例已由 SDKG 檢索選出，一至兩筆參考仍可能只涵蓋部分撰寫資訊，例如事故事實、傷勢描述或賠償請求其中之一，而無法同時提供完整支撐。隨著 \(k\) 增加，提示可納入更多來自 light-heavy 與 heavy-light 方向的可比較案例，使生成模型取得較完整的法律與嚴重度參考。因此，分數通常會在加入更多參考案例後上升，直到有效資訊逐漸飽和。

In the number-of-cases experiment, the x-axis is the number of cases used to construct the SDKG retrieval trees, including 1,000, 2,000, 3,000, 4,000, 5,000, and the full database of 6,057 cases. For Baseline Method, the same x-axis controls the size of the paragraph and sentence summary database used for retrieval. Since the best top-\(k\) result is observed around top-8, this experiment fixes \(k=8\) and varies only the available case size. Therefore, when the case count reaches 6,057, the scores are consistent with the top-\(k\) experiment at \(k=8\).

在案件數實驗中，x 軸為用於建構 SDKG 檢索樹的案件數量，包含 1,000、2,000、3,000、4,000、5,000 與完整資料庫 6,057 筆。對 Baseline Method 而言，同一 x 軸則表示可用於段落與句子摘要檢索的案件資料規模。由於前述 top-\(k\) 實驗顯示 top-8 附近可取得最佳或接近最佳表現，因此本實驗固定 \(k=8\)，僅改變可用案件規模。因此，當案件數達 6,057 時，其分數與 top-\(k\) 實驗中 \(k=8\) 的結果一致。

Across all figures, the three panels correspond to \(\alpha=0.2\), \(\alpha=0.3\), and \(\alpha=0.5\). Within each panel, different SDKG curves represent different combinations of \(\beta\), \(\lambda\), and \(\tau\). The gpt-4o-mini line is used as a strong external reference, TAARN is used as the graph-based competing method, and Baseline Method is used as the Chapter 4 retrieval baseline.

在所有圖中，三個子圖分別對應 \(\alpha=0.2\)、\(\alpha=0.3\) 與 \(\alpha=0.5\)。每一個子圖內，不同 SDKG 曲線表示不同 \(\beta\)、\(\lambda\) 與 \(\tau\) 組合。gpt-4o-mini 作為外部強模型參考線，TAARN 作為圖檢索式對手方法，Baseline Method 則作為第四章檢索方法之 baseline。

### 6.3.1 BERTScore Performance

![Figure 6.1 top-\(k\) BERTScore results of SDKG configurations and Baseline Method.](</home/aru/AI_LAW/image copy 31.png>)

**Figure 6.1. top-\(k\) BERTScore results.** The x-axis is top-\(k\), and the three panels correspond to \(\alpha=0.2\), \(\alpha=0.3\), and \(\alpha=0.5\). Baseline Method is included as the Chapter 4 retrieval baseline.

Figure 6.1 shows the BERTScore results under different top-\(k\) values. In all three \(\alpha\) groups, SDKG improves rapidly from top-1 to top-3 because the prompt begins to include more than one comparable case and can cover more accident facts, injury descriptions, and compensation cues. After top-4, the curves increase more gradually and reach the strongest or near-strongest values around top-8. top-9 and top-10 then become stable or slightly weaker, indicating that additional cases may provide repeated information rather than new semantic support. Baseline Method is consistently higher than TAARN, which shows that the paragraph and sentence summaries from Chapter 4 already provide useful semantic retrieval support. However, Baseline Method remains lower than all SDKG curves because it does not use the case-level node \(n_i\), the distance \(d_{i,j}^{p,\ell}\), the threshold \(\tau^u\), or the light-heavy and heavy-light direction constraints to retrieve legally comparable full cases.

圖 6.1 顯示不同 top-\(k\) 下之 BERTScore 結果。在三個 \(\alpha\) 組中，SDKG 皆由 top-1 至 top-3 呈現較明顯提升，原因是提示開始納入不只一筆可比較案例，因此能涵蓋更多事故經過、傷勢描述與賠償線索。top-4 之後，曲線提升逐漸趨緩，並於 top-8 附近達到最佳或接近最佳表現。top-9 與 top-10 則呈現穩定或微幅下降，表示額外案例可能更多提供重複資訊，而非新的語意支撐。Baseline Method 穩定高於 TAARN，顯示第四章的段落與句子摘要已能提供有用的語意檢索支撐。然而，Baseline Method 仍低於所有 SDKG 曲線，原因是其未使用案件節點 \(n_i\)、距離 \(d_{i,j}^{p,\ell}\)、門檻 \(\tau^u\)，以及 light-heavy 與 heavy-light 方向限制來取得法律上可比較的完整案件。

![Figure 6.2 Number-of-cases BERTScore results of SDKG configurations and Baseline Method.](</home/aru/AI_LAW/image copy 32.png>)

**Figure 6.2. Number-of-cases BERTScore results.** The x-axis is the number of cases used to construct the retrieval trees, and top-\(k\) is fixed at 8.

Figure 6.2 reports the BERTScore results when the number of cases used to construct the retrieval trees is varied. The curves generally rise from 1,000 cases to 6,057 cases. The gain from 1,000 to 2,000 or 3,000 cases is especially visible because a small tree contains fewer directionally comparable neighbors for each anchor case. Baseline Method also improves as the case count increases, which indicates that more paragraph and sentence summaries improve retrieval coverage. However, the improvement of Baseline Method is smaller than that of SDKG because increasing paragraph and sentence chunks alone does not guarantee full-case legal comparability. As more cases are added, the SDKG graph provides broader semantic coverage and more stable lighter-side and heavier-side references. After approximately 4,000 cases, the improvement becomes more gradual, suggesting that the retrieval coverage begins to approach saturation. At 6,057 cases, the BERTScore values correspond to the top-\(k\) experiment at \(k=8\). Among the three panels, the \(\alpha=0.5\) group contains the highest BERTScore curve, especially the setting with \(\beta=0.2\), \(\lambda=0.5\), and \(\tau=0.5\).

圖 6.2 呈現改變檢索樹建構案件數時的 BERTScore 結果。整體曲線由 1,000 筆至 6,057 筆逐步上升，其中 1,000 至 2,000 或 3,000 筆的提升較明顯，原因是小規模檢索樹中，每個錨點可取得的方向性可比較鄰近案例較少。Baseline Method 也會隨案件數增加而改善，表示更多段落與句子摘要能提高檢索覆蓋率。然而，Baseline Method 的提升幅度小於 SDKG，因為僅增加 paragraph and sentence chunks 並不能保證完整案件層級的法律可比較性。隨著案件數增加，SDKG 圖能提供更廣的語意覆蓋，並提供更穩定的較輕與較重方向參考。約 4,000 筆後，提升幅度逐漸變緩，表示檢索覆蓋開始接近飽和。當案件數達 6,057 筆時，其 BERTScore 數值對應於 top-\(k\) 實驗中 \(k=8\) 的結果。三個子圖中，\(\alpha=0.5\) 組包含最高 BERTScore 曲線，尤其是 \(\beta=0.2\)、\(\lambda=0.5\)、\(\tau=0.5\) 的設定。

### 6.3.2 BLEU Performance

![Figure 6.3 top-\(k\) BLEU results of SDKG configurations and Baseline Method.](</home/aru/AI_LAW/image copy 33.png>)

**Figure 6.3. top-\(k\) BLEU results.** BLEU evaluates exact phrase and n-gram overlap under different top-\(k\) values. Baseline Method represents the Chapter 4 paragraph and sentence retrieval baseline.

Figure 6.3 shows the top-\(k\) results under BLEU. Compared with BERTScore, BLEU values are lower because BLEU depends on exact n-gram overlap and is more sensitive to wording differences. Nevertheless, the overall trend remains consistent: SDKG improves from small top-\(k\) values to approximately top-8, and then becomes stable or slightly weaker. Baseline Method is slightly higher than TAARN, which suggests that the retrieved paragraph and sentence summaries help preserve some legal phrases, compensation-item wording, and common complaint expressions. However, its BLEU values remain below SDKG because sentence-level retrieval may return useful local wording without preserving the complete compensation structure of a comparable case. The parameter separation is also more visible in BLEU. In the \(\alpha=0.2\) panel, stronger curves are mostly associated with higher \(\beta\), especially \(\beta=0.5\). In the \(\alpha=0.3\) and \(\alpha=0.5\) panels, stronger curves shift toward \(\beta=0.2\), particularly when \(\lambda=0.5\) and \(\tau=0.5\).

圖 6.3 顯示 BLEU 下的 top-\(k\) 結果。相較於 BERTScore，BLEU 數值較低，因為 BLEU 依賴精確 n-gram 重疊，且對文字改寫較敏感。然而，整體趨勢仍一致：SDKG 由較小 top-\(k\) 提升至約 top-8，之後呈現穩定或微幅下降。Baseline Method 略高於 TAARN，表示檢索段落與句子摘要有助於保留部分法條片語、賠償項目用語與常見起訴書表達。然而，其 BLEU 仍低於 SDKG，原因是 sentence-level retrieval 雖可取得局部有用語句，卻不一定保留可比較案件的完整賠償結構。BLEU 中參數差異也更明顯。在 \(\alpha=0.2\) 子圖中，較強曲線多與較高 \(\beta\) 有關，尤其是 \(\beta=0.5\)。在 \(\alpha=0.3\) 與 \(\alpha=0.5\) 子圖中，較強曲線則轉向 \(\beta=0.2\)，特別是搭配 \(\lambda=0.5\) 與 \(\tau=0.5\) 時。

![Figure 6.4 Number-of-cases BLEU results of SDKG configurations and Baseline Method.](</home/aru/AI_LAW/image copy 34.png>)

**Figure 6.4. Number-of-cases BLEU results.** The x-axis is the number of cases used to construct the retrieval trees, and top-\(k\) is fixed at 8.

Figure 6.4 shows that BLEU increases as the number of cases grows. The improvement from 1,000 to 2,000 and 3,000 cases is clear because a larger graph provides more reusable legal expressions and compensation descriptions. Baseline Method also rises with more cases because a larger database contains more paragraph and sentence summaries that may match the query wording. However, Baseline Method remains close to TAARN and below all SDKG curves, showing that exact wording alone is not sufficient for stable complaint generation. As the graph grows, SDKG can retrieve cases with more similar pleading language while still controlling comparability through \(\mathbf{f}_i\), \(\mathbf{s}_i\), and \(d_{i,j}^{p,\ell}\). The curves continue to rise toward 6,057 cases, but the slope becomes milder after the middle range, which indicates that the reusable wording gradually becomes saturated.

圖 6.4 顯示 BLEU 會隨案件數增加而提升。由 1,000 筆增加至 2,000 與 3,000 筆時提升明顯，原因是較大的圖可提供更多可重用法律表述與賠償描述。Baseline Method 也會隨案件數增加而上升，因為較大的資料庫包含更多可能符合查詢文字的段落與句子摘要。然而，Baseline Method 仍接近 TAARN 且低於所有 SDKG 曲線，顯示僅依局部文字表達仍不足以穩定提升起訴書生成。隨著圖規模增加，SDKG 較容易取得具有相似起訴書語言的案例，同時仍透過 \(\mathbf{f}_i\)、\(\mathbf{s}_i\) 與 \(d_{i,j}^{p,\ell}\) 控制案例可比較性。曲線持續往 6,057 筆上升，但中段後斜率逐漸變緩，表示可重用用語逐漸飽和。

### 6.3.3 ROUGE-L Performance

![Figure 6.5 top-\(k\) ROUGE-L results of SDKG configurations and Baseline Method.](</home/aru/AI_LAW/image copy 35.png>)

**Figure 6.5. top-\(k\) ROUGE-L results.** ROUGE-L evaluates sequence and document-structure overlap under different top-\(k\) values. Baseline Method provides the paragraph and sentence retrieval comparison.

Figure 6.5 shows the ROUGE-L results for the top-\(k\) experiment. The curves again rise from top-1 to approximately top-8 and then become stable or slightly weaker. Since ROUGE-L measures longest common subsequence overlap, this trend suggests that SDKG references help preserve the main order of accident facts, legal grounds, damages, and claims. Baseline Method is above TAARN, indicating that paragraph and sentence summaries provide useful structural cues. However, it stays below SDKG because retrieved paragraphs and sentences may be relevant in isolation but may not come from a complete case with a comparable severity direction. Compared with BLEU, the ROUGE-L curves are slightly more stable because document-level order is less sensitive to exact wording than n-gram overlap. The strongest pattern still appears in the \(\alpha=0.5\) panel, where configurations with \(\beta=0.2\), \(\lambda=0.5\), and \(\tau=0.5\) achieve the highest structural overlap.

圖 6.5 顯示 top-\(k\) 實驗下的 ROUGE-L 結果。曲線同樣由 top-1 提升至約 top-8，之後呈現穩定或微幅下降。由於 ROUGE-L 衡量最長共同子序列重疊，此趨勢表示 SDKG 參考案例有助於保留事故事實、法律依據、損害賠償與請求事項之主要順序。Baseline Method 高於 TAARN，表示段落與句子摘要可提供部分結構線索。然而，其仍低於 SDKG，原因是被檢索出的段落與句子即使局部相關，也不一定來自嚴重度方向可比較的完整案件。相較於 BLEU，ROUGE-L 曲線略為平穩，因為文書層級順序比 n-gram 重疊較不受精確措辭影響。最強趨勢仍出現在 \(\alpha=0.5\) 子圖，其中 \(\beta=0.2\)、\(\lambda=0.5\)、\(\tau=0.5\) 的配置取得最高結構重疊。

![Figure 6.6 Number-of-cases ROUGE-L results of SDKG configurations and Baseline Method.](</home/aru/AI_LAW/image copy 36.png>)

**Figure 6.6. Number-of-cases ROUGE-L results.** The x-axis is the number of cases used to construct the retrieval trees, and top-\(k\) is fixed at 8.

Figure 6.6 shows that ROUGE-L also improves as the number of cases increases. This confirms that larger SDKG graphs help the model retrieve references that better cover the full drafting sequence. Baseline Method also benefits from more cases, but its curve remains below the SDKG group. This pattern supports the transition from Chapter 4 to Chapter 5: paragraph and sentence summaries are useful for locating relevant local content, but SDKG further organizes each case as \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\) and retrieves complete comparable case nodes. The increase is clear from 1,000 to 3,000 cases, and the slope becomes more moderate afterward. This means that once enough structurally useful cases are available, additional cases mainly provide smaller refinements. At 6,057 cases, the ROUGE-L values match the \(k=8\) endpoint in the top-\(k\) experiment. The \(\alpha=0.5\) panel again contains the strongest overall curve.

圖 6.6 顯示 ROUGE-L 亦隨案件數增加而提升。此結果確認較大的 SDKG 圖有助於模型取得更能涵蓋完整撰寫順序的參考案例。Baseline Method 也受益於更多案件，但其曲線仍低於 SDKG 群。此趨勢支撐第四章至第五章的轉換：段落與句子摘要有助於定位局部相關內容，而 SDKG 進一步將每筆案件整理為 \(\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i)\)，並以完整案件節點作為可比較案例召回單位。由 1,000 筆至 3,000 筆的提升較明顯，之後斜率逐漸變緩，表示當系統已取得足夠具結構價值的案例後，新增案例主要帶來較小幅度修正。當案件數達 6,057 筆時，ROUGE-L 數值與 top-\(k\) 實驗中 \(k=8\) 的端點一致。\(\alpha=0.5\) 子圖再次包含整體最強曲線。

### 6.3.4 Discussion of Parameter Effects

The three metrics show a consistent parameter interpretation. Before comparing SDKG parameters, the position of Baseline Method should be noted. Across BERTScore, BLEU, and ROUGE-L, Baseline Method is higher than TAARN but lower than all SDKG configurations. This result indicates that the Chapter 4 design is a meaningful retrieval baseline and provides an experimental bridge to the proposed SDKG scheme. The paragraph and sentence summaries \(\bar{\theta}_{i,o}\) and \(\bar{\theta}_{i,o,v}\) help the model locate relevant drafting content, but the baseline does not yet compare complete cases through \(\mathbf{f}_i\), \(\mathbf{s}_i\), \(d_{i,j}^{p,\ell}\), and the severity direction of LH/HL retrieval. Therefore, the performance gap between Baseline Method and SDKG supports the proposed transition from sentence-level-aware retrieval to severity-aware case-level retrieval.

三項指標呈現一致的參數解讀。在比較 SDKG 參數前，需先觀察 Baseline Method 的位置。於 BERTScore、BLEU 與 ROUGE-L 中，Baseline Method 皆高於 TAARN，但低於所有 SDKG 配置。此結果表示第四章方法是一個有意義的檢索 baseline，並提供通往 SDKG 方法的實驗銜接。段落與句子摘要 \(\bar{\theta}_{i,o}\)、\(\bar{\theta}_{i,o,v}\) 可協助模型定位相關撰寫內容，但 baseline 尚未透過 \(\mathbf{f}_i\)、\(\mathbf{s}_i\)、\(d_{i,j}^{p,\ell}\) 與 LH/HL 檢索方向比較完整案件。因此，Baseline Method 與 SDKG 之間的差距，支持本文由 sentence-level-aware retrieval 進一步轉向 severity-aware case-level retrieval 的設計。

First, \(\alpha\) changes the main severity focus of retrieval. When \(\alpha=0.2\), accident-fact severity is less dominant, so increasing \(\beta\) helps the system use injury-related severity to identify closer references. When \(\alpha=0.3\) or \(\alpha=0.5\), accident-fact severity already contributes enough information, so the stronger configurations usually use a smaller \(\beta\) value to keep the retrieval balanced. This explains why the best \(\beta\) is not always the largest \(\beta\): injury severity is useful, but it should not dominate when accident facts are already strongly weighted.

首先，\(\alpha\) 會改變檢索時的主要嚴重度重心。當 \(\alpha=0.2\) 時，事故事實嚴重度較不主導，因此提高 \(\beta\) 有助於系統利用傷勢嚴重度找到較接近的參考案例。當 \(\alpha=0.3\) 或 \(\alpha=0.5\) 時，事故事實嚴重度已提供足夠資訊，因此較強配置通常採用較小的 \(\beta\)，以維持檢索平衡。這也說明為何最佳 \(\beta\) 不一定是最大值：傷勢嚴重度很重要，但當事故事實已被充分加權時，不宜讓傷勢權重過度主導。

Second, \(\lambda\) determines whether the edge distance relies more on legal-feature similarity or severity similarity. The results show that \(\lambda=0.5\) is usually the most stable setting, while \(\lambda=0.7\) is often competitive and \(\lambda=0.2\) is weaker. This indicates that the generation model benefits from references that are close in both legal structure and severity level. If \(\lambda\) is too low, the retrieved cases may match severity scores but lack enough legal-feature similarity; if \(\lambda\) is too high, the retrieved cases may share boolean features but become less sensitive to severity-side differences.

其次，\(\lambda\) 決定邊距離較依賴法律特徵相似性或嚴重度相似性。結果顯示，\(\lambda=0.5\) 通常最穩定，\(\lambda=0.7\) 多具有競爭力，而 \(\lambda=0.2\) 較弱。這表示生成模型較受益於同時具有法律結構相似與嚴重度相近的參考案例。若 \(\lambda\) 過低，檢索案例可能只在嚴重度分數上相近，但法律特徵不夠相似；若 \(\lambda\) 過高，檢索案例可能共享布林特徵，卻對嚴重度差異較不敏感。

Third, \(\tau\) mainly controls candidate availability. In the current figures, \(\tau=0.5\) generally produces the highest curves, followed by \(\tau=0.25\) and \(\tau=0.1\). This does not mean that a looser threshold is always better in every retrieval system. In this SDKG setting, candidate cases have already been filtered by shared boolean features and severity direction, so a higher threshold increases coverage without fully removing legal comparability. In contrast, \(\tau=0.1\) keeps only very close case pairs and may cause the prompt to miss useful references, especially when \(k\) becomes larger.

第三，\(\tau\) 主要控制候選案例可得性。在目前圖中，\(\tau=0.5\) 通常產生最高曲線，其次為 \(\tau=0.25\) 與 \(\tau=0.1\)。這並不表示在所有檢索系統中門檻越寬一定越好，而是因為本 SDKG 設定已先透過共同布林特徵與嚴重度方向過濾案例，所以較高門檻能增加覆蓋率，同時仍保留法律可比較性。相對地，\(\tau=0.1\) 只保留非常接近的案件對，可能導致提示在 \(k\) 增加時缺少足夠有用參考。

Overall, the best setting across the current automatic metrics is \(\alpha=0.5\), \(\beta=0.2\), \(\lambda=0.5\), and \(\tau=0.5\). This configuration can be interpreted as a fact-oriented but still severity-balanced retrieval setting: it emphasizes accident-fact severity, keeps injury severity as a supporting signal, balances legal-feature and severity distances, and uses a threshold that provides enough comparable references for top-\(k\) retrieval.

整體而言，目前自動化指標中的最佳設定為 \(\alpha=0.5\)、\(\beta=0.2\)、\(\lambda=0.5\)、\(\tau=0.5\)。此配置可解釋為以事故事實為主、但仍保留嚴重度平衡的檢索設定：其強調事故事實嚴重度，以傷勢嚴重度作為輔助訊號，並平衡法律特徵距離與嚴重度距離，同時使用足以提供 top-\(k\) 檢索候選的門檻。

## 6.4 Summary

This chapter evaluates SDKG from both automatic and legal-domain perspectives. The automatic evaluation compares 54 SDKG configurations across top-\(k\) values from 1 to 10 using BERTScore, BLEU, and ROUGE-L, and further examines the effect of case coverage by fixing top-\(k\) at 8 and varying the number of cases used to construct the retrieval trees. Baseline Method is included to connect the Chapter 4 sentence-level-aware retrieval design with the Chapter 5 SDKG design. The results show that Baseline Method outperforms TAARN, confirming the usefulness of paragraph and sentence summary retrieval, but it remains below SDKG because it does not retrieve complete severity-aware comparable case nodes. The top-\(k\) results show that adding comparable references improves generation quality until the prompt reaches a useful reference range. The number-of-cases results show that larger SDKG graphs provide better retrieval coverage, especially from 1,000 to 3,000 cases, and then gradually approach saturation. The parameter analysis further shows that \(\alpha=0.5\), \(\beta=0.2\), \(\lambda=0.5\), and \(\tau=0.5\) is the strongest overall setting in the current automatic evaluation. The human evaluation is defined as a legal-domain validation protocol and will be used to supplement the automatic metrics.

本章從自動化指標與法律專業評估兩個角度檢驗 SDKG。自動化評估使用 BERTScore、BLEU 與 ROUGE-L，比較 54 組 SDKG 配置於 top-\(k\) 1 至 10 下之表現，並進一步固定 top-\(k\) 為 8，透過改變建構檢索樹之案件數量觀察案件覆蓋效果。Baseline Method 則用以銜接第四章 sentence-level-aware retrieval 設計與第五章 SDKG 設計。結果顯示，Baseline Method 優於 TAARN，確認段落與句子摘要檢索具有實質幫助，但其仍低於 SDKG，原因是 Baseline Method 尚未以完整案件節點進行 severity-aware comparable-case retrieval。top-\(k\) 結果顯示，增加可比較參考案例可改善生成品質，直到提示達到有效參考範圍。案件數結果則顯示，較大的 SDKG 圖能提供較佳檢索覆蓋，尤其由 1,000 至 3,000 筆案件時提升較明顯，之後逐漸接近飽和。參數分析進一步顯示，\(\alpha=0.5\)、\(\beta=0.2\)、\(\lambda=0.5\)、\(\tau=0.5\) 為目前自動化評估中整體最佳設定。人工驗證則作為法律專業驗證流程，用以補充自動化指標之不足。
