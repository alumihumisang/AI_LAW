# Chapter 4 Sentence-Level-Aware Dual Retrieval Method

Chapter 3 formulates the traffic-accident civil complaint generation task as a retrieval-conditioned generation problem. The goal is to reduce the gap between the generated complaint \(\hat{\mathbf{y}}\) and the human-written reference complaint \(\mathbf{y}^{*}\). This chapter presents a sentence-level-aware dual retrieval method for constructing drafting references from paragraph-level and sentence-level text. The term sentence-level-aware emphasizes that detailed factual, legal, and compensation information is grounded in sentence elements, while paragraph units preserve the local structure of a civil complaint. It does not mean that isolated sentences are sufficient as final legal references. This distinction becomes the basis for the case-level SDKG method in Chapter 5.

第三章將交通事故民事起訴書生成任務表述為檢索條件下之生成問題，其目標在於降低生成起訴書 \(\hat{\mathbf{y}}\) 與人工參考起訴書 \(\mathbf{y}^{*}\) 之間的差距。本章提出 sentence-level-aware dual retrieval method，用以從段落層與句子層文字資訊中建構撰寫參考。所謂 sentence-level-aware，是指細部事故事實、法律依據與損害賠償資訊以句子元素為基礎進行定位，而段落單位則保留民事起訴書的局部結構；此名稱並不表示孤立句子即可作為最終法律參考。此區分也成為第五章案件層級 SDKG 方法的設計基礎。

## 4.1 Phase 1: Data, Paragraph, and Sentence Construction

The first phase constructs the paragraph and sentence units used by the sentence-level-aware method. It first describes the source data and the overall KG-RAG flow, and then defines how each case material \(\mathbf{m}_i\) is decomposed into paragraph units \(\theta_{i,o}\) and sentence elements \(\theta_{i,o,v}\). This phase also explains how paragraph and sentence summaries are stored for later retrieval in Section 4.2.

第一階段負責建立 sentence-level-aware method 所需之段落與句子文字。本文先說明資料來源與整體 KG-RAG 流程，再定義每筆案件材料 \(\mathbf{m}_i\) 如何拆解為段落單位 \(\theta_{i,o}\) 與句子元素 \(\theta_{i,o,v}\)。此階段產生之段落與句子單位，將作為第 4.2 節檢索階段的基礎。

### 4.1.1 Data Construction and Overall Flow

The sentence-level-aware method originated from a research project on traffic-accident compensation complaint generation. The initial project dataset size is denoted as \(N_0=2{,}995\). The original materials were collected from publicly available Taiwanese first-instance traffic-accident civil judgments. After keyword filtering, \(N_{\mathrm{raw}}=9{,}794\) judgments were initially identified. Cases with unrelated dispute types or procedural issues were removed, leaving \(N_{\mathrm{flt}}=6{,}542\) filtered judgments for complaint-style data construction. After automated reconstruction and legal-domain correction, the final usable database size became \(N=6{,}057\).

本章方法源自交通事故賠償起訴書生成計畫。初始計畫資料量記為 \(N_0=2{,}995\)。原始資料來自臺灣公開之一審交通事故民事判決，經關鍵字篩選後，最初取得 \(N_{\mathrm{raw}}=9{,}794\) 篇判決；再排除爭點不相關或偏向程序事項之案件後，留下 \(N_{\mathrm{flt}}=6{,}542\) 篇過濾後判決作為起訴書樣式資料建構來源。經自動重建與法律專業修正後，最終可用資料庫規模為 \(N=6{,}057\)。

Using the notation in Chapter 3, each reconstructed complaint-style case is still associated with a case unit \(\mathbf{c}_i\), and its raw case material is denoted by \(\mathbf{m}_i\). In this chapter, \(\mathbf{m}_i\) is decomposed into paragraph units and sentence elements so that the system can retrieve both local sentence information and broader paragraph context. The method therefore approximates the reference selection problem in \(\mathbf{P}_2\) through paragraph-and-sentence-level retrieval, while still keeping each paragraph or sentence connected to its source case \(\mathbf{c}_i\).

