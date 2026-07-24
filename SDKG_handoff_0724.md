# SDKG 論文交接摘要（2026-07-24）

本檔用於電腦關機或換環境後，在新對話快速接續 `/home/aru/AI_LAW` 論文工作。

## 目前核心題目

本論文提出 Severity-Aware Dual-Knowledge-Graph（SDKG），用於臺灣交通事故民事起訴書生成。核心問題是傳統檢索增強生成多依語意相似度取案例，但語意相似不代表法律上可比較。SDKG 改以案件法律特徵、嚴重度、距離門檻與嚴重度方向建立 light-heavy / heavy-light 雙樹，使生成模型取得較輕與較重方向的可比較案例。

## 老師最新偏好

- 符號可以多，但要簡單直觀。
- 不要突然出現未解釋的大寫符號。
- 生成模型用 \(M(\cdot)\)，不要用 \(\mathcal{M}\)。
- 公式內避免英文敘述。
- 第三章方法不要寫死 50 queries；50 筆只放第六章實驗。
- `top-\(k\)` 統一寫法；固定值寫 top-1、top-8。
- 不要使用舊符號：\(\sigma\)、正式 \(\Delta_{i,j}^p\)、\(c_a\)、\(\lambda_f,\lambda_s\)、\((1-\alpha-\beta)^p\)、\(G(p)\)、\(R_{LH}^{k/2},R_{HL}^{k/2}\)。

## 目前章節狀態

- `Ch3.md`：System Model and Problem Formulation。
- `Ch4.md`：Sentence-Level-Aware Dual Retrieval Method，作為 Baseline Method，不要稱為 early/preliminary。
- `Ch5.md`：Proposed SDKG Scheme。
- `Ch6.md`：Experimental Results and Discussion，含 Baseline Method、TAARN、SDKG 比較。
- `Ch7.md`：Conclusions。

## 第四章到第五章的包裝口徑

第四章不是失敗方法，而是基準方法。它把起訴書切成段落與句子，能定位局部法律資訊，例如相似事故事實、法條句子、賠償項目。但片段層級檢索的限制是召回單位太細，最後難以判斷應該引用哪個完整案件，也容易失去案件整體脈絡。因此第五章 SDKG 不是丟掉第四章，而是把局部摘要與法律資訊整理的精神延伸為案件層級可比較檢索。

## 最新重要修正：共享特徵不是硬門檻

老師質疑「兩案至少共享一個主導特徵才可以比較」會有漏洞，因為頭部受傷與四肢受傷的案件仍可能因事故型態、賠償項目與嚴重程度接近而可比較。

最新建議口徑：

> 共享特徵不是限制門檻，而是法律特徵距離的一部分。共享越多，\(d_f\) 越小；差異越多，\(d_f\) 越大。最後是否建邊仍由總距離 \(d_{i,j}^{p,\ell}\leq\tau^u\) 決定。

不要再說：

> 兩案必須在主導特徵群中至少共享一個 boolean feature。

應改成：

> 兩案的布林法律特徵差異由法律特徵距離衡量。布林特徵不作為硬性共同特徵門檻，而是作為案件可比較性的距離基礎。

## 建議公式修正方向

案件法律特徵表示改成維度上標：

\[
\mathbf{f}_i=
[
\mathbf{b}_i^L,
\mathbf{b}_i^F,
\mathbf{b}_i^U,
\mathbf{b}_i^P
]
\]

其中每個 \(\mathbf{b}_i^\cdot\) 都是布林陣列，不是單一值。

分群距離：

\[
d_{i,j}^{F},\quad d_{i,j}^{U},\quad d_{i,j}^{P}
\]

可用布林陣列逐格差異平均表示。例如傷勢類型：

\[
d_{i,j}^{U}
=
\frac{1}{r_U}
\sum_{t=1}^{r_U}
\left|b_{i,t}^{U}-b_{j,t}^{U}\right|
\]

其中 \(r_U\) 是傷勢類型布林陣列的固定格數，不是新增參數。平均只是正規化，使距離落在 0 到 1。

法律特徵距離建議改成：

\[
d_f^p(\mathbf{f}_i,\mathbf{f}_j)
=
\alpha^p d_{i,j}^{F}
+
\beta^p d_{i,j}^{U}
+
(1-\alpha^p-\beta^p)d_{i,j}^{P}
\]

