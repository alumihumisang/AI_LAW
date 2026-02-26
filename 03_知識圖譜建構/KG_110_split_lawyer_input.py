# KG_110_split_lawyer_input.py
# 分割律師輸入的三段文字並存成新的 Excel（保留小標題）

import pandas as pd
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

def split_lawyer_input_with_headers(text):
    """
    分割律師輸入文字為三段，並保留小標題
    策略：找到「一、」「二、」「三、」的位置，不管後面的標題文字是什麼
    注意：必須避開「三、四趾骨折」「第二、三、四節」這種非標題的數字列舉
    """
    # 初始化三段（保留小標題）
    section_1 = ""
    section_2 = ""
    section_3 = ""

    # 找「一、」
    match_1 = re.search(r'一、', text)
    if not match_1:
        return section_1, section_2, section_3

    start_1 = match_1.start()

    # 從「一、」之後找「二、」
    match_2 = re.search(r'二、', text[start_1:])
    if match_2:
        start_2 = start_1 + match_2.start()

        # 從「二、」之後找「三、」，但要避開「三、四」這種數字列舉
        # 策略：找所有「三、」，選擇後面不是數字的那個
        text_after_section2 = text[start_2:]
        matches_3 = list(re.finditer(r'三、', text_after_section2))

        start_3 = None
        for match in matches_3:
            pos = match.end()
            # 檢查「三、」後面的字符
            if pos < len(text_after_section2):
                next_chars = text_after_section2[pos:pos+3].strip()
                # 如果後面是「四」「五」等數字，跳過
                if next_chars and next_chars[0] not in '四五六七八九十0123456789０-９':
                    start_3 = start_2 + match.start()
                    break

        if start_3:
            # 提取三段
            section_1 = text[start_1:start_2].strip()
            section_2 = text[start_2:start_3].strip()
            section_3 = text[start_3:].strip()
        else:
            # 沒有找到合適的「三、」
            section_1 = text[start_1:start_2].strip()
            section_2 = text[start_2:].strip()
    else:
        # 沒有找到「二、」
        section_1 = text[start_1:].strip()

    return section_1, section_2, section_3

def main():
    input_file = "/home/aru/AI_LAW/09_輸入輸出資料/6057律師輸入.xlsx"
    output_file = "/home/aru/AI_LAW/09_輸入輸出資料/6057律師輸入_三段切分.xlsx"

    logger.info(f"讀取檔案: {input_file}")
    df = pd.read_excel(input_file, sheet_name="3062律師輸入")

    logger.info(f"共有 {len(df)} 筆資料")

    # 分割每一筆律師輸入
    results = []
    empty_count = 0

    for idx, row in df.iterrows():
        case_id = row['case_id']
        text = str(row['律師輸入'])

        section_1, section_2, section_3 = split_lawyer_input_with_headers(text)

        # 檢查是否有空白段落
        if not section_1 or not section_2 or not section_3:
            empty_count += 1
            if empty_count <= 3:  # 只顯示前3筆有問題的
                logger.warning(f"Case {case_id} 有空白段落")

        results.append({
            'case_id': case_id,
            '一、事故發生緣由': section_1,
            '二、原告受傷情形': section_2,
            '三、請求賠償的事實根據': section_3
        })

        if (idx + 1) % 1000 == 0:
            logger.info(f"已處理 {idx + 1} 筆")

    logger.info(f"發現 {empty_count} 筆資料有空白段落")

    # 建立新的 DataFrame
    result_df = pd.DataFrame(results)

    # 儲存
    logger.info(f"儲存至: {output_file}")
    result_df.to_excel(output_file, index=False, sheet_name="律師輸入_三段")

    logger.info("✅ 完成！")

    # 顯示前3筆範例
    print("\n" + "=" * 80)
    print("前3筆範例（保留小標題）：")
    print("=" * 80)
    for i in range(min(3, len(result_df))):
        print(f"\n--- Case {result_df.iloc[i]['case_id']} ---")
        for col in ['一、事故發生緣由', '二、原告受傷情形', '三、請求賠償的事實根據']:
            content = str(result_df.iloc[i][col])
            if content == 'nan' or content == '' or len(content) < 5:
                print(f'\n{col}: [空白或過短]')
            else:
                print(f'\n{col}:\n{content[:200]}...')

if __name__ == "__main__":
    main()
