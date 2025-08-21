#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能续传任务生成脚本
作者: Gemini & CDJ_LP
描述:
该脚本用于实现断点续传功能。它会对比目标文件和已完成文件，
找出所有未处理的报告，然后将这些任务平均分配给多个API，
为每个API生成一个专属的任务清单文件。
"""

import os
import sys
import re
import argparse
import random
from typing import List, Set
from loguru import logger

# 添加项目根目录到Python路径，以便导入其他模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from knowledge_distillation.process_worker import natural_sort_key

def get_target_reports(input_dir: str, num_to_process: int) -> List[str]:
    """获取目标处理的报告文件绝对路径列表 (经过自然排序)"""
    logger.info(f"正在从 {input_dir} 获取前 {num_to_process} 个目标报告...")
    try:
        all_files = sorted(
            [f for f in os.listdir(input_dir) if f.endswith(".txt")],
            key=natural_sort_key
        )
        target_files = all_files[:num_to_process]
        target_paths = [os.path.abspath(os.path.join(input_dir, f)) for f in target_files]
        logger.success(f"已确定 {len(target_paths)} 个目标文件。")
        return target_paths
    except Exception as e:
        logger.error(f"获取目标报告失败: {e}")
        return []

def get_completed_reports(results_dir: str) -> Set[str]:
    """扫描结果目录，获取所有已成功处理的报告的基础文件名（不含扩展名）"""
    logger.info(f"正在从 {results_dir} 扫描已完成的处理结果...")
    completed_basenames: Set[str] = set()
    if not os.path.isdir(results_dir):
        logger.warning(f"结果目录 {results_dir} 不存在，认为已完成任务为0。")
        return completed_basenames
        
    try:
        worker_dirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d)) and d.startswith('worker_')]
        for worker_dir in worker_dirs:
            worker_path = os.path.join(results_dir, worker_dir)
            processed_files = [f for f in os.listdir(worker_path) if f.endswith('_processed.json')]
            for processed_file in processed_files:
                # 从 'report_xxx_processed.json' 中提取 'report_xxx'
                basename = processed_file.replace('_processed.json', '')
                completed_basenames.add(basename)
        logger.success(f"扫描完成，共找到 {len(completed_basenames)} 个已处理的报告。")
        return completed_basenames
    except Exception as e:
        logger.error(f"扫描结果目录失败: {e}")
        return completed_basenames

def main():
    parser = argparse.ArgumentParser(description="生成断点续传的任务清单文件")
    parser.add_argument("--input_dir", type=str, required=True, help="包含原始.txt报告的目录")
    parser.add_argument("--results_dir", type=str, required=True, help="包含worker子目录的结果目录 (e.g., result_new)")
    parser.add_argument("--task_output_dir", type=str, required=True, help="存放生成的任务清单文件的目录")
    parser.add_argument("--total_to_process", type=int, required=True, help="原始的目标处理总数 (e.g., 10000)")
    parser.add_argument("--api_keys", nargs='+', required=True, help="要分配任务的API key名称列表 (e.g., api_1 api_4 api_5)")
    args = parser.parse_args()

    # 1. 获取目标列表和已完成列表
    target_paths = get_target_reports(args.input_dir, args.total_to_process)
    completed_basenames = get_completed_reports(args.results_dir)

    # 2. 计算待办事项列表
    pending_paths = []
    for path in target_paths:
        basename = os.path.splitext(os.path.basename(path))[0]
        if basename not in completed_basenames:
            pending_paths.append(path)
    
    if not pending_paths:
        logger.success("🎉 恭喜！所有任务均已完成，无需续传。")
        return

    logger.info(f"计算完成，有 {len(pending_paths)} 个报告需要继续处理。")

    # 3. 分配任务
    random.shuffle(pending_paths) # 打乱任务，避免所有失败任务集中在某个worker
    
    num_apis = len(args.api_keys)
    chunk_size = (len(pending_paths) + num_apis - 1) // num_apis # 向上取整的除法

    os.makedirs(args.task_output_dir, exist_ok=True)

    for i, api_key_name in enumerate(args.api_keys):
        start = i * chunk_size
        end = start + chunk_size
        task_chunk = pending_paths[start:end]
        
        if not task_chunk:
            continue

        task_filename = os.path.join(args.task_output_dir, f"task_{api_key_name}.txt")
        try:
            with open(task_filename, 'w', encoding='utf-8') as f:
                for path in task_chunk:
                    f.write(path + '\n')
            logger.success(f"已为 {api_key_name} 生成任务清单: {task_filename}，包含 {len(task_chunk)} 个任务。")
        except Exception as e:
            logger.error(f"写入任务清单 {task_filename} 失败: {e}")

if __name__ == "__main__":
    main() 