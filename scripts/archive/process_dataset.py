#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集处理脚本
使用知识蒸馏模块处理源数据集的前1000条记录
"""

import os
import json
import glob
from typing import List, Dict, Any
from loguru import logger

# 添加项目根目录到路径
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_distillation.extractors.llm_extractor import LLMExtractor
from knowledge_distillation.processors.data_processor import DataProcessor
from configs.system_config import get_config

class DatasetProcessor:
    """数据集处理器"""
    
    def __init__(self, dataset_path: str, output_path: str, k: int = 1000):
        """
        初始化数据集处理器
        
        Args:
            dataset_path: 源数据集路径
            output_path: 输出文件路径
            k: 处理前k个文件
        """
        self.dataset_path = dataset_path
        self.output_path = output_path
        self.k = k
        
        # 初始化提取器和处理器
        self.extractor = LLMExtractor(model="deepseek")
        self.processor = DataProcessor()
        
        # 加载配置
        self.config = get_config("system")
        
    def load_dataset_files(self) -> List[Dict[str, str]]:
        """
        加载数据集文件
        
        Returns:
            文件列表，每个元素包含case_id和content
        """
        logger.info(f"正在加载数据集文件: {self.dataset_path}")
        
        # 获取所有txt文件
        pattern = os.path.join(self.dataset_path, "*.txt")
        files = glob.glob(pattern)
        
        # 按数字顺序排序文件名
        def extract_number(filename):
            basename = os.path.basename(filename)
            number_str = basename.replace("report_", "").replace(".txt", "")
            try:
                return int(number_str)
            except ValueError:
                return float('inf')  # 非数字文件名排在最后
        
        files.sort(key=extract_number)  # 按数字顺序排序
        
        logger.info(f"找到 {len(files)} 个文件")
        
        dataset_entries = []
        for i, file_path in enumerate(files[:self.k]):
            try:
                # 从文件名提取case_id
                filename = os.path.basename(file_path)
                case_id = filename.replace(".txt", "")
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                dataset_entries.append({
                    "case_id": case_id,
                    "content": content
                })
                
                if (i + 1) % 100 == 0:
                    logger.info(f"已加载 {i + 1} 个文件")
                    
            except Exception as e:
                logger.error(f"加载文件 {file_path} 失败: {str(e)}")
                continue
        
        logger.info(f"成功加载 {len(dataset_entries)} 个文件")
        return dataset_entries
    
    def extract_medical_info(self, entries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        提取医学信息并逐个保存
        
        Args:
            entries: 数据集条目列表
            
        Returns:
            提取结果列表
        """
        logger.info("开始提取医学信息...")
        
        results = []
        for i, entry in enumerate(entries):
            try:
                logger.info(f"处理第 {i+1}/{len(entries)} 个文件: {entry['case_id']}")
                
                # 使用LLM提取器提取信息
                extraction_result = self.extractor.extract_medical_info(
                    text=entry['content'],
                    case_id=entry['case_id'],
                    specialty="general"
                )
                
                current_extractions = []
                if extraction_result.get("success", False):
                    extractions = extraction_result.get("extractions", [])
                    
                    # 为每个提取结果添加case_id
                    for extraction in extractions:
                        extraction["case_id"] = entry['case_id']
                        # Add original_organ field to match target format
                        extraction["original_organ"] = extraction.get("organ", "")
                        
                        # Ensure all fields are in English
                        if extraction.get("organ") in ["heart", "lung", "liver", "thyroid"]:
                            # Organ is already in English, no mapping needed
                            extraction["original_organ"] = extraction["organ"]
                        current_extractions.append(extraction)
                        results.append(extraction)
                    
                    # 立即保存当前report的结果
                    if current_extractions:
                        self.save_single_report(entry['case_id'], current_extractions)
                        logger.info(f"✅ 已保存 {entry['case_id']}: {len(current_extractions)} 条提取结果")
                else:
                    logger.warning(f"提取失败 {entry['case_id']}: {extraction_result.get('error', '未知错误')}")
                
                # 添加延迟以避免API限制
                if (i + 1) % 10 == 0:
                    import time
                    time.sleep(5)  # 增加延迟到5秒
                    
            except Exception as e:
                logger.error(f"处理文件 {entry['case_id']} 时出错: {str(e)}")
                continue
        
        logger.info(f"提取完成，共获得 {len(results)} 条医学信息")
        return results
    
    def convert_to_target_format(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换为目标格式（匹配rag_corpus_0.json）
        
        Args:
            extractions: 提取结果列表
            
        Returns:
            转换后的结果列表
        """
        logger.info("转换为目标格式...")
        
        converted_results = []
        for extraction in extractions:
            # 确保所有必需字段都存在
            converted_item = {
                "case_id": extraction.get("case_id", ""),
                "disease_symptom": extraction.get("disease_symptom", ""),
                "organ": extraction.get("organ", ""),
                "specific_part": extraction.get("specific_part", ""),
                "confidence": extraction.get("confidence", "中"),
                "evidence": extraction.get("evidence", ""),
                "original_organ": extraction.get("original_organ", "")
            }
            
            # 过滤掉无效条目
            if (converted_item["disease_symptom"] and 
                converted_item["organ"] and 
                converted_item["evidence"]):
                converted_results.append(converted_item)
        
        logger.info(f"转换完成，有效条目数: {len(converted_results)}")
        return converted_results
    
    def save_single_report(self, case_id: str, extractions: List[Dict[str, Any]]):
        """
        保存单个report的提取结果
        
        Args:
            case_id: 病例ID
            extractions: 提取结果列表
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(self.output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名：report_i_QA.json
        filename = f"{case_id}_QA.json"
        file_path = os.path.join(output_dir, filename)
        
        # 保存为JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(extractions, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存单个report结果: {file_path}")

    def save_results(self, results: List[Dict[str, Any]]):
        """
        保存汇总结果到文件
        
        Args:
            results: 结果列表
        """
        logger.info(f"保存汇总结果到: {self.output_path}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # 保存为JSON文件
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"汇总结果已保存，共 {len(results)} 条记录")
    
    def process(self):
        """执行完整的处理流程"""
        logger.info("开始处理数据集...")
        
        # 1. 加载数据集文件
        entries = self.load_dataset_files()
        
        if not entries:
            logger.error("没有找到可处理的数据文件")
            return
        
        # 2. 提取医学信息
        extractions = self.extract_medical_info(entries)
        
        if not extractions:
            logger.error("没有提取到有效的医学信息")
            return
        
        # 3. 转换为目标格式
        converted_results = self.convert_to_target_format(extractions)
        
        # 4. 保存结果
        self.save_results(converted_results)
        
        logger.info("数据集处理完成！")

def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="处理数据集并提取医学信息")
    parser.add_argument("--k", type=int, default=1000, help="处理前k个文件 (默认: 1000)")
    parser.add_argument("--dataset", type=str, default="dataset", help="数据集路径 (默认: dataset)")
    parser.add_argument("--output", type=str, default="knowledge_distillation/results/output_1000/rag_corpus_1000.json", 
                       help="输出文件路径 (默认: knowledge_distillation/results/output_1000/rag_corpus_1000.json)")
    
    args = parser.parse_args()
    
    # 创建处理器并执行
    processor = DatasetProcessor(
        dataset_path=args.dataset,
        output_path=args.output,
        k=args.k
    )
    
    processor.process()

if __name__ == "__main__":
    main() 