#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识蒸馏运行示例
展示如何使用不同的k值运行知识蒸馏
"""

import os
import sys
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_distillation_examples():
    """运行知识蒸馏示例"""
    
    # 示例1: 处理前100个文件（快速测试）
    logger.info("示例1: 处理前100个文件（快速测试）")
    os.system("python scripts/process_dataset.py --k 100 --output knowledge_distillation/results/rag_corpus_test_100.json")
    
    # 示例2: 处理前500个文件（中等规模）
    logger.info("示例2: 处理前500个文件（中等规模）")
    os.system("python scripts/process_dataset.py --k 500 --output knowledge_distillation/results/rag_corpus_test_500.json")
    
    # 示例3: 处理前1000个文件（完整测试）
    logger.info("示例3: 处理前1000个文件（完整测试）")
    os.system("python scripts/process_dataset.py --k 1000 --output knowledge_distillation/results/rag_corpus_test_1000.json")

def run_single_distillation(k: int = 1000, output_name: str = "rag_corpus_1.json"):
    """
    运行单次知识蒸馏
    
    Args:
        k: 处理前k个文件
        output_name: 输出文件名
    """
    output_path = f"knowledge_distillation/results/{output_name}"
    
    logger.info(f"开始处理前{k}个文件...")
    logger.info(f"输出文件: {output_path}")
    
    cmd = f"python scripts/process_dataset.py --k {k} --output {output_path}"
    logger.info(f"执行命令: {cmd}")
    
    result = os.system(cmd)
    
    if result == 0:
        logger.info(f"处理完成！结果保存在: {output_path}")
    else:
        logger.error(f"处理失败，退出码: {result}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="知识蒸馏运行示例")
    parser.add_argument("--mode", choices=["examples", "single"], default="single", 
                       help="运行模式: examples(运行所有示例) 或 single(运行单次)")
    parser.add_argument("--k", type=int, default=1000, help="处理前k个文件 (默认: 1000)")
    parser.add_argument("--output", type=str, default="rag_corpus_1.json", 
                       help="输出文件名 (默认: rag_corpus_1.json)")
    
    args = parser.parse_args()
    
    if args.mode == "examples":
        run_distillation_examples()
    else:
        run_single_distillation(k=args.k, output_name=args.output) 