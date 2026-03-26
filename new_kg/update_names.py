import json, re
from pathlib import Path
from neo4j import GraphDatabase

TENSORS_FILE = Path("/home/aru/AI_LAW/new_kg/phase1_tensors_v4.jsonl")
driver = GraphDatabase.driver(
    "neo4j+s://3a29e735.databases.neo4j.io",
    auth=("3a29e735","WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8")
)

P_SECTION = re.compile(r'原告(\S{1,15}?)(?:部分|之損害|之損失|之請求|之費用|之賠償)\s*[：:]')
NON_NAME = re.compile(
    r'^(?:因|其|已|疏|竟|雖|仍|本|所|當|並|亦|之|依|自|明|知|應|主|請|表|稱|'
    r'對|向|為|係|騎|駕|持|乃|逕|受|撞|倒|跌|發|造|致|被|衝|遭|與|及|人|車|的|'
    r'從|到|在|就|他|她|它|我|你|這|那|有|無|不|沒|更|也|還|又|再|只|都|很|太|'
    r'全|各|等|此|該|上|下|前|後|左|右)'
)

def extract_plaintiff_names(comp_text, fact_text, li_fact):
    results = set()
    for m in P_SECTION.finditer(comp_text):
        n = m.group(1).strip()
        if len(n) >= 2 and not NON_NAME.match(n):
            results.add(n)
    if results:
        return sorted(results)
    text = fact_text[:800] + ' ' + li_fact[:500]
    for m in re.finditer(r'原告([甲乙丙丁戊己庚辛壬癸子丑寅卯][○◯〇]{1,2})'
                         r'((?:[、，及]?[甲乙丙丁戊己庚辛壬癸子丑寅卯][○◯〇]{1,2})*)', text):
        results.add(m.group(1))
        for x in re.findall(r'[甲乙丙丁戊己庚辛壬癸子丑寅卯][○◯〇]{1,2}', m.group(2)):
            results.add(x)
    for m in re.finditer(r'原告([\u4e00-\u9fff]{2,4})(?=(?:於民國|在民國|騎乘|駕駛|所有))', text):
        n = m.group(1)
        if not NON_NAME.match(n): results.add(n)
    return sorted(results) if results else ['未提及']

def extract_defendant_names(fact_text, li_fact):
    results = set()
    text = fact_text[:800] + ' ' + li_fact[:500]
    for m in re.finditer(r'被告([甲乙丙丁戊己庚辛壬癸子丑寅卯][○◯〇]{1,2})'
                         r'((?:[、，及]?[甲乙丙丁戊己庚辛壬癸子丑寅卯][○◯〇]{1,2})*)', text):
        results.add(m.group(1))
        for x in re.findall(r'[甲乙丙丁戊己庚辛壬癸子丑寅卯][○◯〇]{1,2}', m.group(2)):
            results.add(x)
    for m in re.finditer(r'被告([\u4e00-\u9fff]{2,4})(?=(?:於民國|在民國|騎乘|駕駛|所有))', text):
        n = m.group(1)
        if not NON_NAME.match(n): results.add(n)
    for m in re.finditer(r'被告([\u4e00-\u9fff]{1,15}(?:股份有限公司|有限公司|公司|商行|企業行|汽車行|機車行))', text):
        results.add(m.group(1))
    cleaned = set()
    for n in results:
        n = re.sub(r'[（()）\s].*', '', n).strip()
        if len(n) >= 2 and not NON_NAME.match(n): cleaned.add(n)
    return sorted(cleaned) if cleaned else ['未提及']

records = []
with open(TENSORS_FILE) as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

for rec in records:
    rec['plaintiff_names'] = extract_plaintiff_names(
        rec.get('compensation_text',''), rec.get('fact_text',''), rec.get('LI_fact',''))
    rec['defendant_names'] = extract_defendant_names(
        rec.get('fact_text',''), rec.get('LI_fact',''))

with open(TENSORS_FILE, 'w') as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print("JSONL 完成")

BATCH = 200
for i in range(0, len(records), BATCH):
    batch = records[i:i+BATCH]
    params = [{'cid': str(r['case_id']),
               'pn': r['plaintiff_names'],
               'dn': r['defendant_names']} for r in batch]
    with driver.session() as s:
        s.run('''
            UNWIND $rows AS row
            MATCH (c:Case {case_id: row.cid})
            SET c.plaintiff_names = row.pn,
                c.defendant_names = row.dn
        ''', rows=params)
    print(f"  {i+len(batch)}/{len(records)}")

driver.close()
print("✅ 完成")
