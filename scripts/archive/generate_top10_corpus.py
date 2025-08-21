#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量从报告文件中提取最重要的10个句子，并生成一个语料库JSON文件。
"""
import sys
import os
import json
import time
from pathlib import Path
from loguru import logger
from tqdm import tqdm

# 将项目根目录添加到sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# 正常导入项目模块
from RAG_Evidence4Organ.configs.system_config import MULTI_API_CONFIG
from RAG_Evidence4Organ.knowledge_distillation.extractors.llm_extractor import LLMExtractor

def get_extraction_prompt(report_text: str) -> str:
    """生成用于提取的精确提示词"""
    return f"""
    Please analyze the following medical report. Your task is to act as a medical expert and extract the 10 most important and descriptive sentences that describe diseases, symptoms, or abnormal findings.

    Guidelines:
    - Focus on sentences that provide clear, specific information about the patient's condition.
    - Prioritize primary diagnoses, acute problems, and significant test results.
    - Do NOT extract medication lists, social history, or normal findings unless they are directly explaining a pathology.
    - The output MUST be a JSON object with a single key "top_10_sentences", and its value must be a list of exactly 10 strings.
    - Each string in the list must be a direct quote from the report. Do not summarize or create new sentences.

    Medical Report:
    ---
    {report_text}
    ---

    Now, please extract the top 10 sentences and provide them in the specified JSON format.
    """

def parse_llm_response(response_content: str) -> list | None:
    """尝试解析LLM返回的JSON响应"""
    try:
        # 找到第一个 '{' 和最后一个 '}' 来提取JSON块
        json_start = response_content.find('{')
        json_end = response_content.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = response_content[json_start:json_end]
            parsed_json = json.loads(json_str)
            sentences = parsed_json.get("top_10_sentences")
            if isinstance(sentences, list):
                return sentences
        logger.warning(f"无法从响应中正确解析出 'top_10_sentences' 列表: {response_content}")
        return None
    except json.JSONDecodeError:
        logger.warning(f"未能将响应作为JSON解析: {response_content}")
        return None


def main(start_id: int, end_id: int):
    """
    主函数，执行批量提取任务。
    """
    logger.info(f"🚀 开始批量提取Top 10句子，范围: {start_id}-{end_id}")

    # 1. 初始化提取器
    try:
        api_config = MULTI_API_CONFIG.get("api_1")
        if not api_config:
            logger.error("❌ 在 system_config.py 中未找到 'api_1' 配置。")
            return
        extractor = LLMExtractor(
            model=api_config["model"],
            api_key=api_config["api_key"],
            base_url=api_config["base_url"]
        )
        logger.success("✅ LLM提取器初始化成功。")
    except Exception as e:
        logger.error(f"❌ 初始化LLM提取器失败: {e}")
        return

    # 2. 准备路径和数据结构
    dataset_dir = PROJECT_ROOT / "RAG_Evidence4Organ" / "dataset"
    output_file = PROJECT_ROOT / f"top10_sentences_corpus_{start_id}-{end_id}.json"
    all_results = []
    
    # 3. 循环处理文件
    report_ids = range(start_id, end_id + 1)
    for report_id in tqdm(report_ids, desc="处理报告"):
        report_file_path = dataset_dir / f"report_{report_id}.txt"
        
        if not report_file_path.exists():
            logger.warning(f"⚠️ 报告 {report_id}: 文件未找到，已跳过。")
            continue

        try:
            report_text = report_file_path.read_text(encoding="utf-8")
            prompt = get_extraction_prompt(report_text)
            
            # 调用API
            result = extractor.call_api(prompt)

            if result["success"]:
                sentences = parse_llm_response(result["response"])
                if sentences:
                    all_results.append({
                        "case_id": str(report_id),
                        "sentences": sentences
                    })
                    logger.success(f"✅ 报告 {report_id}: 成功提取 {len(sentences)} 条句子。")
                else:
                    logger.error(f"❌ 报告 {report_id}: 成功调用API但无法解析出有效句子。")
            else:
                logger.error(f"❌ 报告 {report_id}: LLM API调用失败: {result['error']}")
        
        except Exception as e:
            logger.error(f"❌ 报告 {report_id}: 处理过程中发生未知错误: {e}")
        
        # 增加一点延迟避免API过载
        time.sleep(1)

    # 4. 保存结果
    logger.info(f"💾 正在将 {len(all_results)} 条结果保存到文件: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        logger.success(f"🎉 任务完成！语料库已成功保存。")
    except Exception as e:
        logger.error(f"❌ 保存文件失败: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="批量提取医疗报告中的Top 10关键句。")
    parser.add_argument("--start", type=int, default=40000, help="起始报告ID")
    parser.add_argument("--end", type=int, default=41000, help="结束报告ID")
    args = parser.parse_args()
    
    main(args.start, args.end) 