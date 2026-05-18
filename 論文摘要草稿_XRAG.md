# XRAG: eXtended Retrieval-Augmented Generation with Graph Reasoning and Dual-Tree Retrieval for Traffic-Accident Civil Complaint Generation

# Abstract

Retrieval-Augmented Generation (RAG) is a technique that assists large language models in generating text by retrieving relevant external documents. However, when applied to generating civil complaint documents for Taiwanese traffic accident cases, traditional RAG can only retrieve cases based on semantic similarity. It often fails to control how accident facts, compensation items, and legal reasoning are incorporated into the final document, making it difficult to produce complaints that remain focused on the query while following proper legal format and maintaining factual accuracy.

To address this issue, this paper proposes XRAG (eXtended Retrieval-Augmented Generation), which combines knowledge graph reasoning with bidirectional tree-based retrieval for civil complaint generation in traffic accident cases. In the proposed framework, 6,057 Taiwanese traffic accident civil cases are first converted into fixed boolean case profiles covering four dimensions: Litigants, Fact, Injury, and Compensation. These profiles are then used to derive three severity scores for the Fact, Injury, and Compensation dimensions.

Depending on the experimental setting, XRAG weights the severity scores using external legal domain knowledge and constructs case relations through distance functions. At query time, the system first identifies the nearest anchor case, then applies bidirectional tree expansion to retrieve neighboring cases with relatively lower or higher severity. Rather than feeding the retrieved cases directly into the model as full text, the framework extracts structural cues and argumentative prompts, which are then passed into a segmented generation pipeline covering facts, legal provisions, damages, and conclusions.

This study builds 18 XRAG experimental configurations based on six weight arrangements and three distance thresholds. Preliminary validation is conducted using 50 test queries that simulate attorney inputs, compared against manually written complaints drafted by law school professionals. The results suggest that XRAG is a feasible approach for controlled generation of civil complaint documents in traffic accident litigation.

Keywords: traffic accident, civil complaint generation, legal generative AI, retrieval-augmented generation, XRAG, structured legal retrieval

# 摘要

檢索增強生成（Retrieval-Augmented Generation, RAG）是一種透過外部檢索結果輔助大型語言模型生成文本之技術。然而，對於臺灣交通事故民事賠償部分起訴書生成而言，傳統 RAG 往往僅能依語意相似度擷取相似案例，卻難以有效控制生成階段時事故事實、賠償項目與法律論述如何進入最終書狀，使其難以在維持 query 主體性的前提下生成兼具法律格式與精度之民事起訴書。為此，本文提出 XRAG（eXtended Retrieval-Augmented Generation）方法，結合知識圖譜推理與雙向樹狀檢索，以應用於交通事故民事起訴書生成。本文所提出之 XRAG 架構，首先將 6,057 筆臺灣交通事故民事案件轉換為涵蓋 Litigants、Fact、Injury 與 Compensation 四個面向之固定 boolean case profiles，並進一步重建為 Fact、Injury 與 Compensation 三項 severity scores。其後，XRAG 依不同實驗參數，以外部法律領域知識權重加權 severity 分數、距離函數建立 experiment-specific case relations，並於 query 階段先找出最近之 anchor case，再透過雙向樹狀擴展擷取相對較輕與相對較重之鄰近案例。檢索所得案例不直接以全文輸入模型，而是先提取為結構線索與論述提示，再接入事實、法條、損害賠償與結論之分段式生成流程。本研究共建立 18 組 XRAG 實驗設定，係由六種權重排列與三種距離閾值組成，並以 50 筆模擬律師輸入之測試 query 與由法律系專業人員撰寫之人工起訴書進行初步驗證。整體而言，XRAG 可作為交通事故民事起訴書受控生成之一條可行方法。

關鍵詞：交通事故、民事起訴書生成、法律生成式人工智慧、檢索增強生成、XRAG、法律文本生成
