#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
症状描述提取器
专门用于从医学报告中提取和标准化症状描述，用于测试集构建
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

# 复用原有的LLM基础设施
import sys
import os
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor

class SymptomExtractor:
    """症状描述提取器类"""
    
    def __init__(self, model: str, api_key: str, base_url: str, 
                 max_retries: int = 3, retry_delay: float = 2.0):
        """
        初始化症状提取器
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间
        """
        self.llm_extractor = LLMExtractor(
            model=model,
            api_key=api_key,
            base_url=base_url
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def extract_symptoms_from_text(self, text: str, prompt: str) -> List[Dict[str, Any]]:
        """
        从医学文本中提取症状描述
        
        Args:
            text: 医学报告文本
            prompt: 提示词模板
            
        Returns:
            提取的症状描述列表
        """
        try:
            # 构建完整的提示词
            full_prompt = prompt + "\n\n" + text + "\n\n请开始分析："
            
            # 调用LLM进行提取
            for attempt in range(self.max_retries):
                try:
                    result = self.llm_extractor.call_api(full_prompt)
                    
                    if not result.get("success"):
                        logger.warning(f"第 {attempt + 1} 次尝试：API调用失败 - {result.get('error', 'Unknown error')}")
                        continue
                    
                    response = result.get("response", "")
                    
                    if response and response.strip():
                        # 调试：打印原始响应
                        logger.debug(f"原始API响应: {response[:500]}...")
                        
                        # 解析JSON响应
                        extracted_symptoms = self._parse_symptom_response(response)
                        
                        if extracted_symptoms is not None:
                            logger.info(f"成功提取到 {len(extracted_symptoms)} 个症状描述")
                            return extracted_symptoms
                        else:
                            logger.warning(f"第 {attempt + 1} 次尝试：响应解析失败")
                            logger.debug(f"解析失败的响应: {response[:200]}...")
                            
                except Exception as e:
                    logger.error(f"第 {attempt + 1} 次尝试失败: {str(e)}")
                    
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            logger.error("所有提取尝试都失败了")
            return []
            
        except Exception as e:
            logger.error(f"症状提取过程中发生异常: {str(e)}")
            return []
    
    def _parse_symptom_response(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """
        解析LLM响应，提取症状描述信息
        
        Args:
            response: LLM的原始响应
            
        Returns:
            解析后的症状描述列表，解析失败时返回None
        """
        try:
            # 清理响应文本
            cleaned_response = self._clean_response_text(response)
            
            # 尝试解析JSON
            if cleaned_response.strip():
                parsed_data = json.loads(cleaned_response)
                
                # 验证解析结果
                if isinstance(parsed_data, list):
                    return self._validate_symptom_data(parsed_data)
                elif isinstance(parsed_data, dict) and "extracted_symptoms" in parsed_data:
                    # 处理批量处理格式
                    return self._validate_symptom_data(parsed_data.get("consolidated_symptoms", []))
                else:
                    logger.warning("响应格式不符合预期")
                    return None
            else:
                logger.warning("清理后的响应为空")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.debug(f"原始响应: {response[:500]}...")
            return None
        except Exception as e:
            logger.error(f"响应解析异常: {str(e)}")
            return None
    
    def _clean_response_text(self, text: str) -> str:
        """
        清理LLM响应文本，提取JSON部分
        
        Args:
            text: 原始响应文本
            
        Returns:
            清理后的JSON文本
        """
        try:
            # 移除可能的markdown代码块标记
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            # 查找JSON数组或对象的开始和结束
            start_idx = text.find('[')
            if start_idx == -1:
                start_idx = text.find('{')
            
            if start_idx != -1:
                # 从JSON开始位置截取
                text = text[start_idx:]
                
                # 查找对应的结束位置
                bracket_count = 0
                end_idx = -1
                
                for i, char in enumerate(text):
                    if char in '[{':
                        bracket_count += 1
                    elif char in ']}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
                
                if end_idx != -1:
                    text = text[:end_idx]
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"文本清理异常: {str(e)}")
            return text
    
    def _validate_symptom_data(self, symptom_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和清理症状描述数据
        
        Args:
            symptom_list: 原始症状描述列表
            
        Returns:
            验证后的症状描述列表
        """
        validated_symptoms = []
        
        for i, symptom in enumerate(symptom_list):
            try:
                if not isinstance(symptom, dict):
                    logger.warning(f"症状 {i}: 不是字典格式，跳过")
                    continue
                
                # 基本字段验证 - 支持多种可能的字段名
                symptom_desc_field = None
                original_text_field = None
                
                # 查找症状描述字段
                for field in ["symptom_description", "standardized_description", "disease_symptom"]:
                    if field in symptom and symptom[field]:
                        symptom_desc_field = field
                        break
                
                # 查找原文字段  
                for field in ["original_text", "evidence", "evidence_from_report"]:
                    if field in symptom and symptom[field]:
                        original_text_field = field
                        break
                
                if not symptom_desc_field:
                    logger.warning(f"症状 {i}: 缺少症状描述字段，跳过。可用字段: {list(symptom.keys())}")
                    continue
                
                # 检查描述是否为空
                symptom_desc = symptom.get(symptom_desc_field, "").strip()
                if not symptom_desc:
                    logger.warning(f"症状 {i}: 症状描述为空，跳过")
                    continue
                
                # 标准化字段
                validated_symptom = {
                    "symptom_description": symptom_desc,
                    "original_text": symptom.get(original_text_field, "").strip() if original_text_field else "",
                    "symptom_type": symptom.get("symptom_type", symptom.get("symptom_category", "unclassified")),
                    "body_system": symptom.get("body_system", "unspecified"),
                    "severity": symptom.get("severity", "unspecified"),
                    "context": symptom.get("context", ""),
                    "confidence_score": symptom.get("confidence_score", symptom.get("confidence", 5)),
                    "anatomical_location": symptom.get("anatomical_location", ""),
                    "clinical_significance": symptom.get("clinical_significance", ""),
                    "test_suitable": symptom.get("test_suitable", True)
                }
                
                # 处理症状特征
                if "symptom_characteristics" in symptom:
                    validated_symptom["symptom_characteristics"] = symptom["symptom_characteristics"]
                
                validated_symptoms.append(validated_symptom)
                
            except Exception as e:
                logger.error(f"验证症状 {i} 时发生异常: {str(e)}")
                continue
        
        logger.info(f"验证完成：{len(validated_symptoms)}/{len(symptom_list)} 个症状通过验证")
        return validated_symptoms
    
    def extract_symptoms_from_chunks(self, chunks: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        """
        从文档片段中批量提取症状描述
        
        Args:
            chunks: 文档片段列表
            prompt: 提示词模板
            
        Returns:
            所有提取的症状描述列表
        """
        all_symptoms = []
        
        for i, chunk in enumerate(chunks):
            try:
                chunk_text = chunk.get("content", "")
                chunk_name = chunk.get("section_name", f"chunk_{i}")
                
                logger.info(f"处理片段 {i+1}/{len(chunks)}: {chunk_name}")
                
                # 提取该片段的症状
                chunk_symptoms = self.extract_symptoms_from_text(chunk_text, prompt)
                
                # 为每个症状添加片段信息
                for symptom in chunk_symptoms:
                    symptom["source_chunk"] = chunk_name
                    symptom["chunk_index"] = i
                
                all_symptoms.extend(chunk_symptoms)
                
                # 避免API频率限制
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"处理片段 {i} 时发生异常: {str(e)}")
                continue
        
        # 去重处理
        deduplicated_symptoms = self._deduplicate_symptoms(all_symptoms)
        
        logger.info(f"片段处理完成：共提取 {len(all_symptoms)} 个症状，去重后 {len(deduplicated_symptoms)} 个")
        return deduplicated_symptoms
    
    def _deduplicate_symptoms(self, symptoms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对症状描述进行去重处理
        
        Args:
            symptoms: 原始症状列表
            
        Returns:
            去重后的症状列表
        """
        seen_descriptions = set()
        deduplicated = []
        
        for symptom in symptoms:
            description = symptom.get("symptom_description", "").strip().lower()
            
            if description and description not in seen_descriptions:
                seen_descriptions.add(description)
                deduplicated.append(symptom)
        
        return deduplicated 