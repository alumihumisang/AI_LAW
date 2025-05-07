# ts_retrieve_main.py
import sys
import time
import os
import re
from typing import List, Dict
import traceback
from dotenv import load_dotenv
from ts_retrieval_system import RetrievalSystem
from ts_prompt import get_compensation_prompt_part3
from ts_define_case_type import get_case_type

def extract_calculate_tags(text: str) -> Dict[str, float]:
    """
    Extract and calculate the sum of values inside <calculate> </calculate> tags.
    
    Args:
        text: Text containing <calculate> </calculate> tags
        
    Returns:
        Dictionary mapping plaintiff identifiers to their total compensation amounts
    """
    print(f"\n start of calculate func")
    # Find all <calculate> </calculate> tags
    pattern = r'<calculate>(.*?)</calculate>'
    matches = re.findall(pattern, text)
    print(f"找到 {len(matches)} 個標籤內容")

    sums = {}
    default_count = 0
    
    for match in matches:
        # First try to find "原告X" pattern
        plaintiff_pattern = r'原告(\w+)'
        plaintiff_match = re.search(plaintiff_pattern, match)
        
        plaintiff_id = "default"
        
        if plaintiff_match:
            # Found "原告X" format
            plaintiff_id = plaintiff_match.group(1)
        else:
            # Try to find a name at the beginning (without "原告" prefix)
            name_pattern = r'^(\w+)'
            name_match = re.search(name_pattern, match.strip())
            
            if name_match and not name_match.group(1).isdigit():
                plaintiff_id = name_match.group(1)
            else:
                # This is a default tag
                if "default" in sums:
                    # We already have a default, create a numbered default
                    default_count += 1
                    plaintiff_id = f"原告{default_count}"
                # else use "default" as is
        
        # Extract and sum all numbers
        number_pattern = r'\d+'
        numbers = re.findall(number_pattern, match)
        
        if numbers:
            try:
                total = sum(float(num) for num in numbers)
                
                # Handle case where this plaintiff ID already exists
                if plaintiff_id in sums:
                    default_count += 1
                    plaintiff_id = f"原告{default_count}"
                
                sums[plaintiff_id] = total
                print(f"計算 {plaintiff_id}: {total}")
            except ValueError:
                print(f"警告: 無法計算標籤內的金額: {match}")
    
    # Handle case where all tags are defaults - rename them to 原告1, 原告2, etc.
    if "default" in sums and len(matches) > 1:
        default_value = sums["default"]
        del sums["default"]
        
        # Only add it back if there isn't already an 原告1
        if "原告1" not in sums:
            sums["原告1"] = default_value
        else:
            sums[f"原告{default_count+1}"] = default_value
    
    print(f"最終計算結果: {sums}")
    print(f"\n end of calculate func")
    print("========== DEBUG: 提取計算標籤結束 ==========\n")
    return sums

