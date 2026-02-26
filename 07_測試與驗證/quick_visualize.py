#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速視覺化工具 - 簡化版
直接執行即可看到視覺化結果
"""

from visualize_vector_retrieval import visualize_retrieval

# 測試案例
test_query = """
被告於民國110年8月18日晚間9時26分許，騎乘重型機車行經新北市板橋區長江路1段往北向民生路方向，
當時天候晴朗、視線良好、路面平坦乾燥且設有路燈照明，被告本應依規定於欲左轉時先行打方向燈、
暫停並注意來往車輛，竟疏未為之，逕自行駛至路旁欲左轉，適原告騎乘機車自被告後方同向直行而至，
因閃避不及，遂與被告所駕駛機車發生碰撞。原告因而人車倒地，造成原告受有左膝挫傷併十字韌帶撕裂性骨折及左肩挫擦傷。
"""

if __name__ == "__main__":
    print("🎨 開始視覺化...")
    print(f"📝 Query 內容: {test_query[:80]}...")
    print()

    # 執行視覺化
    visualize_retrieval(
        query_text=test_query,
        top_k=5,              # 顯示前 5 筆最相似的句子
        label="Facts",        # 只檢索事實段落
        method="tsne",        # 使用 t-SNE 降維
        include_background=80  # 包含 80 筆背景資料點做對比
    )

    print("\n✅ 完成！請查看生成的圖片檔案。")