若以第三章之符號表示，每一筆重建後之起訴書樣式案件仍可對應至案件單位 \(\mathbf{c}_i\)，其原始案件材料記為 \(\mathbf{m}_i\)。在本章中，\(\mathbf{m}_i\) 會被拆解為段落單位與句子元素，使系統能同時檢索局部句子資訊與較完整的段落脈絡。因此，本方法可視為一種以段落與句子層級檢索近似第三章 \(\mathbf{P}_2\) 參考集合選擇問題的做法，但每個段落或句子仍保留其所屬來源案件 \(\mathbf{c}_i\)。

![Figure 4.1 Sentence-level-aware KG-RAG retrieval-generation flow.](/home/aru/AI_LAW/ch4_slide-08.png)

**Figure 4.1. Sentence-level-aware KG-RAG retrieval-generation flow.** The method uses graph storage, vector retrieval, summary modules, top-\(k\) textual retrieval, structured prompt construction, and Gemma3:27b generation.

Figure 4.1 summarizes the overall flow of this chapter. Following the notation in Chapter 3, the lawyer query is denoted by \(\mathbf{q}_m\), the retrieved paragraphs and retrieved sentences are later represented by \(R_o(\mathbf{q}_m)\) and \(R_v(\mathbf{q}_m)\), and the retrieved text is assembled into \(\mathbf{z}_m\) before being passed to \(M(\cdot)\) for generating \(\hat{\mathbf{y}}_m\).

圖 4.1 概括本章方法流程。依第三章符號，律師查詢記為 \(\mathbf{q}_m\)，雙層檢索結果於後文分別表示為 \(R_o(\mathbf{q}_m)\) 與 \(R_v(\mathbf{q}_m)\)，檢索所得文字再組成 \(\mathbf{z}_m\)，並輸入 \(M(\cdot)\) 生成 \(\hat{\mathbf{y}}_m\)。

### 4.1.2 Paragraph and Sentence Construction

The key idea of the sentence-level-aware method is to avoid treating a complaint as one unstructured text block. For each case material \(\mathbf{m}_i\), the system first decomposes the complaint into paragraph-level units:

本方法的核心想法，是避免將起訴書視為未結構化的整塊文字。對每一筆案件材料 \(\mathbf{m}_i\)，系統先將起訴書拆解為段落層單位：

![Figure 4.2 Preprocessing flow for paragraph and sentence construction.](/home/aru/AI_LAW/ch4_slide-08_preprocessing.png)

**Figure 4.2. Preprocessing flow for paragraph and sentence construction.** The legal dataset is transformed into paragraph and sentence chunks and connected to the knowledge-graph storage before retrieval.

Figure 4.2 focuses on the preprocessing part of Figure 4.1. The legal dataset provides case materials \(\mathbf{m}_i\), which are decomposed into paragraph units \(\theta_{i,o}\) and sentence elements \(\theta_{i,o,v}\). These units are then connected to the graph-based representation so that later retrieval can trace retrieved paragraphs and sentences back to their source case.

圖 4.2 對應圖 4.1 中的前處理區塊。法律資料集提供案件材料 \(\mathbf{m}_i\)，系統再將其拆解為段落單位 \(\theta_{i,o}\) 與句子元素 \(\theta_{i,o,v}\)。這些單位會進一步連結至圖形化表示，使後續檢索所得段落與句子能回溯至其來源案件。

\[
\mathbf{m}_i
\rightarrow
\theta_{i,1},
\theta_{i,2},
\ldots,
\theta_{i,O_i},
\tag{4.1}
\]

where \(\theta_{i,o}\) denotes the \(o\)-th paragraph-level unit in case \(i\), and \(O_i\) denotes the number of paragraph-level units extracted from \(\mathbf{m}_i\). Each paragraph-level unit may correspond to facts, legal grounds, compensation, or conclusion.

