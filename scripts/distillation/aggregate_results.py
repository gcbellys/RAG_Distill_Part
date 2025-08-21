#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果聚合脚本
作者: Gemini & CDJ_LP
描述:
该脚本用于将在并行处理中生成的多个独立JSON结果文件，
合并成一个单一的、最终的语料库文件。

执行方法:
python RAG_Evidence4Organ/scripts/aggregate_results.py \
    --input_dir RAG_Evidence4Organ/knowledge_distillation/results/parallel_outputs/ \
    --output_file RAG_Evidence4Organ/data/corpus_inferred.json
"""

import os
import json
import argparse
from typing import List, Dict, Any
from loguru import logger

def aggregate_json_files(input_dir: str, output_file: str):
    """
    遍历目录中的所有worker子目录，并将它们包含的独立JSON文件合并成一个单一的语料库。
    支持通用器官提取结果。
    """
    logger.info(f"🚀 开始从父目录 '{input_dir}' 聚合结果...")
    
    if not os.path.isdir(input_dir):
        logger.error(f"错误: 输入目录不存在 -> {input_dir}")
        return

    all_data: List[Dict[str, Any]] = []
    organ_stats = {}
    
    # 查找所有worker_*子目录
    try:
        worker_dirs = [d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d)) and d.startswith('worker_')]
    except FileNotFoundError:
        logger.error(f"无法访问目录: {input_dir}。请检查路径和权限。")
        return
        
    if not worker_dirs:
        logger.warning(f"在目录 '{input_dir}' 中未找到任何 'worker_*' 子目录进行聚合。")
        return

    logger.info(f"找到了 {len(worker_dirs)} 个worker子目录进行处理。")

    for worker_dir in worker_dirs:
        worker_path = os.path.join(input_dir, worker_dir)
        logger.info(f"正在处理子目录: {worker_dir}...")
        
        result_files = [f for f in os.listdir(worker_path) if f.endswith('_processed.json')]
        
        for filename in result_files:
            file_path = os.path.join(worker_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                        # 统计器官分布
                        for item in data:
                            organ = item.get('inferred_organ', 'Unknown')
                            organ_category = item.get('organ_category', 'unknown')
                            if organ not in organ_stats:
                                organ_stats[organ] = {'count': 0, 'category': organ_category}
                            organ_stats[organ]['count'] += 1
                    else:
                        logger.warning(f"文件 {filename} 的内容不是一个列表，已跳过。")
            except json.JSONDecodeError:
                logger.error(f"解析JSON失败: {filename}，已跳过。")
            except Exception as e:
                logger.error(f"读取文件 {filename} 失败: {e}，已跳过。")

    logger.success(f"聚合完成，总共合并了 {len(all_data)} 条记录。")
    
    # 输出统计信息
    logger.info("📊 器官分布统计:")
    specified_organs = []
    other_organs = []
    
    for organ, stats in sorted(organ_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        category = stats['category']
        count = stats['count']
        if category == 'specified':
            specified_organs.append(f"{organ}: {count}")
        else:
            other_organs.append(f"{organ}: {count}")
    
    if specified_organs:
        logger.info("  📍 指定器官 (5个核心器官):")
        for stat in specified_organs:
            logger.info(f"    {stat}")
    
    if other_organs:
        logger.info("  🌐 其他器官:")
        for stat in other_organs:
            logger.info(f"    {stat}")

    try:
        # 确保输出文件的目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logger.success(f"✅ 最终语料库已成功保存到: {output_file}")
    except Exception as e:
        logger.error(f"保存最终输出文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="合并多个JSON结果文件")
    parser.add_argument("--input_dir", type=str, required=True, help="包含独立JSON文件的输入目录")
    parser.add_argument("--output_file", type=str, required=True, help="最终合并后的JSON文件路径")
    args = parser.parse_args()
    
    aggregate_json_files(args.input_dir, args.output_file)

if __name__ == "__main__":
    main() 