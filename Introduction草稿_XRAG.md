# Introduction Draft

## English Version

Large language models (LLMs) have recently become an important foundation for automatic legal text generation. Among the existing approaches, Retrieval-Augmented Generation (RAG) is widely adopted because it supplements the language model with externally retrieved references and thus improves factual grounding and domain adaptation. For legal applications, however, especially in Taiwan traffic-accident civil complaint generation, merely retrieving semantically similar texts is often insufficient. A civil complaint is not a free-form summary but a formal pleading that must preserve accident facts, litigant relations, compensation claims, and legal reasoning in a structured manner. When conventional RAG directly feeds similar cases into the model, the generated output may inherit case-specific details, monetary amounts, or factual descriptions that do not belong to the current query, thereby reducing legal precision and document reliability.

Traffic-accident civil complaints constitute a representative and challenging legal generation task. In practice, the drafting process must transform lawyer-style factual inputs into a complaint containing multiple coordinated sections, including facts, legal grounds, damages, and conclusion. This task is difficult because the model must not only organize fragmented factual statements into formal legal language, but also maintain consistency across compensation items, party structure, and legal argumentation. Existing semantic retrieval methods can provide relevant textual support, yet they often do not explicitly preserve the relative seriousness of factual circumstances, injuries, and damages among cases. As a result, the retrieval stage may fail to provide references that are structurally appropriate for downstream generation.

To address these challenges, this thesis proposes XRAG, an eXtended Retrieval-Augmented Generation method with graph reasoning and dual-tree retrieval for traffic-accident civil complaint generation. The core idea of XRAG is to move beyond conventional text-level similarity and instead organize case retrieval through structured case relations. In the proposed framework, 6,057 Taiwan traffic-accident civil cases are first transformed into fixed boolean case profiles covering Litigants, Fact, Injury, and Compensation, and are further reconstructed into Fact, Injury, and Compensation severity scores. Based on these scores, XRAG builds experiment-specific case relations using weighted severity scores, distance measurement, and litigant-structure penalty, so that retrieval can better reflect the relative position of each case in the legal drafting space.

At query time, XRAG first identifies the nearest anchor case for the input query, and then performs bidirectional retrieval through dual-tree expansion. One tree expands toward comparatively lighter neighboring cases, while the other expands toward comparatively heavier neighboring cases. In this way, XRAG does not treat retrieved examples as an unordered collection, but as a locally organized reference structure centered around the anchor case. Moreover, the retrieved cases are not directly passed to the language model as full texts. Instead, they are compressed into structural cues, issue patterns, and reasoning hints, and are then integrated into a section-wise generation pipeline that separately produces the facts, legal grounds, damages, and conclusion sections. This design aims to improve query fidelity, reduce factual drift, and prevent the inappropriate transfer of case-specific details.

To evaluate the proposed approach, this thesis defines 18 XRAG settings based on six permutations of Fact, Injury, and Compensation weights and three threshold values, and validates them on 50 test queries. At the current stage, because human-revised gold references are still under preparation, a silver reference is used for pipeline verification and preliminary automatic evaluation. Through this design, the present study seeks not only to improve retrieval quality, but also to explicitly connect retrieval structure to downstream legal text generation.

The main contributions of this thesis are summarized as follows:

- This thesis proposes XRAG, a legal-domain retrieval-augmented generation method for Taiwan traffic-accident civil complaint generation, with explicit integration of graph reasoning and dual-tree retrieval.
- This thesis introduces a case-relation construction process that organizes 6,057 traffic-accident civil cases into experiment-specific retrieval structures based on severity scores, distance measurement, and litigant-structure penalty.
- This thesis designs an anchor-centered bidirectional retrieval mechanism and a section-wise generation pipeline, so that retrieved references can be aligned with the drafting needs of facts, legal grounds, damages, and conclusion.
- This thesis establishes 18 XRAG experimental settings and a 50-query evaluation pipeline, providing a practical basis for preliminary comparison with baseline retrieval-generation approaches.

The rest of this thesis is organized as follows. Chapter 2 reviews related work and research motivation. Chapter 3 introduces the proposed XRAG framework, including case representation, severity reconstruction, graph-style case relation construction, and dual-tree retrieval design. Chapter 4 presents the implementation details of the generation pipeline and the experimental setup. Chapter 5 reports the experimental results and discussion. Finally, Chapter 6 concludes this thesis and outlines future research directions.

## 中文版本

