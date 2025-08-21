#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON文件转换脚本
将分散的JSON文件转换为RAG系统需要的单一corpus文件
"""

import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
import argparse

def load_json_file(file_path: str) -> Dict[str, Any]:
    """加载单个JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载文件 {file_path} 失败: {e}")
        return None

def extract_records_from_json(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从JSON数据中提取记录"""
    records = []
    
    if not json_data or 'extractions' not in json_data:
        return records
    
    case_id = json_data.get('report_info', {}).get('case_id', 'unknown')
    
    for extraction in json_data['extractions']:
        # 确保所有必需字段都存在
        record = {
            "case_id": case_id,
            "symptom_or_disease": extraction.get('symptom_or_disease', ''),
            "inferred_organ": extraction.get('inferred_organ', ''),
            "suggested_anatomical_parts_to_examine": extraction.get('suggested_anatomical_parts_to_examine', []),
            "evidence_from_report": extraction.get('evidence_from_report', ''),
            "organ_category": extraction.get('organ_category', 'other')
        }
        
        # 添加可选的source_section字段
        if 'source_section' in extraction:
            record['source_section'] = extraction['source_section']
        
        # 验证记录的有效性
        if (record['symptom_or_disease'] and 
            record['inferred_organ'] and 
            record['suggested_anatomical_parts_to_examine']):
            records.append(record)
    
    return records

def convert_json_files_to_corpus(input_dir: str, output_file: str, 
                                start_index: int = None, end_index: int = None) -> None:
    """
    将JSON文件转换为RAG语料库
    
    Args:
        input_dir: 输入JSON文件目录
        output_file: 输出语料库文件路径
        start_index: 起始索引（可选）
        end_index: 结束索引（可选）
    """
    logger.info(f"开始转换JSON文件从 {input_dir} 到 {output_file}")
    
    # 获取所有JSON文件
    json_pattern = os.path.join(input_dir, "report_*_extracted*.json")
    json_files = glob.glob(json_pattern)
    json_files.sort()  # 按文件名排序
    
    logger.info(f"找到 {len(json_files)} 个JSON文件")
    
    # 过滤文件范围
    if start_index is not None or end_index is not None:
        filtered_files = []
        for file_path in json_files:
            filename = os.path.basename(file_path)
            # 提取报告编号
            if filename.startswith('report_') and '_extracted' in filename:
                try:
                    report_num = int(filename.split('_')[1])
                    if start_index is None or report_num >= start_index:
                        if end_index is None or report_num <= end_index:
                            filtered_files.append(file_path)
                except ValueError:
                    continue
        json_files = filtered_files
        logger.info(f"过滤后剩余 {len(json_files)} 个文件")
    
    # 处理所有文件
    all_records = []
    processed_files = 0
    total_extractions = 0
    
    for file_path in json_files:
        logger.info(f"处理文件: {os.path.basename(file_path)}")
        
        json_data = load_json_file(file_path)
        if json_data is None:
            continue
        
        records = extract_records_from_json(json_data)
        all_records.extend(records)
        
        processed_files += 1
        total_extractions += len(records)
        
        if processed_files % 100 == 0:
            logger.info(f"已处理 {processed_files} 个文件，提取 {total_extractions} 条记录")
    
    # 保存语料库
    logger.info(f"保存语料库到 {output_file}")
    logger.info(f"总计: {processed_files} 个文件，{total_extractions} 条记录")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    logger.success(f"语料库转换完成！")
    logger.info(f"输出文件: {output_file}")
    logger.info(f"记录数量: {len(all_records)}")

def analyze_json_structure(input_dir: str, sample_size: int = 5) -> None:
    """分析JSON文件结构"""
    logger.info(f"分析 {input_dir} 中的JSON文件结构")
    
    json_pattern = os.path.join(input_dir, "report_*_extracted*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        logger.error("未找到JSON文件")
        return
    
    # 分析前几个文件
    sample_files = json_files[:sample_size]
    
    total_extractions = 0
    organ_counts = {}
    category_counts = {}
    
    for file_path in sample_files:
        logger.info(f"分析文件: {os.path.basename(file_path)}")
        
        json_data = load_json_file(file_path)
        if json_data is None:
            continue
        
        extractions = json_data.get('extractions', [])
        total_extractions += len(extractions)
        
        for extraction in extractions:
            organ = extraction.get('inferred_organ', 'unknown')
            category = extraction.get('organ_category', 'unknown')
            
            organ_counts[organ] = organ_counts.get(organ, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
    
    logger.info(f"样本分析结果:")
    logger.info(f"  样本文件数: {len(sample_files)}")
    logger.info(f"  总提取数: {total_extractions}")
    logger.info(f"  平均每文件提取数: {total_extractions / len(sample_files):.1f}")
    
    logger.info(f"器官分布:")
    for organ, count in sorted(organ_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {organ}: {count}")
    
    logger.info(f"类别分布:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {category}: {count}")

def main():
    parser = argparse.ArgumentParser(description="将JSON文件转换为RAG语料库")
    parser.add_argument("--input_dir", type=str, required=True, 
                       help="输入JSON文件目录")
    parser.add_argument("--output_file", type=str, required=True,
                       help="输出语料库文件路径")
    parser.add_argument("--start_index", type=int, default=None,
                       help="起始报告索引")
    parser.add_argument("--end_index", type=int, default=None,
                       help="结束报告索引")
    parser.add_argument("--analyze_only", action="store_true",
                       help="仅分析文件结构，不进行转换")
    parser.add_argument("--sample_size", type=int, default=5,
                       help="分析时的样本文件数量")
    
    args = parser.parse_args()
    
    if args.analyze_only:
        analyze_json_structure(args.input_dir, args.sample_size)
    else:
        convert_json_files_to_corpus(
            args.input_dir, 
            args.output_file,
            args.start_index,
            args.end_index
        )

if __name__ == "__main__":
    main() 