其中，\(\theta_{i,o}\) 表示第 \(i\) 筆案件中第 \(o\) 個段落層單位，\(O_i\) 表示由 \(\mathbf{m}_i\) 抽出的段落層單位數量。每一個段落層單位可對應事故事實、法律依據、損害賠償或結論。

Each paragraph unit \(\theta_{i,o}\) was further decomposed into sentence-level elements:

每一個段落單位 \(\theta_{i,o}\) 再進一步拆解為句子層元素：

\[
\theta_{i,o}
\rightarrow
\theta_{i,o,1},
\theta_{i,o,2},
\ldots,
\theta_{i,o,V_{i,o}},
\tag{4.2}
\]

where \(\theta_{i,o,v}\) denotes the \(v\)-th sentence element inside the \(o\)-th paragraph of case \(i\), and \(V_{i,o}\) denotes the number of sentence elements in \(\theta_{i,o}\). This notation uses the same base symbol \(\theta\) for both levels: \(\theta_{i,o}\) denotes a paragraph unit, while \(\theta_{i,o,v}\) denotes a sentence element inside that paragraph. This decomposition allowed the system to preserve both the broader structure of a civil complaint and the fine-grained factual units inside each paragraph.

其中，\(\theta_{i,o,v}\) 表示第 \(i\) 筆案件第 \(o\) 個段落中的第 \(v\) 個句子元素，\(V_{i,o}\) 表示 \(\theta_{i,o}\) 中的句子元素數量。此處以同一個基本符號 \(\theta\) 表示兩個層級：\(\theta_{i,o}\) 表示段落單位，而 \(\theta_{i,o,v}\) 表示該段落中的句子元素。此拆解使系統能同時保留民事起訴書之段落結構與段落內部的細部事實單位。

![Figure 4.3 Graph database construction for the sentence-level-aware method.](/home/aru/AI_LAW/ch4_slide-09.png)

**Figure 4.3. Graph database construction for the sentence-level-aware method.** Each complaint-style case is decomposed into graph nodes and relations corresponding to facts, laws, compensation items, and conclusions.

![Figure 4.4 Vector database construction for the sentence-level-aware method.](/home/aru/AI_LAW/ch4_slide-10.png)

**Figure 4.4. Vector database construction for the sentence-level-aware method.** Paragraph and sentence summaries are embedded and loaded into the vector database during preprocessing.

Figure 4.4 shows the vector-database construction performed in this chapter method. After paragraph units \(\theta_{i,o}\) and sentence elements \(\theta_{i,o,v}\) are summarized into \(\bar{\theta}_{i,o}\) and \(\bar{\theta}_{i,o,v}\), the summaries are embedded and loaded into the vector database for later paragraph-and-sentence-level retrieval. This database is used in the sentence-level-aware method; Chapter 5 changes the final retrieval unit to case nodes \(n_i\).

圖 4.4 說明本章方法在前處理階段進行的向量資料庫建構。段落單位 \(\theta_{i,o}\) 與句子元素 \(\theta_{i,o,v}\) 被摘要為 \(\bar{\theta}_{i,o}\) 與 \(\bar{\theta}_{i,o,v}\) 後，系統將其向量化並載入向量資料庫，以供後續段落與句子層級檢索使用。此向量資料庫屬於本章方法；第五章則將最終檢索單位改為案件節點 \(n_i\)。

![Figure 4.5 Paragraph-level decomposition in the sentence-level-aware method.](/home/aru/AI_LAW/ch4_slide-11.png)

**Figure 4.5. Paragraph-level decomposition in the sentence-level-aware method.** Complaint text is separated into fact, law, compensation, and conclusion paragraphs.

![Figure 4.6 Sentence-level chunking for fact paragraphs.](/home/aru/AI_LAW/ch4_slide-12.png)

**Figure 4.6. Sentence-level chunking for fact paragraphs.** A fact paragraph is divided into sentence elements so that local accident information can be retrieved at a finer level.