不要除以 2，避免被問為什麼要除以 2。也不要新增當事人權重。Litigants 可作為案件結構資訊與提示資訊，不放進這個三面向主距離公式。

總距離：

\[
d_{i,j}^{p,\ell}
=
\lambda^\ell d_f^p(\mathbf{f}_i,\mathbf{f}_j)
+
(1-\lambda^\ell)d_s^p(c_i,c_j)
\]

建邊條件：

\[
d_{i,j}^{p,\ell}\leq\tau^u
\]

## 口試回答範例：0101 與 1010

若傷勢類型有四格 \([頭頸,軀幹,四肢,其他]\)，案件 \(c_i\) 為：

\[
[1,0,0,1]
\]

案件 \(c_j\) 為：

\[
[0,0,1,0]
\]

兩案不是被直接排除，而是逐格比較：

\[
[|1-0|,|0-0|,|0-1|,|1-0|]=[1,0,1,1]
\]

所以傷勢類型距離為 \(3/4=0.75\)，表示傷勢類型差異較大。若兩案在事故事實、賠償項目與嚴重度距離上仍接近，總距離仍可能小於 \(\tau^u\)，因此仍可能建邊；若其他面向也差很多，總距離就會超過門檻，不建邊。

## 頭傷與腳傷的口試說法

頭部與腳部是傷勢類型，不是嚴重度大小。頭部擦傷不一定比腳部骨折嚴重。布林矩陣處理的是類型差異；嚴重度距離處理的是程度差異。受傷部位不同會讓 \(d_U\) 變大，但不會直接禁止比較。真正是否可比較由總距離 \(d_{i,j}^{p,\ell}\leq\tau^u\) 決定。

## 為什麼不要新增共享比例參數

不要新增共享比例門檻，因為比例差異已經包含在 \(d_f^p\) 中。若 16 格布林特徵差 1 格，距離就是 \(1/16\)；差 2 格就是 \(2/16\)。若再設定「至少相同 25% 或 50%」這種共享比例門檻，功能會和 \(\tau^u\) 重疊，變成兩個門檻同時控制案件可比較性，也會多出一個新的實驗維度。

可以重跑實驗，但應強調是「修正建樹邏輯後重跑同一套 \(\alpha,\beta,\lambda,\tau\) 設定」，不是新增參數實驗。

## 程式碼狀態提醒

目前正式建樹腳本：

- `new_kg/XRAG_phase2_build_severity_trees.py`

其中仍有硬門檻：

```python
shared_dominant_feature = (parent_dominant_features @ dominant_features.T) > 0
lh_mask = shared_dominant_feature & (dist <= tau) & (delta > 0) & not_self
hl_mask = shared_dominant_feature & (dist <= tau) & (delta < 0) & not_self
```

若採用最新口徑，需改成距離式處理，拿掉 `shared_dominant_feature` 硬條件，並視需要把 \(d_f\) 改成分群加權距離 \(d_f^p\)。之後要重建樹並重跑同一套實驗。

## 目前最佳實驗設定與結果

最佳 SDKG 設定：

- \(\alpha=0.5\)
- \(\beta=0.2\)
- \(\lambda=0.5\)
- \(\tau=0.5\)
- \(k=8\)

相較 TAARN：

- BERTScore：+1.65 percentage points / +1.85%
- BLEU：+6.71 percentage points / +11.35%
- ROUGE-L：+6.17 percentage points / +8.67%
- 三者平均相對提升約 7.3%

Baseline Method 高於 TAARN，但低於 SDKG。其解釋是：段落與句子摘要檢索能提供局部線索，但仍不及 SDKG 的案件層級法律特徵與嚴重度方向比較。

## 口試逐字稿

目前逐字稿檔案：

- `口試-0723逐頁演講稿_全中文40分鐘版.txt`

已補強：

- Introduction：現有 RAG 與圖檢索缺點。
- TAARN：路徑抽取、文字增強表示、注意力式循環網路。
- Problem formulation：任務是降低生成起訴書與人工起訴書差距。
- Ch4：細切分的好處與限制，並呼應第六章 Baseline Method 結果。

