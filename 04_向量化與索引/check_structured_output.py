#!/usr/bin/env python3
"""檢查structured_summaries輸出"""
import json

# 讀取前10個chunk
with open('structured_summaries_test_3.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f.readlines()[:10]]

# 分類統計
stats = {}
for line in lines:
    section = line['parent_section']
    detail_type = line.get('extracted_detail', {}).get('detail_type', 'None')
    key = f"{section} - {detail_type}"
    stats[key] = stats.get(key, 0) + 1

print("📊 前10個chunk的統計：\n")
for key, count in sorted(stats.items()):
    print(f"  {key}: {count}個")

print("\n" + "="*60)
print("🔍 範例展示：\n")

# 展示每種類型的第一個例子
seen_types = set()
for idx, line in enumerate(lines):
    detail = line.get('extracted_detail', {})
    detail_type = detail.get('detail_type', 'None')

    if detail_type not in seen_types:
        seen_types.add(detail_type)

        print(f"\n【範例 {idx+1}】{line['parent_section']} - {detail_type}")
        print(f"Chunk ID: {line['chunk_id']}")
        print(f"原文: {line['chunk_text'][:80]}...")
        print(f"提取資訊: {json.dumps(detail.get('extracted_info', {}), ensure_ascii=False, indent=2)}")
        print(f"摘要: {detail.get('semantic_summary', 'N/A')}")
        print("-" * 60)

print(f"\n✅ 總共讀取 {len(lines)} 個chunks")