Figures 4.2--4.6 correspond to (4.1) and (4.2). Figure 4.2 shows the preprocessing flow from \(\mathbf{m}_i\) to paragraph and sentence units. Figure 4.3 illustrates the graph-based organization of a case material \(\mathbf{m}_i\). Figure 4.4 shows how paragraph and sentence summaries are loaded into the vector database. Figure 4.5 shows the paragraph-level units \(\theta_{i,o}\), and Figure 4.6 shows how a fact paragraph \(\theta_{i,o}\) is further divided into sentence elements \(\theta_{i,o,v}\). Therefore, sentence-level awareness is built on top of paragraph-level structure, rather than replacing it.

圖 4.2 至圖 4.6 對應式 (4.1) 與式 (4.2)。圖 4.2 呈現由 \(\mathbf{m}_i\) 到段落與句子單位的前處理流程；圖 4.3 說明案件材料 \(\mathbf{m}_i\) 的圖形化組織；圖 4.4 呈現段落與句子摘要如何載入向量資料庫；圖 4.5 呈現段落層單位 \(\theta_{i,o}\)；圖 4.6 則表示事實段落 \(\theta_{i,o}\) 如何再被 chunking 為句子元素 \(\theta_{i,o,v}\)。因此，本章的 sentence-level awareness 是建立在段落層結構之上，而不是取代段落層。

## 4.2 Phase 2: Dual-Level Summary-Based Semantic Retrieval

The second phase retrieves paragraphs and sentences from the summaries built in Phase 1. It first defines the summary and retrieval notation, and then explains how fact, legal, and compensation information are represented as structured summaries. The purpose of this phase is to produce \(R_o(\mathbf{q}_m)\) and \(R_v(\mathbf{q}_m)\) for prompt construction.

第二階段依據第一階段建立的段落與句子摘要進行語意檢索。本文先定義摘要與檢索符號，再說明事實、法律依據與賠償資訊如何被整理為結構化摘要。此階段的目的，是產生可供提示建構使用的 \(R_o(\mathbf{q}_m)\) 與 \(R_v(\mathbf{q}_m)\)。

### 4.2.1 Summary-Based Retrieval Formulation

The sentence-level-aware method does not directly insert all long paragraph and sentence texts into the prompt. Instead, the paragraph unit \(\theta_{i,o}\) and sentence element \(\theta_{i,o,v}\) are summarized into compact textual units. In this chapter, the keyword-guided LLM summary rule is denoted by \(\psi_x(\cdot)\), where the subscript \(x\) denotes the keyword condition used to select legally relevant text before summary generation:

本方法並未直接將所有長段落與句子文字放入提示，而是先將段落單位 \(\theta_{i,o}\) 與句子元素 \(\theta_{i,o,v}\) 摘要為較精簡的文字單位。本章將 keyword-guided LLM summary rule 記為 \(\psi_x(\cdot)\)，其中下標 \(x\) 表示摘要生成前用於篩選法律相關文字的關鍵字條件，並非權重參數：

![Figure 4.7 Dual-level semantic retrieval flow.](/home/aru/AI_LAW/ch4_slide-08_retrieval.png)

**Figure 4.7. Dual-level semantic retrieval flow.** Paragraph and sentence summaries are used to retrieve similar paragraphs, similar sentences, and source case identifiers.

Figure 4.7 focuses on the retrieval part of Figure 4.1. The query \(\mathbf{q}_m\) is matched against the paragraph summaries \(\bar{\theta}_{i,o}\) and sentence summaries \(\bar{\theta}_{i,o,v}\) prepared in Phase 1. Sentence-level hits can be traced back to their source case index \(i\), which helps the system retrieve related paragraphs. However, these case identifiers serve as backtracking links in this method; they are not yet the SDKG case nodes \(n_i\) introduced in Chapter 5.

圖 4.7 對應圖 4.1 中的檢索區塊。段落摘要 \(\bar{\theta}_{i,o}\) 與句子摘要 \(\bar{\theta}_{i,o,v}\) 已於前處理階段向量化，查詢 \(\mathbf{q}_m\) 再與這些摘要進行比對。句子層命中結果可回溯至其來源案件索引 \(i\)，並協助系統取得相關段落。然而，這些案件識別資訊在本章方法中只是回溯連結，尚不是第五章 SDKG 所定義的案件節點 \(n_i\)。

