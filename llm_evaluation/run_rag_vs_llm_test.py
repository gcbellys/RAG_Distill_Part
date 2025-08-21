#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 系统 vs 独立LLM 对比测试脚本 (升级版)
作者: Gemini & CDJ_LP
描述:
该脚本接收一个英文医学问题，并行获取RAG答案和多个独立LLM的答案，
并将所有相关信息（问题、prompt、RAG结果、各LLM结果）
完整地保存到一个结构化的JSON文件中，以便于分析和评估。

执行方法:
python RAG_Evidence4Organ/llm_evaluation/run_rag_vs_llm_test.py --question "A sample English medical question"
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List

# 将项目根目录添加到Python路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from loguru import logger
from RAG_Evidence4Organ.configs.system_config import MULTI_API_CONFIG, RAG_CONFIG
from RAG_Evidence4Organ.configs.evaluation_llm_config import EVAL_LLM_CONFIG
from RAG_Evidence4Organ.configs.model_config import ORGAN_ANATOMY_STRUCTURE
from RAG_Evidence4Organ.knowledge_distillation.extractors.llm_extractor import LLMExtractor
# from RAG_Evidence4Organ.rag_system.query_handler import RAGQueryHandler
# from RAG_Evidence4Organ.rag_system.embedding_loader import EmbeddingLoader
# from RAG_Evidence4Organ.rag_system.vector_store_handler import VectorStoreHandler
# from RAG_Evidence4Organ.rag_system.llm_qa_handler import LLMQAHandler
# 导入新的RAG服务
from RAG_Evidence4Organ.rag_system.api.main import RAGService

# def get_rag_answer(question: str, query_handler: RAGQueryHandler) -> Dict[str, Any]:
#     """通过RAG系统获取答案"""
#     logger.info("... 正在通过RAG系统查询 ...")
#     try:
#         result = query_handler.handle_query(question)
#         logger.success("✅ RAG系统查询成功。")
#         return result
#     except Exception as e:
#         logger.error(f"❌ RAG系统查询失败: {e}")
#         return {"error": str(e)}

def get_structured_prompt_template() -> str:
    """构建包含规范化器官结构的严格Prompt模板。"""
    # 转义JSON中的花括号，以便它们在.format()中被当作文字处理
    structure_json_escaped = json.dumps(ORGAN_ANATOMY_STRUCTURE, indent=2).replace("{", "{{").replace("}", "}}")
    
    system_prompt_template = f"""You are an expert radiologist. Your task is to analyze a clinical query based on the provided context and determine which organ and specific anatomical structures should be examined.

--- Retrieved Knowledge ---
{{context_docs}}
--- End Retrieved Knowledge ---

You MUST follow these rules:
1.  First, provide a brief "Symptom Analysis".
2.  Second, identify the primary "Organ" to be examined from the keys in the provided JSON structure.
3.  Third, from the list of anatomical structures corresponding to that organ in the JSON, select the specific "Anatomical Structures" that require examination.
4.  Your final output MUST be a single JSON object with three keys: "Symptom Analysis", "Organ", and "Anatomical Structures". The value for "Anatomical Structures" must be a list of strings.
5.  The organ and structure names you choose MUST EXACTLY match the names provided in the JSON structure below. Do not invent new names or use synonyms.

Here is the authoritative list of organs and their anatomical structures:
{structure_json_escaped}

--- Clinical Query ---
{{query}}
--- End Clinical Query ---

Please provide your analysis in the specified JSON format.
"""
    return system_prompt_template

def get_rag_answer(question: str, rag_service: RAGService, structured_prompt_template: str) -> Dict[str, Any]:
    """通过RAG系统获取答案"""
    logger.info("... 正在通过RAG系统查询 ...")
    try:
        # 使用新的服务来处理查询, 并传入新的prompt模板
        result = rag_service.answer_query(question, custom_qa_prompt_template=structured_prompt_template)
        logger.success("✅ RAG系统查询成功。")
        return result
    except Exception as e:
        logger.error(f"❌ RAG系统查询失败: {e}")
        return {"error": str(e)}

def get_direct_llm_answers(question: str, llm_configs: Dict[str, Any], structured_prompt_template: str) -> List[Dict[str, Any]]:
    """直接从多个LLM获取答案，并包含prompt"""
    logger.info("... 正在直接向多个LLM查询 ...")
    direct_answers = []
    # 为直接调用LLM格式化prompt，不提供上下文
    direct_llm_prompt = structured_prompt_template.format(
        context_docs="N/A. Please rely on your general knowledge.",
        query=question
    )

    for api_name, config in llm_configs.items():
        logger.info(f"  - 正在查询API: '{api_name}' ({config.get('model')})...")
        api_result = {
            "api_name": api_name,
            "model": config.get('model', 'N/A'),
            "answer": None,
            "prompt": direct_llm_prompt, # 保存最终发送的完整prompt
            "error": None
        }
        try:
            extractor = LLMExtractor(
                model=config["model"],
                api_key=config["api_key"],
                base_url=config["base_url"]
            )
            
            result = extractor.call_api(direct_llm_prompt)

            if result["success"]:
                api_result["answer"] = result["response"]
            else:
                api_result["error"] = result["error"]
        except Exception as e:
            api_result["error"] = str(e)
            logger.error(f"  - 查询API '{api_name}' 失败: {e}")
        
        direct_answers.append(api_result)

    logger.success("✅ 所有独立LLM查询完成。")
    return direct_answers

def save_results_to_json(output_dir: Path, data: Dict[str, Any]):
    """将结果保存到JSON文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用时间戳创建唯一文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.json"
    
    file_path = output_dir / filename
    
    logger.info(f"💾 正在将测试结果保存到: {file_path}")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.success("✅ 结果文件保存成功。")
    except Exception as e:
        logger.error(f"❌ 保存结果文件失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="RAG系统 vs 独立LLM 对比测试工具 (升级版)")
    parser.add_argument("--question", type=str, required=True, help="要测试的英文医学问题")
    args = parser.parse_args()

    logger.info("🚀 启动对比测试流程...")
    
    # 最终结果的输出目录
    output_dir = PROJECT_ROOT / "RAG_output"

    # 准备新的、严格的prompt模板
    structured_prompt_template = get_structured_prompt_template()

    # 1. 初始化RAG服务
    try:
        logger.info("正在初始化RAG服务...")
        rag_service = RAGService()
        logger.success("✅ RAG服务初始化完毕。")
    except Exception as e:
        logger.error(f"❌ 初始化RAG服务失败: {e}")
        return

    # 2. 获取答案
    rag_answer = get_rag_answer(args.question, rag_service, structured_prompt_template)
    direct_llm_answers = get_direct_llm_answers(args.question, EVAL_LLM_CONFIG, structured_prompt_template)
    
    # 3. 准备要保存的完整数据结构
    final_result = {
        "question": args.question,
        "rag_result": rag_answer,
        "direct_llm_results": direct_llm_answers
    }
    
    # 4. 保存结果到JSON文件
    save_results_to_json(output_dir, final_result)
    
    logger.success("🎉 对比测试完成！")


if __name__ == "__main__":
    main() 