近年來，大型語言模型已成為法律文本自動生成的重要基礎技術。在既有方法中，檢索增強生成（Retrieval-Augmented Generation, RAG）因能透過外部檢索結果輔助模型生成，進而提升文本的事實依據與領域適應性，而被廣泛應用於各類知識密集型任務。然而，就法律應用而言，尤其是在臺灣交通事故民事起訴書生成任務中，僅依賴語意相似度擷取相關文本往往仍不足以支撐高精度書狀生成。民事起訴書並非一般自由文本，而是一種具有嚴格格式、明確事實結構與法律論述要求之正式法律文件。當傳統 RAG 直接將相似案例輸入模型時，生成結果容易夾帶不屬於當前 query 之個案細節、金額資訊或事故描述，進而降低書狀內容之準確性與可信度。

交通事故民事起訴書是一項具代表性且具挑戰性的法律文本生成任務。在實務上，起訴書撰寫必須將律師式輸入之事故經過、受傷情形與損害請求，轉換為包含事實、法條、損害賠償與結論等多個段落之正式法律文書。此任務之困難，不僅在於模型需將零散事實整理為合乎書狀格式之敘述，更在於不同賠償項目、當事人結構與法律論理之間必須保持一致性。既有語意檢索方法雖能提供一定程度之文本參考，但通常未能明確保留案件在事實嚴重度、傷勢程度與賠償結構上的相對位置，因此在下游生成階段，未必能提供真正適合的參考案例。

為解決上述問題，本論文提出 XRAG（eXtended Retrieval-Augmented Generation）方法，結合圖譜推理與雙向樹狀檢索，以應用於交通事故民事起訴書生成。XRAG 的核心想法，在於不再僅以文本相似度作為檢索依據，而是進一步透過案件間的結構關係來組織檢索流程。在本研究架構中，首先將 6,057 筆臺灣交通事故民事案件轉換為涵蓋 Litigants、Fact、Injury 與 Compensation 四個面向之固定 boolean case profiles，並進一步重建為 Fact、Injury 與 Compensation 三項 severity scores。其後，再依不同實驗參數，以加權 severity 分數、距離函數與 litigant structure penalty 建立 experiment-specific case relations，使檢索結果能更合理地反映案件在法律生成空間中的相對位置。

在 query 階段，XRAG 先為輸入案件找出距離最近之 anchor case，再透過雙向樹狀擴展進行雙向案例檢索。其中一棵樹朝向相對較輕之鄰近案例擴展，另一棵樹則朝向相對較重之鄰近案例擴展。藉由此一設計，XRAG 並非將檢索到的案例視為無序集合，而是視為以 anchor case 為中心、具有局部方向性之參考結構。此外，檢索所得案例不直接以全文輸入大型語言模型，而是先壓縮為結構線索、爭點模式與論述提示，再接入分段式生成流程，依序生成事實、法條、損害賠償與結論段落。此設計之目的，在於提升生成結果對 query 的忠實度，降低 factual drift，並避免模型不當借用相似案例之個案細節。

為評估所提出方法，本論文共建立 18 組 XRAG 實驗設定，係由 Fact、Injury、Compensation 三項權重之六種排列與三種距離閾值組成，並以 50 筆測試 query 進行驗證。由於目前人工校正之正式 gold references 尚在建置中，現階段暫以 silver reference 用於流程驗證與初步自動評估。透過此一設計，本研究不僅希望提升檢索品質，更希望明確建立從檢索結構到法律文本生成之連結。

本論文之主要貢獻如下：

- 提出 XRAG 方法，將圖譜推理與雙向樹狀檢索明確導入臺灣交通事故民事起訴書生成任務。
- 建立一套以 severity scores、距離函數與 litigant structure penalty 為基礎之案件關係建構流程，用以組織 6,057 筆交通事故民事案件之 experiment-specific 檢索結構。
- 設計以 anchor case 為中心之雙向檢索機制與分段式生成流程，使檢索參考能分別對應事實、法條、損害賠償與結論之撰寫需求。
- 建立 18 組 XRAG 實驗設定與 50-query 評估流程，作為後續與 baseline 檢索生成方法比較之實作基礎。

本論文其餘章節安排如下。第二章回顧相關研究與研究動機。第三章介紹所提出之 XRAG 架構，包括案件表示、severity 重建、圖譜式案件關係建構與雙向樹狀檢索設計。第四章說明生成流程之實作細節與實驗設定。第五章呈現實驗結果與討論。最後，第六章總結本論文並提出未來研究方向。