\[
\bar{\theta}_{i,o}
=
\psi_x(\theta_{i,o}),
\quad
\bar{\theta}_{i,o,v}
=
\psi_x(\theta_{i,o,v}).
\tag{4.3}
\]

Here, \(\bar{\theta}_{i,o}\) denotes the paragraph-level summary of \(\theta_{i,o}\), and \(\bar{\theta}_{i,o,v}\) denotes the sentence-level summary of \(\theta_{i,o,v}\). The rule \(\psi_x(\cdot)\) first retains factual, legal, and compensation-related text according to \(x\), and then uses an LLM to rewrite the selected text into a compact summary. These summaries are prepared during preprocessing and used for semantic retrieval. Given a lawyer query \(\mathbf{q}_m\), the dual-level retriever produces paragraph-level and sentence-level retrieval results according to semantic similarity:

其中，\(\bar{\theta}_{i,o}\) 表示 \(\theta_{i,o}\) 的段落層摘要，\(\bar{\theta}_{i,o,v}\) 表示 \(\theta_{i,o,v}\) 的句子層摘要。\(\psi_x(\cdot)\) 會先依 \(x\) 保留事實、法律依據與賠償相關文字，再由 LLM 將被選出的文字整理為較精簡的摘要。這些摘要已於前處理階段向量化，並於本節用於語意檢索。給定律師查詢 \(\mathbf{q}_m\)，雙層檢索器依語意相似度產生段落層與句子層檢索結果：

\[
R_o(\mathbf{q}_m)
=
\operatorname{Top}_{k_o}
\left\{
\bar{\theta}_{i,o}
\mid
\mathrm{sim}(\mathbf{q}_m,\bar{\theta}_{i,o})
\right\},
\tag{4.4}
\]

\[
R_v(\mathbf{q}_m)
=
\operatorname{Top}_{k_v}
\left\{
\bar{\theta}_{i,o,v}
\mid
\mathrm{sim}(\mathbf{q}_m,\bar{\theta}_{i,o,v})
\right\}.
\tag{4.5}
\]

In (4.4), \(R_o(\mathbf{q}_m)\) denotes the paragraph-level retrieval result, and \(k_o\) denotes the paragraph-level retrieval budget. In (4.5), \(R_v(\mathbf{q}_m)\) denotes the sentence-level retrieval result, and \(k_v\) denotes the sentence-level retrieval budget. The subscripts follow the indexing rule in (4.1) and (4.2): \(o\) indexes paragraph units, while \(v\) indexes sentence elements. The function \(\mathrm{sim}(\cdot,\cdot)\) denotes semantic similarity. The two retrieval results are used as textual support for prompt construction, with \(|R_o(\mathbf{q}_m)|\leq k_o\), \(|R_v(\mathbf{q}_m)|\leq k_v\), and \(k_o+k_v\leq k\).

式 (4.4) 中，\(R_o(\mathbf{q}_m)\) 表示段落層檢索結果，\(k_o\) 表示段落層檢索額度。式 (4.5) 中，\(R_v(\mathbf{q}_m)\) 表示句子層檢索結果，\(k_v\) 表示句子層檢索額度。這組下標延續式 (4.1) 與式 (4.2) 的索引規則：\(o\) 表示段落索引，\(v\) 表示句子索引。\(\mathrm{sim}(\cdot,\cdot)\) 表示語意相似度。兩個檢索結果隨後作為提示建構之文字支援，並滿足 \(|R_o(\mathbf{q}_m)|\leq k_o\)、\(|R_v(\mathbf{q}_m)|\leq k_v\) 與 \(k_o+k_v\leq k\)。

![Figure 4.8 Sentence-level fact extraction in the sentence-level-aware method.](/home/aru/AI_LAW/ch4_slide-13.png)

**Figure 4.8. Sentence-level fact extraction in the sentence-level-aware method.** Fact sentences are normalized into structured summaries such as time, location, vehicle, action, and consequence information.

