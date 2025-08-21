#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚合0805版本蒸馏结果脚本
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

def aggregate_json_files(input_dir: str, output_file: str) -> None:
    """聚合指定目录下的所有JSON文件"""
    logger.info(f"🚀 开始从目录 '{input_dir}' 聚合结果...")
    
    if not os.path.exists(input_dir):
        logger.error(f"错误: 输入目录不存在 -> {input_dir}")
        return
    
    all_results = []
    worker_dirs = [d for d in os.listdir(input_dir) if d.startswith('worker_') and os.path.isdir(os.path.join(input_dir, d))]
    
    if not worker_dirs:
        logger.error(f"错误: 在 {input_dir} 中未找到worker目录")
        return
    
    logger.info(f"找到 {len(worker_dirs)} 个worker目录")
    
    for worker_dir in sorted(worker_dirs):
        worker_path = os.path.join(input_dir, worker_dir)
        logger.info(f"处理worker目录: {worker_dir}")
        
        # 查找该worker目录下的所有JSON文件
        json_files = [f for f in os.listdir(worker_path) if f.endswith('.json')]
        
        for json_file in sorted(json_files):
            file_path = os.path.join(worker_path, json_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    all_results.extend(data)
                    logger.info(f"  {json_file}: 添加了 {len(data)} 条记录")
                else:
                    all_results.append(data)
                    logger.info(f"  {json_file}: 添加了 1 条记录")
                    
            except Exception as e:
                logger.error(f"读取文件 {file_path} 失败: {e}")
    
    # 保存聚合结果
    logger.info(f"📊 总共聚合了 {len(all_results)} 条记录")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        logger.success(f"✅ 结果已保存到: {output_file}")
        
        # 输出统计信息
        print("\n📈 统计信息:")
        print(f"总记录数: {len(all_results)}")
        
        # 器官分布统计
        organ_counts = {}
        organ_category_counts = {}
        
        for item in all_results:
            if isinstance(item, dict):
                organ = item.get('inferred_organ', 'Unknown')
                organ_counts[organ] = organ_counts.get(organ, 0) + 1
                
                category = item.get('organ_category', 'Unknown')
                organ_category_counts[category] = organ_category_counts.get(category, 0) + 1
        
        print(f"\n🏥 器官分布 (前10):")
        sorted_organs = sorted(organ_counts.items(), key=lambda x: x[1], reverse=True)
        for organ, count in sorted_organs[:10]:
            print(f"  {organ}: {count}")
        
        print(f"\n📋 器官类别分布:")
        for category, count in organ_category_counts.items():
            print(f"  {category}: {count}")
            
    except Exception as e:
        logger.error(f"保存结果文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="聚合0805版本蒸馏结果")
    parser.add_argument("--input_dir", default="/hy-tmp/output_final_0805", help="输入目录路径")
    parser.add_argument("--output_file", default="/hy-tmp/output_final_0805/final_0805_corpus.json", help="输出文件路径")
    
    args = parser.parse_args()
    
    logger.info("开始聚合0805版本蒸馏结果...")
    aggregate_json_files(args.input_dir, args.output_file)
    logger.success("聚合完成！")

if __name__ == "__main__":
    main() 