#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理器
用于处理医学文本数据和提取结果
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

# 导入配置
import sys
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)
from configs.model_config import normalize_organ, is_allowed_organ, detect_specialty, is_allowed_specific_part

class DataProcessor:
    """数据处理器类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化数据处理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_text_length": 2048,
            "min_text_length": 50,
            "allowed_organs": ["heart", "lung", "liver", "thyroid"],
            "quality_threshold": 0.7,
            "enable_validation": True
        }
    
    def load_medical_texts(self, file_path: str) -> List[Dict[str, str]]:
        """
        加载医学文本数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            医学文本列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            texts = []
            for item in data:
                text = item.get("text", "")
                case_id = item.get("case_id", "")
                
                # 验证文本质量
                if self._validate_text(text):
                    # 检测专科类型
                    specialty = detect_specialty(text)
                    
                    texts.append({
                        "text": text,
                        "case_id": case_id,
                        "specialty": specialty
                    })
            
            logger.info(f"成功加载 {len(texts)} 条医学文本")
            return texts
            
        except Exception as e:
            logger.error(f"加载医学文本失败: {str(e)}")
            return []
    
    def _validate_text(self, text: str) -> bool:
        """验证文本质量"""
        if not text or not isinstance(text, str):
            return False
        
        # 长度检查
        if len(text) < self.config["min_text_length"]:
            return False
        
        if len(text) > self.config["max_text_length"]:
            # 截断过长的文本
            text = text[:self.config["max_text_length"]]
        
        # 基本内容检查
        if not any(keyword in text for keyword in ["症状", "疾病", "检查", "诊断", "治疗"]):
            return False
        
        return True
    
    def process_extraction_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理提取结果
        
        Args:
            results: 提取结果列表
            
        Returns:
            处理后的结果
        """
        processed_results = []
        
        for result in results:
            if not result.get("success", False):
                continue
            
            case_id = result.get("case_id", "")
            extractions = result.get("extractions", [])
            specialty = result.get("specialty", "general")
            
            # 处理每个提取结果
            processed_extractions = []
            for extraction in extractions:
                processed = self._process_single_extraction(extraction)
                if processed:
                    processed_extractions.append(processed)
            
            if processed_extractions:
                processed_results.append({
                    "case_id": case_id,
                    "specialty": specialty,
                    "extractions": processed_extractions,
                    "success": True
                })
        
        logger.info(f"处理完成，有效结果: {len(processed_results)}")
        return processed_results
    
    def _process_single_extraction(self, extraction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个提取结果"""
        try:
            # 基本字段验证
            required_fields = ["disease_symptom", "organ", "specific_part"]
            for field in required_fields:
                if not extraction.get(field):
                    return None
            
            # 标准化器官名称
            original_organ = extraction["organ"]
            normalized_organ = normalize_organ(original_organ)
            
            # 检查是否为允许的器官
            if not is_allowed_organ(normalized_organ):
                return None
            
            # 检查解剖部位是否属于该器官
            specific_part = extraction["specific_part"]
            if not is_allowed_specific_part(normalized_organ, specific_part):
                logger.warning(f"过滤掉不合规的解剖部位: Organ='{normalized_organ}', Part='{specific_part}'")
                return None
            
            # 构建处理后的结果
            processed = {
                "disease_symptom": extraction["disease_symptom"].strip(),
                "organ": normalized_organ,
                "specific_part": extraction["specific_part"].strip(),
                "confidence": extraction.get("confidence", "中"),
                "evidence": extraction.get("evidence", "").strip(),
                "original_organ": original_organ
            }
            
            # 质量检查
            if self.config["enable_validation"]:
                if not self._validate_extraction_quality(processed):
                    return None
            
            return processed
            
        except Exception as e:
            logger.error(f"处理单个提取结果异常: {str(e)}")
            return None
    
    def _validate_extraction_quality(self, extraction: Dict[str, Any]) -> bool:
        """验证提取结果质量"""
        # 症状描述质量
        symptom = extraction["disease_symptom"]
        if len(symptom) < 2 or len(symptom) > 100:
            return False
        
        # 部位描述质量
        part = extraction["specific_part"]
        if len(part) < 2 or len(part) > 50:
            return False
        
        # 置信度检查
        confidence = extraction["confidence"]
        if confidence not in ["高", "中", "低"]:
            return False
        
        return True
    
    def merge_multi_part_extractions(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并多部位提取结果
        
        Args:
            extractions: 提取结果列表
            
        Returns:
            合并后的结果
        """
        from collections import defaultdict
        
        # 按症状和器官分组
        grouped = defaultdict(list)
        for extraction in extractions:
            key = f"{extraction['disease_symptom']}|{extraction['organ']}"
            grouped[key].append(extraction)
        
        # 合并每组结果
        merged = []
        for group in grouped.values():
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged_item = self._merge_extraction_group(group)
                merged.append(merged_item)
        
        return merged
    
    def _merge_extraction_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并提取结果组"""
        # 使用第一个作为基础
        base = group[0].copy()
        
        # 收集所有部位
        parts = []
        evidences = []
        confidences = []
        
        for item in group:
            part = item.get("specific_part", "")
            if part and part not in parts:
                parts.append(part)
            
            evidence = item.get("evidence", "")
            if evidence and evidence not in evidences:
                evidences.append(evidence)
            
            confidence = item.get("confidence", "中")
            if confidence not in confidences:
                confidences.append(confidence)
        
        # 合并部位
        if len(parts) > 1:
            base["specific_part"] = "、".join(parts)
        elif len(parts) == 1:
            base["specific_part"] = parts[0]
        
        # 合并证据（取最长的）
        if evidences:
            base["evidence"] = max(evidences, key=len)
        
        # 取最高置信度
        if confidences:
            confidence_levels = {"高": 3, "中": 2, "低": 1}
            best_confidence = max(confidences, key=lambda x: confidence_levels.get(x, 0))
            base["confidence"] = best_confidence
        
        return base
    
    def convert_to_rag_format(self, processed_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换为RAG格式
        
        Args:
            processed_results: 处理后的结果
            
        Returns:
            RAG格式的语料
        """
        rag_corpus = []
        
        for result in processed_results:
            case_id = result["case_id"]
            extractions = result["extractions"]
            
            for extraction in extractions:
                rag_item = {
                    "case_id": case_id,
                    "disease_symptom": extraction["disease_symptom"],
                    "organ": extraction["organ"],
                    "specific_part": extraction["specific_part"],
                    "confidence": extraction["confidence"],
                    "evidence": extraction["evidence"],
                    "specialty": result["specialty"]
                }
                
                # 生成查询文本
                rag_item["query"] = self._generate_query_text(extraction)
                
                # 生成文档文本
                rag_item["document"] = self._generate_document_text(extraction)
                
                rag_corpus.append(rag_item)
        
        logger.info(f"转换为RAG格式完成，共 {len(rag_corpus)} 条记录")
        return rag_corpus
    
    def _generate_query_text(self, extraction: Dict[str, Any]) -> str:
        """生成查询文本"""
        symptom = extraction["disease_symptom"]
        organ = extraction["organ"]
        part = extraction["specific_part"]
        
        return f"{symptom} {organ} {part}"
    
    def _generate_document_text(self, extraction: Dict[str, Any]) -> str:
        """生成文档文本"""
        symptom = extraction["disease_symptom"]
        organ = extraction["organ"]
        part = extraction["specific_part"]
        evidence = extraction["evidence"]
        
        if evidence:
            return f"症状：{symptom}，涉及器官：{organ}，具体部位：{part}。证据：{evidence}"
        else:
            return f"症状：{symptom}，涉及器官：{organ}，具体部位：{part}。"
    
    def save_results(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """保存结果到文件"""
        try:
            # 确保输出目录存在
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到: {output_file}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {str(e)}")
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析结果统计"""
        stats = {
            "total_cases": len(results),
            "total_extractions": 0,
            "organ_distribution": {},
            "specialty_distribution": {},
            "confidence_distribution": {},
            "success_rate": 0
        }
        
        successful_cases = 0
        
        for result in results:
            if result.get("success", False):
                successful_cases += 1
                extractions = result.get("extractions", [])
                stats["total_extractions"] += len(extractions)
                
                specialty = result.get("specialty", "unknown")
                stats["specialty_distribution"][specialty] = stats["specialty_distribution"].get(specialty, 0) + 1
                
                for extraction in extractions:
                    organ = extraction.get("organ", "unknown")
                    stats["organ_distribution"][organ] = stats["organ_distribution"].get(organ, 0) + 1
                    
                    confidence = extraction.get("confidence", "unknown")
                    stats["confidence_distribution"][confidence] = stats["confidence_distribution"].get(confidence, 0) + 1
        
        if stats["total_cases"] > 0:
            stats["success_rate"] = successful_cases / stats["total_cases"]
        
        return stats

def create_processor(config: Dict[str, Any] = None) -> DataProcessor:
    """创建数据处理器实例"""
    return DataProcessor(config=config)

if __name__ == "__main__":
    # 测试数据处理器
    print("数据处理器测试")
    print("=" * 40)
    
    # 创建处理器
    processor = create_processor()
    
    # 测试文本验证
    test_texts = [
        "患者主诉胸痛，心电图异常",
        "正常体检",
        "患者出现胸痛、心悸等症状，心电图显示ST段抬高，考虑急性心肌梗死"
    ]
    
    for text in test_texts:
        is_valid = processor._validate_text(text)
        print(f"文本: {text[:30]}... -> 有效: {is_valid}")
    
    # 测试提取结果处理
    test_extraction = {
        "disease_symptom": "胸痛",
                    "organ": "heart",
        "specific_part": "左心室",
        "confidence": "高",
        "evidence": "心电图显示ST段抬高"
    }
    
    processed = processor._process_single_extraction(test_extraction)
    print(f"\n处理结果: {processed}") 