### 4.2.2 Fact, Legal, and Compensation Summaries

Figure 4.8 corresponds to the sentence-summary transformation \(\theta_{i,o,v}\rightarrow\bar{\theta}_{i,o,v}\) for fact-related information. In the fact paragraph, each \(\theta_{i,o,v}\) may contain accident time, location, vehicle movement, party action, or injury consequence, and \(\bar{\theta}_{i,o,v}\) keeps these elements in a compact form for semantic retrieval.

圖 4.8 對應事實資訊中的句子摘要轉換 \(\theta_{i,o,v}\rightarrow\bar{\theta}_{i,o,v}\)。在事實段落中，每個 \(\theta_{i,o,v}\) 可能包含事故時間、地點、車輛動態、當事人行為或受傷結果，而 \(\bar{\theta}_{i,o,v}\) 則將這些資訊壓縮為可供語意檢索使用的摘要形式。

The same idea was applied to legal provisions and compensation paragraphs. Legal-ground chunks were summarized into article-content-source triples, while compensation chunks were summarized into item-amount-summary-source records. This design reduced legal hallucination because the generator could receive explicit legal and compensation references rather than relying only on the internal knowledge of the language model.

同樣的設計亦應用於法條段落與賠償段落。法律依據 chunks 會被摘要為條號、條文內容與來源句子之結構化資訊；賠償 chunks 則會被摘要為項目、金額、摘要與來源句子。此設計可降低法條與賠償內容之幻覺，因為生成模型能接收明確的法律與賠償參考，而不必只依賴語言模型內部知識。

![Figure 4.9 Sentence-level chunking for legal provisions.](/home/aru/AI_LAW/ch4_slide-14.png)

**Figure 4.9. Sentence-level chunking for legal provisions.** A legal-ground paragraph is divided into sentence elements so that legal responsibility statements and cited articles can be identified at the sentence level.

Figure 4.9 illustrates the legal-ground case of (4.2). A legal paragraph \(\theta_{i,o}\) is divided into sentence elements \(\theta_{i,o,v}\), and closely related sentence elements may form a legal pair, such as a responsibility statement and its corresponding statutory article. These sentence elements are then summarized into legal-ground summaries \(\bar{\theta}_{i,o,v}\).

圖 4.9 說明式 (4.2) 在法律依據段落中的情形。法律段落 \(\theta_{i,o}\) 會被切分為句子元素 \(\theta_{i,o,v}\)，而彼此關聯密切的句子元素可能形成法律配對，例如責任敘述與其對應法條。這些句子元素後續再被摘要為法律依據摘要 \(\bar{\theta}_{i,o,v}\)。

![Figure 4.10 Sentence-level legal provision summarization.](/home/aru/AI_LAW/ch4_slide-15.png)

**Figure 4.10. Sentence-level legal provision summarization.** Legal provision chunks are converted into structured article-content-source triples.

Figure 4.10 shows the summary form of legal sentence elements. Each summarized legal element \(\bar{\theta}_{i,o,v}\) records the article number, article content, and source sentence so that the generated complaint can cite legal provisions with explicit textual support.

圖 4.10 呈現法律句子元素的摘要形式。每個法律摘要元素 \(\bar{\theta}_{i,o,v}\) 會記錄條號、條文內容與來源句子，使生成起訴書能依據明確文字支援引用法條。

![Figure 4.11 Sentence-level chunking for compensation paragraphs.](/home/aru/AI_LAW/ch4_slide-16.png)

**Figure 4.11. Sentence-level chunking for compensation paragraphs.** A compensation paragraph is divided into sentence elements corresponding to compensation items, amounts, and supporting facts.

Figure 4.11 illustrates the compensation case of (4.2). A compensation paragraph \(\theta_{i,o}\) may contain multiple compensation items, and each sentence element \(\theta_{i,o,v}\) can carry an item name, claimed amount, and supporting facts. This design allows the retriever to locate compensation information at a finer level before prompt assembly.

