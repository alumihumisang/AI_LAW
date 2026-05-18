from __future__ import annotations

import re


FORBIDDEN_DAMAGE_LINES = [
    "綜上所述",
    "綜上所陳",
    "總計",
    "請求被告賠償",
    "按年息5%",
    "繕本送達翌日起",
]


def extract_damage_constraints(comp_facts: str, injuries: str) -> dict:
    source_text = f"{injuries}\n{comp_facts}"
    return {
        "allowed_amounts": extract_currency_amounts(source_text),
        "allowed_hospitals": extract_hospital_like_terms(source_text),
        "allowed_income_terms": extract_income_terms(source_text),
        "allowed_damage_labels": infer_damage_labels(source_text),
        "required_items": extract_required_damage_items(comp_facts),
    }


def extract_currency_amounts(text: str) -> set[str]:
    amounts = set()
    for match in re.finditer(r"([0-9][0-9,]*)\s*元", text):
        amounts.add(match.group(1).replace(",", ""))
    return amounts


def extract_hospital_like_terms(text: str) -> set[str]:
    terms = set()
    pattern = r"[\u4e00-\u9fffA-Za-z0-9○]{2,30}(?:醫院|診所|中醫|紀念醫院)"
    for match in re.finditer(pattern, text):
        terms.add(match.group(0).strip())
    return terms


