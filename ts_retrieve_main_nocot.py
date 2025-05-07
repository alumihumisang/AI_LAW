# ts_retrieve_main_nocot.py

from ts_retrieval_system import RetrievalSystem
from ts_define_case_type import get_case_type
import time

def main():
    print("🔍 初始化檢索系統")
    retrieval_system = RetrievalSystem()

    print("\n📥 請輸入 User Query（貼上完整律師輸入，一段即可）：")
    user_input_lines = []
    while True:
        line = input()
        if line.lower() in ['q', 'quit']:
            break
        user_input_lines.append(line)
    user_query = "\n".join(user_input_lines).strip()

    if not user_query:
        print("❌ 未輸入查詢內容，程序結束")
        return

    print("\n📌 請選擇搜尋類型:")
    print("1: 使用 'full' 文本進行搜尋")
    print("2: 使用 'fact' 文本進行搜尋")
    search_type_choice = input("輸入 1 或 2: ").strip()
    search_type = "full" if search_type_choice == '1' else "fact"

    try:
        k = int(input("🔢 請輸入要搜尋的 Top-K 數量: ").strip())
        if k <= 0:
            print("❌ K 必須大於 0")
            return
    except:
        print("❌ 無效的 K 值")
        return

    print("\n📌 是否查詢結論金額？")
    print("1: 只查 used_law")
    print("2: 查 used_law 和 conclusion")
    include_conclusion = input("輸入 1 或 2: ").strip() == '2'

    print("\n🧠 判斷案件類型中...")
    case_type, _ = get_case_type(user_query)
    print(f"📂 案件類型: {case_type}")

    print(f"\n🔎 在 Elasticsearch 搜尋 {search_type} 類型 Top {k} 個文檔")
    search_results = retrieval_system.search_elasticsearch(user_query, search_type, k, case_type)

    if not search_results:
        print("❌ 無法找到相符案例")
        return

    print("\n📋 搜尋結果:")
    for i, r in enumerate(search_results):
        print(f"{i+1}. Case ID: {r['case_id']} | 分數: {r['score']:.4f} | Text preview: {r['text'][:60].replace(chr(10), ' ')}...")

    case_ids = [r["case_id"] for r in search_results]
    print(f"\n✅ 找到 Case IDs: {case_ids}")

    print("\n📚 從 Neo4j 查詢法條...")
    laws = retrieval_system.get_laws_from_neo4j(case_ids)
    if laws:
        law_counts = retrieval_system.count_law_occurrences(laws)
        for law, count in law_counts.items():
            print(f"⚖️ 法條 {law}: 出現 {count} 次")
    else:
        print("⚠️ 未找到任何法條")

    if include_conclusion:
        print("\n📌 從 Neo4j 查詢結論...")
        conclusions = retrieval_system.get_conclusions_from_neo4j(case_ids)
        if conclusions:
            avg_amt = retrieval_system.calculate_average_compensation(conclusions)
            print(f"\n💰 平均賠償金額: {avg_amt:,.0f} 元")
            for c in conclusions:
                amt = retrieval_system.extract_compensation_amount(c["conclusion_text"])
                print(f"Case ID {c['case_id']}: {amt if amt else '無法解析金額'}")
        else:
            print("⚠️ 無法取得結論內容")

if __name__ == "__main__":
    main()
