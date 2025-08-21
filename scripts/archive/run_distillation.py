#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识蒸馏运行脚本
用于从医学文本中提取症状-器官-部位关系
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from knowledge_distillation.extractors.llm_extractor import create_extractor
from knowledge_distillation.processors.data_processor import create_processor
from configs.system_config import get_config, get_data_path, ensure_directories

def setup_logging():
    """设置日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 添加文件日志
    log_file = project_root / "logs" / "distillation.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )

def load_medical_data(input_file: str) -> List[Dict[str, str]]:
    """加载医学数据"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"成功加载 {len(data)} 条医学数据")
        return data
        
    except Exception as e:
        logger.error(f"加载医学数据失败: {e}")
        return []

def run_distillation(input_file: str, 
                    output_file: str,
                    model: str = "deepseek",
                    api_key: str = None,
                    batch_size: int = 10,
                    max_cases: int = None) -> None:
    """
    运行知识蒸馏
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        model: LLM模型类型
        api_key: API密钥
        batch_size: 批处理大小
        max_cases: 最大处理病例数
    """
    logger.info("开始知识蒸馏流程")
    logger.info(f"输入文件: {input_file}")
    logger.info(f"输出文件: {output_file}")
    logger.info(f"使用模型: {model}")
    
    # 加载数据
    raw_data = load_medical_data(input_file)
    if not raw_data:
        logger.error("没有可处理的数据")
        return
    
    # 限制处理数量
    if max_cases and max_cases < len(raw_data):
        raw_data = raw_data[:max_cases]
        logger.info(f"限制处理 {max_cases} 个病例")
    
    # 创建提取器和处理器
    extractor = create_extractor(model=model, api_key=api_key)
    processor = create_processor()
    
    # 处理数据
    logger.info(f"开始处理 {len(raw_data)} 个病例...")
    
    all_results = []
    for i in range(0, len(raw_data), batch_size):
        batch_data = raw_data[i:i + batch_size]
        logger.info(f"处理批次 {i//batch_size + 1}/{(len(raw_data) + batch_size - 1)//batch_size}")
        
        # 准备批次数据
        batch_texts = []
        for item in batch_data:
            batch_texts.append({
                "text": item.get("text", ""),
                "case_id": item.get("case_id", f"case_{len(batch_texts)}"),
                "specialty": item.get("specialty", "general")
            })
        
        # 批量提取
        batch_results = extractor.batch_extract(batch_texts)
        all_results.extend(batch_results)
        
        logger.info(f"批次 {i//batch_size + 1} 完成，成功: {sum(1 for r in batch_results if r.get('success', False))}")
    
    # 处理提取结果
    logger.info("处理提取结果...")
    processed_results = processor.process_extraction_results(all_results)
    
    # 合并多部位提取结果
    logger.info("合并多部位提取结果...")
    for result in processed_results:
        if result.get("extractions"):
            result["extractions"] = processor.merge_multi_part_extractions(result["extractions"])
    
    # 转换为RAG格式
    logger.info("转换为RAG格式...")
    rag_corpus = processor.convert_to_rag_format(processed_results)
    
    # 保存结果
    logger.info("保存结果...")
    processor.save_results(processed_results, output_file)
    
    # 保存RAG语料
    rag_output_file = output_file.replace(".json", "_rag.json")
    processor.save_results(rag_corpus, rag_output_file)
    
    # 分析结果
    logger.info("分析结果...")
    stats = processor.analyze_results(processed_results)
    
    # 输出统计信息
    logger.info("=" * 50)
    logger.info("知识蒸馏完成！")
    logger.info(f"总病例数: {stats['total_cases']}")
    logger.info(f"成功病例数: {int(stats['total_cases'] * stats['success_rate'])}")
    logger.info(f"成功率: {stats['success_rate']:.2%}")
    logger.info(f"总提取数: {stats['total_extractions']}")
    logger.info(f"RAG语料数: {len(rag_corpus)}")
    
    logger.info("\n器官分布:")
    for organ, count in stats['organ_distribution'].items():
        logger.info(f"  {organ}: {count}")
    
    logger.info("\n专科分布:")
    for specialty, count in stats['specialty_distribution'].items():
        logger.info(f"  {specialty}: {count}")
    
    logger.info("\n置信度分布:")
    for confidence, count in stats['confidence_distribution'].items():
        logger.info(f"  {confidence}: {count}")
    
    logger.info(f"\n结果文件:")
    logger.info(f"  提取结果: {output_file}")
    logger.info(f"  RAG语料: {rag_output_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="医学知识蒸馏")
    parser.add_argument("--input", "-i", required=True, help="输入文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    parser.add_argument("--model", "-m", default="deepseek", help="LLM模型类型")
    parser.add_argument("--api-key", help="API密钥")
    parser.add_argument("--batch-size", "-b", type=int, default=10, help="批处理大小")
    parser.add_argument("--max-cases", type=int, help="最大处理病例数")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    # 确保目录存在
    ensure_directories()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        logger.error(f"输入文件不存在: {args.input}")
        return
    
    # 获取API密钥
    api_key = args.api_key
    if not api_key:
        env_var = f"{args.model.upper()}_API_KEY"
        api_key = os.getenv(env_var)
        if not api_key:
            logger.warning(f"未找到API密钥，请设置环境变量 {env_var} 或使用 --api-key 参数")
    
    # 运行蒸馏
    try:
        run_distillation(
            input_file=args.input,
            output_file=args.output,
            model=args.model,
            api_key=api_key,
            batch_size=args.batch_size,
            max_cases=args.max_cases
        )
    except KeyboardInterrupt:
        logger.info("用户中断处理")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

if __name__ == "__main__":
    main() 