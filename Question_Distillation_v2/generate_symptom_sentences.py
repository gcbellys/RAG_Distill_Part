import os
import sys
import argparse
import json
from loguru import logger
from tqdm import tqdm

# 将项目根目录添加到Python路径中
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from RAG_Evidence4Organ.knowledge_distillation.extractors.llm_extractor import create_extractor
from RAG_Evidence4Organ.configs.system_config import MULTI_API_CONFIG, PROJECT_ROOT
from RAG_Evidence4Organ.configs.model_config import ALLOWED_ORGANS
from RAG_Evidence4Organ.prompts.medical_prompts import get_symptom_sentence_extraction_prompt, get_organ_classification_prompt

def detect_organ_from_text(text: str) -> str:
    """
    根据关键词从文本中检测主要器官。
    使用 ORGAN_MAPPING 以获得更广泛的关键词匹配。
    """
    text_lower = text.lower()
    # 优先匹配更具体的关键词，所以可以按键长排序
    # (虽然在当前场景下影响不大，但这是一个好习惯)
    sorted_keywords = sorted(ORGAN_MAPPING.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword in text_lower:
            return ORGAN_MAPPING[keyword]
            
    return "Unknown"

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从医疗报告中提取症状/发现的完整句子块。")
    parser.add_argument("--start", type=int, required=True, help="起始报告文件编号。")
    parser.add_argument("--end", type=int, required=True, help="结束报告文件编号（包含）。")
    parser.add_argument("--api_key_name", type=str, default="api_1", help="在system_config中要使用的API密钥名称。")
    parser.add_argument("--output_file", type=str, default="symptom_sentence_corpus_test.json", help="输出JSON文件的名称。")
    return parser.parse_args()

def main():
    args = parse_args()
    logger.info(f"🚀 开始提取症状句子，范围: {args.start}-{args.end}")

    # 获取API配置
    if args.api_key_name not in MULTI_API_CONFIG:
        logger.error(f"错误: API密钥 '{args.api_key_name}' 在 system_config.py 中未找到。")
        return
    api_config = MULTI_API_CONFIG[args.api_key_name]

    # 初始化提取器
    try:
        extractor = create_extractor(
            model=api_config["model"],
            api_key=api_config["api_key"],
            base_url=api_config["base_url"]
        )
        logger.success(f"LLM提取器初始化成功，使用模型: {api_config['model']}")
    except Exception as e:
        logger.error(f"初始化LLM提取器失败: {e}")
        return
        
    dataset_dir = PROJECT_ROOT / "RAG_Evidence4Organ" / "dataset"
    all_results = []

    file_range = range(args.start, args.end + 1)
    for report_num in tqdm(file_range, desc="处理报告"):
        report_filename = f"report_{report_num}.txt"
        report_path = dataset_dir / report_filename
        case_id = str(report_num)

        if not report_path.exists():
            logger.warning(f"文件 {report_filename} 不存在，跳过。")
            continue

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_text = f.read()
            
            if not report_text.strip():
                logger.warning(f"文件 {report_filename} 为空，跳过。")
                continue

            # --- STAGE 1: Classify Organ System ---
            classification_prompt = get_organ_classification_prompt(report_text)
            classification_response = extractor.call_api(classification_prompt)

            if not classification_response or not classification_response.get("success"):
                logger.error(f"报告 {case_id}: 器官分类API调用失败。跳过。")
                continue
            
            primary_organ = classification_response["response"].strip().replace('"', '')

            if primary_organ not in ALLOWED_ORGANS:
                logger.info(f"报告 {case_id}: 主要器官为 '{primary_organ}'，不属于目标器官，跳过。")
                continue

            logger.success(f"报告 {case_id}: 已识别为与 '{primary_organ}' 相关，开始提取症状句子。")

            # --- STAGE 2: Extract Sentences using chunking ---
            chunk_num = 1
            report_fully_extracted = False
            while not report_fully_extracted:
                prompt = get_symptom_sentence_extraction_prompt(report_text, chunk_num=chunk_num)
                api_response = extractor.call_api(prompt)

                if not (api_response and api_response.get("success")):
                    logger.error(f"报告 {case_id} (块 {chunk_num}): API调用失败。")
                    break # Stop processing this report

                response_text = api_response["response"].strip()
                
                # Cleanup logic
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.startswith("```"):
                    response_text = response_text[3:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()

                try:
                    extracted_blocks = json.loads(response_text)
                    
                    if not isinstance(extracted_blocks, list):
                        logger.warning(f"报告 {case_id} (块 {chunk_num}): LLM返回了非列表格式的JSON，停止处理此报告。")
                        break

                    if not extracted_blocks: # Empty list means we are done
                        report_fully_extracted = True
                        logger.info(f"报告 {case_id}: LLM在块 {chunk_num} 返回空列表，表示提取完成。")
                        continue

                    # Process the received chunk
                    for block in extracted_blocks:
                        if "original_sentences" in block and isinstance(block["original_sentences"], list) and block["original_sentences"]:
                            block['case_id'] = case_id
                            block['inferred_organ'] = primary_organ
                            all_results.append(block)
                    
                    logger.info(f"报告 {case_id}: 成功处理块 {chunk_num}，提取了 {len(extracted_blocks)} 条新句子块。")
                    chunk_num += 1

                except json.JSONDecodeError:
                    logger.error(f"报告 {case_id} (块 {chunk_num}): 无法解析LLM返回的JSON响应。将尝试请求下一块。")
                    logger.debug(f"原始响应: {response_text}") # Log the faulty response for debugging
                    chunk_num += 1 # Crucial: increment chunk_num to avoid an infinite loop on the same faulty chunk
                    continue # Skip to the next iteration of the while loop

        except Exception as e:
            logger.error(f"处理文件 {report_filename} 时发生未知错误: {e}")

    # 保存最终结果
    output_path = PROJECT_ROOT / "RAG_Evidence4Organ" / args.output_file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.success(f"✅ 提取完成！总共提取了 {len(all_results)} 条句子块。")
        logger.info(f"结果已保存到: {output_path}")
    except IOError as e:
        logger.error(f"无法写入输出文件 {output_path}: {e}")

if __name__ == "__main__":
    main() 