圖 4.11 說明式 (4.2) 在賠償段落中的情形。賠償段落 \(\theta_{i,o}\) 可能包含多個賠償項目，而每個句子元素 \(\theta_{i,o,v}\) 可承載項目名稱、請求金額與支撐事實。此設計使檢索器能在提示組裝前，以更細緻層級定位賠償資訊。

![Figure 4.12 Sentence-level compensation summarization.](/home/aru/AI_LAW/ch4_slide-17.png)

**Figure 4.12. Sentence-level compensation summarization.** Compensation chunks are converted into structured information containing item, amount, summary, and source identifier.

Figure 4.12 shows the summarized compensation form. The compensation summary \(\bar{\theta}_{i,o,v}\) keeps the item, amount, summary, and source identifier, which helps \(M(\cdot)\) maintain compensation consistency when producing \(\hat{\mathbf{y}}_m\).

圖 4.12 呈現賠償資訊的摘要形式。賠償摘要 \(\bar{\theta}_{i,o,v}\) 保留項目、金額、摘要與來源識別資訊，有助於 \(M(\cdot)\) 在生成 \(\hat{\mathbf{y}}_m\) 時維持賠償內容一致性。

## 4.3 Phase 3: Prompt Assembly, Generation, and Transition

The third phase assembles the retrieved paragraphs and sentences into the generation prompt and produces the complaint text. It also explains why paragraph-and-sentence-level retrieval remains limited when retrieved paragraphs and sentences are used as final references. This limitation motivates the transition to the case-level SDKG method in Chapter 5.

第三階段將檢索所得段落與句子組成生成提示，並產生起訴書文本。本節同時說明當段落與句子被直接作為最終參考時，段落與句子層級檢索仍會產生的限制。此限制進一步銜接第五章案件層級 SDKG 方法。

### 4.3.1 Structured Prompt Assembly and Complaint Generation

The structured prompt of this method is denoted as \(\mathbf{z}_m\). It is assembled from the lawyer query, paragraph-level retrieval result, sentence-level retrieval result, and drafting instructions:

本方法之結構化提示記為 \(\mathbf{z}_m\)。該提示由律師查詢、段落層檢索結果、句子層檢索結果與撰寫指令組成：

![Figure 4.13 Structured prompt assembly and complaint generation flow.](/home/aru/AI_LAW/ch4_slide-08_generation.png)

**Figure 4.13. Structured prompt assembly and complaint generation flow.** Retrieved paragraphs, retrieved sentences, and lawyer input are assembled into a structured prompt, and Gemma3:27b generates the complaint with output checking.

Figure 4.13 focuses on the generation part of Figure 4.1. The retrieved paragraphs and retrieved sentences, together with the lawyer query \(\mathbf{q}_m\) and drafting instructions, form the structured prompt \(\mathbf{z}_m\). The generation model \(M(\cdot)\) then produces \(\hat{\mathbf{y}}_m\), and the output-checking step is used to reduce format, legal-citation, and compensation-calculation errors.

圖 4.13 對應圖 4.1 中的生成區塊。檢索所得段落與句子會與律師查詢 \(\mathbf{q}_m\) 及撰寫指令共同組成結構化提示 \(\mathbf{z}_m\)。生成模型 \(M(\cdot)\) 進一步產生 \(\hat{\mathbf{y}}_m\)，並透過輸出檢查降低格式、法條引用與賠償計算錯誤。

\[
\mathbf{z}_m
=
\Phi
\left(
\mathbf{q}_m,
R_o(\mathbf{q}_m),
R_v(\mathbf{q}_m)
\right),
\tag{4.6}
\]

and the generated complaint of this method is:

本方法生成之起訴書表示為：

\[
\hat{\mathbf{y}}_m
=
M(\mathbf{z}_m).
\tag{4.7}
\]

This design improves the structure of the prompt by combining broader paragraph context and fine-grained sentence information. The retrieved sentences \(R_v(\mathbf{q}_m)\) are useful for locating local facts, legal provisions, and compensation items, while the retrieved paragraphs \(R_o(\mathbf{q}_m)\) preserve the surrounding complaint structure. Each retrieved paragraph or sentence also carries its source case index \(i\), so the system can trace a matched summary back to its original case material \(\mathbf{m}_i\).

