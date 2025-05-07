import pandas as pd
import os
from elasticsearch import Elasticsearch
from tqdm import tqdm
from dotenv import load_dotenv
from ts_define_case_type import get_case_type  

# 載入 .env
load_dotenv()
es = Elasticsearch(
    os.getenv("ELASTIC_HOST"),
    basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
    verify_certs=False
)

# 讀取 Excel
df = pd.read_excel("整合_模擬律師輸入_2995.xlsx")

# 讀取上次成功進度
resume_file = "last_success_case_id.txt"
if os.path.exists(resume_file):
    with open(resume_file, "r") as f:
        last_success_id = int(f.read().strip())
else:
    last_success_id = 0  # 從頭開始

print(f"🔁 從 case_id > {last_success_id} 開始執行...\n")

updated = 0
skipped = 0
type_counter = {}
preview = {}

for _, row in tqdm(df.iterrows(), total=len(df)):
    case_id = row.get("case_id")
    user_input = row.get("律師輸入")

    if not isinstance(case_id, int) or not isinstance(user_input, str):
        skipped += 1
        continue

    if case_id <= last_success_id:
        continue  # 已經處理過

    case_type = get_case_type(user_input)

    type_counter[case_type] = type_counter.get(case_type, 0) + 1
    if case_type not in preview:
        preview[case_type] = [(case_id, user_input[:120].replace("\n", ""))]

    script = {
        "script": {
            "source": "ctx._source.case_type = params.type",
            "lang": "painless",
            "params": {"type": case_type}
        },
        "query": {
            "term": {"case_id": case_id}
        }
    }

    try:
        es.update_by_query(index="legal_kg_chunks", body=script, refresh=True)
        updated += 1

        # 成功就記錄最新成功的 case_id
        with open(resume_file, "w") as f:
            f.write(str(case_id))

    except Exception as e:
        print(f"❌ case_id {case_id} 更新失敗：{str(e)}")
        skipped += 1

# 統計與預覽
print("\n📊 分類統計：")
for k, v in sorted(type_counter.items(), key=lambda x: -x[1]):
    print(f"  {k:25} ➜ {v} 筆")

print("\n📌 範例預覽：\n")
for k, v in preview.items():
    print(f"--- 類型：{k} ---")
    for cid, txt in v[:2]:
        print(f"🔸 case_id: {cid}\n{txt}...\n")