def main():
    """Main function to run the legal document retrieval system"""
    start_time = time.time()
    retrieval_system = None
    
    try:
        print("初始化檢索系統...")
        # Initialize retrieval system
        retrieval_system = RetrievalSystem()
        
        # Get user query
        print("\n請輸入 User Query (請貼上完整的律師回覆文本，格式需包含「一、二、三、」三個部分)")
        print("輸入完畢後按 Enter 再輸入 'q' 或 'quit' 結束:")
        user_input_lines = []
        while True:
            line = input()
            if line.lower() in ['q', 'quit']:
                break
            user_input_lines.append(line)
            
        user_query = "\n".join(user_input_lines)
        query_sections = retrieval_system.split_user_query(user_query)
        
        if not user_query.strip():
            print("未輸入查詢內容，程序結束")
            return
        
        # Choose search type
        print("\n請選擇搜尋類型:")
        print("1: 使用 'full' 文本進行搜尋")
        print("2: 使用 'fact' 文本進行搜尋")
        
        search_type_choice = input("輸入 1 或 2: ").strip()
        
        if search_type_choice == '1':
            search_type = "full"
        elif search_type_choice == '2':
            search_type = "fact"
        else:
            print("無效選擇，程序結束")
            return
        
        # Choose k for top-k
        try:
            k = int(input("\n請輸入要搜尋的 Top-K 數量: ").strip())
            if k <= 0:
                print("K 必須大於 0，程序結束")
                return
        except ValueError:
            print("無效的 K 值，程序結束")
            return
        
        # Choose whether to include conclusion
        print("\n請選擇要抓取的內容:")
        print("1: 只抓取 'used_law'")
        print("2: 抓取 'used_law' 和 'conclusion'")
        
        include_conclusion_choice = input("輸入 1 或 2: ").strip()
        
        if include_conclusion_choice == '1':
            include_conclusion = False
        elif include_conclusion_choice == '2':
            include_conclusion = True
        else:
            print("無效選擇，程序結束")
            return
        

        print("\n處理用戶查詢分类...")
        # Get case type from the query
        print("判斷案件類型...")
        
        case_type, plaintiffs_info = get_case_type(user_query)
        print(f"案件類型: {case_type}")

        # Search Elasticsearch
        print(f"\n在 Elasticsearch 中搜索 '{search_type}' 類型的 Top {k} 個文檔...")
        search_results = retrieval_system.search_elasticsearch(user_query, search_type, k, case_type)
        
        if not search_results:
            print("未找到相符的文檔，程序結束")
            return
        
        # Print search results
        print("\n搜索結果:")
        for i, result in enumerate(search_results):
            print(f"{i+1}. Case ID: {result['case_id']}, 相似度分數: {result['score']:.4f}")
            print(f"   Chunk ID: {result['chunk_id']}, 類型: {result['text_type']}")
            # Print a preview of the text
            preview = result['text'][:100].replace('\n', ' ') + "..." if len(result['text']) > 100 else result['text'].replace('\n', ' ')
            print(f"   Text: {preview}")
            print()
        
        # Extract case IDs
        case_ids = [result['case_id'] for result in search_results]
        print(f"找到的 Case IDs: {case_ids}")
        
        # Get the most similar case (first result)
        most_similar_case_id = search_results[0]['case_id']
        print(f"\n獲取最相似案件 (Case ID: {most_similar_case_id}) 的完整起訴狀...")
        
        # Get full indictment text from Neo4j for the most similar case
        reference_indictment = retrieval_system.get_indictment_from_neo4j(most_similar_case_id)
        
        if not reference_indictment:
            print("警告: 無法獲取參考案件的起訴狀，將使用標準生成流程")
            reference_parts = {
                "fact_text": "",
                "law_text": "",
                "compensation_text": "",
                "conclusion_text": ""
            }
        else:
            # Split the indictment into parts
            print("分割參考案件起訴狀...")
            reference_parts = retrieval_system.split_indictment_text(reference_indictment)
            print("參考案件分割完成")
        
        # Get laws from Neo4j
        print("\n從 Neo4j 獲取相關法條...")
        laws = retrieval_system.get_laws_from_neo4j(case_ids)
        
        if not laws:
            print("警告: 未找到相關法條")
            laws = []
        
        # Count law occurrences
        law_counts = retrieval_system.count_law_occurrences(laws)
        print("\n法條出現頻率:")
        for law, count in sorted(law_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"法條 {law}: 出現 {count} 次")
        
        # Choose threshold j
        try:
            j = int(input(f"\n請輸入法條保留閾值 (出現次數 >= j): ").strip())
            if j <= 0:
                print("閾值必須大於 0，設置為 1")
                j = 1
        except ValueError:
            print("無效的閾值，設置為 1")
            j = 1
        
        # Filter laws by occurrence threshold
        filtered_law_numbers = retrieval_system.filter_laws_by_occurrence(law_counts, j)
        print(f"\n符合出現次數 >= {j} 的法條: {filtered_law_numbers}")
        
        print("\n進行法條適用性檢查...")
        # Generate laws by keyword mapping
        print("使用關鍵詞映射生成可能適用的法條...")
        keyword_laws = retrieval_system.get_laws_by_keyword_mapping(
            query_sections['accident_facts'], 
            query_sections['injuries'],
            query_sections['compensation_facts']
        )
        print(f"關鍵詞映射生成的法條: {keyword_laws}")

        # Compare with filtered laws
        missing_laws = [law for law in keyword_laws if law not in filtered_law_numbers]
        extra_laws = [law for law in filtered_law_numbers if law not in keyword_laws]

        print(f"可能缺少的法條: {missing_laws}")
        print(f"可能多餘的法條: {extra_laws}")

        # Check each missing law
        for law_number in missing_laws:
            print(f"\n檢查缺少的法條 {law_number}...")
            # Get law content from Neo4j
            law_content = ""
            with retrieval_system.neo4j_driver.session() as session:
                query = """
                MATCH (l:law_node {number: $number})
                RETURN l.content AS content
                """
                result = session.run(query, number=law_number)
                record = result.single()
                if record and record.get("content"):
                    law_content = record["content"]
            
            if not law_content:
                print(f"無法獲取法條 {law_number} 的內容，跳過檢查")
                continue
            
            # Check if the law is applicable
            check_result = retrieval_system.check_law_content(
                query_sections['accident_facts'],
                query_sections['injuries'],
                law_number,
                law_content
            )
            
            print(f"法條 {law_number} 檢查結果: {check_result['result']}")
            print(f"原因: {check_result['reason']}")
            
            # Add to filtered laws if applicable
            if check_result['result'] == 'pass':
                print(f"添加法條 {law_number} 到適用法條列表")
                filtered_law_numbers.append(law_number)
                # Sort the list again
                filtered_law_numbers = sorted(filtered_law_numbers)

        # Check each extra law
        for law_number in extra_laws:
            print(f"\n檢查可能多餘的法條 {law_number}...")
            # Get law content
            law_content = ""
            with retrieval_system.neo4j_driver.session() as session:
                query = """
                MATCH (l:law_node {number: $number})
                RETURN l.content AS content
                """
                result = session.run(query, number=law_number)
                record = result.single()
                if record and record.get("content"):
                    law_content = record["content"]
            
            if not law_content:
                print(f"無法獲取法條 {law_number} 的內容，跳過檢查")
                continue
            
            # Check if the law is applicable
            check_result = retrieval_system.check_law_content(
                query_sections['accident_facts'],
                query_sections['injuries'],
                law_number,
                law_content
            )
            
            print(f"法條 {law_number} 檢查結果: {check_result['result']}")
            print(f"原因: {check_result['reason']}")
            
            # Remove from filtered laws if not applicable
            if check_result['result'] == 'fail':
                print(f"從適用法條列表中移除法條 {law_number}")
                filtered_law_numbers.remove(law_number)
        # Filter out duplicates and sort
        filtered_law_numbers = sorted(list(set(filtered_law_numbers)))
        print(f"\n最終適用法條列表: {filtered_law_numbers}")

        # Get law contents
        law_contents = [] 
        if filtered_law_numbers:
            law_contents = retrieval_system.get_law_contents(filtered_law_numbers)
            print("\n獲取到的法條內容:")
            for law in law_contents:
                print(f"法條 {law['number']}: {law['content']}")
        
        # Get conclusions if requested
        conclusions = []
        average_compensation = 0.0
        
        if include_conclusion:
            print("\n從 Neo4j 獲取結論文本...")
            conclusions = retrieval_system.get_conclusions_from_neo4j(case_ids)
            
            if not conclusions:
                print("警告: 未找到結論文本")
            else:
                # Calculate average compensation
                average_compensation = retrieval_system.calculate_average_compensation(conclusions)
                print(f"\n平均賠償金額: {average_compensation:.2f} 元")
                print("提取的賠償金額:")
                for i, conclusion in enumerate(conclusions):
                    amount = retrieval_system.extract_compensation_amount(conclusion["conclusion_text"])
                    if amount:
                        print(f"Case ID {conclusion['case_id']}: {amount:.2f} 元")
                    else:
                        print(f"Case ID {conclusion['case_id']}: 無法提取賠償金額")
        
        # Process user query
        print("\n處理用戶查詢...")
        # Check if query was split correctly
        if not query_sections["accident_facts"]:
            print("警告: 無法正確分割查詢中的事故事實部分")
        if not query_sections["injuries"]:
            print("警告: 無法正確分割查詢中的受傷情形部分")
        if not query_sections["compensation_facts"]:
            print("警告: 無法正確分割查詢中的賠償事實部分")
        
        # Generate summary for quality check
        print("\n生成案件摘要以供質量檢查...")
        case_summary = retrieval_system.generate_case_summary(
            query_sections['accident_facts'], 
            query_sections['injuries']
        )
        print("\n案件摘要:")
        print(case_summary)
        
        # Generate first part with LLM using loop for quality control
        print("\n生成第一部分 (事故事實)...")
        max_attempts = 5
        first_part = None
        
        for attempt in range(1, max_attempts + 1):
            print(f"\n正在進行第 {attempt} 次嘗試生成事故事實...")
            print(f"query_sections['accident_facts']: {query_sections['accident_facts']}")
            print(f"reference_parts['fact_text']: {reference_parts['fact_text']}")
            first_part = retrieval_system.generate_facts(
                query_sections['accident_facts'],
                reference_parts['fact_text']
            )
            print("\n生成的事故事實:")
            print(first_part)
            first_part = retrieval_system.clean_facts_part(first_part)
            print("\n清理後的fact:")
            print(first_part)
            # Check quality
            print("\n檢查生成質量...")
            quality_check = retrieval_system.check_fact_quality(first_part, case_summary)
            print(f"質量檢查結果: {quality_check['result']}")
            print(f"原因: {quality_check['reason']}")
            
            if quality_check['result'] == 'pass':
                print("質量檢查通過，繼續下一步")
                break
                
            if attempt == max_attempts:
                print(f"警告: 達到最大嘗試次數 ({max_attempts})，使用最後一次生成的結果")
        
        # Generate hardcoded law section
        law_section = "二、按「"
        if law_contents:
            for i, law in enumerate(law_contents):
                content = law["content"]
                if "：" in content:
                    content = content.split("：")[1].strip()
                elif ":" in content:
                    content = content.split(":")[1].strip()
                
                if i > 0:
                    law_section += "、「"
                law_section += content
                law_section += "」"
            
            law_section += "民法第"
            for i, law in enumerate(law_contents):
                if i > 0:
                    law_section += "、第"
                law_section += law["number"]
                law_section += "條"
            
            law_section += "分別定有明文。查被告因上開侵權行為，使原告受有下列損害，依前揭規定，被告應負損害賠償責任："
        else:
            law_section += "NO LAW"
        
        # Compensation generation with unified loop approach
        print("\n生成賠償部分...")
        
        compensation_part1 = None
        compensation_part2 = None
        compensation_part3 = None
        compensation_sums = None
        final_compensation = None     
        
        # Generate part 1
        print("\n生成第一部分 (損害賠償項目)...")
        compensation_part1 = None
        part1_success = False

        for part1_attempt in range(1, 6):  # max 3 attempts for part 1
            print(f"\n正在進行第 {part1_attempt} 次嘗試生成賠償項目...")
            
            compensation_part1 = retrieval_system.generate_compensation_part1(
                query_sections['injuries'],
                query_sections['compensation_facts'],
                include_conclusion,
                average_compensation,
                case_type,
                plaintiffs_info
            )
            
            print("\n========== DEBUG: 第一部分賠償生成結果 ==========")
            print(f"compensation_part1: {compensation_part1}")
            print("========== DEBUG 結束 ==========\n")
            
            compensation_part1 = retrieval_system.clean_compensation_part(compensation_part1)
            
            # Check quality
            print("\n檢查賠償項目質量...")
            quality_check = retrieval_system.check_compensation_part1(
                compensation_part1, 
                query_sections['injuries'],
                query_sections['compensation_facts'],
                plaintiffs_info
            )
            
            print(f"質量檢查結果: {quality_check['result']}")
            print(f"原因: {quality_check['reason']}")
            
            if quality_check['result'] == 'pass':
                print("質量檢查通過，繼續下一步")
                part1_success = True
                break
                
            if part1_attempt == 3:
                print(f"警告: 達到最大嘗試次數 (3)，使用最後一次生成的賠償項目")
        
        # Generate part 2
        print("\n生成第二部分 (計算標籤)...")
        compensation_part2 = None
        part2_success = False
        for part2_attempt in range(1, 4):  # max 3 attempts for part 2
            print(f"\n正在進行第 {part2_attempt} 次嘗試生成計算標籤...")
            
            compensation_part2 = retrieval_system.generate_compensation_part2(compensation_part1, plaintiffs_info)
            
            print("\n========== DEBUG: 計算標籤生成結果 ==========")
            print(compensation_part2)
            calc_tags = re.findall(r'<calculate>.*?</calculate>', compensation_part2)
            print(f"找到的計算標籤數量: {len(calc_tags)}")
            for i, tag in enumerate(calc_tags):
                print(f"標籤 {i+1}: {tag}")
            print("========== DEBUG 結束 ==========\n")
            
            # Check quality
            print("\n檢查計算標籤質量...")
            quality_check = retrieval_system.check_calculation_tags(compensation_part1, compensation_part2)
            print(f"質量檢查結果: {quality_check['result']}")
            print(f"原因: {quality_check['reason']}")
            
            if quality_check['result'] == 'pass':
                print("質量檢查通過，繼續下一步")
                part2_success = True
                break
                
            if part2_attempt == 3:
                print(f"警告: 達到最大嘗試次數 (3)，使用最後一次生成的計算標籤")
        # Continue with extracting and calculating sums from the tags
        # Extract and calculate sums from the tags
        print("\n提取並計算賠償金額...")
        compensation_sums = extract_calculate_tags(compensation_part2)
        
        # Print extracted sums
        for plaintiff, amount in compensation_sums.items():
            if plaintiff == "default":
                print(f"總賠償金額: {amount:.2f} 元")
            else:
                print(f"[原告{plaintiff}]賠償金額: {amount:.2f} 元")
        
        # Format the compensation totals for part 3
        summary_totals = []
        for plaintiff, amount in compensation_sums.items():
            if plaintiff == "default":
                summary_totals.append(f"總計{amount:.0f}元")
            else:
                summary_totals.append(f"應賠償[原告{plaintiff}]之損害，總計{amount:.0f}元")
        summary_format = "；".join(summary_totals)
        
        # Inner loop - up to 3 attempts for part 3 with quality check
        print("\n生成第三部分 (綜上所陳)...")
        compensation_part3 = None
        part3_success = False
        
        for part3_attempt in range(1, 6):  # max 6 attempts for part 3
            print(f"\n正在進行第 {part3_attempt} 次嘗試生成總結...")
            
            compensation_part3 = retrieval_system.generate_compensation_part3(compensation_part1, summary_format, plaintiffs_info)
            
            print(f"COMPENSATION_PART3 BEFORE QUALITY CHECK AND BEFORE CLEAN:\n {compensation_part3}")
            compensation_part3 = retrieval_system.clean_conclusion_part(compensation_part3)
            # Extract the part after "綜上所陳" or "綜上所述"
            summary_section = ""
            if "綜上所陳" in compensation_part3:
                summary_section = compensation_part3[compensation_part3.find("綜上所陳"):]
            elif "綜上所述" in compensation_part3:
                summary_section = compensation_part3[compensation_part3.find("綜上所述"):]
            
            # Check if all amounts from compensation_sums appear in the summary section
            print("\n檢查總結中是否包含所有賠償金額...")
            check_result = retrieval_system.check_amounts_in_summary(summary_section, compensation_sums)
            print(f"檢查結果: {check_result['result']}")
            print(f"原因: {check_result['reason']}")
            
            if check_result['result'] == 'pass':
                print("檢查通過，總結中包含所有賠償金額")
                part3_success = True
                break
            
            if part3_attempt == 5: # Changed from 3 to 5 to match the loop range
                print(f"警告: 達到最大嘗試次數 (5)，使用最後一次生成的總結")
        
        # Combine parts for final check
        final_compensation = f"{compensation_part1}\n\n{compensation_part3}"
        
        
        # Combine all parts
        final_response = f"{first_part}\n\n{law_section}\n\n{final_compensation}"
        final_response = retrieval_system.remove_special_chars(final_response)
        # Print final response
        print("\n========== 最終起訴狀 ==========\n")
        print(final_response)
        print("\n========== 起訴狀結束 ==========\n")
        
    except Exception as e:
        print(f"執行過程中發生錯誤: {str(e)}")
        traceback.print_exc()
    finally:
        if retrieval_system:
            retrieval_system.close()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        
        print(f"\n執行時間: {hours}h {minutes}m {seconds}s")

if __name__ == "__main__":
    main()