此設計藉由結合較廣的段落脈絡與細緻的句子資訊，改善了提示結構。句子層檢索結果 \(R_v(\mathbf{q}_m)\) 有助於定位局部事實、法律依據與賠償項目，段落層檢索結果 \(R_o(\mathbf{q}_m)\) 則保留周邊書狀結構。每個被檢索到的段落或句子亦帶有其來源案件索引 \(i\)，因此系統可以由摘要回溯至原始案件材料 \(\mathbf{m}_i\)。

### 4.3.2 Limitation and Transition to Case-Level SDKG Retrieval

Although the sentence-level-aware method provides useful local information, retrieved paragraphs and retrieved sentences are unstable as final legal references. If \(k_o\) is too large, the prompt may contain broad but redundant paragraph information; if \(k_v\) is too large, it may contain locally similar sentences without complete case context. More importantly, high semantic similarity between \(\mathbf{q}_m\) and \(\bar{\theta}_{i,o,v}\) does not necessarily imply that the complete case \(\mathbf{c}_i\) is legally comparable to the query.

雖然本方法能提供有用的局部資訊，但段落與句子作為最終法律參考時仍不穩定。若 \(k_o\) 過大，提示可能包含過多廣泛但重複的段落資訊；若 \(k_v\) 過大，提示可能充滿局部相似的句子，卻缺乏完整案件脈絡。更重要的是，\(\mathbf{q}_m\) 與 \(\bar{\theta}_{i,o,v}\) 具有高度語意相似，並不必然表示完整案件 \(\mathbf{c}_i\) 在法律上適合作為可比較案例。

This limitation motivates the SDKG scheme in Chapter 5. The difference is not that SDKG discards paragraphs, sentences, or summaries, but that it changes their role. This chapter is built from output-side complaint paragraphs, such as fact, legal-ground, compensation, and conclusion paragraphs, whereas Chapter 5 constructs case-level features from input-side lawyer descriptions. Therefore, the paragraph roles in this chapter are not reused as SDKG input fields; their summaries instead support the legal feature profile \(\mathbf{f}_i\) and severity vector \(\mathbf{s}_i\). In compact form, this transition can be described as \(\bar{\theta}_{i,o,v}\rightarrow(\mathbf{f}_i,\mathbf{s}_i)\rightarrow\mathbf{c}_i\mapsto n_i\).

此限制促成第五章的 SDKG scheme。SDKG 並非捨棄段落、句子或摘要，而是改變其角色。本章由 output-side 起訴書段落建立，例如事實、法律依據、賠償與結論段落；第五章則由 input-side 律師輸入內容建立案件層級特徵。因此，本章的段落角色不直接重複作為 SDKG 的輸入欄位符號，而是透過摘要支援法律特徵 profile \(\mathbf{f}_i\) 與嚴重度向量 \(\mathbf{s}_i\) 的建構。簡言之，此轉換可表示為 \(\bar{\theta}_{i,o,v}\rightarrow(\mathbf{f}_i,\mathbf{s}_i)\rightarrow\mathbf{c}_i\mapsto n_i\)。

After this transformation, each complete case is represented as:

完成此轉換後，每一筆完整案件表示為：

\[
\mathbf{c}_i=(\mathbf{m}_i,\mathbf{f}_i,\mathbf{s}_i),
\tag{4.8}
\]

and is converted into a case node:

並進一步轉換為案件節點：

\[
\mathbf{c}_i\mapsto n_i.
\tag{4.9}
\]

Thus, SDKG performs retrieval at the case-node level rather than the paragraph or sentence level. The transition is therefore from paragraph-and-sentence-level retrieval to summary-supported case-level retrieval.

因此，SDKG 的檢索單位為案件節點，而非段落或句子。故從本章方法到 SDKG 的轉換，是從段落與句子層級檢索，提升為由摘要支援的案件層級雙方向檢索。
