import os
import re
import pandas as pd
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm

# 載入環境變數
load_dotenv()
es = Elasticsearch(
    os.getenv("ELASTIC_HOST"),
    basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
    verify_certs=False
)

# 載入 Excel
xlsx_path = "整合_起訴書_四段(FINAL)_2995_深夜鉅作.xlsx"
df = pd.read_excel(xlsx_path, sheet_name="2995結論")

priority_columns = [
    "單一原告總計金額(不含肇事責任且已根據事實扣除費用)",
    "單一原告總計金額(不含肇事責任)",
    "多名原告總計金額(不含肇事責任且已根據事實扣除費用)",
    "多名原告總計金額(不含肇事責任)"
]

success = 0
fail = 0

print("🚀 正在補入 compensation_amount 到 Elasticsearch...\n")

for _, row in tqdm(df.iterrows(), total=len(df)):
    cid = row.get("case_id")
    if not isinstance(cid, int):
        continue

    final_amount = None

    # 從結論抓最後金額
    conclusion_text = str(row.get("結論", ""))
    matches = re.findall(r'(\d{1,3}(?:,\d{3})*)元', conclusion_text)
    if matches:
        try:
            amount_str = matches[-1].replace(",", "")
            final_amount = int(amount_str)
        except:
            pass

    # fallback：人工欄位
    if final_amount is None:
        for col in priority_columns:
            if col in row and pd.notna(row[col]):
                try:
                    val = str(row[col]).replace(",", "").replace("元", "")
                    val = ''.join(c for c in val if c.isdigit())
                    if val:
                        final_amount = int(val)
                        break
                except:
                    continue

    if final_amount is None:
        fail += 1
        continue

    # 執行 update 並印出
    for index_name in ["legal_kg_chunks", "legal_kg_paragraphs"]:
        script = {
            "script": {
                "source": "ctx._source.compensation_amount = params.amount",
                "lang": "painless",
                "params": {"amount": final_amount}
            },
            "query": {
                "term": {"case_id": cid}
            }
        }
        es.update_by_query(index=index_name, body=script, refresh=True, conflicts="proceed")

    print(f"✅ case_id: {cid} ➜ 補入金額：{final_amount:,} 元")
    success += 1

print(f"\n✅ 寫入完成！總共補入：{success} 筆（含 chunks + paragraphs）")
print(f"❌ 略過（無法擷取金額）：{fail} 筆")