def extract_income_terms(text: str) -> set[str]:
    terms = set()
    patterns = [
        r"日薪[^\n，。；]{0,20}",
        r"月薪[^\n，。；]{0,20}",
        r"年收入[^\n，。；]{0,20}",
        r"所得[^\n，。；]{0,20}",
        r"從事[^\n，。；]{0,20}",
        r"任職[^\n，。；]{0,20}",
        r"工作[^\n，。；]{0,20}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            terms.add(match.group(0).strip())
    return terms


def extract_required_damage_items(comp_facts: str) -> list[dict]:
    items = []
    for match in re.finditer(r"^\s*\d+\.\s*([^\n]+)", comp_facts, re.M):
        line = match.group(1).strip()
        amount_match = re.search(r"([0-9][0-9,]*)\s*元", line)
        if not amount_match:
            continue
        amount_raw = amount_match.group(1)
        amount_value = amount_raw.replace(",", "")
        label = line.replace(amount_match.group(0), "").strip(" ：:，,。")
        if not label:
            label = infer_damage_labels(line)[0]
        items.append({
            "label": label,
            "amount_raw": amount_raw,
            "amount_value": amount_value,
            "source_line": line,
        })
    return items


def split_compensation_facts_into_items(text: str) -> str:
    text = re.sub(r"(\d+\.\s*)", r"\n\1", text)
    text = re.sub(r"(（[一二三四五六七八九十]+）)", r"\n\1", text)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return "\n\n".join(paragraphs)


def infer_damage_labels(text: str) -> list[str]:
    labels = []
    rules = [
        ("醫療費用", ["醫療", "醫藥", "診療", "住院", "門診", "手術", "復健"]),
        ("交通費用", ["交通費", "計程車", "車資", "往返"]),
        ("工作損失", ["工作損失", "薪資", "收入", "不能工作", "無法工作", "勞動能力"]),
        ("看護費用", ["看護", "照護", "照顧"]),
        ("車輛修復費用", ["修車", "修復", "修理", "零件", "工資", "鈑金"]),
        ("精神慰撫金", ["慰撫金", "精神", "痛苦", "憂鬱", "失眠"]),
        ("其他必要費用", ["營養品", "護具", "安全帽", "輔具"]),
    ]
    for label, keywords in rules:
        if any(keyword in text for keyword in keywords):
            labels.append(label)
    return labels or ["一般損害項目"]


def build_generation_support_context(similar_cases: list[dict], parent_map: dict[str, str], corpus_by_id: dict[str, dict]) -> str:
    case_blocks = []
    for case in similar_cases:
        parent_id = parent_map.get(case["case_id"])
        parent_note = ""
        if parent_id and parent_id in corpus_by_id:
            parent = corpus_by_id[parent_id]
            parent_note = (
                f"；父案例={parent_id}"
                f"（F={parent['severity_scores']['Fact']},"
                f" I={parent['severity_scores']['Injury']},"
                f" C={parent['severity_scores']['Compensation']}）"
            )
        damage_labels = "、".join(infer_damage_labels(case["comp_text"]))
        case_blocks.append(
            f"相似案例{case['rank']}：case_id={case['case_id']}，distance={case['distance']:.4f}，score={case['case_score']:.4f}{parent_note}\n"
            f"- 可參考的損害結構：{damage_labels}\n"
            f"- 事故摘要：{case['fact_text'][:120]}\n"
            f"- 傷勢摘要：{case['injury_text'][:120]}"
        )
    return "\n\n".join(case_blocks)


def build_damages_prompt(comp_facts: str, injuries: str, support_context: str, parties: dict, constraints: dict) -> str:
    preprocessed = split_compensation_facts_into_items(comp_facts)
    allowed_amounts_text = "、".join(sorted(constraints["allowed_amounts"])) if constraints["allowed_amounts"] else "無"
    allowed_hospitals_text = "、".join(sorted(constraints["allowed_hospitals"])) if constraints["allowed_hospitals"] else "無"
    allowed_income_text = "、".join(sorted(constraints["allowed_income_terms"])) if constraints["allowed_income_terms"] else "無"
    required_items_text = "；".join(
        f"{item['label']}={item['amount_raw']}元（原文：{item['source_line']}）" for item in constraints["required_items"]
    ) if constraints["required_items"] else "無"
    return f"""你是台灣律師，請把以下損害賠償事實整理成起訴狀中的損害項目段落。

當事人資訊：
原告：{parties.get('原告', '原告')}（共{parties.get('原告數量', 1)}名）
被告：{parties.get('被告', '被告')}（共{parties.get('被告數量', 1)}名）

原告受傷情形：
{injuries}

原始損害描述：
{preprocessed}

XRAG檢索與父子圖譜輔助資訊：
{support_context}

Query 中明示可使用的敏感資訊：
- 金額：{allowed_amounts_text}
- 醫療院所：{allowed_hospitals_text}
- 工作/收入資訊：{allowed_income_text}
- 必須保留的賠償項目：{required_items_text}

要求：
1. 使用「（一）」「（二）」等編號。
2. 保留原文中的金額、醫院名稱、計算式與重要細節。
3. 項目名稱可整理成：醫療費用、交通費用、工作損失、看護費用、慰撫金、車輛修復費用等。
4. XRAG相似案例只能幫助你判斷常見損害項目結構，不可借用其中的金額、醫院名稱、日期、職業、收入或事故細節。
5. 直接輸出損害段落，不要解釋。
6. 不要輸出「綜上所述」「綜上所陳」「總計」「請求被告賠償」「按年息5%」「繕本送達翌日起」等結論句。
7. 若原始損害描述未出現某金額或事實，不能自行補寫。
8. 只有上面列出的敏感資訊可以出現在答案中；若 query 沒有提到某醫院、職業、薪資、所得或金額，就不能自行補寫。
9. 若 query 已明列賠償項目與金額，該項目不得漏掉。
10. 每一個賠償項目都要盡量引用原始損害描述中的事實理由，例如「需休養1個月」、「傷勢不良於行」、「車輛因事故受損需修理」、「耗費時間與精神」等；不要只剩項目名稱與金額。
"""


def clean_damage_section(text: str, constraints: dict | None = None) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        if any(token in line for token in FORBIDDEN_DAMAGE_LINES):
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = strip_case_borrowing_markers(cleaned)
    if constraints is not None:
        cleaned = remove_unsupported_sensitive_lines(cleaned, constraints)
        cleaned = ensure_required_damage_items(cleaned, constraints["required_items"])
    return cleaned


def strip_case_borrowing_markers(text: str) -> str:
    text = re.sub(r"^相似案例.*$", "", text, flags=re.M)
    text = re.sub(r"^案例\s*\d+.*$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_unsupported_sensitive_lines(text: str, constraints: dict) -> str:
    kept_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            kept_lines.append(raw_line)
            continue
        if line_mentions_unsupported_amount(line, constraints["allowed_amounts"]):
            continue
        if line_mentions_unsupported_hospital(line, constraints["allowed_hospitals"]):
            continue
        if line_mentions_unsupported_income(line, constraints["allowed_income_terms"]):
            continue
        kept_lines.append(raw_line)
    cleaned = "\n".join(kept_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def ensure_required_damage_items(text: str, required_items: list[dict]) -> str:
    if not required_items:
        return text
    blocks = [b for b in re.split(r"\n\n(?=（[一二三四五六七八九十\d]+）)", text.strip()) if b.strip()]
    next_idx = count_damage_items(text) + 1
    appended_blocks = []

    for item in required_items:
        if item["amount_raw"] in text or item["amount_value"] in text:
            continue
        merged = False
        for idx, block in enumerate(blocks):
            if block_can_absorb_required_item(block, item):
                blocks[idx] = block.rstrip() + f"\n因本次事故，產生{item['label']}新台幣{item['amount_raw']}元。"
                merged = True
                break
        if not merged:
            prefix = to_chinese_item_marker(next_idx)
            appended_blocks.append(f"{prefix}{item['label']}：新台幣{item['amount_raw']}元。")
            next_idx += 1
    merged_text = "\n\n".join(blocks).strip()
    if not appended_blocks:
        return merged_text
    joiner = "\n\n" if merged_text else ""
    return f"{merged_text}{joiner}" + "\n\n".join(appended_blocks)


def count_damage_items(text: str) -> int:
    return len(re.findall(r"（[一二三四五六七八九十]+）", text))


def to_chinese_item_marker(index: int) -> str:
    numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 1 <= index <= 10:
        return f"（{numerals[index]}）"
    return f"（{index}）"


def block_can_absorb_required_item(block: str, item: dict) -> bool:
    label = item["label"]
    normalized_block = block.replace(" ", "")
    if "醫療" in label and "醫療" in normalized_block and not re.search(r"[0-9][0-9,]*元", block):
        return True
    if "交通" in label and "交通" in normalized_block and not re.search(r"[0-9][0-9,]*元", block):
        return True
    if "工作" in label and "工作" in normalized_block and not re.search(r"[0-9][0-9,]*元", block):
        return True
    if "修復" in label and "修復" in normalized_block and not re.search(r"[0-9][0-9,]*元", block):
        return True
    if "慰撫" in label and "慰撫" in normalized_block and not re.search(r"[0-9][0-9,]*元", block):
        return True
    return False


def line_mentions_unsupported_amount(line: str, allowed_amounts: set[str]) -> bool:
    found = [match.group(1).replace(",", "") for match in re.finditer(r"([0-9][0-9,]*)\s*元", line)]
    return bool(found) and any(amount not in allowed_amounts for amount in found)


def line_mentions_unsupported_hospital(line: str, allowed_hospitals: set[str]) -> bool:
    if not re.search(r"(醫院|診所|中醫|紀念醫院)", line):
        return False
    if not allowed_hospitals:
        return True
    return not any(term in line for term in allowed_hospitals)


def line_mentions_unsupported_income(line: str, allowed_income_terms: set[str]) -> bool:
    if not re.search(r"(日薪|月薪|年收入|所得|從事|任職|工作)", line):
        return False
    if not allowed_income_terms:
        return True
    return not any(term in line for term in allowed_income_terms)


def compute_total_from_damage_section(damage_section: str) -> int:
    blocks = [b.strip() for b in re.split(r"\n(?=（[一二三四五六七八九十]+）)", damage_section) if b.strip()]
    totals = []
    for block in blocks:
        amount = extract_claim_amount_from_block(block)
        if amount is not None:
            totals.append(amount)
    return sum(totals)


def extract_claim_amount_from_block(block: str) -> int | None:
    preferred_patterns = [
        r"(?:共計|合計)[^\n，。；]*?([0-9][0-9,]*)元",
        r"(?:費用|損失|慰撫金)[^\n，。；：:]*?(?:為|計|共計|合計)?[^\n，。；]*?([0-9][0-9,]*)元",
    ]
    for pattern in preferred_patterns:
        match = re.search(pattern, block)
        if match:
            return safe_parse_amount(match.group(1))

    first_amount_match = re.search(r"([0-9][0-9,]*)元", block)
    if first_amount_match:
        return safe_parse_amount(first_amount_match.group(1))
    return None


def safe_parse_amount(raw: str) -> int | None:
    try:
        return int(raw.replace(",", ""))
    except ValueError:
        return None


def build_conclusion_section(damage_section: str, parties: dict) -> str:
    total_amount = compute_total_from_damage_section(damage_section)
    plaintiff = parties.get("原告", "原告")
    defendant = parties.get("被告", "被告")
    next_marker = to_chinese_item_marker(count_damage_items(damage_section) + 1)
    return (
        f"{next_marker}綜上所陳，{defendant}因前揭侵權行為，應賠償{plaintiff}所受之各項損害，"
        f"合計新台幣{total_amount:,}元，並自起訴狀繕本送達翌日起至清償日止，按年息5%計算之利息。"
    )
